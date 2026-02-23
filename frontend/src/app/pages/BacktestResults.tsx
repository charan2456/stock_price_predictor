import { useState, useEffect } from "react";
import { TrendingUp, TrendingDown, Activity, Target, Percent, BarChart3, Clock } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { fetchBacktestResults, fetchBacktestTrades, type BacktestMetricsAPI, type TradeAPI } from "../services/api";

// Fallback data
const FALLBACK_METRICS = {
  totalReturn: 34.7, sharpeRatio: 1.82, maxDrawdown: -8.3,
  winRate: 67.4, alpha: 12.5, totalTrades: 847,
};

const FALLBACK_TRADES = [
  { date: '2026-02-22', time: '14:30', action: 'LONG', predictedReturn: 0.42, actualReturn: 0.38, pnl: 380, ticker: 'AAPL' },
  { date: '2026-02-22', time: '13:00', action: 'LONG', predictedReturn: 0.28, actualReturn: 0.31, pnl: 310, ticker: 'TSLA' },
  { date: '2026-02-22', time: '11:30', action: 'FLAT', predictedReturn: -0.15, actualReturn: -0.22, pnl: 0, ticker: 'AMZN' },
  { date: '2026-02-22', time: '10:00', action: 'LONG', predictedReturn: 0.51, actualReturn: 0.18, pnl: 180, ticker: 'GOOGL' },
  { date: '2026-02-21', time: '15:00', action: 'LONG', predictedReturn: 0.35, actualReturn: -0.08, pnl: -80, ticker: 'MSFT' },
  { date: '2026-02-21', time: '13:30', action: 'FLAT', predictedReturn: -0.22, actualReturn: -0.31, pnl: 0, ticker: 'AMZN' },
  { date: '2026-02-21', time: '12:00', action: 'LONG', predictedReturn: 0.48, actualReturn: 0.52, pnl: 520, ticker: 'TSLA' },
  { date: '2026-02-21', time: '10:30', action: 'LONG', predictedReturn: 0.33, actualReturn: 0.29, pnl: 290, ticker: 'AAPL' },
];

function generateEquityCurve() {
  const data = [];
  let pv = 100000, sv = 100000;
  const now = new Date();
  for (let d = 4; d >= 0; d--) {
    for (let h = 9; h <= 15; h++) {
      const t = new Date(now);
      t.setDate(t.getDate() - d);
      t.setHours(h, 30, 0, 0);
      pv *= (1 + Math.random() * 0.004 + 0.0005);
      sv *= (1 + Math.random() * 0.003);
      data.push({
        time: `${t.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} ${h}:30`,
        portfolio: parseFloat(pv.toFixed(2)),
        spy: parseFloat(sv.toFixed(2)),
      });
    }
  }
  return data;
}

export function BacktestResults() {
  const [metricsData, setMetricsData] = useState(FALLBACK_METRICS);
  const [tradesData, setTradesData] = useState<any[]>(FALLBACK_TRADES);
  const equityCurve = generateEquityCurve();

  useEffect(() => {
    async function loadData() {
      const [btResults, btTrades] = await Promise.all([
        fetchBacktestResults(),
        fetchBacktestTrades(50),
      ]);

      if (btResults && btResults.total_return != null) {
        setMetricsData({
          totalReturn: btResults.total_return,
          sharpeRatio: btResults.sharpe_ratio,
          maxDrawdown: btResults.max_drawdown,
          winRate: btResults.win_rate,
          alpha: btResults.alpha,
          totalTrades: btResults.total_trades ?? 0,
        });
      }

      if (btTrades?.trades?.length) {
        setTradesData(btTrades.trades.map((t: TradeAPI) => ({
          date: t.date,
          time: t.time,
          action: t.action,
          predictedReturn: t.predicted_return,
          actualReturn: t.actual_return,
          pnl: t.pnl,
          ticker: t.ticker,
        })));
      }
    }
    loadData();
  }, []);

  const metrics = [
    { label: 'Total Return', value: `${metricsData.totalReturn}%`, icon: TrendingUp, color: 'text-[#10b981]', bgColor: 'bg-[#10b981]/10' },
    { label: 'Sharpe Ratio', value: metricsData.sharpeRatio.toFixed(2), icon: Activity, color: 'text-[#3b82f6]', bgColor: 'bg-[#3b82f6]/10' },
    { label: 'Max Drawdown', value: `${metricsData.maxDrawdown}%`, icon: TrendingDown, color: 'text-[#ef4444]', bgColor: 'bg-[#ef4444]/10' },
    { label: 'Win Rate', value: `${metricsData.winRate}%`, icon: Target, color: 'text-[#10b981]', bgColor: 'bg-[#10b981]/10' },
    { label: 'Alpha vs SPY', value: `${metricsData.alpha}%`, icon: Percent, color: 'text-[#8b5cf6]', bgColor: 'bg-[#8b5cf6]/10' },
    { label: 'Total Trades', value: metricsData.totalTrades.toLocaleString(), icon: BarChart3, color: 'text-[#f59e0b]', bgColor: 'bg-[#f59e0b]/10' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold text-white mb-2">Backtest Results</h1>
        <div className="flex items-center gap-2">
          <p className="text-gray-400">Hourly strategy performance analysis and trade metrics</p>
          <div className="flex items-center gap-1 px-2 py-0.5 bg-[#f59e0b]/10 border border-[#f59e0b]/20 rounded-full">
            <Clock className="w-3 h-3 text-[#f59e0b]" />
            <span className="text-[10px] text-[#f59e0b] font-medium">HOURLY INTERVALS</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-6 gap-4">
        {metrics.map((m) => {
          const Icon = m.icon;
          return (
            <div key={m.label} className="p-5 bg-white/5 border border-white/10 rounded-xl backdrop-blur-xl hover:bg-white/[0.08] transition-all">
              <div className="flex items-start justify-between mb-3">
                <div className={`p-2 ${m.bgColor} rounded-lg`}><Icon className={`w-5 h-5 ${m.color}`} /></div>
              </div>
              <div className={`text-2xl font-semibold mb-1 ${m.color}`}>{m.value}</div>
              <div className="text-sm text-gray-400">{m.label}</div>
            </div>
          );
        })}
      </div>

      <div className="p-6 bg-white/5 border border-white/10 rounded-xl backdrop-blur-xl">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-white">Equity Curve vs Benchmark (Hourly)</h3>
          <span className="text-xs text-gray-500">Last 5 trading days • Hourly intervals</span>
        </div>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={equityCurve}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="time" stroke="#6b7280" tick={{ fill: '#6b7280', fontSize: 10 }} interval={4} />
            <YAxis stroke="#6b7280" tick={{ fill: '#6b7280', fontSize: 12 }} tickFormatter={(v) => `$${(v / 1000).toFixed(1)}K`} />
            <Tooltip contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(71, 85, 105, 0.3)', borderRadius: '8px', color: '#e2e8f0' }} formatter={(v: number) => [`$${v.toFixed(2)}`, '']} />
            <Legend wrapperStyle={{ paddingTop: '20px' }} iconType="line" />
            <Line type="monotone" dataKey="portfolio" stroke="#3b82f6" strokeWidth={3} dot={false} name="Portfolio" />
            <Line type="monotone" dataKey="spy" stroke="#6b7280" strokeWidth={2} strokeDasharray="5 5" dot={false} name="SPY Benchmark" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white/5 border border-white/10 rounded-xl backdrop-blur-xl overflow-hidden">
        <div className="p-6 border-b border-white/10 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">Hourly Trade Log</h3>
          <span className="text-xs text-gray-500">{tradesData.length} recent hourly trades</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-white/5 border-b border-white/10">
              <tr>
                <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">Date & Time</th>
                <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">Ticker</th>
                <th className="px-6 py-4 text-center text-sm font-medium text-gray-400">Action</th>
                <th className="px-6 py-4 text-right text-sm font-medium text-gray-400">Predicted (1H)</th>
                <th className="px-6 py-4 text-right text-sm font-medium text-gray-400">Actual (1H)</th>
                <th className="px-6 py-4 text-right text-sm font-medium text-gray-400">P&L</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/10">
              {tradesData.map((trade, i) => (
                <tr key={i} className="hover:bg-white/5 transition-colors">
                  <td className="px-6 py-4 text-white">
                    <div>
                      <div className="text-sm">{new Date(trade.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</div>
                      <div className="text-xs text-gray-500">{trade.time}</div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-white font-medium">{trade.ticker}</td>
                  <td className="px-6 py-4 text-center">
                    <span className={`inline-flex px-3 py-1 rounded-full text-xs font-medium ${trade.action === 'LONG' ? 'bg-[#10b981]/20 text-[#10b981]' : 'bg-gray-500/20 text-gray-400'}`}>{trade.action}</span>
                  </td>
                  <td className="px-6 py-4 text-right text-white">{trade.predictedReturn > 0 ? '+' : ''}{trade.predictedReturn.toFixed(2)}%</td>
                  <td className={`px-6 py-4 text-right font-medium ${trade.actualReturn > 0 ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>{trade.actualReturn > 0 ? '+' : ''}{trade.actualReturn.toFixed(2)}%</td>
                  <td className={`px-6 py-4 text-right font-semibold ${trade.pnl > 0 ? 'text-[#10b981]' : trade.pnl === 0 ? 'text-gray-400' : 'text-[#ef4444]'}`}>
                    {trade.pnl === 0 ? '-' : `${trade.pnl > 0 ? '+' : ''}$${Math.abs(trade.pnl)}`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
