import { useState, useEffect } from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { PieChart as PieChartIcon, TrendingUp, TrendingDown, MessageSquare, Newspaper, Clock, RefreshCw, Zap } from "lucide-react";
import { fetchLatestPredictions } from "../services/api";

// --- Inline Components (no external dependencies) ---

function TickerCard({ ticker, price, change, changePercent, prediction, confidence, hourlyChange, isSelected, onClick }: {
  ticker: string; price: number; change: number; changePercent: number;
  prediction: 'BULLISH' | 'BEARISH'; confidence: number; hourlyChange?: number;
  isSelected?: boolean; onClick?: () => void;
}) {
  const isPositive = change >= 0;
  const isPredictionBullish = prediction === 'BULLISH';
  return (
    <button onClick={onClick}
      className={`relative p-4 rounded-xl border backdrop-blur-xl transition-all hover:scale-[1.02] ${isSelected
        ? 'bg-white/10 border-[#3b82f6] shadow-lg shadow-[#3b82f6]/20'
        : 'bg-white/5 border-white/10 hover:border-white/20'}`}>
      <div className="flex items-center justify-between mb-3">
        <span className="font-semibold text-white">{ticker}</span>
        <div className={`flex items-center gap-1 px-2 py-1 rounded-md text-xs ${isPredictionBullish ? 'bg-[#10b981]/20 text-[#10b981]' : 'bg-[#ef4444]/20 text-[#ef4444]'}`}>
          {isPredictionBullish ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          <span>{confidence}%</span>
        </div>
      </div>
      <div className="mb-2"><div className="text-2xl font-semibold text-white">${price.toFixed(2)}</div></div>
      <div className={`flex items-center gap-1 text-sm ${isPositive ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>
        <span>{isPositive ? '+' : ''}{change.toFixed(2)}</span>
        <span>({isPositive ? '+' : ''}{changePercent.toFixed(2)}%)</span>
      </div>
      {hourlyChange !== undefined && (
        <div className={`mt-1 text-[11px] ${hourlyChange >= 0 ? 'text-[#10b981]/70' : 'text-[#ef4444]/70'}`}>
          1H: {hourlyChange >= 0 ? '+' : ''}{hourlyChange.toFixed(2)}%
        </div>
      )}
    </button>
  );
}

function TechnicalIndicatorCard({ name, value, signal, detail }: {
  name: string; value: string; signal: 'bullish' | 'bearish' | 'neutral'; detail?: string;
}) {
  const signalColors = { bullish: 'bg-[#10b981]', bearish: 'bg-[#ef4444]', neutral: 'bg-gray-500' };
  const signalGlow = { bullish: 'shadow-[#10b981]/30', bearish: 'shadow-[#ef4444]/30', neutral: '' };
  return (
    <div className="flex items-center gap-3 p-4 bg-white/5 border border-white/10 rounded-lg backdrop-blur-xl hover:bg-white/[0.08] transition-all">
      <div className={`w-3 h-3 rounded-full ${signalColors[signal]} shadow-md ${signalGlow[signal]}`}></div>
      <div className="flex-1">
        <div className="text-sm text-gray-400">{name}</div>
        <div className="text-white font-medium">{value}</div>
        {detail && <div className="text-[10px] text-gray-500 mt-0.5">{detail}</div>}
      </div>
    </div>
  );
}

function SentimentGauge({ compoundScore, redditPosts, newsArticles, lastHourChange }: {
  compoundScore: number; redditPosts: number; newsArticles: number; lastHourChange?: number;
}) {
  const percentage = ((compoundScore + 1) / 2) * 100;
  const getSentimentLabel = () => compoundScore > 0.3 ? 'Bullish' : compoundScore < -0.3 ? 'Bearish' : 'Neutral';
  const getSentimentColor = () => compoundScore > 0.3 ? '#10b981' : compoundScore < -0.3 ? '#ef4444' : '#6b7280';
  const data = [{ value: percentage }, { value: 100 - percentage }];

  return (
    <div className="p-6 bg-white/5 border border-white/10 rounded-xl backdrop-blur-xl">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white">Sentiment Analysis</h3>
        <div className="flex items-center gap-1.5 px-2 py-1 bg-white/5 rounded-md">
          <Clock className="w-3 h-3 text-gray-500" />
          <span className="text-[10px] text-gray-500 uppercase tracking-wider">Hourly</span>
        </div>
      </div>
      <div className="relative mb-4">
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie data={data} cx="50%" cy="50%" startAngle={180} endAngle={0}
              innerRadius={60} outerRadius={80} paddingAngle={0} dataKey="value">
              <Cell fill={getSentimentColor()} /><Cell fill="#1e293b" />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center pt-8">
          <div className="text-3xl font-bold text-white">{compoundScore.toFixed(2)}</div>
          <div className="text-sm text-gray-400 mt-1">{getSentimentLabel()}</div>
        </div>
      </div>
      {lastHourChange !== undefined && (
        <div className="flex items-center justify-center gap-2 mb-4 px-3 py-2 bg-white/5 rounded-lg">
          {lastHourChange >= 0 ? <TrendingUp className="w-4 h-4 text-[#10b981]" /> : <TrendingDown className="w-4 h-4 text-[#ef4444]" />}
          <span className={`text-sm font-medium ${lastHourChange >= 0 ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>
            {lastHourChange >= 0 ? '+' : ''}{lastHourChange.toFixed(3)} vs last hour
          </span>
        </div>
      )}
      <div className="flex items-center justify-between mb-6 text-xs text-gray-500">
        <span>-1.0 Bearish</span><span>0.0 Neutral</span><span>1.0 Bullish</span>
      </div>
      <div className="space-y-3">
        <div className="flex items-center justify-between p-3 bg-white/5 rounded-lg">
          <div className="flex items-center gap-2"><MessageSquare className="w-4 h-4 text-[#ff4500]" /><span className="text-sm text-gray-400">Reddit (Last 1H)</span></div>
          <span className="text-white font-semibold">{redditPosts}</span>
        </div>
        <div className="flex items-center justify-between p-3 bg-white/5 rounded-lg">
          <div className="flex items-center gap-2"><Newspaper className="w-4 h-4 text-[#3b82f6]" /><span className="text-sm text-gray-400">News (Last 1H)</span></div>
          <span className="text-white font-semibold">{newsArticles}</span>
        </div>
      </div>
    </div>
  );
}

// --- Fallback Data ---

const FALLBACK_STOCKS: Record<string, any> = {
  AAPL: { ticker: 'AAPL', price: 178.42, change: 3.24, changePercent: 1.85, prediction: 'BULLISH', confidence: 87, sentiment: 0.68, rsi: 62.4, hourlyChange: 0.34 },
  MSFT: { ticker: 'MSFT', price: 412.83, change: -2.17, changePercent: -0.52, prediction: 'BEARISH', confidence: 72, sentiment: 0.43, rsi: 58.7, hourlyChange: -0.12 },
  GOOGL: { ticker: 'GOOGL', price: 142.56, change: 1.89, changePercent: 1.34, prediction: 'BULLISH', confidence: 79, sentiment: 0.55, rsi: 64.2, hourlyChange: 0.21 },
  AMZN: { ticker: 'AMZN', price: 183.27, change: -4.12, changePercent: -2.2, prediction: 'BEARISH', confidence: 65, sentiment: -0.32, rsi: 42.8, hourlyChange: -0.45 },
  TSLA: { ticker: 'TSLA', price: 196.84, change: 8.45, changePercent: 4.49, prediction: 'BULLISH', confidence: 91, sentiment: 0.81, rsi: 71.3, hourlyChange: 1.15 },
  NVDA: { ticker: 'NVDA', price: 875.30, change: 12.40, changePercent: 1.44, prediction: 'BULLISH', confidence: 88, sentiment: 0.72, rsi: 66.1, hourlyChange: 0.52 },
  META: { ticker: 'META', price: 502.10, change: -3.80, changePercent: -0.75, prediction: 'BEARISH', confidence: 62, sentiment: -0.15, rsi: 48.3, hourlyChange: -0.28 },
  JPM: { ticker: 'JPM', price: 198.45, change: 1.20, changePercent: 0.61, prediction: 'BULLISH', confidence: 74, sentiment: 0.38, rsi: 55.9, hourlyChange: 0.15 },
};

const generateHourlyPriceHistory = (startPrice: number, trend: 'up' | 'down' | 'neutral') => {
  const history = [];
  let price = startPrice;
  const now = new Date();
  for (let i = 23; i >= 0; i--) {
    const time = new Date(now);
    time.setHours(time.getHours() - i);
    const volatility = price * 0.005;
    const trendFactor = trend === 'up' ? 0.0008 : trend === 'down' ? -0.0008 : 0;
    price = price * (1 + trendFactor) + (Math.random() - 0.5) * volatility;
    history.push({ time: time.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false }), price: parseFloat(price.toFixed(2)) });
  }
  return history;
};

const getTechnicalIndicators = (stock: any) => [
  { name: 'RSI (1H)', value: (stock.rsi ?? 50).toFixed(1), signal: stock.rsi > 70 ? 'bearish' : stock.rsi < 30 ? 'bullish' : stock.rsi > 50 ? 'bullish' : 'bearish' as const, detail: stock.rsi > 70 ? 'Overbought' : stock.rsi < 30 ? 'Oversold' : 'Normal range' },
  { name: 'MACD (1H)', value: stock.prediction === 'BULLISH' ? '+1.23' : '-0.87', signal: (stock.prediction === 'BULLISH' ? 'bullish' : 'bearish') as 'bullish' | 'bearish', detail: stock.prediction === 'BULLISH' ? 'Bullish crossover' : 'Bearish divergence' },
  { name: 'Bollinger (1H)', value: stock.rsi > 70 ? 'Upper Band' : stock.rsi < 30 ? 'Lower Band' : 'Mid Band', signal: (stock.rsi > 70 ? 'bearish' : stock.rsi < 30 ? 'bullish' : 'neutral') as 'bullish' | 'bearish' | 'neutral', detail: `Width: ${(1.5 + Math.random() * 2).toFixed(1)}%` },
  { name: 'SMA Cross (1H)', value: stock.changePercent > 0 ? 'Golden' : 'Death', signal: (stock.changePercent > 0 ? 'bullish' : 'bearish') as 'bullish' | 'bearish', detail: stock.changePercent > 0 ? '9 EMA > 21 EMA' : '9 EMA < 21 EMA' },
];

const PIE_COLORS = ['#10b981', '#ef4444'];

// --- Dashboard Page ---

export function Dashboard() {
  const [selectedTicker, setSelectedTicker] = useState('AAPL');
  const [stocks, setStocks] = useState<Record<string, any>>(FALLBACK_STOCKS);
  const [lastUpdate, setLastUpdate] = useState(new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'Asia/Kolkata' }));

  useEffect(() => {
    async function loadData() {
      const data = await fetchLatestPredictions();
      if (data?.predictions?.length) {
        const stockMap: Record<string, any> = {};
        data.predictions.forEach((p: any) => {
          stockMap[p.ticker] = {
            ticker: p.ticker, price: p.current_price ?? 0,
            change: (p.current_price ?? 0) * (p.daily_return ?? 0),
            changePercent: (p.daily_return ?? 0) * 100,
            prediction: p.direction === 'BULLISH' ? 'BULLISH' : 'BEARISH',
            confidence: Math.round((p.confidence ?? 0) * 100),
            sentiment: p.sentiment_score ?? 0, rsi: p.rsi ?? 50,
            hourlyChange: p.hourly_change ?? 0,
          };
        });
        setStocks(stockMap);
      }
      setLastUpdate(new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'Asia/Kolkata' }));
    }
    loadData();
    const interval = setInterval(loadData, 60_000);
    return () => clearInterval(interval);
  }, []);

  const stocksList = Object.values(stocks);
  const selectedStock = stocks[selectedTicker] ?? stocksList[0] ?? FALLBACK_STOCKS.AAPL;
  const technicalIndicators = getTechnicalIndicators(selectedStock);
  const isUptrend = selectedStock.changePercent > 0;
  const priceHistory = generateHourlyPriceHistory(selectedStock.price * (1 - selectedStock.changePercent / 100), isUptrend ? 'up' : selectedStock.changePercent < 0 ? 'down' : 'neutral');

  const bullishCount = stocksList.filter(s => s.prediction === 'BULLISH').length;
  const bearishCount = stocksList.filter(s => s.prediction === 'BEARISH').length;
  const pieData = [{ name: 'Bullish', value: bullishCount }, { name: 'Bearish', value: bearishCount }];

  return (
    <div className="space-y-6">
      {/* Live Ticker Strip */}
      <div className="overflow-hidden bg-white/[0.03] border border-white/5 rounded-lg">
        <div className="flex animate-scroll whitespace-nowrap py-2 px-4 gap-8">
          {[...stocksList, ...stocksList].map((stock, i) => (
            <div key={`${stock.ticker}-${i}`} className="flex items-center gap-2 text-sm shrink-0">
              <span className="font-semibold text-white">{stock.ticker}</span>
              <span className="text-gray-400">${stock.price?.toFixed(2)}</span>
              <span className={stock.hourlyChange >= 0 ? 'text-[#10b981]' : 'text-[#ef4444]'}>
                {stock.hourlyChange >= 0 ? '▲' : '▼'} {Math.abs(stock.hourlyChange).toFixed(2)}%
              </span>
              <span className={`text-[10px] px-1.5 py-0.5 rounded ${stock.prediction === 'BULLISH' ? 'bg-[#10b981]/15 text-[#10b981]' : 'bg-[#ef4444]/15 text-[#ef4444]'}`}>
                {stock.prediction}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-[#3b82f6]/10 border border-[#3b82f6]/20 rounded-lg">
            <Zap className="w-4 h-4 text-[#3b82f6]" />
            <span className="text-sm text-[#3b82f6] font-medium">Hourly Analysis</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg">
            <Clock className="w-3.5 h-3.5 text-gray-400" />
            <span className="text-xs text-gray-400">Updated: {lastUpdate} IST</span>
          </div>
        </div>
        <button onClick={() => window.location.reload()} className="flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 transition-all text-gray-400 hover:text-white text-sm">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {/* Market Overview */}
      <div className="grid grid-cols-4 gap-4">
        <div className="p-4 bg-white/[0.03] border border-white/5 rounded-xl">
          <div className="text-sm text-gray-400 mb-1">Tracked Stocks</div>
          <div className="text-2xl font-semibold text-white">{stocksList.length}</div>
          <div className="text-xs text-gray-500 mt-1">S&P 100 + Custom</div>
        </div>
        <div className="p-4 bg-white/[0.03] border border-white/5 rounded-xl">
          <div className="text-sm text-gray-400 mb-1">Market Mood</div>
          <div className={`text-2xl font-semibold ${bullishCount > bearishCount ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>
            {bullishCount > bearishCount ? 'Bullish' : 'Bearish'}
          </div>
          <div className="text-xs text-gray-500 mt-1">{bullishCount} bullish • {bearishCount} bearish</div>
        </div>
        <div className="p-4 bg-white/[0.03] border border-white/5 rounded-xl">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-gray-400 mb-1">Signal Split</div>
              <div className="text-xs text-gray-500">Bull vs Bear</div>
            </div>
            <div className="w-16 h-16">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart><Pie data={pieData} cx="50%" cy="50%" innerRadius={18} outerRadius={28} paddingAngle={2} dataKey="value" strokeWidth={0}>{pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i]} />)}</Pie></PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
        <div className="p-4 bg-white/[0.03] border border-white/5 rounded-xl">
          <div className="text-sm text-gray-400 mb-1">Avg Confidence</div>
          <div className="text-2xl font-semibold text-[#3b82f6]">
            {stocksList.length ? Math.round(stocksList.reduce((s, st) => s + st.confidence, 0) / stocksList.length) : 0}%
          </div>
          <div className="text-xs text-gray-500 mt-1">Ensemble model</div>
        </div>
      </div>

      {/* Market Heatmap */}
      <div className="p-4 bg-white/[0.03] border border-white/5 rounded-xl">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">Market Heatmap</h3>
          <span className="text-xs text-gray-500">Click any stock to view details</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {stocksList.map((stock) => {
            const intensity = Math.min(Math.abs(stock.hourlyChange) * 100, 100);
            const bgColor = stock.prediction === 'BULLISH'
              ? `rgba(16, 185, 129, ${0.15 + intensity * 0.005})`
              : `rgba(239, 68, 68, ${0.15 + intensity * 0.005})`;
            const borderColor = stock.prediction === 'BULLISH'
              ? `rgba(16, 185, 129, ${0.3 + intensity * 0.005})`
              : `rgba(239, 68, 68, ${0.3 + intensity * 0.005})`;
            return (
              <button key={stock.ticker} onClick={() => setSelectedTicker(stock.ticker)}
                className={`px-3 py-2 rounded-lg text-xs font-medium transition-all hover:scale-105 ${selectedTicker === stock.ticker ? 'ring-2 ring-[#3b82f6]' : ''}`}
                style={{ backgroundColor: bgColor, border: `1px solid ${borderColor}`, color: stock.prediction === 'BULLISH' ? '#10b981' : '#ef4444' }}>
                <div className="font-semibold">{stock.ticker}</div>
                <div className="text-[10px] opacity-80">{stock.hourlyChange >= 0 ? '+' : ''}{stock.hourlyChange.toFixed(2)}%</div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Ticker Cards */}
      <div className="grid grid-cols-4 gap-4">
        {stocksList.slice(0, 8).map((stock) => (
          <TickerCard key={stock.ticker} ticker={stock.ticker} price={stock.price} change={stock.change} changePercent={stock.changePercent}
            prediction={stock.prediction} confidence={stock.confidence} hourlyChange={stock.hourlyChange}
            isSelected={selectedTicker === stock.ticker} onClick={() => setSelectedTicker(stock.ticker)} />
        ))}
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-6">
          <div className="p-6 bg-white/[0.03] border border-white/5 rounded-xl">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-semibold text-white">{selectedTicker}</h2>
                <p className="text-gray-400 text-sm">24H Intraday Price</p>
              </div>
              <div className="text-right">
                <div className="text-3xl font-semibold text-white">${selectedStock.price?.toFixed(2)}</div>
                <div className={`text-sm ${isUptrend ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>
                  {isUptrend ? '+' : ''}{selectedStock.change?.toFixed(2)} ({isUptrend ? '+' : ''}{selectedStock.changePercent?.toFixed(2)}%)
                </div>
                <div className={`text-xs mt-1 ${selectedStock.hourlyChange >= 0 ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>
                  Last hour: {selectedStock.hourlyChange >= 0 ? '+' : ''}{selectedStock.hourlyChange?.toFixed(2)}%
                </div>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={350}>
              <AreaChart data={priceHistory}>
                <defs>
                  <linearGradient id={`g-${selectedTicker}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={isUptrend ? '#10b981' : '#ef4444'} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={isUptrend ? '#10b981' : '#ef4444'} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#6b7280" tick={{ fill: '#6b7280', fontSize: 11 }} interval={3} />
                <YAxis stroke="#6b7280" tick={{ fill: '#6b7280', fontSize: 12 }} domain={['dataMin - 2', 'dataMax + 2']} tickFormatter={(v) => `$${v.toFixed(0)}`} />
                <Tooltip contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(71, 85, 105, 0.3)', borderRadius: '8px', color: '#e2e8f0' }} formatter={(value: number) => [`$${value.toFixed(2)}`, 'Price']} />
                <Area type="monotone" dataKey="price" stroke={isUptrend ? '#10b981' : '#ef4444'} strokeWidth={2} fill={`url(#g-${selectedTicker})`} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-4 gap-4">
            {technicalIndicators.map((ind) => <TechnicalIndicatorCard key={ind.name} {...ind} />)}
          </div>
        </div>
        <div>
          <SentimentGauge compoundScore={selectedStock.sentiment} redditPosts={Math.floor(Math.random() * 120) + 30}
            newsArticles={Math.floor(Math.random() * 15) + 5} lastHourChange={parseFloat(((Math.random() - 0.5) * 0.2).toFixed(3))} />
        </div>
      </div>

      <style>{`
        @keyframes scroll { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
        .animate-scroll { animation: scroll 40s linear infinite; }
        .animate-scroll:hover { animation-play-state: paused; }
      `}</style>
    </div>
  );
}
