<div align="center">

# 🧠 Market Sentinel Intelligence Engine

### Production-Grade Stock Prediction via Multi-Source NLP + Ensemble ML

A complete **end-to-end ML pipeline** that scrapes financial sentiment from Reddit and news feeds, scores it using **FinBERT** (finance-tuned BERT), engineers 50+ technical and sentiment features, and predicts stock movements using an **LSTM + XGBoost ensemble** — backed by **PostgreSQL**, scheduled with **APScheduler** (hourly cron), tracked with **MLflow**, served via **FastAPI**, alerted via **n8n**, and visualized on a **React dashboard**.

[![CI](https://github.com/charan2456/stock_price_predictor/actions/workflows/ci.yml/badge.svg)](https://github.com/charan2456/stock_price_predictor/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)](https://www.postgresql.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Prediction_API-009688)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-Dashboard-61DAFB)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED)](https://www.docker.com/)

</div>

---

## 💡 Why This Exists

Stock prediction is a well-explored domain, but most projects on GitHub share the same fatal flaw: **they treat it as a single-model, single-signal problem**. In reality, markets are driven by a complex interplay of quantitative signals, crowd psychology, and information flow.

This project takes a fundamentally different approach:

1. **Multi-source signal fusion** — Not just price data. We combine Reddit sentiment (crowd psychology), financial news (information flow), and technical indicators (quantitative patterns)
2. **Finance-specific NLP** — Instead of generic VADER sentiment, we use **FinBERT**, a transformer fine-tuned on 10,000+ financial texts that understands "bearish divergence" and "guidance raised"
3. **Ensemble heterogeneity** — LSTM captures sequential temporal dynamics while XGBoost excels at feature interactions. Combining them yields better generalization
4. **Hourly analysis** — Predictions run every hour via APScheduler cron jobs, stored in PostgreSQL, with n8n polling for automated alerts
5. **Production-grade engineering** — PostgreSQL persistence, MLflow tracking, FastAPI serving, React dashboard, Docker deployment, CI/CD

---

## 🏗️ System Architecture



```
┌─────────────────┐     ┌───────────────────────────────────────────────┐     ┌──────────────┐
│  DATA SOURCES   │     │           BACKEND (Python)                   │     │   FRONTEND   │
│                 │     │                                               │     │              │
│  Reddit API     │────→│  FastAPI Server ←→ PostgreSQL                │←───→│ React + Vite │
│  News RSS       │     │  APScheduler (Hourly Cron)                   │     │ TypeScript   │
│  Yahoo Finance  │     │  FinBERT NLP + LSTM + XGBoost Ensemble      │     │ Recharts     │
│                 │     │  MLflow Experiment Tracking                   │     │              │
└─────────────────┘     └──────────────┬────────────────────────────────┘     └──────────────┘
                                       │
                                       ▼
                               ┌───────────────┐     ┌──────────────────┐
                               │  PostgreSQL    │────→│  n8n Workflow    │
                               │  Predictions   │     │  Engine          │
                               │  Sentiment     │     │  → Email Alerts  │
                               │  Trade Logs    │     │  → Slack Alerts  │
                               └───────────────┘     └──────────────────┘
```

### Data Flow

1. **APScheduler** triggers hourly cron job on weekdays
2. Backend scrapes Reddit, News RSS, and Yahoo Finance market data
3. **FinBERT** scores sentiment on financial text
4. **LSTM + XGBoost ensemble** predicts stock direction + confidence
5. Results saved to **PostgreSQL** (predictions, sentiment, trade logs)
6. **FastAPI** serves results to React dashboard via REST API
7. **n8n** polls PostgreSQL for alerts → sends Email/Slack notifications

---

## ✨ Key Features

| Category | Feature | Details |
|----------|---------|---------| 
| **Data** | Multi-source ingestion | Reddit (PRAW), Financial News (RSS), Market Data (yfinance) |
| **Data** | Ticker-aligned merging | Aggregates text by ticker × hour with `[SEP]` tokenization |
| **NLP** | FinBERT sentiment | Finance-tuned BERT (`ProsusAI/finbert`) with GPU acceleration |
| **NLP** | Weighted aggregation | Length-weighted multi-text sentiment scoring |
| **Features** | 8 technical indicators | RSI, MACD, Bollinger Bands, SMA, EMA, ATR, OBV, VWAP |
| **Features** | Derived signals | Crossover detection, overbought/oversold, price-to-MA ratios |
| **Features** | Lag features | Price lags, sentiment lags, rolling μ/σ, momentum, gap |
| **ML** | LSTM (PyTorch) | Multi-layer with dropout, AdamW, LR scheduling, early stopping |
| **ML** | XGBoost | Histogram-based gradient boosting with feature importance |
| **ML** | Ensemble | Weighted averaging, stacking (Ridge meta-learner), blending |
| **Database** | PostgreSQL 16 | Predictions, sentiment entries, trade logs, backtest results |
| **Scheduling** | APScheduler | Hourly cron jobs (weekdays), configurable timezone |
| **Automation** | n8n | Webhook polling, Email/Slack alerts on prediction events |
| **MLOps** | MLflow tracking | Parameters, metrics, artifacts, model registry |
| **Serving** | FastAPI | 12 REST endpoints with CORS + PostgreSQL backend |
| **Frontend** | React + Vite | 4-page dashboard: Overview, Predictions, Sentiment, Backtest |
| **Validation** | Backtesting | Sharpe ratio, max drawdown, alpha vs benchmark, win rate |
| **DevOps** | Docker + CI/CD | Multi-service compose, GitHub Actions, matrix testing |

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **PostgreSQL 16** (or use Docker)
- **Node.js 18+** (for frontend)

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/charan2456/stock_price_predictor.git
cd stock_price_predictor

# Set up environment variables
cp .env.example .env
# Edit .env with your Reddit API credentials + database URL

# Start all services (PostgreSQL + API + MLflow + Frontend)
make docker-up

# Services:
# - API:       http://localhost:8000
# - Frontend:  http://localhost:3000
# - MLflow:    http://localhost:5000
# - PostgreSQL: localhost:5432
```

### Option 2: Manual Setup

```bash
# 1. Install Python dependencies
pip install -e ".[dev]"

# 2. Start PostgreSQL
docker run -d --name sentinel-pg \
  -e POSTGRES_DB=market_sentinel \
  -e POSTGRES_USER=sentinel \
  -e POSTGRES_PASSWORD=sentinel \
  -p 5432:5432 \
  postgres:16-alpine

# 3. Set up environment
cp .env.example .env

# 4. Run the backend pipeline
make scrape     # Collect data from Reddit + News + Yahoo Finance
make train      # Train ensemble model with MLflow tracking
make serve      # Start FastAPI server (auto-creates DB tables)

# 5. Start the frontend
cd frontend
npm install
npm run dev     # → http://localhost:5180
```

---

## 📦 Project Structure

```
stock_price_predictor/
│
├── src/                              # Backend — Production source code
│   ├── data/                         # Data ingestion layer
│   │   ├── reddit_scraper.py         #   PRAW multi-subreddit scraper
│   │   ├── news_scraper.py           #   RSS feed aggregator
│   │   ├── market_data.py            #   yfinance OHLCV fetcher
│   │   └── data_pipeline.py          #   Pipeline orchestrator
│   │
│   ├── features/                     # Feature engineering
│   │   ├── sentiment.py              #   FinBERT sentiment analyzer
│   │   ├── technical_indicators.py   #   RSI, MACD, BB, SMA, EMA, ATR, OBV, VWAP
│   │   └── feature_engineering.py    #   Full pipeline orchestrator
│   │
│   ├── models/                       # ML models
│   │   ├── lstm_model.py             #   PyTorch LSTM with early stopping
│   │   ├── xgboost_model.py          #   XGBoost with feature importance
│   │   ├── ensemble.py               #   Weighted/Stacking/Blending ensemble
│   │   └── trainer.py                #   MLflow-instrumented training
│   │
│   ├── database/                     # PostgreSQL persistence layer
│   │   ├── models.py                 #   SQLAlchemy ORM models
│   │   └── db.py                     #   Engine, session factory, init
│   │
│   ├── serving/                      # API serving
│   │   └── app.py                    #   FastAPI server (12 endpoints)
│   │
│   ├── scheduling/                   # Hourly cron jobs
│   │   └── scheduler.py             #   APScheduler configuration
│   │
│   ├── backtesting/                  # Strategy validation
│   │   └── backtester.py             #   Sharpe, drawdown, alpha computation
│   │
│   └── utils/                        # Shared utilities
│       ├── config.py                 #   YAML config with env-var overrides
│       └── logger.py                 #   Structured logging (loguru)
│
├── frontend/                         # Frontend — React Dashboard
│   ├── src/
│   │   ├── app/
│   │   │   ├── pages/                #   Dashboard, Predictions, Sentiment, Backtest
│   │   │   ├── components/           #   Layout (sidebar + shell)
│   │   │   ├── services/
│   │   │   │   └── api.ts            #   API client (fetch from FastAPI)
│   │   │   ├── Layout.tsx            #   App shell with navigation
│   │   │   └── routes.ts             #   React Router configuration
│   │   ├── styles/                   #   Tailwind CSS + dark theme
│   │   └── main.tsx                  #   App entry point
│   ├── package.json
│   └── vite.config.ts
│
├── configs/
│   └── default.yaml                  # All hyperparameters + DB config
│
├── tests/
│   └── test_core.py                  # Config, indicators, backtester tests
│
├── docker/
│   ├── Dockerfile                    # API server container
│   └── docker-compose.yml            # PostgreSQL + API + MLflow + Frontend
│
│
├── .github/workflows/
│   └── ci.yml                        # Lint + typecheck + test (Python 3.10, 3.11)
│
├── Makefile                          # One-command operations
├── pyproject.toml                    # Modern Python packaging
└── .env.example                      # Required environment variables
```

---

## 🗄️ Database Schema (PostgreSQL)

The application persists all prediction results, sentiment data, and trade logs to PostgreSQL using SQLAlchemy ORM:

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  prediction_runs    │     │ ticker_predictions    │     │  sentiment_entries  │
├─────────────────────┤     ├─────────────────────┤     ├─────────────────────┤
│ id (PK)             │     │ id (PK)             │     │ id (PK)             │
│ run_id (UNIQUE)     │──┐  │ run_id (FK)         │     │ ticker              │
│ timestamp           │  └─→│ ticker              │     │ source              │
│ status              │     │ current_price       │     │ headline            │
│ total_tickers       │     │ predicted_return    │     │ sentiment           │
│ bullish_count       │     │ direction           │     │ sentiment_score     │
│ bearish_count       │     │ confidence          │     │ timestamp           │
└─────────────────────┘     │ hourly_change       │     └─────────────────────┘
                            │ sentiment_score     │
                            │ rsi                 │     ┌─────────────────────┐
                            └─────────────────────┘     │  backtest_results   │
                                                        ├─────────────────────┤
┌─────────────────────┐                                 │ id (PK)             │
│    trade_log        │                                 │ run_id              │
├─────────────────────┤                                 │ total_return        │
│ id (PK)             │                                 │ sharpe_ratio        │
│ run_id              │                                 │ max_drawdown        │
│ ticker              │                                 │ win_rate            │
│ action              │                                 │ total_trades        │
│ predicted_return    │                                 │ alpha               │
│ actual_return       │                                 │ profit_factor       │
│ pnl                 │                                 │ timestamp           │
│ date / time         │                                 └─────────────────────┘
└─────────────────────┘
```

---

## 🔬 Technical Deep Dives

### FinBERT vs VADER — Why It Matters

| Text | VADER Score | FinBERT Score | Correct? |
|------|-----------|-------------|----------|
| *"Stock surged on strong earnings guidance"* | +0.42 | **+0.91** | FinBERT ✅ |
| *"The short squeeze is getting out of hand"* | -0.31 | **+0.15** | FinBERT ✅ |
| *"Revenue declined but beat expectations"* | -0.44 | **+0.62** | FinBERT ✅ |
| *"Bearish divergence on the daily chart"* | -0.24 | **-0.78** | FinBERT ✅ |

FinBERT understands **financial context** — "short squeeze" is positive for holders, "beat expectations" is positive despite "declined", and "bearish divergence" has stronger negative signal than generic sentiment tools detect.

### Ensemble Strategy — Why LSTM + XGBoost?

```
LSTM Strengths:                    XGBoost Strengths:
├── Sequential pattern learning    ├── Feature interaction detection
├── Long-range temporal deps       ├── Handles heterogeneous features
├── Non-linear dynamics            ├── Naturally handles missing values
└── Momentum/regime detection      └── Built-in feature importance

                Combined = More robust predictions
                    │
                    ▼
        ┌───────────────────────┐
        │  Ensemble Methods:    │
        │  • Weighted (0.4/0.6) │
        │  • Stacking (Ridge)   │
        │  • Blending           │
        └───────────────────────┘
```

### Hourly Scheduling — APScheduler + Cron

```yaml
# configs/default.yaml
scheduling:
  enabled: true
  cron_hour: "*"              # Every hour
  cron_minute: 0              # At :00
  cron_day_of_week: "mon-fri" # Weekdays only
  timezone: "Asia/Kolkata"    # IST

database:
  url: "postgresql://sentinel:sentinel@localhost:5432/market_sentinel"
```

The scheduler runs inside the FastAPI server process. Each hourly run:
1. Fetches latest market data for all configured tickers
2. Runs FinBERT sentiment + technical indicators
3. Predicts direction/returns via LSTM + XGBoost ensemble
4. Writes results to PostgreSQL
5. n8n polls the database and sends Email/Slack alerts if thresholds are met

---

## 📡 API Reference

Start the server with `make serve`, then:

### `GET /health`
```json
{
  "status": "healthy",
  "model_loaded": true,
  "database": "postgresql",
  "scheduler_running": true,
  "last_prediction_run": "2026-02-22T14:00:00Z",
  "uptime_seconds": 3600.5,
  "version": "1.0.0"
}
```

### `GET /predictions/latest`
Returns the most recent hourly prediction run with all ticker predictions.

### `GET /predictions/history?limit=24`
Returns the last 24 prediction runs (one per hour).

### `GET /predictions/ticker/{ticker}?limit=24`
Returns hourly prediction history for a specific ticker.

### `POST /predictions/run-now`
Manually trigger an immediate prediction run (for n8n or testing).

### `GET /sentiment/feed?limit=20`
Get recent sentiment entries from PostgreSQL.

### `GET /sentiment/ticker/{ticker}?limit=24`
Get hourly sentiment history for a specific ticker.

### `GET /backtest/results`
Get latest backtest metrics (Sharpe, drawdown, alpha, win rate).

### `GET /backtest/trades?limit=50`
Get recent trade log entries with P&L.

### `GET /scheduler/status`
Get scheduler status and next run time.

### Interactive docs: `http://localhost:8000/docs`

---

## 📊 MLflow Experiment Tracking

Every training run automatically logs:

| What | Example |
|------|---------| 
| **Parameters** | `lstm_hidden_size=128`, `xgb_n_estimators=500`, `ensemble_method=weighted` |
| **Metrics** | `rmse=0.0234`, `mae=0.0189`, `r2=0.42`, `directional_accuracy=0.58`, `sharpe=1.23` |
| **Artifacts** | Model weights, feature importance CSV, scaler objects |

```bash
# Launch MLflow UI
make mlflow-ui
# Visit http://localhost:5000
```

---

## 🐳 Docker Deployment

```bash
# Start all 4 services
make docker-up

# Services:
# ┌──────────────┬──────────────────────────────────────┐
# │ Service      │ URL                                  │
# ├──────────────┼──────────────────────────────────────┤
# │ PostgreSQL   │ localhost:5432                        │
# │ FastAPI      │ http://localhost:8000                 │
# │ Frontend     │ http://localhost:3000                 │
# │ MLflow       │ http://localhost:5000                 │
# │ API Docs     │ http://localhost:8000/docs            │
# └──────────────┴──────────────────────────────────────┘
```

### Docker Compose Architecture

```yaml
services:
  postgres:     # PostgreSQL 16 Alpine — persistent storage
  api:          # FastAPI + APScheduler + ML models
  mlflow:       # MLflow tracking server
  frontend:     # React + Vite dashboard
```

---

## ⚙️ Configuration

All hyperparameters live in `configs/default.yaml`:

```yaml
# Key sections:
data:
  tickers: ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
  reddit:
    subreddits: ["stocks", "wallstreetbets", "investing"]

features:
  sentiment:
    model: "ProsusAI/finbert"
  technical_indicators:
    - rsi (window: 14)
    - macd (12/26/9)
    - bollinger_bands (20, 2σ)

training:
  lstm:
    hidden_size: 128
    num_layers: 2
    sequence_length: 30
  xgboost:
    n_estimators: 500
    max_depth: 8
  ensemble:
    method: weighted  # or "stacking"
    weights: { lstm: 0.4, xgboost: 0.6 }

database:
  url: "postgresql://sentinel:sentinel@localhost:5432/market_sentinel"

scheduling:
  enabled: true
  cron_hour: "*"              # Every hour
  cron_minute: 0
  cron_day_of_week: "mon-fri"
  timezone: "Asia/Kolkata"

mlflow:
  experiment_name: "market-sentiment-engine"
```

Override any config via environment variables: `DATABASE_URL=postgresql://...`

---

## 🔔 n8n Alerting Integration

The system integrates with **n8n** for automated alerts:

1. **Webhook Trigger** — n8n polls `GET /predictions/latest` every hour
2. **Filter** — Check if any ticker has confidence > 80% or sentiment shift > 0.3
3. **Action** — Send Email/Slack notification with prediction details
4. **Dashboard Link** — Alert includes direct link to the Market Sentinel dashboard

---

## 🧪 Testing

```bash
make test          # Full test suite with coverage
make test-fast     # Quick run without coverage
make lint          # Ruff linting
make typecheck     # mypy type checking
make quality       # All checks (lint + typecheck + test)
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Run quality checks (`make quality`)
4. Commit with conventional commits (`git commit -m 'feat: add new indicator'`)
5. Push and open a PR

---

## 📝 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built by [Charan Kotapati](https://github.com/charan2456)**

*If this project helped you, consider giving it a ⭐*

</div>
