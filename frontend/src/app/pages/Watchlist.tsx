import { useState, useEffect } from "react";
import { fetchWatchlist, addToWatchlist, removeFromWatchlist, updateWatchlistAlerts } from "../services/api";
import { Star, Bell, BellOff, Trash2, Plus, Search, TrendingUp, TrendingDown, Settings, X, Mail } from "lucide-react";

// S&P 100 tickers for search
const SP100 = ['AAPL', 'ABBV', 'ABT', 'ACN', 'ADBE', 'AIG', 'AMD', 'AMGN', 'AMT', 'AMZN', 'AVGO', 'AXP', 'BA', 'BAC', 'BK', 'BKNG', 'BLK', 'BMY', 'C', 'CAT', 'CHTR', 'CL', 'CMCSA', 'COF', 'COP', 'COST', 'CRM', 'CSCO', 'CVS', 'CVX', 'DE', 'DHR', 'DIS', 'DOW', 'DUK', 'EMR', 'EXC', 'F', 'FDX', 'GD', 'GE', 'GILD', 'GM', 'GOOG', 'GOOGL', 'GS', 'HD', 'HON', 'IBM', 'INTC', 'INTU', 'JNJ', 'JPM', 'KHC', 'KO', 'LIN', 'LLY', 'LMT', 'LOW', 'MA', 'MCD', 'MDLZ', 'MDT', 'MET', 'META', 'MMM', 'MO', 'MRK', 'MS', 'MSFT', 'NEE', 'NFLX', 'NKE', 'NVDA', 'ORCL', 'PEP', 'PFE', 'PG', 'PM', 'PYPL', 'QCOM', 'RTX', 'SBUX', 'SCHW', 'SO', 'SPG', 'T', 'TGT', 'TMO', 'TMUS', 'TSLA', 'TXN', 'UNH', 'UNP', 'UPS', 'USB', 'V', 'VZ', 'WBA', 'WFC', 'WMT', 'XOM'];

const FALLBACK_WATCHLIST = [
    { id: 1, ticker: 'AAPL', company_name: 'Apple Inc.', alert_enabled: true, price_change_threshold: 2.0, confidence_threshold: 80, daily_digest: true, latest_prediction: { current_price: 178.42, direction: 'BULLISH', confidence: 0.87, hourly_change: 0.34, sentiment_score: 0.68, rsi: 62.4 } },
    { id: 2, ticker: 'TSLA', company_name: 'Tesla Inc.', alert_enabled: true, price_change_threshold: 3.0, confidence_threshold: 85, daily_digest: true, latest_prediction: { current_price: 196.84, direction: 'BULLISH', confidence: 0.91, hourly_change: 1.15, sentiment_score: 0.81, rsi: 71.3 } },
    { id: 3, ticker: 'NVDA', company_name: 'NVIDIA Corp.', alert_enabled: true, price_change_threshold: 2.5, confidence_threshold: 80, daily_digest: false, latest_prediction: { current_price: 875.30, direction: 'BULLISH', confidence: 0.88, hourly_change: 0.52, sentiment_score: 0.72, rsi: 66.1 } },
    { id: 4, ticker: 'AMZN', company_name: 'Amazon.com Inc.', alert_enabled: false, price_change_threshold: 2.0, confidence_threshold: 70, daily_digest: false, latest_prediction: { current_price: 183.27, direction: 'BEARISH', confidence: 0.65, hourly_change: -0.45, sentiment_score: -0.32, rsi: 42.8 } },
];

export function Watchlist() {
    const [items, setItems] = useState<any[]>(FALLBACK_WATCHLIST);
    const [showAddModal, setShowAddModal] = useState(false);
    const [showSettingsFor, setShowSettingsFor] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<string[]>([]);
    const [alertSettings, setAlertSettings] = useState<any>({});

    useEffect(() => {
        async function loadData() {
            const data = await fetchWatchlist();
            if (data?.items?.length) setItems(data.items);
        }
        loadData();
    }, []);

    const handleSearch = (query: string) => {
        setSearchQuery(query);
        if (query.length >= 1) {
            const q = query.toUpperCase();
            const existing = items.map(i => i.ticker);
            setSearchResults(SP100.filter(t => t.includes(q) && !existing.includes(t)).slice(0, 10));
        } else {
            setSearchResults([]);
        }
    };

    const handleAdd = async (ticker: string) => {
        await addToWatchlist({ ticker, alert_enabled: true });
        // Add locally immediately
        setItems(prev => [...prev, {
            id: Date.now(), ticker, alert_enabled: true, price_change_threshold: 2.0,
            confidence_threshold: 80, daily_digest: false, latest_prediction: null,
        }]);
        setShowAddModal(false);
        setSearchQuery('');
        setSearchResults([]);
    };

    const handleRemove = async (ticker: string) => {
        await removeFromWatchlist(ticker);
        setItems(prev => prev.filter(i => i.ticker !== ticker));
    };

    const handleToggleAlert = async (ticker: string, currentState: boolean) => {
        await updateWatchlistAlerts(ticker, { alert_enabled: !currentState });
        setItems(prev => prev.map(i => i.ticker === ticker ? { ...i, alert_enabled: !currentState } : i));
    };

    const handleSaveSettings = async (ticker: string) => {
        const settings = alertSettings[ticker];
        if (settings) await updateWatchlistAlerts(ticker, settings);
        setShowSettingsFor(null);
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-semibold text-white mb-1 flex items-center gap-3">
                        <Star className="w-7 h-7 text-[#f59e0b]" /> My Watchlist
                    </h2>
                    <p className="text-sm text-gray-500">Starred stocks with alert configurations • Alerts sent via n8n email workflow</p>
                </div>
                <button onClick={() => setShowAddModal(true)}
                    className="flex items-center gap-2 px-5 py-2.5 bg-[#3b82f6] hover:bg-[#2563eb] text-white rounded-lg text-sm font-medium transition-all">
                    <Plus className="w-4 h-4" /> Add Stock
                </button>
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-4 gap-4">
                <div className="p-4 bg-white/[0.03] border border-white/5 rounded-xl">
                    <div className="text-sm text-gray-400">Watching</div>
                    <div className="text-2xl font-semibold text-white">{items.length}</div>
                </div>
                <div className="p-4 bg-white/[0.03] border border-white/5 rounded-xl">
                    <div className="text-sm text-gray-400">Alerts Active</div>
                    <div className="text-2xl font-semibold text-[#10b981]">{items.filter(i => i.alert_enabled).length}</div>
                </div>
                <div className="p-4 bg-white/[0.03] border border-white/5 rounded-xl">
                    <div className="text-sm text-gray-400">Bullish</div>
                    <div className="text-2xl font-semibold text-[#10b981]">{items.filter(i => i.latest_prediction?.direction === 'BULLISH').length}</div>
                </div>
                <div className="p-4 bg-white/[0.03] border border-white/5 rounded-xl">
                    <div className="text-sm text-gray-400">Bearish</div>
                    <div className="text-2xl font-semibold text-[#ef4444]">{items.filter(i => i.latest_prediction?.direction === 'BEARISH').length}</div>
                </div>
            </div>

            {/* Watchlist Grid */}
            <div className="grid grid-cols-2 gap-4">
                {items.map((item) => {
                    const pred = item.latest_prediction || {};
                    const isUp = pred.direction === 'BULLISH';
                    const isSettingsOpen = showSettingsFor === item.ticker;

                    return (
                        <div key={item.ticker} className="p-5 bg-white/[0.03] border border-white/5 rounded-xl hover:bg-white/[0.05] transition-all">
                            <div className="flex items-start justify-between mb-4">
                                <div className="flex items-center gap-3">
                                    <Star className="w-5 h-5 text-[#f59e0b] fill-[#f59e0b]" />
                                    <div>
                                        <div className="text-lg font-semibold text-white">{item.ticker}</div>
                                        {item.company_name && <div className="text-xs text-gray-500">{item.company_name}</div>}
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <button onClick={() => handleToggleAlert(item.ticker, item.alert_enabled)}
                                        className={`p-1.5 rounded-lg transition-colors ${item.alert_enabled ? 'bg-[#10b981]/10 hover:bg-[#10b981]/20' : 'bg-white/5 hover:bg-white/10'}`}>
                                        {item.alert_enabled ? <Bell className="w-4 h-4 text-[#10b981]" /> : <BellOff className="w-4 h-4 text-gray-500" />}
                                    </button>
                                    <button onClick={() => setShowSettingsFor(isSettingsOpen ? null : item.ticker)}
                                        className="p-1.5 bg-white/5 hover:bg-white/10 rounded-lg transition-colors">
                                        <Settings className="w-4 h-4 text-gray-400" />
                                    </button>
                                    <button onClick={() => handleRemove(item.ticker)}
                                        className="p-1.5 hover:bg-[#ef4444]/10 rounded-lg transition-colors">
                                        <Trash2 className="w-4 h-4 text-gray-500 hover:text-[#ef4444]" />
                                    </button>
                                </div>
                            </div>

                            {pred.current_price ? (
                                <>
                                    <div className="grid grid-cols-4 gap-3 mb-3">
                                        <div>
                                            <div className="text-[10px] text-gray-500">Price</div>
                                            <div className="text-sm font-semibold text-white">${pred.current_price?.toFixed(2)}</div>
                                        </div>
                                        <div>
                                            <div className="text-[10px] text-gray-500">1H Change</div>
                                            <div className={`text-sm font-semibold ${(pred.hourly_change || 0) >= 0 ? 'text-[#10b981]' : 'text-[#ef4444]'}`}>
                                                {(pred.hourly_change || 0) >= 0 ? '+' : ''}{(pred.hourly_change || 0).toFixed(2)}%
                                            </div>
                                        </div>
                                        <div>
                                            <div className="text-[10px] text-gray-500">Sentiment</div>
                                            <div className={`text-sm font-semibold ${(pred.sentiment_score || 0) > 0 ? 'text-[#10b981]' : (pred.sentiment_score || 0) < 0 ? 'text-[#ef4444]' : 'text-gray-400'}`}>
                                                {(pred.sentiment_score || 0).toFixed(2)}
                                            </div>
                                        </div>
                                        <div>
                                            <div className="text-[10px] text-gray-500">Confidence</div>
                                            <div className="text-sm font-semibold text-[#3b82f6]">{Math.round((pred.confidence || 0) * 100)}%</div>
                                        </div>
                                    </div>
                                    <div className="flex items-center justify-between">
                                        <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium ${isUp ? 'bg-[#10b981]/15 text-[#10b981]' : 'bg-[#ef4444]/15 text-[#ef4444]'}`}>
                                            {isUp ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                            {pred.direction}
                                        </span>
                                        {item.daily_digest && (
                                            <span className="flex items-center gap-1 text-[10px] text-gray-500"><Mail className="w-3 h-3" /> Email Digest ON</span>
                                        )}
                                    </div>
                                </>
                            ) : (
                                <div className="text-sm text-gray-500">Data will be available after next prediction run</div>
                            )}

                            {/* Alert Settings */}
                            {isSettingsOpen && (
                                <div className="mt-4 pt-4 border-t border-white/5 space-y-3">
                                    <div className="text-sm font-medium text-white mb-2">Alert Thresholds (n8n email)</div>
                                    <div className="grid grid-cols-2 gap-3">
                                        <div>
                                            <label className="text-[10px] text-gray-500 mb-1 block">Price Change (%)</label>
                                            <input type="number" step="0.5" defaultValue={item.price_change_threshold}
                                                onChange={(e) => setAlertSettings((prev: any) => ({ ...prev, [item.ticker]: { ...prev[item.ticker], price_change_threshold: parseFloat(e.target.value) } }))}
                                                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-white text-sm focus:outline-none focus:ring-1 focus:ring-[#3b82f6]" />
                                        </div>
                                        <div>
                                            <label className="text-[10px] text-gray-500 mb-1 block">Confidence (%)</label>
                                            <input type="number" step="5" defaultValue={item.confidence_threshold}
                                                onChange={(e) => setAlertSettings((prev: any) => ({ ...prev, [item.ticker]: { ...prev[item.ticker], confidence_threshold: parseFloat(e.target.value) } }))}
                                                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-white text-sm focus:outline-none focus:ring-1 focus:ring-[#3b82f6]" />
                                        </div>
                                    </div>
                                    <div className="flex items-center justify-between">
                                        <label className="flex items-center gap-2 cursor-pointer">
                                            <input type="checkbox" defaultChecked={item.daily_digest}
                                                onChange={(e) => setAlertSettings((prev: any) => ({ ...prev, [item.ticker]: { ...prev[item.ticker], daily_digest: e.target.checked } }))}
                                                className="w-4 h-4 rounded border-white/20 bg-white/5 text-[#3b82f6]" />
                                            <span className="text-sm text-gray-400">Daily Email Digest</span>
                                        </label>
                                        <button onClick={() => handleSaveSettings(item.ticker)}
                                            className="px-3 py-1.5 bg-[#3b82f6] text-white text-xs rounded-lg hover:bg-[#2563eb] transition-all">Save</button>
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Add Stock Modal */}
            {showAddModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
                    <div className="w-[480px] p-6 bg-[#0f172a] border border-white/10 rounded-2xl shadow-2xl">
                        <div className="flex items-center justify-between mb-6">
                            <h3 className="text-xl font-semibold text-white">Add to Watchlist</h3>
                            <button onClick={() => { setShowAddModal(false); setSearchResults([]); setSearchQuery(''); }}>
                                <X className="w-5 h-5 text-gray-400" />
                            </button>
                        </div>
                        <div className="relative mb-4">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                            <input type="text" value={searchQuery} onChange={(e) => handleSearch(e.target.value)}
                                placeholder="Search S&P 100 tickers... (AAPL, TSLA, NVDA)"
                                className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-[#3b82f6] placeholder:text-gray-500"
                                autoFocus />
                        </div>
                        {searchQuery.length > 0 && (
                            <div className="space-y-1 max-h-[300px] overflow-y-auto">
                                {searchResults.length === 0 ? (
                                    <div className="p-4 text-center text-gray-500 text-sm">
                                        {SP100.some(t => t.includes(searchQuery.toUpperCase()))
                                            ? `"${searchQuery.toUpperCase()}" matches are already in your watchlist`
                                            : `No S&P 100 ticker matches "${searchQuery.toUpperCase()}"`}
                                    </div>
                                ) : (
                                    searchResults.map((ticker) => (
                                        <button key={ticker} onClick={() => handleAdd(ticker)}
                                            className="w-full flex items-center justify-between p-3 bg-white/[0.03] border border-white/5 rounded-lg hover:bg-white/[0.06] transition-all text-left">
                                            <div className="text-white font-semibold">{ticker}</div>
                                            <div className="flex items-center gap-2 text-[#3b82f6]">
                                                <span className="text-xs">Add</span>
                                                <Plus className="w-4 h-4" />
                                            </div>
                                        </button>
                                    ))
                                )}
                            </div>
                        )}
                        {searchQuery.length === 0 && (
                            <div className="text-sm text-gray-500 text-center py-4">Type a ticker symbol to search from S&P 100</div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
