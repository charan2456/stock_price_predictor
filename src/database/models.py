"""SQLAlchemy ORM models for the Market Sentinel platform.

Tables:
  - prediction_runs       — Aggregate hourly run metadata
  - ticker_predictions    — Per-ticker prediction results
  - sentiment_entries     — NLP-scored headlines from Reddit/News
  - trade_log             — Backtesting trade entries
  - backtest_results      — Backtest summary metrics
  - watchlist_items       — User's starred stocks + alert config
  - portfolio_holdings    — User's real stock holdings
  - user_tickers          — Custom tickers added by user (beyond S&P 100)
  - prediction_accuracy   — Historical accuracy tracking per ticker
  - alerts_log            — Alert history (sent notifications)
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ─── Prediction Models ───────────────────────

class PredictionRun(Base):
    """A single scheduled prediction run (one per cron trigger)."""
    __tablename__ = "prediction_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), unique=True, nullable=False, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String(20), default="success")
    total_tickers = Column(Integer, default=0)
    bullish_count = Column(Integer, default=0)
    bearish_count = Column(Integer, default=0)


class TickerPrediction(Base):
    """Individual ticker prediction within a run."""
    __tablename__ = "ticker_predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), nullable=False, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    current_price = Column(Float)
    predicted_return = Column(Float)
    predicted_price_1h = Column(Float)
    predicted_price_4h = Column(Float)
    predicted_price_1d = Column(Float)
    predicted_price_1w = Column(Float)
    confidence_upper = Column(Float)
    confidence_lower = Column(Float)
    direction = Column(String(10))
    confidence = Column(Float)
    daily_return = Column(Float)
    hourly_change = Column(Float)
    volume = Column(Integer)
    sentiment_score = Column(Float)
    rsi = Column(Float)
    macd = Column(Float)
    bollinger_position = Column(String(20))
    model_agreement = Column(Boolean, default=True)
    lstm_prediction = Column(Float)
    xgboost_prediction = Column(Float)
    confidence_breakdown = Column(Text)  # JSON: {model_agreement, sentiment_aligned, technical_confirmed, historical_accuracy}
    status = Column(String(20))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SentimentEntry(Base):
    """Sentiment score from a specific source at a point in time."""
    __tablename__ = "sentiment_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False, index=True)
    source = Column(String(20))
    headline = Column(Text)
    url = Column(Text)
    sentiment = Column(String(10))
    sentiment_score = Column(Float)
    key_phrases = Column(Text)  # JSON array of highlighted phrases
    source_credibility = Column(Float)  # 0-1 score
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class TradeLog(Base):
    """Backtesting trade entry."""
    __tablename__ = "trade_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), index=True)
    ticker = Column(String(10), nullable=False)
    action = Column(String(10))
    predicted_return = Column(Float)
    actual_return = Column(Float)
    pnl = Column(Float)
    date = Column(String(10))
    time = Column(String(10))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class BacktestResult(Base):
    """Summary metrics from a backtest run."""
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), index=True)
    total_return = Column(Float)
    annualized_return = Column(Float)
    sharpe_ratio = Column(Float)
    sortino_ratio = Column(Float)
    max_drawdown = Column(Float)
    win_rate = Column(Float)
    total_trades = Column(Integer)
    alpha = Column(Float)
    beta = Column(Float)
    profit_factor = Column(Float)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ─── User Features ───────────────────────────

class WatchlistItem(Base):
    """User's starred stocks with alert configuration."""
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False, unique=True, index=True)
    company_name = Column(String(100))
    alert_enabled = Column(Boolean, default=True)
    price_change_threshold = Column(Float, default=2.0)   # Alert if price changes > X%
    confidence_threshold = Column(Float, default=80.0)     # Alert if confidence > X%
    sentiment_threshold = Column(Float, default=0.5)       # Alert if sentiment flips
    daily_digest = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PortfolioHolding(Base):
    """User's real stock holdings."""
    __tablename__ = "portfolio_holdings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False, index=True)
    company_name = Column(String(100))
    shares = Column(Float, nullable=False)
    buy_price = Column(Float, nullable=False)
    buy_date = Column(String(10))
    notes = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class UserTicker(Base):
    """Custom tickers added by user (beyond default S&P 100)."""
    __tablename__ = "user_tickers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False, unique=True, index=True)
    company_name = Column(String(100))
    exchange = Column(String(20))
    sector = Column(String(50))
    added_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PredictionAccuracy(Base):
    """Historical accuracy tracking per ticker per timeframe."""
    __tablename__ = "prediction_accuracy"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False, index=True)
    timeframe = Column(String(10))  # 1h, 4h, 1d, 1w
    total_predictions = Column(Integer, default=0)
    correct_predictions = Column(Integer, default=0)
    accuracy_pct = Column(Float, default=0.0)
    avg_confidence = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AlertLog(Base):
    """Alert history — sent notifications."""
    __tablename__ = "alert_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False, index=True)
    alert_type = Column(String(30))  # price_change, confidence_spike, sentiment_flip
    message = Column(Text)
    severity = Column(String(10))  # info, warning, critical
    read = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
