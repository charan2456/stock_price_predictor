"""Technical indicator computation for market data.

Computes a comprehensive set of technical indicators (RSI, MACD,
Bollinger Bands, SMA, EMA, ATR, OBV, VWAP) using the `ta` library.
All indicators are configurable via YAML config.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import ta
from loguru import logger

from src.utils.config import get_config


class TechnicalIndicators:
    """Computes technical analysis indicators from OHLCV data.

    Generates a feature-rich DataFrame with momentum, volatility,
    trend, and volume indicators used as input features for ML models.

    Supported Indicators:
        - RSI (Relative Strength Index)
        - MACD (Moving Average Convergence Divergence)
        - Bollinger Bands (upper, middle, lower, bandwidth, %B)
        - SMA (Simple Moving Average) — multiple windows
        - EMA (Exponential Moving Average) — multiple windows
        - ATR (Average True Range)
        - OBV (On-Balance Volume)
        - VWAP (Volume-Weighted Average Price)
    """

    def __init__(self) -> None:
        cfg = get_config()
        self.indicator_configs: list[dict] = cfg.features.technical_indicators

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all configured technical indicators.

        Args:
            df: DataFrame with columns: open, high, low, close, volume.

        Returns:
            DataFrame with additional technical indicator columns.
        """
        result = df.copy()

        for indicator_cfg in self.indicator_configs:
            name = indicator_cfg["name"] if isinstance(indicator_cfg, dict) else indicator_cfg.name
            try:
                if name == "rsi":
                    result = self._add_rsi(result, indicator_cfg)
                elif name == "macd":
                    result = self._add_macd(result, indicator_cfg)
                elif name == "bollinger_bands":
                    result = self._add_bollinger(result, indicator_cfg)
                elif name == "sma":
                    result = self._add_sma(result, indicator_cfg)
                elif name == "ema":
                    result = self._add_ema(result, indicator_cfg)
                elif name == "atr":
                    result = self._add_atr(result, indicator_cfg)
                elif name == "obv":
                    result = self._add_obv(result)
                elif name == "vwap":
                    result = self._add_vwap(result)
                else:
                    logger.warning("Unknown indicator: {name}", name=name)
            except Exception as e:
                logger.error("Failed to compute {name}: {err}", name=name, err=e)

        logger.info(
            "Computed {n} technical indicator columns",
            n=len(result.columns) - len(df.columns),
        )
        return result

    def _add_rsi(self, df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
        """Relative Strength Index — momentum oscillator (0-100)."""
        window = cfg.get("window", 14) if isinstance(cfg, dict) else getattr(cfg, "window", 14)
        df[f"rsi_{window}"] = ta.momentum.rsi(df["close"], window=window)
        # Also add RSI-based signals
        df["rsi_oversold"] = (df[f"rsi_{window}"] < 30).astype(int)
        df["rsi_overbought"] = (df[f"rsi_{window}"] > 70).astype(int)
        return df

    def _add_macd(self, df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
        """MACD — trend-following momentum indicator."""
        fast = cfg.get("fast", 12) if isinstance(cfg, dict) else getattr(cfg, "fast", 12)
        slow = cfg.get("slow", 26) if isinstance(cfg, dict) else getattr(cfg, "slow", 26)
        signal = cfg.get("signal", 9) if isinstance(cfg, dict) else getattr(cfg, "signal", 9)

        macd = ta.trend.MACD(df["close"], window_fast=fast, window_slow=slow, window_sign=signal)
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["macd_histogram"] = macd.macd_diff()
        df["macd_crossover"] = (
            (df["macd"] > df["macd_signal"]) &
            (df["macd"].shift(1) <= df["macd_signal"].shift(1))
        ).astype(int)
        return df

    def _add_bollinger(self, df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
        """Bollinger Bands — volatility indicator."""
        window = cfg.get("window", 20) if isinstance(cfg, dict) else getattr(cfg, "window", 20)
        std_dev = cfg.get("std_dev", 2) if isinstance(cfg, dict) else getattr(cfg, "std_dev", 2)

        bb = ta.volatility.BollingerBands(df["close"], window=window, window_dev=std_dev)
        df["bb_upper"] = bb.bollinger_hband()
        df["bb_middle"] = bb.bollinger_mavg()
        df["bb_lower"] = bb.bollinger_lband()
        df["bb_bandwidth"] = bb.bollinger_wband()
        df["bb_pband"] = bb.bollinger_pband()  # %B indicator
        return df

    def _add_sma(self, df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
        """Simple Moving Average — multiple windows."""
        windows = cfg.get("windows", [5, 10, 20, 50]) if isinstance(cfg, dict) else getattr(cfg, "windows", [5, 10, 20, 50])
        for w in windows:
            df[f"sma_{w}"] = ta.trend.sma_indicator(df["close"], window=w)
            # Price relative to SMA
            df[f"close_to_sma_{w}"] = df["close"] / df[f"sma_{w}"] - 1
        return df

    def _add_ema(self, df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
        """Exponential Moving Average — multiple windows."""
        windows = cfg.get("windows", [12, 26]) if isinstance(cfg, dict) else getattr(cfg, "windows", [12, 26])
        for w in windows:
            df[f"ema_{w}"] = ta.trend.ema_indicator(df["close"], window=w)
        return df

    def _add_atr(self, df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
        """Average True Range — volatility measure."""
        window = cfg.get("window", 14) if isinstance(cfg, dict) else getattr(cfg, "window", 14)
        df[f"atr_{window}"] = ta.volatility.average_true_range(
            df["high"], df["low"], df["close"], window=window
        )
        # Normalized ATR (as % of close price)
        df[f"atr_{window}_pct"] = df[f"atr_{window}"] / df["close"]
        return df

    def _add_obv(self, df: pd.DataFrame) -> pd.DataFrame:
        """On-Balance Volume — volume-based momentum."""
        df["obv"] = ta.volume.on_balance_volume(df["close"], df["volume"])
        df["obv_change"] = df["obv"].pct_change()
        return df

    def _add_vwap(self, df: pd.DataFrame) -> pd.DataFrame:
        """Volume-Weighted Average Price."""
        df["vwap"] = ta.volume.volume_weighted_average_price(
            df["high"], df["low"], df["close"], df["volume"]
        )
        df["close_to_vwap"] = df["close"] / df["vwap"] - 1
        return df
