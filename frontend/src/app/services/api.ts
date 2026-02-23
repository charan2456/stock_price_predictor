/**
 * API service — Complete typed client for all Market Sentinel endpoints.
 * Falls back gracefully when API is unavailable.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T | null> {
    try {
        const res = await fetch(`${API_BASE}${path}`, {
            headers: { 'Content-Type': 'application/json' },
            ...options,
        });
        if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
        return await res.json();
    } catch (err) {
        console.warn(`[API] ${path}:`, err);
        return null;
    }
}

// ─── Health ──────────────────────────────────
export const fetchHealth = () => apiFetch<any>('/health');

// ─── Search ──────────────────────────────────
export const searchTickers = (q: string) => apiFetch<any>(`/search?q=${encodeURIComponent(q)}`);
export const addCustomTicker = (data: { ticker: string; company_name?: string }) =>
    apiFetch<any>('/tickers/add', { method: 'POST', body: JSON.stringify(data) });
export const getAllTickers = () => apiFetch<any>('/tickers/all');

// ─── Predictions ─────────────────────────────
export const fetchLatestPredictions = () => apiFetch<any>('/predictions/latest');
export const fetchPredictionHistory = (limit = 24) => apiFetch<any>(`/predictions/history?limit=${limit}`);
export const fetchTickerPredictions = (ticker: string, limit = 24) => apiFetch<any>(`/predictions/ticker/${ticker}?limit=${limit}`);
export const triggerPredictionRun = () => apiFetch<any>('/predictions/run-now', { method: 'POST' });

// ─── Forecasts ───────────────────────────────
export const fetchForecast = (ticker: string, horizon = '1d') => apiFetch<any>(`/forecast/${ticker}?horizon=${horizon}`);

// ─── Calculator ──────────────────────────────
export const calculateReturns = (data: { ticker: string; investment_amount: number; horizon: string }) =>
    apiFetch<any>('/calculator/returns', { method: 'POST', body: JSON.stringify(data) });

// ─── Watchlist ───────────────────────────────
export const fetchWatchlist = () => apiFetch<any>('/watchlist');
export const addToWatchlist = (data: { ticker: string; company_name?: string; alert_enabled?: boolean }) =>
    apiFetch<any>('/watchlist/add', { method: 'POST', body: JSON.stringify(data) });
export const removeFromWatchlist = (ticker: string) =>
    apiFetch<any>(`/watchlist/remove/${ticker}`, { method: 'DELETE' });
export const updateWatchlistAlerts = (ticker: string, data: any) =>
    apiFetch<any>(`/watchlist/${ticker}/alerts`, { method: 'PUT', body: JSON.stringify(data) });

// ─── Portfolio ───────────────────────────────
export const fetchPortfolio = () => apiFetch<any>('/portfolio');
export const addPortfolioHolding = (data: { ticker: string; shares: number; buy_price: number; buy_date?: string }) =>
    apiFetch<any>('/portfolio/add', { method: 'POST', body: JSON.stringify(data) });
export const removePortfolioHolding = (id: number) =>
    apiFetch<any>(`/portfolio/remove/${id}`, { method: 'DELETE' });
export const fetchPortfolioForecast = () => apiFetch<any>('/portfolio/forecast');

// ─── Sentiment ───────────────────────────────
export const fetchSentimentFeed = (limit = 20) => apiFetch<any>(`/sentiment/feed?limit=${limit}`);
export const fetchTickerSentiment = (ticker: string) => apiFetch<any>(`/sentiment/ticker/${ticker}`);

// ─── Backtest ────────────────────────────────
export const fetchBacktestResults = () => apiFetch<any>('/backtest/results');
export const fetchBacktestTrades = (limit = 50) => apiFetch<any>(`/backtest/trades?limit=${limit}`);

// ─── Accuracy ────────────────────────────────
export const fetchAccuracy = () => apiFetch<any>('/accuracy');
export const fetchTickerAccuracy = (ticker: string) => apiFetch<any>(`/accuracy/ticker/${ticker}`);

// ─── Alerts ──────────────────────────────────
export const fetchAlerts = (limit = 50, unreadOnly = false) => apiFetch<any>(`/alerts?limit=${limit}&unread_only=${unreadOnly}`);
export const markAlertRead = (id: number) => apiFetch<any>(`/alerts/${id}/read`, { method: 'PUT' });
export const markAllAlertsRead = () => apiFetch<any>('/alerts/read-all', { method: 'PUT' });

// ─── Market Overview ─────────────────────────
export const fetchMarketOverview = () => apiFetch<any>('/market/overview');

// ─── Comparison ──────────────────────────────
export const compareStocks = (tickers: string[]) => apiFetch<any>(`/compare?tickers=${tickers.join(',')}`);

// ─── Scheduler + Model ──────────────────────
export const fetchSchedulerStatus = () => apiFetch<any>('/scheduler/status');
export const fetchModelInfo = () => apiFetch<any>('/model/info');
