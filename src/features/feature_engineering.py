"""Feature engineering pipeline.

Orchestrates the full feature engineering process: sentiment scoring,
technical indicator computation, lag feature generation, target variable
creation, and feature normalization.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.preprocessing import StandardScaler

from src.features.sentiment import SentimentAnalyzer
from src.features.technical_indicators import TechnicalIndicators
from src.utils.config import DATA_DIR, get_config


class FeatureEngineer:
    """End-to-end feature engineering pipeline.

    Transforms raw merged data into ML-ready features by:
        1. Computing FinBERT sentiment scores
        2. Adding technical indicators (RSI, MACD, BBands, etc.)
        3. Generating lag features for time-series modeling
        4. Creating target variables (next-day return/direction)
        5. Handling missing values and normalization

    Pipeline Flow:
        Raw merged data → Sentiment → Technical Indicators →
        Lag Features → Target Creation → Normalization → ML-ready dataset
    """

    def __init__(self, skip_sentiment: bool = False) -> None:
        """
        Args:
            skip_sentiment: If True, skip FinBERT scoring
                           (useful for testing without GPU).
        """
        self.cfg = get_config()
        self.skip_sentiment = skip_sentiment
        self.technical = TechnicalIndicators()
        self.scaler = StandardScaler()
        self._feature_columns: list[str] = []

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Run the full feature engineering pipeline.

        Args:
            df: Merged DataFrame from DataPipeline (market + text data).

        Returns:
            Feature-engineered DataFrame ready for model training.
        """
        logger.info("=" * 60)
        logger.info("Starting feature engineering pipeline")
        logger.info("Input shape: {shape}", shape=df.shape)
        logger.info("=" * 60)

        result = df.copy()

        # Step 1: Sentiment scoring
        if not self.skip_sentiment and "combined_text" in result.columns:
            logger.info("Step 1/5: FinBERT sentiment scoring...")
            analyzer = SentimentAnalyzer()
            result = analyzer.score_dataframe(result, text_column="combined_text")
        else:
            logger.info("Step 1/5: Skipping sentiment scoring")
            # Add placeholder columns
            for col in ["sentiment_positive", "sentiment_negative", "sentiment_neutral", "sentiment_compound"]:
                if col not in result.columns:
                    result[col] = 0.0

        # Step 2: Technical indicators (per ticker)
        logger.info("Step 2/5: Computing technical indicators...")
        result = self._compute_indicators_per_ticker(result)

        # Step 3: Lag features
        logger.info("Step 3/5: Generating lag features...")
        result = self._add_lag_features(result)

        # Step 4: Target variable
        logger.info("Step 4/5: Creating target variables...")
        result = self._create_targets(result)

        # Step 5: Clean up
        logger.info("Step 5/5: Cleaning and finalizing...")
        result = self._clean_features(result)

        # Store feature column names
        exclude_cols = {"date", "ticker", "combined_text", "reddit_text", "news_text",
                       "title", "text", "url", "author", "link", "summary",
                       "next_day_return", "next_day_direction", "next_5day_return"}
        self._feature_columns = [c for c in result.columns if c not in exclude_cols]

        logger.info("=" * 60)
        logger.info(
            "Feature engineering complete | "
            "Output shape: {shape} | Features: {n_feat}",
            shape=result.shape,
            n_feat=len(self._feature_columns),
        )
        logger.info("=" * 60)

        return result

    def _compute_indicators_per_ticker(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute technical indicators separately for each ticker."""
        if "ticker" not in df.columns:
            return self.technical.compute(df)

        ticker_dfs = []
        for ticker in df["ticker"].unique():
            ticker_df = df[df["ticker"] == ticker].sort_values("date").copy()
            ticker_df = self.technical.compute(ticker_df)
            ticker_dfs.append(ticker_df)

        return pd.concat(ticker_dfs, ignore_index=True)

    def _add_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate lag and rolling features for time-series modeling.

        Creates lagged versions of key features to capture temporal
        dependencies that the models can learn from.
        """
        lag_cfg = self.cfg.features.lag_features

        # Price lags
        price_lags = lag_cfg.price_lags if hasattr(lag_cfg, 'price_lags') else [1, 2, 3, 5, 10]
        for lag in price_lags:
            df[f"return_lag_{lag}"] = df.groupby("ticker")["daily_return"].shift(lag)
            df[f"close_lag_{lag}"] = df.groupby("ticker")["close"].shift(lag)

        # Sentiment lags
        sentiment_lags = lag_cfg.sentiment_lags if hasattr(lag_cfg, 'sentiment_lags') else [1, 2, 3]
        if "sentiment_compound" in df.columns:
            for lag in sentiment_lags:
                df[f"sentiment_lag_{lag}"] = df.groupby("ticker")["sentiment_compound"].shift(lag)

        # Rolling features
        rolling_windows = lag_cfg.rolling_windows if hasattr(lag_cfg, 'rolling_windows') else [3, 5, 10, 20]
        for window in rolling_windows:
            # Rolling return statistics
            df[f"return_rolling_mean_{window}"] = (
                df.groupby("ticker")["daily_return"]
                .transform(lambda x: x.rolling(window, min_periods=1).mean())
            )
            df[f"return_rolling_std_{window}"] = (
                df.groupby("ticker")["daily_return"]
                .transform(lambda x: x.rolling(window, min_periods=1).std())
            )

            # Rolling volume
            df[f"volume_rolling_mean_{window}"] = (
                df.groupby("ticker")["volume"]
                .transform(lambda x: x.rolling(window, min_periods=1).mean())
            )
            df[f"volume_ratio_{window}"] = df["volume"] / df[f"volume_rolling_mean_{window}"]

            # Rolling sentiment
            if "sentiment_compound" in df.columns:
                df[f"sentiment_rolling_mean_{window}"] = (
                    df.groupby("ticker")["sentiment_compound"]
                    .transform(lambda x: x.rolling(window, min_periods=1).mean())
                )

        # Momentum features
        df["momentum_5d"] = df.groupby("ticker")["close"].transform(
            lambda x: x / x.shift(5) - 1
        )
        df["momentum_10d"] = df.groupby("ticker")["close"].transform(
            lambda x: x / x.shift(10) - 1
        )

        # Volatility features
        df["intraday_range"] = (df["high"] - df["low"]) / df["close"]
        df["gap"] = df.groupby("ticker").apply(
            lambda x: x["open"] / x["close"].shift(1) - 1
        ).reset_index(level=0, drop=True)

        logger.info("Added {n} lag/rolling features", n=sum(1 for c in df.columns if "lag" in c or "rolling" in c or "momentum" in c))

        return df

    def _create_targets(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create prediction target variables.

        Targets:
            - next_day_return: Continuous return (regression target)
            - next_day_direction: Binary up/down (classification target)
            - next_5day_return: 5-day forward return
        """
        df["next_day_return"] = df.groupby("ticker")["daily_return"].shift(-1)
        df["next_day_direction"] = (df["next_day_return"] > 0).astype(int)
        df["next_5day_return"] = df.groupby("ticker")["close"].transform(
            lambda x: x.shift(-5) / x - 1
        )

        return df

    def _clean_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values and remove non-feature columns."""
        # Drop text columns (no longer needed after sentiment scoring)
        text_cols = ["combined_text", "reddit_text", "news_text", "title",
                     "text", "url", "author", "link", "summary"]
        df = df.drop(columns=[c for c in text_cols if c in df.columns], errors="ignore")

        # Drop rows where target is NaN (last rows of each ticker)
        initial_len = len(df)
        df = df.dropna(subset=["next_day_return"])

        # Forward-fill remaining NaNs in features
        feature_cols = [c for c in df.columns if c not in {"date", "ticker"}]
        df[feature_cols] = df[feature_cols].ffill().fillna(0)

        # Replace infinities
        df = df.replace([np.inf, -np.inf], 0)

        logger.info(
            "Cleaned dataset: {dropped} rows dropped (missing targets), "
            "{final} rows remaining",
            dropped=initial_len - len(df),
            final=len(df),
        )

        return df

    @property
    def feature_columns(self) -> list[str]:
        """Return list of computed feature column names."""
        return self._feature_columns

    def save(self, df: pd.DataFrame, filename: str = "features.parquet") -> str:
        """Save feature-engineered dataset."""
        path = DATA_DIR / "processed" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, index=False)
        logger.info("Saved features to {path} ({n} rows, {c} cols)", path=path, n=len(df), c=len(df.columns))
        return str(path)
