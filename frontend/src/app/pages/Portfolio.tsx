import { useState, useEffect } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts";
import { fetchPortfolio, addPortfolioHolding, removePortfolioHolding, fetchPortfolioForecast } from "../services/api";
import { Plus, Trash2, TrendingUp, TrendingDown, DollarSign, PieChart as PieIcon, Target, ChevronDown, X } from "lucide-react";

const PIE_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316'];

// Fallback data
const FALLBACK_HOLDINGS = [
    { id: 1, ticker: 'AAPL', shares: 50, buy_price: 165.00, current_price: 178.42, buy_date: '2025-11-15', direction: 'BULLISH', confidence: 87, predicted_price_1d: 182.40 },
    { id: 2, ticker: 'MSFT', shares: 20, buy_price: 380.00, current_price: 412.83, buy_date: '2025-10-20', direction: 'BULLISH', confidence: 72, predicted_price_1d: 418.50 },
    { id: 3, ticker: 'GOOGL', shares: 100, buy_price: 135.00, current_price: 142.56, buy_date: '2025-12-01', direction: 'BULLISH', confidence: 79, predicted_price_1d: 145.30 },
    { id: 4, ticker: 'TSLA', shares: 30, buy_price: 210.00, current_price: 196.84, buy_date: '2026-01-10', direction: 'BULLISH', confidence: 91, predicted_price_1d: 204.20 },
];

export function Portfolio() {
    const [holdings, setHoldings] = useState<any[]>([]);
    const [summary, setSummary] = useState<any>({});
    const [portfolioForecast, setPortfolioForecast] = useState<any>(null);
    const [showAddModal, setShowAddModal] = useState(false);
    const [newHolding, setNewHolding] = useState({ ticker: '', shares: '', buy_price: '', buy_date: '' });

    useEffect(() => {
        loadData();
    }, []);

    async function loadData() {
        const data = await fetchPortfolio();
        if (data?.holdings?.length) {
            setHoldings(data.holdings);
            setSummary(data.summary);
        } else {
            // Fallback
            const fallback = FALLBACK_HOLDINGS.map(h => ({
                ...h,
                current_value: h.shares * h.current_price,
                invested_value: h.shares * h.buy_price,
                unrealized_pnl: h.shares * (h.current_price - h.buy_price),
                unrealized_pnl_pct: ((h.current_price - h.buy_price) / h.buy_price * 100),
                predicted_value_1d: h.shares * h.predicted_price_1d,
                predicted_pnl_1d: h.shares * (h.predicted_price_1d - h.current_price),
            }));
            setHoldings(fallback);
            const totalInvested = fallback.reduce((s, h) => s + h.invested_value, 0);
            const totalCurrent = fallback.reduce((s, h) => s + h.current_value, 0);
            const totalPredicted = fallback.reduce((s, h) => s + h.predicted_value_1d, 0);
            setSummary({
                total_invested: totalInvested, total_current_value: totalCurrent,
                total_unrealized_pnl: totalCurrent - totalInvested,
                total_unrealized_pnl_pct: ((totalCurrent - totalInvested) / totalInvested * 100),
                total_predicted_value_1d: totalPredicted,
                predicted_change_1d: totalPredicted - totalCurrent,
            });
        }

        const forecast = await fetchPortfolioForecast();
        if (forecast) setPortfolioForecast(forecast);
    }

    const handleAddHolding = async () => {
        if (!newHolding.ticker || !newHolding.shares || !newHolding.buy_price) return;
        await addPortfolioHolding({
            ticker: newHolding.ticker.toUpperCase(),
            shares: parseFloat(newHolding.shares),
            buy_price: parseFloat(newHolding.buy_price),
            buy_date: newHolding.buy_date || undefined,
        });
        setShowAddModal(false);
        setNewHolding({ ticker: '', shares: '', buy_price: '', buy_date: '' });
        loadData();
    };

    const handleRemove = async (id: number) => {
        await removePortfolioHolding(id);
        setHoldings(prev => prev.filter(h => h.id !== id));
    };

    const pieData = holdings.map(h => ({ name: h.ticker, value: h.current_value || h.shares * (h.current_price || h.buy_price) }));
    const totalCurrent = summary.total_current_value || 0;
    const totalPnl = summary.total_unrealized_pnl || 0;
    const predictedChange = summary.predicted_change_1d || 0;

    // Performance over time (simulated)
    const perfData = Array.from({ length: 30 }, (_, i) => {
        const d = new Date();
        d.setDate(d.getDate() - (29 - i));
        return {
            date: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
            value: (totalCurrent * 0.9) + (totalCurrent * 0.1 * i / 29) + (Math.random() - 0.5) * totalCurrent * 0.02,
        };
    });

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-semibold text-white mb-2">My Portfolio</h1>
                    <p className="text-gray-400">Track your holdings, P&L, and predicted portfolio value</p>
                </div>
                <button onClick={() => setShowAddModal(true)}
                    className="flex items-center gap-2 px-5 py-2.5 bg-[#3b82f6] hover:bg-[#2563eb] text-white rounded-lg text-sm font-medium transition-all">
                    <Plus className="w-4 h-4" /> Add Holding
                </button>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-5 gap-4">
                <div className="p-5 bg-white/5 border border-white/10 rounded-xl">
                    <div className="text-sm text-gray-400 mb-1">Total Invested</div>
                    <div className="text-2xl font-semibold text-white">${(summary.total_invested || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</div>
                </div>
                <div className="p-5 bg-white/5 border border-white/10 rounded-xl">
                    <div className="text-sm text-gray-400 mb-1">Current Value</div>
                    <div className="text-2xl font-semibold text-white">${totalCurrent.toLocaleString('en-US', { minimumFractionDigits: 2 })}</div>
                </div>
                <div className="p-5 bg-white/5 border border-white/10 rounded-xl">
                    <div className="text-sm text-gray-400 mb-1">Unrealized P&L</div>
                    <div className={`text-2xl font-semibold ${totalPnl >= 0 ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>
                        {totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(2)}
                    </div>
                    <div className={`text-xs ${totalPnl >= 0 ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>
                        {totalPnl >= 0 ? '+' : ''}{(summary.total_unrealized_pnl_pct || 0).toFixed(2)}%
                    </div>
                </div>
                <div className="p-5 bg-[#3b82f6]/5 border border-[#3b82f6]/20 rounded-xl">
                    <div className="text-sm text-gray-400 mb-1 flex items-center gap-1">
                        <Target className="w-3.5 h-3.5 text-[#3b82f6]" /> Predicted Value (1D)
                    </div>
                    <div className="text-2xl font-semibold text-[#3b82f6]">${(summary.total_predicted_value_1d || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}</div>
                    <div className={`text-xs ${predictedChange >= 0 ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>
                        {predictedChange >= 0 ? '+' : ''}${predictedChange.toFixed(2)} predicted
                    </div>
                </div>
                <div className="p-5 bg-white/5 border border-white/10 rounded-xl">
                    <div className="text-sm text-gray-400 mb-1">Holdings</div>
                    <div className="text-2xl font-semibold text-white">{holdings.length}</div>
                    <div className="text-xs text-gray-500">stocks tracked</div>
                </div>
            </div>

            <div className="grid grid-cols-3 gap-6">
                {/* Holdings Table */}
                <div className="col-span-2 bg-white/5 border border-white/10 rounded-xl overflow-hidden">
                    <div className="p-5 border-b border-white/10">
                        <h3 className="text-lg font-semibold text-white">Holdings</h3>
                    </div>
                    <table className="w-full">
                        <thead className="bg-white/5 border-b border-white/10">
                            <tr>
                                <th className="px-5 py-3 text-left text-xs font-medium text-gray-400">Stock</th>
                                <th className="px-5 py-3 text-right text-xs font-medium text-gray-400">Shares</th>
                                <th className="px-5 py-3 text-right text-xs font-medium text-gray-400">Avg Buy</th>
                                <th className="px-5 py-3 text-right text-xs font-medium text-gray-400">Current</th>
                                <th className="px-5 py-3 text-right text-xs font-medium text-gray-400">P&L</th>
                                <th className="px-5 py-3 text-right text-xs font-medium text-gray-400">Predicted (1D)</th>
                                <th className="px-5 py-3 text-center text-xs font-medium text-gray-400">Signal</th>
                                <th className="px-5 py-3 text-center text-xs font-medium text-gray-400"></th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/10">
                            {holdings.map((h) => {
                                const pnl = h.unrealized_pnl ?? h.shares * ((h.current_price || h.buy_price) - h.buy_price);
                                const pnlPct = h.unrealized_pnl_pct ?? ((h.current_price || h.buy_price) - h.buy_price) / h.buy_price * 100;
                                const predPnl = h.predicted_pnl_1d ?? 0;
                                return (
                                    <tr key={h.id} className="hover:bg-white/5 transition-colors">
                                        <td className="px-5 py-4">
                                            <div className="font-semibold text-white">{h.ticker}</div>
                                            {h.buy_date && <div className="text-[10px] text-gray-500">Since {h.buy_date}</div>}
                                        </td>
                                        <td className="px-5 py-4 text-right text-white">{h.shares}</td>
                                        <td className="px-5 py-4 text-right text-gray-400">${h.buy_price?.toFixed(2)}</td>
                                        <td className="px-5 py-4 text-right text-white">${(h.current_price || h.buy_price)?.toFixed(2)}</td>
                                        <td className="px-5 py-4 text-right">
                                            <div className={`font-semibold ${pnl >= 0 ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>
                                                {pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}
                                            </div>
                                            <div className={`text-[10px] ${pnl >= 0 ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>
                                                {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
                                            </div>
                                        </td>
                                        <td className="px-5 py-4 text-right">
                                            <div className={`text-sm font-medium ${predPnl >= 0 ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>
                                                {predPnl >= 0 ? '+' : ''}${predPnl.toFixed(2)}
                                            </div>
                                        </td>
                                        <td className="px-5 py-4 text-center">
                                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${(h.direction || 'BULLISH') === 'BULLISH' ? 'bg-[#10b981]/15 text-[#10b981]' : 'bg-[#ef4444]/15 text-[#ef4444]'}`}>
                                                {(h.direction || 'BULLISH') === 'BULLISH' ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                                {h.direction || 'BULLISH'}
                                            </span>
                                        </td>
                                        <td className="px-5 py-4 text-center">
                                            <button onClick={() => handleRemove(h.id)} className="p-1.5 hover:bg-[#ef4444]/10 rounded-lg transition-colors">
                                                <Trash2 className="w-4 h-4 text-gray-500 hover:text-[#ef4444]" />
                                            </button>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>

                {/* Right Panel */}
                <div className="space-y-6">
                    {/* Allocation Pie Chart */}
                    <div className="p-6 bg-white/5 border border-white/10 rounded-xl">
                        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <PieIcon className="w-5 h-5 text-[#3b82f6]" /> Allocation
                        </h3>
                        <ResponsiveContainer width="100%" height={200}>
                            <PieChart>
                                <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                                    {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                                </Pie>
                                <Tooltip formatter={(v: number) => [`$${v.toFixed(2)}`, 'Value']} />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>

                    {/* Predicted Forecast by Horizon */}
                    {portfolioForecast && (
                        <div className="p-6 bg-white/5 border border-white/10 rounded-xl">
                            <h3 className="text-lg font-semibold text-white mb-4">Portfolio Forecast</h3>
                            <div className="space-y-3">
                                {Object.entries(portfolioForecast.forecasts || {}).map(([horizon, data]: [string, any]) => (
                                    <div key={horizon} className="flex items-center justify-between p-3 bg-white/5 rounded-lg">
                                        <span className="text-sm text-gray-400">{horizon.toUpperCase()}</span>
                                        <div className="text-right">
                                            <div className="text-sm font-semibold text-white">${data.value.toLocaleString()}</div>
                                            <div className={`text-[10px] ${data.change >= 0 ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>
                                                {data.change >= 0 ? '+' : ''}${data.change.toFixed(2)} ({data.change_pct.toFixed(2)}%)
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Performance Chart */}
                    <div className="p-6 bg-white/5 border border-white/10 rounded-xl">
                        <h3 className="text-sm font-semibold text-white mb-3">30-Day Performance</h3>
                        <ResponsiveContainer width="100%" height={150}>
                            <LineChart data={perfData}>
                                <XAxis dataKey="date" hide />
                                <YAxis hide domain={['dataMin - 100', 'dataMax + 100']} />
                                <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} dot={false} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* Add Holding Modal */}
            {showAddModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
                    <div className="w-[480px] p-6 bg-[#0f172a] border border-white/10 rounded-2xl shadow-2xl">
                        <div className="flex items-center justify-between mb-6">
                            <h3 className="text-xl font-semibold text-white">Add Holding</h3>
                            <button onClick={() => setShowAddModal(false)} className="p-1.5 hover:bg-white/5 rounded-lg"><X className="w-5 h-5 text-gray-400" /></button>
                        </div>
                        <div className="space-y-4">
                            <div>
                                <label className="text-sm text-gray-400 mb-1.5 block">Ticker Symbol</label>
                                <input type="text" value={newHolding.ticker} onChange={(e) => setNewHolding(prev => ({ ...prev, ticker: e.target.value.toUpperCase() }))}
                                    placeholder="e.g. AAPL" className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-[#3b82f6] placeholder:text-gray-600" />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="text-sm text-gray-400 mb-1.5 block">Shares</label>
                                    <input type="number" value={newHolding.shares} onChange={(e) => setNewHolding(prev => ({ ...prev, shares: e.target.value }))}
                                        placeholder="50" className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-[#3b82f6] placeholder:text-gray-600" />
                                </div>
                                <div>
                                    <label className="text-sm text-gray-400 mb-1.5 block">Buy Price ($)</label>
                                    <input type="number" step="0.01" value={newHolding.buy_price} onChange={(e) => setNewHolding(prev => ({ ...prev, buy_price: e.target.value }))}
                                        placeholder="165.00" className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-[#3b82f6] placeholder:text-gray-600" />
                                </div>
                            </div>
                            <div>
                                <label className="text-sm text-gray-400 mb-1.5 block">Buy Date (optional)</label>
                                <input type="date" value={newHolding.buy_date} onChange={(e) => setNewHolding(prev => ({ ...prev, buy_date: e.target.value }))}
                                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-[#3b82f6]" />
                            </div>
                            <button onClick={handleAddHolding} className="w-full py-3 bg-[#3b82f6] hover:bg-[#2563eb] text-white rounded-lg font-medium transition-all">
                                Add to Portfolio
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
