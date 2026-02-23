# Market Sentinel Dashboard

A comprehensive stock intelligence platform with multi-horizon price forecasts, portfolio tracking, watchlists with email alerts, and stock comparison tools — built for the Indian market (NSE/BSE).

## Features

| Feature | Description |
|---------|-------------|
| **Dashboard** | Live ticker strip, S&P 100 heatmap, market overview cards, 24H price chart, technical indicators, sentiment gauge |
| **Predictions** | Multi-horizon forecasts (1H, 4H, 1D, 7D) with confidence bands, returns calculator in ₹, confidence breakdown, model signals |
| **Sentiment** | Real-time sentiment feed from Reuters, Reddit, Yahoo Finance with trend charts |
| **Portfolio** | Track holdings with P&L, allocation pie chart, predicted 1D portfolio value, 30-day performance |
| **Watchlist** | Star stocks, per-stock alert thresholds (price change %, confidence %), daily email digest via n8n |
| **Compare** | Compare up to 5 stocks with radar chart, predicted returns bar chart, recommendation engine |
| **Backtest** | Strategy performance metrics (Sharpe, Alpha, Win Rate), equity curve vs SPY, hourly trade log |

## Indian Market Support

- **Trading hours**: 9:15 AM – 3:30 PM IST (Mon–Fri)
- **7-Day forecast**: Calculates across 5 trading days (excludes weekends)
- **Returns calculator**: Uses ₹ (Indian Rupees)
- **IST timestamps**: All times displayed in India Standard Time

## Tech Stack

- **Frontend**: React 19 + TypeScript + Vite
- **Charts**: Recharts (area, radar, pie, bar)
- **Icons**: Lucide React
- **Styling**: Vanilla CSS + utility classes
- **API**: FastAPI backend (optional — dashboard works with fallback data)
- **Alerts**: n8n email workflow integration

## Navigation

Collapsible sidebar with 7 sections:
- Dashboard • Predictions • Sentiment • Portfolio • Watchlist • Compare • Backtest

## Running Locally

```bash
npm install
npm run dev
```

Opens at http://localhost:5173 (or next available port).

## Backend (Optional)

The dashboard works standalone with comprehensive fallback data. To connect the FastAPI backend:

```bash
# Set API URL
echo "VITE_API_URL=http://localhost:8000" > .env

# Start backend
cd ..
python -m src.serving.app
```

## Project Structure

```
src/
├── app/
│   ├── components/       # Layout (sidebar + shell)
│   ├── pages/
│   │   ├── Dashboard.tsx       # Market overview + heatmap
│   │   ├── Predictions.tsx     # Merged forecasts + predictions + calculator
│   │   ├── SentimentFeed.tsx   # Sentiment analysis
│   │   ├── Portfolio.tsx       # Holdings tracker
│   │   ├── Watchlist.tsx       # Alert management
│   │   ├── Comparison.tsx      # Stock comparison
│   │   └── BacktestResults.tsx # Strategy backtesting
│   ├── services/
│   │   └── api.ts             # 30+ API endpoints with fallback
│   └── routes.ts              # Client-side routing
└── styles/
    └── index.css              # Design system
```