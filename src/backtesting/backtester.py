"""Backtesting framework for strategy validation.

Simulates historical trading based on model predictions to evaluate
real-world performance metrics: total return, Sharpe ratio, max drawdown,
win rate, and comparison against benchmark (SPY).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from src.utils.config import get_config


@dataclass
class BacktestResult:
    """Container for backtesting results."""

    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    avg_trade_return: float = 0.0
    benchmark_return: float = 0.0
    alpha: float = 0.0  # Excess return over benchmark
    portfolio_values: list[float] = field(default_factory=list)
    trade_log: list[dict[str, Any]] = field(default_factory=list)

    def summary(self) -> dict[str, float]:
        """Return summary metrics as a dict."""
        return {
            "total_return": self.total_return,
            "annualized_return": self.annualized_return,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "avg_trade_return": self.avg_trade_return,
            "benchmark_return": self.benchmark_return,
            "alpha": self.alpha,
        }


class Backtester:
    """Historical backtesting engine for model-driven strategies.

    Simulates a simple long/flat strategy:
        - When model predicts positive return → go LONG
        - When model predicts negative return → stay FLAT (cash)
        - Position sizing is configurable (default: 10% per trade)

    Includes realistic trading frictions: commission and slippage.

    Attributes:
        initial_capital: Starting portfolio value.
        commission: Commission rate per trade (e.g., 0.001 = 0.1%).
        slippage: Slippage rate per trade.
        position_size: Fraction of portfolio per trade.
    """

    def __init__(self) -> None:
        cfg = get_config()
        self.initial_capital: float = cfg.backtesting.initial_capital
        self.commission: float = cfg.backtesting.commission
        self.slippage: float = cfg.backtesting.slippage
        self.position_size: float = cfg.backtesting.position_size

    def run(
        self,
        predictions: np.ndarray,
        actual_returns: np.ndarray,
        dates: pd.Series | None = None,
    ) -> BacktestResult:
        """Run backtest simulation.

        Args:
            predictions: Model-predicted returns (n_days,).
            actual_returns: Actual realized returns (n_days,).
            dates: Optional date series for trade logging.

        Returns:
            BacktestResult with comprehensive performance metrics.
        """
        n_days = min(len(predictions), len(actual_returns))
        predictions = predictions[:n_days]
        actual_returns = actual_returns[:n_days]

        # Initialize tracking
        capital = self.initial_capital
        portfolio_values = [capital]
        trade_log = []
        trade_returns = []

        for i in range(n_days):
            pred = predictions[i]
            actual = actual_returns[i]

            if pred > 0:
                # Go LONG
                trade_amount = capital * self.position_size
                cost = trade_amount * (self.commission + self.slippage)
                trade_return = trade_amount * actual - cost
                capital += trade_return
                trade_returns.append(actual)

                trade_log.append({
                    "day": i,
                    "date": dates.iloc[i] if dates is not None else None,
                    "action": "LONG",
                    "predicted_return": float(pred),
                    "actual_return": float(actual),
                    "pnl": float(trade_return),
                    "capital": float(capital),
                })
            else:
                # Stay FLAT
                trade_log.append({
                    "day": i,
                    "date": dates.iloc[i] if dates is not None else None,
                    "action": "FLAT",
                    "predicted_return": float(pred),
                    "actual_return": float(actual),
                    "pnl": 0.0,
                    "capital": float(capital),
                })

            portfolio_values.append(capital)

        # Compute metrics
        result = BacktestResult()
        result.portfolio_values = portfolio_values
        result.trade_log = trade_log
        result.total_trades = sum(1 for t in trade_log if t["action"] == "LONG")

        # Returns
        result.total_return = (capital - self.initial_capital) / self.initial_capital

        if n_days > 0:
            result.annualized_return = (1 + result.total_return) ** (252 / n_days) - 1

        # Sharpe ratio
        if trade_returns:
            daily_returns = np.array(trade_returns)
            if np.std(daily_returns) > 0:
                result.sharpe_ratio = (
                    np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)
                )
            result.win_rate = (daily_returns > 0).mean()
            result.avg_trade_return = float(np.mean(daily_returns))

        # Max drawdown
        portfolio_arr = np.array(portfolio_values)
        peak = np.maximum.accumulate(portfolio_arr)
        drawdown = (portfolio_arr - peak) / peak
        result.max_drawdown = float(np.min(drawdown))

        # Benchmark (buy & hold)
        result.benchmark_return = float(np.prod(1 + actual_returns) - 1)
        result.alpha = result.total_return - result.benchmark_return

        # Log results
        logger.info("=" * 50)
        logger.info("Backtest Results")
        logger.info("=" * 50)
        logger.info("  Total Return:      {r:.2%}", r=result.total_return)
        logger.info("  Annualized Return: {r:.2%}", r=result.annualized_return)
        logger.info("  Sharpe Ratio:      {s:.2f}", s=result.sharpe_ratio)
        logger.info("  Max Drawdown:      {d:.2%}", d=result.max_drawdown)
        logger.info("  Win Rate:          {w:.2%}", w=result.win_rate)
        logger.info("  Total Trades:      {t}", t=result.total_trades)
        logger.info("  Benchmark Return:  {b:.2%}", b=result.benchmark_return)
        logger.info("  Alpha:             {a:.2%}", a=result.alpha)
        logger.info("=" * 50)

        return result
