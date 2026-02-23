"""FastAPI application — Stock Price Predictor API.

All endpoints for the stock prediction platform:
- /health, /search, /predictions/*, /sentiment/*, /backtest/*
- /watchlist/*, /portfolio/*, /forecast/*, /calculator/*
- /accuracy/*, /alerts/*, /scheduler/*, /model/*
"""

from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import desc, func

from src.database.db import close_db, get_db, init_db
from src.database.models import (
    AlertLog,
    BacktestResult,
    PortfolioHolding,
    PredictionAccuracy,
    PredictionRun,
    SentimentEntry,
    TickerPrediction,
    TradeLog,
    UserTicker,
    WatchlistItem,
)
from src.utils.config import get_config

# ─── Global State ─────────────────────────────

_model = None
_scheduler = None
_start_time: float = 0.0

# S&P 100 — Pre-loaded tickers
SP100_TICKERS = [
    "AAPL", "ABBV", "ABT", "ACN", "ADBE", "AIG", "AMD", "AMGN", "AMT", "AMZN",
    "AVGO", "AXP", "BA", "BAC", "BK", "BKNG", "BLK", "BMY", "BRK.B", "C",
    "CAT", "CHTR", "CL", "CMCSA", "COF", "COP", "COST", "CRM", "CSCO", "CVS",
    "CVX", "DE", "DHR", "DIS", "DOW", "DUK", "EMR", "EXC", "F", "FDX",
    "GD", "GE", "GILD", "GM", "GOOG", "GOOGL", "GS", "HD", "HON", "IBM",
    "INTC", "INTU", "JNJ", "JPM", "KHC", "KO", "LIN", "LLY", "LMT", "LOW",
    "MA", "MCD", "MDLZ", "MDT", "MET", "META", "MMM", "MO", "MRK", "MS",
    "MSFT", "NEE", "NFLX", "NKE", "NVDA", "ORCL", "PEP", "PFE", "PG", "PM",
    "PYPL", "QCOM", "RTX", "SBUX", "SCHW", "SO", "SPG", "T", "TGT", "TMO",
    "TMUS", "TSLA", "TXN", "UNH", "UNP", "UPS", "USB", "V", "VZ", "WBA",
    "WFC", "WMT", "XOM",
]


# ─── Request / Response Models ────────────────

class PredictionRequest(BaseModel):
    ticker: str
    features: dict[str, float]

class WatchlistAddRequest(BaseModel):
    ticker: str
    company_name: Optional[str] = None
    alert_enabled: bool = True
    price_change_threshold: float = 2.0
    confidence_threshold: float = 80.0
    daily_digest: bool = False

class WatchlistUpdateRequest(BaseModel):
    alert_enabled: Optional[bool] = None
    price_change_threshold: Optional[float] = None
    confidence_threshold: Optional[float] = None
    sentiment_threshold: Optional[float] = None
    daily_digest: Optional[bool] = None

class PortfolioAddRequest(BaseModel):
    ticker: str
    company_name: Optional[str] = None
    shares: float
    buy_price: float
    buy_date: Optional[str] = None
    notes: Optional[str] = None

class CalculatorRequest(BaseModel):
    ticker: str
    investment_amount: float
    horizon: str = "1d"  # 1h, 4h, 1d, 1w

class UserTickerAddRequest(BaseModel):
    ticker: str
    company_name: Optional[str] = None
    exchange: Optional[str] = None
    sector: Optional[str] = None


# ─── Lifespan ─────────────────────────────────

@asynccontextmanager
async def _lifespan(app: FastAPI):
    global _model, _scheduler, _start_time
    _start_time = time.time()
    logger.info("Starting Stock Price Predictor API...")

    init_db()
    logger.info("PostgreSQL database ready")

    try:
        from src.models.ensemble import EnsembleModel
        _model = EnsembleModel()
        _model.load()
        logger.info("Ensemble model loaded successfully")
    except Exception as e:
        logger.warning("Model not loaded (will serve DB data): {err}", err=e)
        _model = None

    try:
        from src.scheduling.scheduler import create_scheduler
        _scheduler = create_scheduler()
        _scheduler.start()
        logger.info("APScheduler started (hourly predictions)")
    except Exception as e:
        logger.warning("Scheduler not started: {err}", err=e)
        _scheduler = None

    yield

    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
    close_db()
    logger.info("Server shutdown complete")


# ─── App ──────────────────────────────────────

app = FastAPI(
    title="Stock Price Predictor API",
    description="AI-powered stock predictions with hourly analysis, multi-horizon forecasting, portfolio tracking, and smart alerts",
    version="2.0.0",
    lifespan=_lifespan,
)

cfg = get_config()
cors_origins = cfg.serving.cors_origins if hasattr(cfg, "serving") and hasattr(cfg.serving, "cors_origins") else ["*"]
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


# ═══════════════════════════════════════════════
#  HEALTH
# ═══════════════════════════════════════════════

@app.get("/health")
def health():
    db = get_db()
    try:
        last_run = db.query(PredictionRun).order_by(desc(PredictionRun.timestamp)).first()
        ticker_count = db.query(func.count(func.distinct(TickerPrediction.ticker))).scalar() or 0
        watchlist_count = db.query(func.count(WatchlistItem.id)).scalar() or 0
        portfolio_count = db.query(func.count(PortfolioHolding.id)).scalar() or 0
    finally:
        db.close()

    return {
        "status": "healthy",
        "model_loaded": _model is not None,
        "database": "postgresql",
        "scheduler_running": _scheduler is not None and _scheduler.running if _scheduler else False,
        "last_prediction_run": last_run.timestamp.isoformat() if last_run else None,
        "tracked_tickers": ticker_count,
        "sp100_loaded": len(SP100_TICKERS),
        "watchlist_items": watchlist_count,
        "portfolio_holdings": portfolio_count,
        "uptime_seconds": round(time.time() - _start_time, 1),
        "version": "2.0.0",
    }


# ═══════════════════════════════════════════════
#  STOCK SEARCH
# ═══════════════════════════════════════════════

@app.get("/search")
def search_tickers(q: str = Query(..., min_length=1)):
    """Search for stock tickers. Searches S&P 100 + user-added tickers."""
    query = q.upper().strip()
    results = []

    # Search S&P 100
    for ticker in SP100_TICKERS:
        if query in ticker:
            results.append({"ticker": ticker, "source": "sp100"})

    # Search user-added tickers
    db = get_db()
    try:
        user_tickers = db.query(UserTicker).filter(UserTicker.ticker.ilike(f"%{query}%")).all()
        for ut in user_tickers:
            if not any(r["ticker"] == ut.ticker for r in results):
                results.append({
                    "ticker": ut.ticker,
                    "company_name": ut.company_name,
                    "exchange": ut.exchange,
                    "sector": ut.sector,
                    "source": "user_added",
                })
    finally:
        db.close()

    return {"query": q, "count": len(results), "results": results[:20]}


@app.post("/tickers/add")
def add_custom_ticker(req: UserTickerAddRequest):
    """Add a custom ticker beyond S&P 100. It will be fetched on the next hourly run."""
    db = get_db()
    try:
        existing = db.query(UserTicker).filter(UserTicker.ticker == req.ticker.upper()).first()
        if existing:
            return {"status": "already_exists", "ticker": req.ticker.upper()}

        ut = UserTicker(
            ticker=req.ticker.upper(),
            company_name=req.company_name,
            exchange=req.exchange,
            sector=req.sector,
        )
        db.add(ut)
        db.commit()
        return {"status": "added", "ticker": req.ticker.upper(), "message": "Will be included in next hourly prediction run"}
    finally:
        db.close()


@app.get("/tickers/all")
def get_all_tickers():
    """Get all tracked tickers (S&P 100 + user-added)."""
    db = get_db()
    try:
        user_tickers = db.query(UserTicker).all()
        custom = [{"ticker": ut.ticker, "company_name": ut.company_name, "sector": ut.sector} for ut in user_tickers]
    finally:
        db.close()

    return {
        "sp100": SP100_TICKERS,
        "sp100_count": len(SP100_TICKERS),
        "custom_tickers": custom,
        "custom_count": len(custom),
        "total": len(SP100_TICKERS) + len(custom),
    }


# ═══════════════════════════════════════════════
#  PREDICTIONS
# ═══════════════════════════════════════════════

@app.get("/predictions/latest")
def predictions_latest():
    db = get_db()
    try:
        run = db.query(PredictionRun).order_by(desc(PredictionRun.timestamp)).first()
        if not run:
            return {"status": "no_predictions", "predictions": []}

        predictions = db.query(TickerPrediction).filter(TickerPrediction.run_id == run.run_id).all()
        return {
            "run_id": run.run_id,
            "timestamp": run.timestamp.isoformat(),
            "status": run.status,
            "total_tickers": run.total_tickers,
            "bullish_count": run.bullish_count,
            "bearish_count": run.bearish_count,
            "predictions": [_serialize_prediction(p) for p in predictions],
        }
    finally:
        db.close()


@app.get("/predictions/history")
def predictions_history(limit: int = 24):
    db = get_db()
    try:
        runs = db.query(PredictionRun).order_by(desc(PredictionRun.timestamp)).limit(limit).all()
        return {"count": len(runs), "runs": [
            {"run_id": r.run_id, "timestamp": r.timestamp.isoformat(), "status": r.status,
             "total_tickers": r.total_tickers, "bullish_count": r.bullish_count, "bearish_count": r.bearish_count}
            for r in runs
        ]}
    finally:
        db.close()


@app.get("/predictions/ticker/{ticker}")
def predictions_by_ticker(ticker: str, limit: int = 24):
    db = get_db()
    try:
        preds = db.query(TickerPrediction).filter(
            TickerPrediction.ticker == ticker.upper()
        ).order_by(desc(TickerPrediction.timestamp)).limit(limit).all()
        return {"ticker": ticker.upper(), "count": len(preds), "predictions": [_serialize_prediction(p) for p in preds]}
    finally:
        db.close()


@app.post("/predictions/run-now")
async def run_predictions_now():
    from src.scheduling.scheduler import run_scheduled_predictions
    try:
        results = await run_scheduled_predictions()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction run failed: {e}")


# ═══════════════════════════════════════════════
#  FORECASTS (Multi-Horizon)
# ═══════════════════════════════════════════════

@app.get("/forecast/{ticker}")
def get_forecast(ticker: str, horizon: str = "1d"):
    """Get multi-horizon forecast for a ticker with confidence bands."""
    db = get_db()
    try:
        latest = db.query(TickerPrediction).filter(
            TickerPrediction.ticker == ticker.upper()
        ).order_by(desc(TickerPrediction.timestamp)).first()

        if not latest:
            raise HTTPException(status_code=404, detail=f"No predictions found for {ticker}")

        # Build forecast response
        current_price = latest.current_price or 0
        confidence = latest.confidence or 0.5

        forecasts = {
            "1h": {
                "predicted_price": latest.predicted_price_1h or current_price * (1 + (latest.predicted_return or 0)),
                "confidence_upper": current_price * 1.005,
                "confidence_lower": current_price * 0.995,
                "predicted_return_pct": round((latest.predicted_return or 0) * 100, 3),
            },
            "4h": {
                "predicted_price": latest.predicted_price_4h or current_price * (1 + (latest.predicted_return or 0) * 4),
                "confidence_upper": current_price * 1.015,
                "confidence_lower": current_price * 0.985,
                "predicted_return_pct": round((latest.predicted_return or 0) * 400, 3),
            },
            "1d": {
                "predicted_price": latest.predicted_price_1d or current_price * (1 + (latest.predicted_return or 0) * 8),
                "confidence_upper": current_price * 1.03,
                "confidence_lower": current_price * 0.97,
                "predicted_return_pct": round((latest.predicted_return or 0) * 800, 3),
            },
            "1w": {
                "predicted_price": latest.predicted_price_1w or current_price * (1 + (latest.predicted_return or 0) * 40),
                "confidence_upper": current_price * 1.08,
                "confidence_lower": current_price * 0.92,
                "predicted_return_pct": round((latest.predicted_return or 0) * 4000, 3),
            },
        }

        confidence_breakdown = {}
        if latest.confidence_breakdown:
            try:
                confidence_breakdown = json.loads(latest.confidence_breakdown)
            except Exception:
                pass

        return {
            "ticker": ticker.upper(),
            "current_price": current_price,
            "direction": latest.direction,
            "overall_confidence": round(confidence * 100, 1),
            "forecasts": forecasts,
            "model_breakdown": {
                "lstm_prediction": latest.lstm_prediction,
                "xgboost_prediction": latest.xgboost_prediction,
                "model_agreement": latest.model_agreement,
            },
            "confidence_breakdown": confidence_breakdown,
            "timestamp": latest.timestamp.isoformat() if latest.timestamp else None,
        }
    finally:
        db.close()


# ═══════════════════════════════════════════════
#  RETURNS CALCULATOR
# ═══════════════════════════════════════════════

@app.post("/calculator/returns")
def calculate_returns(req: CalculatorRequest):
    """Calculate predicted returns for a given investment."""
    db = get_db()
    try:
        latest = db.query(TickerPrediction).filter(
            TickerPrediction.ticker == req.ticker.upper()
        ).order_by(desc(TickerPrediction.timestamp)).first()

        if not latest:
            raise HTTPException(status_code=404, detail=f"No predictions found for {req.ticker}")

        current_price = latest.current_price or 0
        predicted_return = latest.predicted_return or 0
        confidence = latest.confidence or 0.5

        # Scale return by horizon
        horizon_multipliers = {"1h": 1, "4h": 4, "1d": 8, "1w": 40}
        multiplier = horizon_multipliers.get(req.horizon, 8)
        scaled_return = predicted_return * multiplier

        expected_value = req.investment_amount * (1 + scaled_return)
        expected_profit = expected_value - req.investment_amount

        # Best/worst case based on confidence bands
        best_case_return = scaled_return * 1.5
        worst_case_return = scaled_return * -0.5 if scaled_return > 0 else scaled_return * 1.5
        best_case_value = req.investment_amount * (1 + best_case_return)
        worst_case_value = req.investment_amount * (1 + worst_case_return)

        return {
            "ticker": req.ticker.upper(),
            "investment_amount": req.investment_amount,
            "horizon": req.horizon,
            "current_price": current_price,
            "direction": latest.direction,
            "expected": {
                "value": round(expected_value, 2),
                "profit": round(expected_profit, 2),
                "return_pct": round(scaled_return * 100, 3),
            },
            "best_case": {
                "value": round(best_case_value, 2),
                "profit": round(best_case_value - req.investment_amount, 2),
                "return_pct": round(best_case_return * 100, 3),
            },
            "worst_case": {
                "value": round(worst_case_value, 2),
                "profit": round(worst_case_value - req.investment_amount, 2),
                "return_pct": round(worst_case_return * 100, 3),
            },
            "confidence": round(confidence * 100, 1),
        }
    finally:
        db.close()


# ═══════════════════════════════════════════════
#  WATCHLIST
# ═══════════════════════════════════════════════

@app.get("/watchlist")
def get_watchlist():
    db = get_db()
    try:
        items = db.query(WatchlistItem).order_by(desc(WatchlistItem.created_at)).all()
        result = []
        for item in items:
            # Get latest prediction for this ticker
            pred = db.query(TickerPrediction).filter(
                TickerPrediction.ticker == item.ticker
            ).order_by(desc(TickerPrediction.timestamp)).first()

            result.append({
                "id": item.id,
                "ticker": item.ticker,
                "company_name": item.company_name,
                "alert_enabled": item.alert_enabled,
                "price_change_threshold": item.price_change_threshold,
                "confidence_threshold": item.confidence_threshold,
                "sentiment_threshold": item.sentiment_threshold,
                "daily_digest": item.daily_digest,
                "notes": item.notes,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "latest_prediction": _serialize_prediction(pred) if pred else None,
            })
        return {"count": len(result), "items": result}
    finally:
        db.close()


@app.post("/watchlist/add")
def add_to_watchlist(req: WatchlistAddRequest):
    db = get_db()
    try:
        existing = db.query(WatchlistItem).filter(WatchlistItem.ticker == req.ticker.upper()).first()
        if existing:
            return {"status": "already_exists", "ticker": req.ticker.upper()}

        item = WatchlistItem(
            ticker=req.ticker.upper(),
            company_name=req.company_name,
            alert_enabled=req.alert_enabled,
            price_change_threshold=req.price_change_threshold,
            confidence_threshold=req.confidence_threshold,
            daily_digest=req.daily_digest,
        )
        db.add(item)
        db.commit()
        return {"status": "added", "id": item.id, "ticker": req.ticker.upper()}
    finally:
        db.close()


@app.delete("/watchlist/remove/{ticker}")
def remove_from_watchlist(ticker: str):
    db = get_db()
    try:
        item = db.query(WatchlistItem).filter(WatchlistItem.ticker == ticker.upper()).first()
        if not item:
            raise HTTPException(status_code=404, detail=f"{ticker} not in watchlist")
        db.delete(item)
        db.commit()
        return {"status": "removed", "ticker": ticker.upper()}
    finally:
        db.close()


@app.put("/watchlist/{ticker}/alerts")
def update_watchlist_alerts(ticker: str, req: WatchlistUpdateRequest):
    db = get_db()
    try:
        item = db.query(WatchlistItem).filter(WatchlistItem.ticker == ticker.upper()).first()
        if not item:
            raise HTTPException(status_code=404, detail=f"{ticker} not in watchlist")

        if req.alert_enabled is not None: item.alert_enabled = req.alert_enabled
        if req.price_change_threshold is not None: item.price_change_threshold = req.price_change_threshold
        if req.confidence_threshold is not None: item.confidence_threshold = req.confidence_threshold
        if req.sentiment_threshold is not None: item.sentiment_threshold = req.sentiment_threshold
        if req.daily_digest is not None: item.daily_digest = req.daily_digest

        db.commit()
        return {"status": "updated", "ticker": ticker.upper()}
    finally:
        db.close()


# ═══════════════════════════════════════════════
#  PORTFOLIO
# ═══════════════════════════════════════════════

@app.get("/portfolio")
def get_portfolio():
    db = get_db()
    try:
        holdings = db.query(PortfolioHolding).order_by(desc(PortfolioHolding.created_at)).all()
        result = []
        total_invested = 0
        total_current = 0
        total_predicted_1d = 0

        for h in holdings:
            pred = db.query(TickerPrediction).filter(
                TickerPrediction.ticker == h.ticker
            ).order_by(desc(TickerPrediction.timestamp)).first()

            current_price = pred.current_price if pred else h.buy_price
            current_value = h.shares * current_price
            invested_value = h.shares * h.buy_price
            unrealized_pnl = current_value - invested_value
            predicted_price_1d = pred.predicted_price_1d if pred and pred.predicted_price_1d else current_price
            predicted_value_1d = h.shares * predicted_price_1d

            total_invested += invested_value
            total_current += current_value
            total_predicted_1d += predicted_value_1d

            result.append({
                "id": h.id,
                "ticker": h.ticker,
                "company_name": h.company_name,
                "shares": h.shares,
                "buy_price": h.buy_price,
                "buy_date": h.buy_date,
                "current_price": round(current_price, 2),
                "current_value": round(current_value, 2),
                "invested_value": round(invested_value, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "unrealized_pnl_pct": round((unrealized_pnl / invested_value * 100) if invested_value else 0, 2),
                "predicted_price_1d": round(predicted_price_1d, 2),
                "predicted_value_1d": round(predicted_value_1d, 2),
                "predicted_pnl_1d": round(predicted_value_1d - current_value, 2),
                "direction": pred.direction if pred else None,
                "confidence": round(pred.confidence * 100, 1) if pred and pred.confidence else None,
                "notes": h.notes,
            })

        return {
            "count": len(result),
            "summary": {
                "total_invested": round(total_invested, 2),
                "total_current_value": round(total_current, 2),
                "total_unrealized_pnl": round(total_current - total_invested, 2),
                "total_unrealized_pnl_pct": round(((total_current - total_invested) / total_invested * 100) if total_invested else 0, 2),
                "total_predicted_value_1d": round(total_predicted_1d, 2),
                "predicted_change_1d": round(total_predicted_1d - total_current, 2),
            },
            "holdings": result,
        }
    finally:
        db.close()


@app.post("/portfolio/add")
def add_portfolio_holding(req: PortfolioAddRequest):
    db = get_db()
    try:
        holding = PortfolioHolding(
            ticker=req.ticker.upper(),
            company_name=req.company_name,
            shares=req.shares,
            buy_price=req.buy_price,
            buy_date=req.buy_date,
            notes=req.notes,
        )
        db.add(holding)
        db.commit()
        return {"status": "added", "id": holding.id, "ticker": req.ticker.upper()}
    finally:
        db.close()


@app.delete("/portfolio/remove/{holding_id}")
def remove_portfolio_holding(holding_id: int):
    db = get_db()
    try:
        holding = db.query(PortfolioHolding).filter(PortfolioHolding.id == holding_id).first()
        if not holding:
            raise HTTPException(status_code=404, detail="Holding not found")
        db.delete(holding)
        db.commit()
        return {"status": "removed", "id": holding_id}
    finally:
        db.close()


@app.get("/portfolio/forecast")
def portfolio_forecast():
    """Predicted portfolio value across all horizons."""
    db = get_db()
    try:
        holdings = db.query(PortfolioHolding).all()
        horizons = {"1h": 0, "4h": 0, "1d": 0, "1w": 0}
        current_total = 0

        for h in holdings:
            pred = db.query(TickerPrediction).filter(
                TickerPrediction.ticker == h.ticker
            ).order_by(desc(TickerPrediction.timestamp)).first()

            cp = pred.current_price if pred else h.buy_price
            current_total += h.shares * cp

            ret = pred.predicted_return or 0 if pred else 0
            horizons["1h"] += h.shares * cp * (1 + ret)
            horizons["4h"] += h.shares * cp * (1 + ret * 4)
            horizons["1d"] += h.shares * cp * (1 + ret * 8)
            horizons["1w"] += h.shares * cp * (1 + ret * 40)

        return {
            "current_value": round(current_total, 2),
            "forecasts": {k: {"value": round(v, 2), "change": round(v - current_total, 2), "change_pct": round((v - current_total) / current_total * 100 if current_total else 0, 2)} for k, v in horizons.items()},
        }
    finally:
        db.close()


# ═══════════════════════════════════════════════
#  SENTIMENT
# ═══════════════════════════════════════════════

@app.get("/sentiment/feed")
def sentiment_feed(limit: int = 20):
    db = get_db()
    try:
        entries = db.query(SentimentEntry).order_by(desc(SentimentEntry.timestamp)).limit(limit).all()
        return {"count": len(entries), "items": [_serialize_sentiment(e) for e in entries]}
    finally:
        db.close()


@app.get("/sentiment/ticker/{ticker}")
def sentiment_by_ticker(ticker: str, limit: int = 24):
    db = get_db()
    try:
        entries = db.query(SentimentEntry).filter(
            SentimentEntry.ticker == ticker.upper()
        ).order_by(desc(SentimentEntry.timestamp)).limit(limit).all()
        return {"ticker": ticker.upper(), "count": len(entries), "entries": [_serialize_sentiment(e) for e in entries]}
    finally:
        db.close()


# ═══════════════════════════════════════════════
#  BACKTEST
# ═══════════════════════════════════════════════

@app.get("/backtest/results")
def backtest_results():
    db = get_db()
    try:
        result = db.query(BacktestResult).order_by(desc(BacktestResult.timestamp)).first()
        if not result:
            return {"status": "no_backtest_data"}
        return {
            "run_id": result.run_id,
            "total_return": result.total_return,
            "annualized_return": result.annualized_return,
            "sharpe_ratio": result.sharpe_ratio,
            "sortino_ratio": result.sortino_ratio,
            "max_drawdown": result.max_drawdown,
            "win_rate": result.win_rate,
            "total_trades": result.total_trades,
            "alpha": result.alpha,
            "beta": result.beta,
            "profit_factor": result.profit_factor,
            "timestamp": result.timestamp.isoformat() if result.timestamp else None,
        }
    finally:
        db.close()


@app.get("/backtest/trades")
def backtest_trades(limit: int = 50):
    db = get_db()
    try:
        trades = db.query(TradeLog).order_by(desc(TradeLog.timestamp)).limit(limit).all()
        return {"count": len(trades), "trades": [
            {"ticker": t.ticker, "action": t.action, "predicted_return": t.predicted_return,
             "actual_return": t.actual_return, "pnl": t.pnl, "date": t.date, "time": t.time}
            for t in trades
        ]}
    finally:
        db.close()


# ═══════════════════════════════════════════════
#  PREDICTION ACCURACY
# ═══════════════════════════════════════════════

@app.get("/accuracy")
def get_accuracy():
    """Historical prediction accuracy per ticker."""
    db = get_db()
    try:
        records = db.query(PredictionAccuracy).order_by(desc(PredictionAccuracy.accuracy_pct)).all()
        return {"count": len(records), "accuracy": [
            {"ticker": r.ticker, "timeframe": r.timeframe, "total_predictions": r.total_predictions,
             "correct_predictions": r.correct_predictions, "accuracy_pct": r.accuracy_pct,
             "avg_confidence": r.avg_confidence}
            for r in records
        ]}
    finally:
        db.close()


@app.get("/accuracy/ticker/{ticker}")
def get_ticker_accuracy(ticker: str):
    db = get_db()
    try:
        records = db.query(PredictionAccuracy).filter(PredictionAccuracy.ticker == ticker.upper()).all()
        return {"ticker": ticker.upper(), "accuracy": [
            {"timeframe": r.timeframe, "total_predictions": r.total_predictions,
             "correct_predictions": r.correct_predictions, "accuracy_pct": r.accuracy_pct}
            for r in records
        ]}
    finally:
        db.close()


# ═══════════════════════════════════════════════
#  ALERTS
# ═══════════════════════════════════════════════

@app.get("/alerts")
def get_alerts(limit: int = 50, unread_only: bool = False):
    db = get_db()
    try:
        query = db.query(AlertLog)
        if unread_only:
            query = query.filter(AlertLog.read == False)
        alerts = query.order_by(desc(AlertLog.timestamp)).limit(limit).all()
        unread_count = db.query(func.count(AlertLog.id)).filter(AlertLog.read == False).scalar() or 0
        return {
            "count": len(alerts),
            "unread_count": unread_count,
            "alerts": [{
                "id": a.id, "ticker": a.ticker, "alert_type": a.alert_type,
                "message": a.message, "severity": a.severity, "read": a.read,
                "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            } for a in alerts],
        }
    finally:
        db.close()


@app.put("/alerts/{alert_id}/read")
def mark_alert_read(alert_id: int):
    db = get_db()
    try:
        alert = db.query(AlertLog).filter(AlertLog.id == alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        alert.read = True
        db.commit()
        return {"status": "marked_read", "id": alert_id}
    finally:
        db.close()


@app.put("/alerts/read-all")
def mark_all_alerts_read():
    db = get_db()
    try:
        db.query(AlertLog).filter(AlertLog.read == False).update({"read": True})
        db.commit()
        return {"status": "all_marked_read"}
    finally:
        db.close()


# ═══════════════════════════════════════════════
#  MARKET OVERVIEW
# ═══════════════════════════════════════════════

@app.get("/market/overview")
def market_overview():
    """Market-wide sentiment and prediction summary."""
    db = get_db()
    try:
        latest_run = db.query(PredictionRun).order_by(desc(PredictionRun.timestamp)).first()
        if not latest_run:
            return {"status": "no_data"}

        preds = db.query(TickerPrediction).filter(TickerPrediction.run_id == latest_run.run_id).all()
        bullish = [p for p in preds if p.direction == "BULLISH"]
        bearish = [p for p in preds if p.direction == "BEARISH"]
        avg_sentiment = sum(p.sentiment_score or 0 for p in preds) / len(preds) if preds else 0
        avg_confidence = sum(p.confidence or 0 for p in preds) / len(preds) if preds else 0

        # Sector breakdown (simplified)
        top_gainers = sorted(preds, key=lambda p: p.hourly_change or 0, reverse=True)[:5]
        top_losers = sorted(preds, key=lambda p: p.hourly_change or 0)[:5]

        return {
            "timestamp": latest_run.timestamp.isoformat(),
            "total_tracked": len(preds),
            "bullish_count": len(bullish),
            "bearish_count": len(bearish),
            "avg_sentiment": round(avg_sentiment, 3),
            "avg_confidence": round(avg_confidence * 100, 1),
            "market_mood": "Bullish" if len(bullish) > len(bearish) else "Bearish" if len(bearish) > len(bullish) else "Neutral",
            "top_gainers": [{"ticker": p.ticker, "change": p.hourly_change, "direction": p.direction} for p in top_gainers],
            "top_losers": [{"ticker": p.ticker, "change": p.hourly_change, "direction": p.direction} for p in top_losers],
        }
    finally:
        db.close()


# ═══════════════════════════════════════════════
#  STOCK COMPARISON
# ═══════════════════════════════════════════════

@app.get("/compare")
def compare_stocks(tickers: str = Query(..., description="Comma-separated tickers, e.g. AAPL,TSLA,MSFT")):
    """Compare 2-5 stocks side-by-side."""
    ticker_list = [t.strip().upper() for t in tickers.split(",")][:5]
    db = get_db()
    try:
        results = []
        for ticker in ticker_list:
            pred = db.query(TickerPrediction).filter(
                TickerPrediction.ticker == ticker
            ).order_by(desc(TickerPrediction.timestamp)).first()

            if pred:
                results.append({
                    "ticker": ticker,
                    "current_price": pred.current_price,
                    "predicted_return": pred.predicted_return,
                    "direction": pred.direction,
                    "confidence": round((pred.confidence or 0) * 100, 1),
                    "sentiment": pred.sentiment_score,
                    "rsi": pred.rsi,
                    "hourly_change": pred.hourly_change,
                    "model_agreement": pred.model_agreement,
                })
            else:
                results.append({"ticker": ticker, "status": "no_data"})

        return {"count": len(results), "comparison": results}
    finally:
        db.close()


# ═══════════════════════════════════════════════
#  SCHEDULER + MODEL INFO
# ═══════════════════════════════════════════════

@app.get("/scheduler/status")
def scheduler_status():
    if _scheduler is None:
        return {"status": "not_configured", "jobs": []}
    jobs = [{"id": j.id, "name": j.name, "next_run": j.next_run_time.isoformat() if j.next_run_time else None, "trigger": str(j.trigger)} for j in _scheduler.get_jobs()]
    return {"status": "running" if _scheduler.running else "stopped", "jobs": jobs}


@app.get("/model/info")
def model_info():
    if _model is None:
        return {"status": "not_loaded"}
    return {"status": "loaded", "type": "EnsembleModel", "components": ["LSTM", "XGBoost"], "ensemble_method": "weighted", "weights": {"lstm": 0.4, "xgboost": 0.6}, "version": "2.0.0"}


# ─── Helpers ──────────────────────────────────

def _serialize_prediction(p: TickerPrediction) -> dict:
    confidence_breakdown = {}
    if p.confidence_breakdown:
        try:
            confidence_breakdown = json.loads(p.confidence_breakdown)
        except Exception:
            pass

    return {
        "ticker": p.ticker,
        "current_price": p.current_price,
        "predicted_return": p.predicted_return,
        "predicted_price_1h": p.predicted_price_1h,
        "predicted_price_4h": p.predicted_price_4h,
        "predicted_price_1d": p.predicted_price_1d,
        "predicted_price_1w": p.predicted_price_1w,
        "direction": p.direction,
        "confidence": p.confidence,
        "confidence_upper": p.confidence_upper,
        "confidence_lower": p.confidence_lower,
        "daily_return": p.daily_return,
        "hourly_change": p.hourly_change,
        "volume": p.volume,
        "sentiment_score": p.sentiment_score,
        "rsi": p.rsi,
        "macd": p.macd,
        "model_agreement": p.model_agreement,
        "lstm_prediction": p.lstm_prediction,
        "xgboost_prediction": p.xgboost_prediction,
        "confidence_breakdown": confidence_breakdown,
        "status": p.status,
        "timestamp": p.timestamp.isoformat() if p.timestamp else None,
    }


def _serialize_sentiment(e: SentimentEntry) -> dict:
    key_phrases = []
    if e.key_phrases:
        try:
            key_phrases = json.loads(e.key_phrases)
        except Exception:
            pass

    return {
        "id": e.id, "ticker": e.ticker, "source": e.source, "headline": e.headline,
        "url": e.url, "sentiment": e.sentiment, "sentiment_score": e.sentiment_score,
        "key_phrases": key_phrases, "source_credibility": e.source_credibility,
        "timestamp": e.timestamp.isoformat() if e.timestamp else None,
    }
