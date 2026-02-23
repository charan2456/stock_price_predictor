"""Scheduled prediction jobs via APScheduler.

Runs hourly stock predictions on a configurable cron schedule and
saves results to the SQLite database. The API serves these results
to the frontend dashboard and n8n can poll for alerts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from src.data.market_data import MarketDataFetcher
from src.database.db import get_db
from src.database.models import PredictionRun, SentimentEntry, TickerPrediction
from src.utils.config import get_config


async def run_scheduled_predictions() -> dict[str, Any]:
    """Execute a full prediction cycle for all configured tickers.

    Fetches latest market data, runs predictions through the loaded model,
    and persists results to the SQLite database.

    Returns:
        Dict with prediction results for all tickers.
    """
    from src.serving.app import _model

    logger.info("=" * 50)
    logger.info("Scheduled prediction run starting...")
    logger.info("=" * 50)

    cfg = get_config()
    tickers = cfg.data.tickers
    run_timestamp = datetime.now(timezone.utc)
    run_id = run_timestamp.isoformat()

    results: dict[str, Any] = {
        "run_id": run_id,
        "timestamp": run_id,
        "status": "success",
        "predictions": [],
    }

    db = get_db()

    try:
        fetcher = MarketDataFetcher()
        bullish_count = 0
        bearish_count = 0

        for ticker in tickers:
            try:
                df = fetcher.fetch(ticker)
                if df.empty:
                    logger.warning("No data for {t}, skipping", t=ticker)
                    prediction_entry = {
                        "ticker": ticker,
                        "status": "no_data",
                        "timestamp": run_id,
                    }
                    results["predictions"].append(prediction_entry)
                    continue

                # Extract latest market stats
                current_price = float(df["close"].iloc[-1])
                daily_return = float(df["daily_return"].iloc[-1])
                volume = int(df["volume"].iloc[-1])

                if _model is not None:
                    exclude = {"date", "ticker", "daily_return", "log_return"}
                    feature_cols = [c for c in df.columns if c not in exclude and df[c].dtype in ["float64", "int64"]]
                    latest_features = df[feature_cols].iloc[-1:].values

                    try:
                        pred = _model.xgb.predict(latest_features)
                        predicted_return = float(pred[0])
                    except Exception:
                        predicted_return = 0.0

                    direction = "BULLISH" if predicted_return > 0 else "BEARISH"
                    confidence = min(abs(predicted_return) * 100, 1.0)

                    if direction == "BULLISH":
                        bullish_count += 1
                    else:
                        bearish_count += 1

                    prediction_entry = {
                        "ticker": ticker,
                        "current_price": current_price,
                        "predicted_return": round(predicted_return, 6),
                        "direction": direction,
                        "confidence": round(confidence, 4),
                        "daily_return": round(daily_return, 6),
                        "volume": volume,
                        "status": "predicted",
                        "timestamp": run_id,
                    }
                else:
                    prediction_entry = {
                        "ticker": ticker,
                        "current_price": current_price,
                        "predicted_return": None,
                        "direction": "UNKNOWN",
                        "confidence": 0.0,
                        "daily_return": round(daily_return, 6),
                        "volume": volume,
                        "status": "no_model",
                        "timestamp": run_id,
                    }

                results["predictions"].append(prediction_entry)

                # Save to database
                db_prediction = TickerPrediction(
                    run_id=run_id,
                    ticker=ticker,
                    current_price=prediction_entry.get("current_price"),
                    predicted_return=prediction_entry.get("predicted_return"),
                    direction=prediction_entry.get("direction", "UNKNOWN"),
                    confidence=prediction_entry.get("confidence", 0.0),
                    daily_return=prediction_entry.get("daily_return"),
                    volume=prediction_entry.get("volume"),
                    status=prediction_entry.get("status", "unknown"),
                    timestamp=run_timestamp,
                )
                db.add(db_prediction)

                logger.info(
                    "{ticker}: {dir} (return={ret}, confidence={conf})",
                    ticker=ticker,
                    dir=prediction_entry["direction"],
                    ret=prediction_entry.get("predicted_return"),
                    conf=prediction_entry.get("confidence"),
                )

            except Exception as e:
                logger.error("Failed prediction for {t}: {err}", t=ticker, err=e)
                results["predictions"].append({
                    "ticker": ticker,
                    "status": "error",
                    "error": str(e),
                    "timestamp": run_id,
                })

        # Save prediction run summary
        db_run = PredictionRun(
            run_id=run_id,
            timestamp=run_timestamp,
            status="success",
            total_tickers=len(results["predictions"]),
            bullish_count=bullish_count,
            bearish_count=bearish_count,
        )
        db.add(db_run)
        db.commit()

    except Exception as e:
        logger.error("Scheduled prediction run failed: {err}", err=e)
        results["status"] = "failed"
        results["error"] = str(e)
        db.rollback()
    finally:
        db.close()

    bullish = sum(1 for p in results["predictions"] if p.get("direction") == "BULLISH")
    bearish = sum(1 for p in results["predictions"] if p.get("direction") == "BEARISH")

    logger.info("=" * 50)
    logger.info(
        "Prediction run complete | {n} tickers | {b} BULLISH | {s} BEARISH | Saved to DB",
        n=len(results["predictions"]),
        b=bullish,
        s=bearish,
    )
    logger.info("=" * 50)

    return results


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance.

    Reads cron schedule from config. Defaults to every hour on weekdays.

    Returns:
        Configured (but not started) AsyncIOScheduler.
    """
    cfg = get_config()

    schedule_cfg = cfg.scheduling if hasattr(cfg, "scheduling") else None

    if schedule_cfg:
        cron_hour = schedule_cfg.cron_hour if hasattr(schedule_cfg, "cron_hour") else "*"
        cron_minute = schedule_cfg.cron_minute if hasattr(schedule_cfg, "cron_minute") else 0
        cron_day_of_week = schedule_cfg.cron_day_of_week if hasattr(schedule_cfg, "cron_day_of_week") else "mon-fri"
        timezone_str = schedule_cfg.timezone if hasattr(schedule_cfg, "timezone") else "Asia/Kolkata"
        enabled = schedule_cfg.enabled if hasattr(schedule_cfg, "enabled") else True
    else:
        cron_hour = "*"
        cron_minute = 0
        cron_day_of_week = "mon-fri"
        timezone_str = "Asia/Kolkata"
        enabled = True

    scheduler = AsyncIOScheduler(timezone=timezone_str)

    if enabled:
        scheduler.add_job(
            run_scheduled_predictions,
            trigger=CronTrigger(
                hour=cron_hour,
                minute=cron_minute,
                day_of_week=cron_day_of_week,
                timezone=timezone_str,
            ),
            id="hourly_predictions",
            name="Hourly Stock Predictions",
            replace_existing=True,
            max_instances=1,
        )

        logger.info(
            "Scheduler configured | Cron: hour={h} minute={m} days={d} ({tz})",
            h=cron_hour,
            m=cron_minute,
            d=cron_day_of_week,
            tz=timezone_str,
        )
    else:
        logger.info("Scheduler is disabled via config")

    return scheduler
