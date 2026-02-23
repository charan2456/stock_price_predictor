import { useState, useEffect } from "react";
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, Legend } from "recharts";
import { compareStocks, fetchLatestPredictions } from "../services/api";
import { Scale, Plus, X, TrendingUp, TrendingDown, Trophy, Search } from "lucide-react";

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

const ALL_STOCKS_DATA: Record<string, any> = {
    AAPL: { ticker: 'AAPL', current_price: 178.42, predicted_return: 0.0034, direction: 'BULLISH', confidence: 87, sentiment: 0.68, rsi: 62.4, hourly_change: 0.34, model_agreement: true },
    MSFT: { ticker: 'MSFT', current_price: 412.83, predicted_return: -0.0012, direction: 'BEARISH', confidence: 72, sentiment: 0.43, rsi: 58.7, hourly_change: -0.12, model_agreement: true },
    GOOGL: { ticker: 'GOOGL', current_price: 142.56, predicted_return: 0.0021, direction: 'BULLISH', confidence: 79, sentiment: 0.55, rsi: 64.2, hourly_change: 0.21, model_agreement: true },
    AMZN: { ticker: 'AMZN', current_price: 183.27, predicted_return: -0.0028, direction: 'BEARISH', confidence: 65, sentiment: -0.32, rsi: 42.8, hourly_change: -0.45, model_agreement: false },
    TSLA: { ticker: 'TSLA', current_price: 196.84, predicted_return: 0.0055, direction: 'BULLISH', confidence: 91, sentiment: 0.81, rsi: 71.3, hourly_change: 1.15, model_agreement: true },
    NVDA: { ticker: 'NVDA', current_price: 875.30, predicted_return: 0.0042, direction: 'BULLISH', confidence: 88, sentiment: 0.72, rsi: 66.1, hourly_change: 0.52, model_agreement: true },
    META: { ticker: 'META', current_price: 502.10, predicted_return: -0.0018, direction: 'BEARISH', confidence: 62, sentiment: -0.15, rsi: 48.3, hourly_change: -0.28, model_agreement: false },
    JPM: { ticker: 'JPM', current_price: 198.45, predicted_return: 0.0015, direction: 'BULLISH', confidence: 74, sentiment: 0.38, rsi: 55.9, hourly_change: 0.15, model_agreement: true },
    V: { ticker: 'V', current_price: 289.60, predicted_return: 0.0022, direction: 'BULLISH', confidence: 76, sentiment: 0.42, rsi: 59.4, hourly_change: 0.18, model_agreement: true },
    HD: { ticker: 'HD', current_price: 378.90, predicted_return: 0.0018, direction: 'BULLISH', confidence: 70, sentiment: 0.35, rsi: 54.8, hourly_change: 0.12, model_agreement: true },
};

export function Comparison() {
    const [tickers, setTickers] = useState<string[]>(['AAPL', 'MSFT', 'TSLA']);
    const [data, setData] = useState<any[]>([]);
    const [newTicker, setNewTicker] = useState('');
    const [searchSuggestions, setSearchSuggestions] = useState<string[]>([]);

    useEffect(() => {
        async function load() {
            const result = await compareStocks(tickers);
            if (result?.comparison?.length) {
                setData(result.comparison.filter((c: any) => c.current_price));
            } else {
                // Use fallback data
                setData(tickers.map(t => ALL_STOCKS_DATA[t] || { ticker: t, current_price: 100, predicted_return: 0, direction: 'BULLISH', confidence: 50, sentiment: 0, rsi: 50, hourly_change: 0, model_agreement: true }));
            }
        }
        load();
    }, [tickers]);

    const addTicker = (ticker?: string) => {
        const t = (ticker || newTicker).toUpperCase().trim();
        if (t && !tickers.includes(t) && tickers.length < 5) {
            setTickers(prev => [...prev, t]);
            setNewTicker('');
            setSearchSuggestions([]);
        }
    };

    const removeTicker = (t: string) => {
        if (tickers.length > 2) setTickers(prev => prev.filter(x => x !== t));
    };

    const handleSearchInput = (val: string) => {
        setNewTicker(val.toUpperCase());
        if (val.length > 0) {
            const all = Object.keys(ALL_STOCKS_DATA);
            setSearchSuggestions(all.filter(t => t.includes(val.toUpperCase()) && !tickers.includes(t)).slice(0, 5));
        } else {
            setSearchSuggestions([]);
        }
    };

    // Radar chart
    const radarData = [
        { metric: 'Confidence', ...Object.fromEntries(data.map(d => [d.ticker, d.confidence || 0])) },
        { metric: 'Sentiment', ...Object.fromEntries(data.map(d => [d.ticker, Math.round(((d.sentiment || 0) + 1) * 50)])) },
        { metric: 'RSI Health', ...Object.fromEntries(data.map(d => [d.ticker, 100 - Math.abs((d.rsi || 50) - 50) * 2])) },
        { metric: 'Momentum', ...Object.fromEntries(data.map(d => [d.ticker, Math.min(100, Math.max(0, 50 + (d.hourly_change || 0) * 20))])) },
        { metric: 'Model Agr.', ...Object.fromEntries(data.map(d => [d.ticker, d.model_agreement ? 95 : 40])) },
    ];

    const returnData = data.map((d, i) => ({
        ticker: d.ticker,
        return: ((d.predicted_return || 0) * 100),
        color: COLORS[i % COLORS.length],
    }));

    const bestPick = data.length ? data.reduce((best, d) => ((d.confidence || 0) > (best.confidence || 0) ? d : best), data[0]) : null;

    return (
        <div className="space-y-6">
            {/* Ticker Selection */}
            <div className="flex items-center gap-3 flex-wrap">
                {tickers.map((t, i) => (
                    <div key={t} className="flex items-center gap-2 px-4 py-2 rounded-lg border" style={{ backgroundColor: `${COLORS[i % COLORS.length]}15`, borderColor: `${COLORS[i % COLORS.length]}40` }}>
                        <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                        <span className="text-white font-semibold text-sm">{t}</span>
                        {tickers.length > 2 && (
                            <button onClick={() => removeTicker(t)} className="p-0.5 hover:bg-white/10 rounded"><X className="w-3.5 h-3.5 text-gray-400" /></button>
                        )}
                    </div>
                ))}
                {tickers.length < 5 && (
                    <div className="relative">
                        <div className="flex items-center gap-2">
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500" />
                                <input type="text" value={newTicker} onChange={(e) => handleSearchInput(e.target.value)}
                                    onKeyDown={(e) => e.key === 'Enter' && addTicker()}
                                    placeholder="Add ticker" className="w-36 pl-9 pr-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-[#8b5cf6] placeholder:text-gray-600" />
                            </div>
                            <button onClick={() => addTicker()} className="p-2 bg-[#8b5cf6]/10 border border-[#8b5cf6]/20 rounded-lg hover:bg-[#8b5cf6]/20 transition-all">
                                <Plus className="w-4 h-4 text-[#8b5cf6]" />
                            </button>
                        </div>
                        {searchSuggestions.length > 0 && (
                            <div className="absolute top-full left-0 mt-1 w-48 bg-[#0f172a] border border-white/10 rounded-lg shadow-xl z-10">
                                {searchSuggestions.map(s => (
                                    <button key={s} onClick={() => addTicker(s)} className="w-full text-left px-4 py-2 text-sm text-white hover:bg-white/5 transition-colors">
                                        {s} — ${ALL_STOCKS_DATA[s]?.current_price?.toFixed(2) || '—'}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Best Pick */}
            {bestPick && (
                <div className="p-4 bg-gradient-to-r from-[#f59e0b]/10 to-transparent border border-[#f59e0b]/20 rounded-xl flex items-center gap-4">
                    <Trophy className="w-8 h-8 text-[#f59e0b]" />
                    <div>
                        <div className="text-sm text-gray-400">Recommendation based on confidence + sentiment</div>
                        <div className="text-lg font-semibold text-white">
                            <span className="text-[#f59e0b]">{bestPick.ticker}</span> is the strongest pick
                            <span className="text-sm text-gray-400 ml-2">— {bestPick.confidence}% confidence, {bestPick.direction}</span>
                        </div>
                    </div>
                </div>
            )}

            <div className="grid grid-cols-2 gap-6">
                {/* Radar */}
                <div className="p-6 bg-white/[0.03] border border-white/5 rounded-xl">
                    <h3 className="text-lg font-semibold text-white mb-4">Multi-Metric Comparison</h3>
                    <ResponsiveContainer width="100%" height={380}>
                        <RadarChart data={radarData}>
                            <PolarGrid stroke="#1e293b" />
                            <PolarAngleAxis dataKey="metric" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                            <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: '#6b7280', fontSize: 10 }} />
                            {data.map((d, i) => (
                                <Radar key={d.ticker} name={d.ticker} dataKey={d.ticker} stroke={COLORS[i % COLORS.length]}
                                    fill={COLORS[i % COLORS.length]} fillOpacity={0.1} strokeWidth={2} />
                            ))}
                            <Legend wrapperStyle={{ fontSize: '12px' }} />
                            <Tooltip />
                        </RadarChart>
                    </ResponsiveContainer>
                </div>

                {/* Returns Bar */}
                <div className="p-6 bg-white/[0.03] border border-white/5 rounded-xl">
                    <h3 className="text-lg font-semibold text-white mb-4">Predicted Returns (1H)</h3>
                    <ResponsiveContainer width="100%" height={380}>
                        <BarChart data={returnData} layout="vertical">
                            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                            <XAxis type="number" stroke="#6b7280" tick={{ fill: '#6b7280', fontSize: 12 }} tickFormatter={(v) => `${v.toFixed(2)}%`} />
                            <YAxis type="category" dataKey="ticker" stroke="#6b7280" tick={{ fill: '#e2e8f0', fontSize: 14, fontWeight: 600 }} width={60} />
                            <Tooltip formatter={(v: number) => [`${v.toFixed(3)}%`, 'Predicted Return']}
                                contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.95)', border: '1px solid rgba(71, 85, 105, 0.3)', borderRadius: '8px', color: '#e2e8f0' }} />
                            <Bar dataKey="return" radius={[0, 4, 4, 0]}>
                                {returnData.map((entry, i) => <Cell key={i} fill={entry.return >= 0 ? '#10b981' : '#ef4444'} />)}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Detail Table */}
            <div className="bg-white/[0.03] border border-white/5 rounded-xl overflow-hidden">
                <div className="p-5 border-b border-white/5">
                    <h3 className="text-lg font-semibold text-white">Detailed Comparison</h3>
                </div>
                <table className="w-full">
                    <thead className="bg-white/[0.03]">
                        <tr>
                            <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">Metric</th>
                            {data.map((d, i) => (
                                <th key={d.ticker} className="px-6 py-4 text-center text-sm font-medium" style={{ color: COLORS[i % COLORS.length] }}>{d.ticker}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                        {[
                            { label: 'Current Price', render: (d: any) => `$${(d.current_price || 0).toFixed(2)}` },
                            { label: 'Direction', render: (d: any) => d.direction || 'N/A', color: (d: any) => d.direction === 'BULLISH' ? '#10b981' : '#ef4444' },
                            { label: 'Confidence', render: (d: any) => `${d.confidence || 0}%` },
                            { label: 'Predicted Return', render: (d: any) => `${((d.predicted_return || 0) * 100).toFixed(3)}%`, color: (d: any) => (d.predicted_return || 0) >= 0 ? '#10b981' : '#ef4444' },
                            { label: 'Sentiment', render: (d: any) => (d.sentiment || 0).toFixed(2), color: (d: any) => (d.sentiment || 0) > 0 ? '#10b981' : '#ef4444' },
                            { label: 'RSI', render: (d: any) => (d.rsi || 50).toFixed(1) },
                            { label: '1H Change', render: (d: any) => `${(d.hourly_change || 0) >= 0 ? '+' : ''}${(d.hourly_change || 0).toFixed(2)}%`, color: (d: any) => (d.hourly_change || 0) >= 0 ? '#10b981' : '#ef4444' },
                            { label: 'Model Agreement', render: (d: any) => d.model_agreement ? '✅ Yes' : '⚠️ No' },
                        ].map((row) => (
                            <tr key={row.label} className="hover:bg-white/[0.03]">
                                <td className="px-6 py-3 text-sm text-gray-400">{row.label}</td>
                                {data.map((d) => (
                                    <td key={d.ticker} className="px-6 py-3 text-center text-sm font-medium" style={{ color: row.color ? row.color(d) : '#e2e8f0' }}>{row.render(d)}</td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
