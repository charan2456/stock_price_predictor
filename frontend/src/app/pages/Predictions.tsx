import { useState, useEffect } from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { fetchLatestPredictions, fetchForecast, calculateReturns } from "../services/api";
import { TrendingUp, TrendingDown, Clock, DollarSign, Target, ChevronDown, Calculator, Shield, BarChart3, AlertTriangle, Activity, ArrowRight, IndianRupee } from "lucide-react";

const HORIZONS = ['1h', '4h', '1d', '7d'] as const;
const HORIZON_LABELS: Record<string, string> = { '1h': '1 Hour', '4h': '4 Hours', '1d': '1 Day', '7d': '7 Days' };

// Indian market: Mon–Fri 9:15 AM – 3:30 PM IST. Calculate trading days.
function tradingDaysAhead(days: number): string {
  const tradingDays: string[] = [];
  const now = new Date();
  let d = new Date(now);
  for (let i = 0; tradingDays.length < days && i < days * 3; i++) {
    d.setDate(d.getDate() + 1);
    const dow = d.getDay();
    if (dow !== 0 && dow !== 6) {
      tradingDays.push(d.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' }));
    }
  }
  return tradingDays.join(', ');
}

// Fallback stocks (S&P 100 subset)
const FALLBACK_STOCKS = [
  { ticker: 'AAPL', current_price: 178.42, predicted_return: 0.0034, direction: 'BULLISH', confidence: 0.87, hourly_change: 0.34, sentiment_score: 0.68, rsi: 62.4, volume: 52340000, model_agreement: true, predicted_price_1h: 179.03, predicted_price_4h: 180.12, predicted_price_1d: 182.40, predicted_price_1w: 188.50, lstm_prediction: 0.0038, xgboost_prediction: 0.0031, confidence_breakdown: { model_agreement: 92, sentiment_aligned: 85, technical_confirmed: 78, historical_accuracy: 71 } },
  { ticker: 'MSFT', current_price: 412.83, predicted_return: -0.0012, direction: 'BEARISH', confidence: 0.72, hourly_change: -0.12, sentiment_score: 0.43, rsi: 58.7, volume: 28100000, model_agreement: true, predicted_price_1h: 412.34, predicted_price_4h: 410.85, predicted_price_1d: 409.50, predicted_price_1w: 405.20, lstm_prediction: -0.0015, xgboost_prediction: -0.0010, confidence_breakdown: { model_agreement: 78, sentiment_aligned: 60, technical_confirmed: 65, historical_accuracy: 68 } },
  { ticker: 'GOOGL', current_price: 142.56, predicted_return: 0.0021, direction: 'BULLISH', confidence: 0.79, hourly_change: 0.21, sentiment_score: 0.55, rsi: 64.2, volume: 31500000, model_agreement: true, predicted_price_1h: 142.86, predicted_price_4h: 143.76, predicted_price_1d: 144.95, predicted_price_1w: 147.80, lstm_prediction: 0.0025, xgboost_prediction: 0.0018, confidence_breakdown: { model_agreement: 82, sentiment_aligned: 72, technical_confirmed: 74, historical_accuracy: 70 } },
  { ticker: 'AMZN', current_price: 183.27, predicted_return: -0.0028, direction: 'BEARISH', confidence: 0.65, hourly_change: -0.45, sentiment_score: -0.32, rsi: 42.8, volume: 45800000, model_agreement: false, predicted_price_1h: 182.76, predicted_price_4h: 181.22, predicted_price_1d: 179.20, predicted_price_1w: 174.50, lstm_prediction: -0.0022, xgboost_prediction: -0.0035, confidence_breakdown: { model_agreement: 40, sentiment_aligned: 55, technical_confirmed: 62, historical_accuracy: 65 } },
  { ticker: 'TSLA', current_price: 196.84, predicted_return: 0.0055, direction: 'BULLISH', confidence: 0.91, hourly_change: 1.15, sentiment_score: 0.81, rsi: 71.3, volume: 98200000, model_agreement: true, predicted_price_1h: 197.92, predicted_price_4h: 200.18, predicted_price_1d: 204.20, predicted_price_1w: 213.60, lstm_prediction: 0.0060, xgboost_prediction: 0.0048, confidence_breakdown: { model_agreement: 95, sentiment_aligned: 90, technical_confirmed: 82, historical_accuracy: 74 } },
  { ticker: 'NVDA', current_price: 875.30, predicted_return: 0.0042, direction: 'BULLISH', confidence: 0.88, hourly_change: 0.52, sentiment_score: 0.72, rsi: 66.1, volume: 41200000, model_agreement: true, predicted_price_1h: 878.98, predicted_price_4h: 890.14, predicted_price_1d: 910.50, predicted_price_1w: 945.20, lstm_prediction: 0.0045, xgboost_prediction: 0.0038, confidence_breakdown: { model_agreement: 88, sentiment_aligned: 80, technical_confirmed: 76, historical_accuracy: 72 } },
  { ticker: 'META', current_price: 502.10, predicted_return: -0.0018, direction: 'BEARISH', confidence: 0.62, hourly_change: -0.28, sentiment_score: -0.15, rsi: 48.3, volume: 22100000, model_agreement: false, predicted_price_1h: 501.20, predicted_price_4h: 498.50, predicted_price_1d: 495.10, predicted_price_1w: 488.30, lstm_prediction: -0.0012, xgboost_prediction: -0.0025, confidence_breakdown: { model_agreement: 42, sentiment_aligned: 48, technical_confirmed: 55, historical_accuracy: 63 } },
  { ticker: 'JPM', current_price: 198.45, predicted_return: 0.0015, direction: 'BULLISH', confidence: 0.74, hourly_change: 0.15, sentiment_score: 0.38, rsi: 55.9, volume: 12800000, model_agreement: true, predicted_price_1h: 198.75, predicted_price_4h: 199.64, predicted_price_1d: 201.20, predicted_price_1w: 204.80, lstm_prediction: 0.0018, xgboost_prediction: 0.0012, confidence_breakdown: { model_agreement: 80, sentiment_aligned: 65, technical_confirmed: 68, historical_accuracy: 69 } },
];

function generateTrajectory(currentPrice: number, targetPrice: number, upper: number, lower: number, horizon: string) {
  const points = [];
  const steps = horizon === '1h' ? 12 : horizon === '4h' ? 16 : horizon === '1d' ? 8 : 7;
  const now = new Date();
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const price = currentPrice + (targetPrice - currentPrice) * t + (Math.random() - 0.5) * (upper - lower) * 0.08;
    const up = currentPrice + (upper - currentPrice) * t;
    const lo = currentPrice + (lower - currentPrice) * t;
    const time = new Date(now);
    if (horizon === '1h') { time.setMinutes(time.getMinutes() + i * 5); }
    else if (horizon === '4h') { time.setMinutes(time.getMinutes() + i * 15); }
    else if (horizon === '1d') { time.setHours(time.getHours() + i); }
    else { time.setDate(time.getDate() + i); }
    const label = horizon === '7d'
      ? time.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric' })
      : time.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false });
    points.push({ time: label, predicted: +price.toFixed(2), upper: +up.toFixed(2), lower: +lo.toFixed(2) });
  }
  return points;
}

export function Predictions() {
  const [stocks, setStocks] = useState<any[]>(FALLBACK_STOCKS);
  const [selectedTicker, setSelectedTicker] = useState('AAPL');
  const [horizon, setHorizon] = useState<string>('1d');
  const [calcAmount, setCalcAmount] = useState(100000);
  const [calcResult, setCalcResult] = useState<any>(null);
  const [showCalc, setShowCalc] = useState(false);

  useEffect(() => {
    async function load() {
      const data = await fetchLatestPredictions();
      if (data?.predictions?.length) setStocks(data.predictions);
    }
    load();
  }, []);

  const selected = stocks.find(s => s.ticker === selectedTicker) || stocks[0];

  // Get predicted price for selected horizon
  const getPredictedPrice = (stock: any, h: string): number => {
    if (h === '1h') return stock.predicted_price_1h || stock.current_price * (1 + (stock.predicted_return || 0));
    if (h === '4h') return stock.predicted_price_4h || stock.current_price * (1 + (stock.predicted_return || 0) * 4);
    if (h === '1d') return stock.predicted_price_1d || stock.current_price * (1 + (stock.predicted_return || 0) * 8);
    return stock.predicted_price_1w || stock.current_price * (1 + (stock.predicted_return || 0) * 40);
  };

  const getReturnPct = (stock: any, h: string): number => {
    const predicted = getPredictedPrice(stock, h);
    return ((predicted - stock.current_price) / stock.current_price) * 100;
  };

  const getConfidenceBand = (stock: any, h: string): { upper: number; lower: number } => {
    const multiplier = h === '1h' ? 0.005 : h === '4h' ? 0.015 : h === '1d' ? 0.03 : 0.08;
    return {
      upper: stock.current_price * (1 + multiplier),
      lower: stock.current_price * (1 - multiplier),
    };
  };

  const predictedPrice = getPredictedPrice(selected, horizon);
  const returnPct = getReturnPct(selected, horizon);
  const isUp = returnPct > 0;
  const band = getConfidenceBand(selected, horizon);
  const trajectory = generateTrajectory(selected.current_price, predictedPrice, band.upper, band.lower, horizon);

  const confidence = Math.round((selected.confidence || 0) * 100);
  const breakdown = selected.confidence_breakdown || { model_agreement: 80, sentiment_aligned: 70, technical_confirmed: 65, historical_accuracy: 68 };

  // Calculator
  const handleCalculate = () => {
    const ret = returnPct / 100;
    const expectedValue = calcAmount * (1 + ret);
    const bestValue = calcAmount * (1 + ret * 1.5);
    const worstValue = calcAmount * (1 + ret * -0.5);
    setCalcResult({
      horizon: HORIZON_LABELS[horizon],
      trading_days: horizon === '7d' ? '5 trading days (Mon–Fri)' : horizon === '1d' ? '1 trading day' : horizon,
      expected: { value: expectedValue, profit: expectedValue - calcAmount, return_pct: ret * 100 },
      best_case: { value: bestValue, profit: bestValue - calcAmount, return_pct: ret * 150 },
      worst_case: { value: worstValue, profit: worstValue - calcAmount, return_pct: ret * -50 },
      confidence,
    });
    setShowCalc(true);
  };

  return (
    <div className="space-y-6">
      {/* Ticker selector row */}
      <div className="flex items-center gap-3 overflow-x-auto pb-2 scrollbar-thin">
        {stocks.map((s) => {
          const isActive = s.ticker === selectedTicker;
          const up = (s.predicted_return || 0) > 0;
          return (
            <button key={s.ticker} onClick={() => setSelectedTicker(s.ticker)}
              className={`shrink-0 px-4 py-3 rounded-xl border transition-all ${isActive ? 'bg-[#3b82f6]/10 border-[#3b82f6]/30 ring-1 ring-[#3b82f6]/20' : 'bg-white/[0.03] border-white/5 hover:bg-white/[0.06]'}`}>
              <div className="text-sm font-semibold text-white">{s.ticker}</div>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-gray-400">${s.current_price?.toFixed(2)}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${up ? 'bg-[#10b981]/15 text-[#10b981]' : 'bg-[#ef4444]/15 text-[#ef4444]'}`}>
                  {s.direction}
                </span>
              </div>
            </button>
          );
        })}
      </div>

      {/* Horizon tabs + Current Price Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-white">{selectedTicker} — Price Forecast</h2>
          <p className="text-sm text-gray-500 mt-1">
            Indian Market: Mon–Fri • 9:15 AM – 3:30 PM IST
            {horizon === '7d' && <span className="text-[#3b82f6] ml-2">• Next 5 trading days: {tradingDaysAhead(5)}</span>}
          </p>
        </div>
        <div className="flex items-center gap-1 bg-white/5 p-1 rounded-lg border border-white/10">
          {HORIZONS.map((h) => (
            <button key={h} onClick={() => { setHorizon(h); setShowCalc(false); }}
              className={`px-4 py-2 rounded-md text-sm transition-all ${horizon === h ? 'bg-[#3b82f6] text-white' : 'text-gray-400 hover:text-white'}`}>
              {HORIZON_LABELS[h]}
            </button>
          ))}
        </div>
      </div>

      {/* Forecast cards for all horizons */}
      <div className="grid grid-cols-4 gap-4">
        {HORIZONS.map((h) => {
          const price = getPredictedPrice(selected, h);
          const ret = getReturnPct(selected, h);
          const up = ret > 0;
          const b = getConfidenceBand(selected, h);
          return (
            <button key={h} onClick={() => { setHorizon(h); setShowCalc(false); }}
              className={`p-5 rounded-xl text-left transition-all border ${horizon === h ? 'bg-[#3b82f6]/10 border-[#3b82f6]/40 ring-1 ring-[#3b82f6]/30' : 'bg-white/[0.03] border-white/5 hover:bg-white/[0.06]'}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-400">{HORIZON_LABELS[h]}</span>
                {up ? <TrendingUp className="w-4 h-4 text-[#10b981]" /> : <TrendingDown className="w-4 h-4 text-[#ef4444]" />}
              </div>
              <div className={`text-2xl font-semibold ${up ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>${price.toFixed(2)}</div>
              <div className={`text-sm mt-1 ${up ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>{up ? '+' : ''}{ret.toFixed(3)}%</div>
              <div className="text-[10px] text-gray-500 mt-2">Range: ${b.lower.toFixed(2)} — ${b.upper.toFixed(2)}</div>
              {h === '7d' && <div className="text-[10px] text-[#3b82f6] mt-1">5 trading days</div>}
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Chart with confidence band */}
        <div className="col-span-2 p-6 bg-white/[0.03] border border-white/5 rounded-xl">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-white">{selectedTicker} — {HORIZON_LABELS[horizon]} Trajectory</h3>
              <p className="text-xs text-gray-500">Shaded area = confidence band • Line = predicted price path</p>
            </div>
            <div className="text-right">
              <div className="text-xl font-semibold text-white">${selected.current_price?.toFixed(2)} → ${predictedPrice.toFixed(2)}</div>
              <div className={`text-sm ${isUp ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>{isUp ? '+' : ''}{returnPct.toFixed(3)}%</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={380}>
            <AreaChart data={trajectory}>
              <defs>
                <linearGradient id="bandGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={isUp ? '#10b981' : '#ef4444'} stopOpacity={0.12} />
                  <stop offset="100%" stopColor={isUp ? '#10b981' : '#ef4444'} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="time" stroke="#6b7280" tick={{ fill: '#6b7280', fontSize: 10 }} interval={Math.max(1, Math.floor(trajectory.length / 7))} />
              <YAxis stroke="#6b7280" tick={{ fill: '#6b7280', fontSize: 12 }} domain={['dataMin - 1', 'dataMax + 1']} tickFormatter={(v) => `$${v.toFixed(0)}`} />
              <Tooltip contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(71, 85, 105, 0.3)', borderRadius: '8px', color: '#e2e8f0' }} />
              <Area type="monotone" dataKey="upper" stroke="transparent" fill="url(#bandGrad)" />
              <Area type="monotone" dataKey="lower" stroke="transparent" fill="transparent" />
              <Area type="monotone" dataKey="predicted" stroke={isUp ? '#10b981' : '#ef4444'} strokeWidth={2.5} fill="transparent" dot={false} name="Predicted Price" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Right panel: confidence + calculator */}
        <div className="space-y-5">
          {/* Confidence breakdown */}
          <div className="p-5 bg-white/[0.03] border border-white/5 rounded-xl">
            <h3 className="text-base font-semibold text-white mb-3">Confidence Breakdown</h3>
            <div className="space-y-3">
              {[
                { label: 'Model Agreement', value: breakdown.model_agreement || 0, icon: Shield, desc: selected.model_agreement ? 'LSTM + XGBoost agree' : 'Models disagree' },
                { label: 'Sentiment Aligned', value: breakdown.sentiment_aligned || 0, icon: Activity, desc: 'News + Reddit match prediction' },
                { label: 'Technical Confirmed', value: breakdown.technical_confirmed || 0, icon: BarChart3, desc: 'RSI + MACD confirm' },
                { label: 'Historical Accuracy', value: breakdown.historical_accuracy || 0, icon: Target, desc: 'Past accuracy on similar setups' },
              ].map((item) => {
                const Icon = item.icon;
                const color = item.value >= 80 ? '#10b981' : item.value >= 50 ? '#f59e0b' : '#ef4444';
                return (
                  <div key={item.label}>
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <Icon className="w-3.5 h-3.5" style={{ color }} />
                        <span className="text-xs text-white">{item.label}</span>
                      </div>
                      <span className="text-xs font-semibold" style={{ color }}>{item.value}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${item.value}%`, backgroundColor: color }} />
                    </div>
                    <div className="text-[10px] text-gray-600 mt-0.5">{item.desc}</div>
                  </div>
                );
              })}
            </div>
            <div className="mt-3 pt-3 border-t border-white/5 flex items-center justify-between">
              <span className="text-sm text-gray-400">Overall</span>
              <span className={`text-lg font-bold ${confidence >= 80 ? 'text-[#10b981]' : confidence >= 50 ? 'text-[#f59e0b]' : 'text-[#ef4444]'}`}>{confidence}%</span>
            </div>
          </div>

          {/* Model signals */}
          <div className="p-5 bg-white/[0.03] border border-white/5 rounded-xl">
            <h3 className="text-base font-semibold text-white mb-3">Model Signals</h3>
            <div className="space-y-2">
              <div className="flex items-center justify-between p-3 bg-white/[0.03] rounded-lg">
                <span className="text-xs text-gray-400">LSTM (40% weight)</span>
                <span className={`text-xs font-semibold ${(selected.lstm_prediction || 0) > 0 ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>
                  {(selected.lstm_prediction || 0) > 0 ? '+' : ''}{((selected.lstm_prediction || 0) * 100).toFixed(3)}%
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-white/[0.03] rounded-lg">
                <span className="text-xs text-gray-400">XGBoost (60% weight)</span>
                <span className={`text-xs font-semibold ${(selected.xgboost_prediction || 0) > 0 ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>
                  {(selected.xgboost_prediction || 0) > 0 ? '+' : ''}{((selected.xgboost_prediction || 0) * 100).toFixed(3)}%
                </span>
              </div>
              <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs ${selected.model_agreement ? 'bg-[#10b981]/10 text-[#10b981]' : 'bg-[#f59e0b]/10 text-[#f59e0b]'}`}>
                {selected.model_agreement ? <Shield className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
                {selected.model_agreement ? 'Models agree — stronger signal' : 'Models disagree — weaker signal'}
              </div>
            </div>
          </div>

          {/* Returns Calculator */}
          <div className="p-5 bg-white/[0.03] border border-white/5 rounded-xl">
            <h3 className="text-base font-semibold text-white mb-3 flex items-center gap-2">
              <Calculator className="w-4 h-4 text-[#3b82f6]" /> Returns Calculator
            </h3>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] text-gray-500 mb-1 block">Investment Amount (₹)</label>
                <div className="relative">
                  <IndianRupee className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500" />
                  <input type="number" value={calcAmount} onChange={(e) => { setCalcAmount(Number(e.target.value)); setShowCalc(false); }}
                    className="w-full pl-9 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-[#3b82f6]" />
                </div>
              </div>
              <div className="p-3 bg-white/[0.03] rounded-lg">
                <div className="text-[10px] text-gray-500">Selected Horizon</div>
                <div className="text-sm text-white font-medium">{HORIZON_LABELS[horizon]}{horizon === '7d' ? ' (5 trading days, Mon–Fri)' : ''}</div>
              </div>
              <button onClick={handleCalculate}
                className="w-full py-2.5 bg-[#3b82f6] hover:bg-[#2563eb] text-white rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2">
                <DollarSign className="w-4 h-4" /> Calculate for {selectedTicker}
              </button>
              {showCalc && calcResult && (
                <div className="space-y-2 pt-3 border-t border-white/5">
                  <div className="text-[10px] text-gray-500">{calcResult.trading_days}</div>
                  <div className="p-3 bg-[#10b981]/10 rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-gray-400">Expected Return</span>
                      <span className="text-[10px] text-gray-500">{confidence}% confidence</span>
                    </div>
                    <div className={`text-lg font-semibold ${calcResult.expected.profit >= 0 ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>
                      {calcResult.expected.profit >= 0 ? '+' : ''}₹{Math.abs(calcResult.expected.profit).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                    </div>
                    <div className="text-[10px] text-gray-400">
                      ₹{calcAmount.toLocaleString('en-IN')} → ₹{calcResult.expected.value.toLocaleString('en-IN', { maximumFractionDigits: 2 })} ({calcResult.expected.return_pct >= 0 ? '+' : ''}{calcResult.expected.return_pct.toFixed(3)}%)
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="p-2.5 bg-white/[0.03] rounded-lg">
                      <div className="text-[10px] text-gray-500">Best Case</div>
                      <div className="text-sm font-semibold text-[#10b981]">+₹{Math.abs(calcResult.best_case.profit).toLocaleString('en-IN', { maximumFractionDigits: 2 })}</div>
                    </div>
                    <div className="p-2.5 bg-white/[0.03] rounded-lg">
                      <div className="text-[10px] text-gray-500">Worst Case</div>
                      <div className="text-sm font-semibold text-[#ef4444]">{calcResult.worst_case.profit >= 0 ? '+' : '-'}₹{Math.abs(calcResult.worst_case.profit).toLocaleString('en-IN', { maximumFractionDigits: 2 })}</div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Full Predictions Table */}
      <div className="bg-white/[0.03] border border-white/5 rounded-xl overflow-hidden">
        <div className="p-5 border-b border-white/5">
          <h3 className="text-lg font-semibold text-white">All Stock Predictions — {HORIZON_LABELS[horizon]} Outlook</h3>
          <p className="text-xs text-gray-500 mt-1">
            {horizon === '7d' ? '5 trading days (excluding Sat–Sun) • Indian market hours' : `${HORIZON_LABELS[horizon]} ahead`} • Click any row to view forecast
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-white/[0.03]">
              <tr>
                <th className="px-5 py-3 text-left text-xs font-medium text-gray-400">Stock</th>
                <th className="px-5 py-3 text-right text-xs font-medium text-gray-400">Current</th>
                <th className="px-5 py-3 text-right text-xs font-medium text-gray-400">Predicted ({HORIZON_LABELS[horizon]})</th>
                <th className="px-5 py-3 text-right text-xs font-medium text-gray-400">Return</th>
                <th className="px-5 py-3 text-center text-xs font-medium text-gray-400">Signal</th>
                <th className="px-5 py-3 text-center text-xs font-medium text-gray-400">Confidence</th>
                <th className="px-5 py-3 text-right text-xs font-medium text-gray-400">Sentiment</th>
                <th className="px-5 py-3 text-right text-xs font-medium text-gray-400">RSI</th>
                <th className="px-5 py-3 text-center text-xs font-medium text-gray-400">Model</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {stocks.map((s) => {
                const price = getPredictedPrice(s, horizon);
                const ret = getReturnPct(s, horizon);
                const up = ret > 0;
                return (
                  <tr key={s.ticker} onClick={() => setSelectedTicker(s.ticker)}
                    className={`cursor-pointer transition-colors ${s.ticker === selectedTicker ? 'bg-[#3b82f6]/5' : 'hover:bg-white/[0.03]'}`}>
                    <td className="px-5 py-3">
                      <span className="font-semibold text-white">{s.ticker}</span>
                    </td>
                    <td className="px-5 py-3 text-right text-sm text-gray-300">${s.current_price?.toFixed(2)}</td>
                    <td className="px-5 py-3 text-right">
                      <span className={`text-sm font-semibold ${up ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>${price.toFixed(2)}</span>
                    </td>
                    <td className="px-5 py-3 text-right">
                      <span className={`text-sm ${up ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>{up ? '+' : ''}{ret.toFixed(3)}%</span>
                    </td>
                    <td className="px-5 py-3 text-center">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${up ? 'bg-[#10b981]/15 text-[#10b981]' : 'bg-[#ef4444]/15 text-[#ef4444]'}`}>
                        {up ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                        {s.direction}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-center">
                      <span className={`text-sm font-medium ${(s.confidence || 0) >= 0.8 ? 'text-[#10b981]' : (s.confidence || 0) >= 0.5 ? 'text-[#f59e0b]' : 'text-[#ef4444]'}`}>
                        {Math.round((s.confidence || 0) * 100)}%
                      </span>
                    </td>
                    <td className="px-5 py-3 text-right">
                      <span className={`text-sm ${(s.sentiment_score || 0) > 0 ? 'text-[#10b981]' : (s.sentiment_score || 0) < 0 ? 'text-[#ef4444]' : 'text-gray-400'}`}>
                        {(s.sentiment_score || 0).toFixed(2)}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-right text-sm text-gray-300">{(s.rsi || 50).toFixed(1)}</td>
                    <td className="px-5 py-3 text-center">
                      <span className={`text-[10px] ${s.model_agreement ? 'text-[#10b981]' : 'text-[#f59e0b]'}`}>
                        {s.model_agreement ? '✅ Agree' : '⚠️ Disagree'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
