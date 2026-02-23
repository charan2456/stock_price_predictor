"""Historical market data fetcher via yfinance.

Downloads OHLCV (Open, High, Low, Close, Volume) data for configured
tickers with automatic date range management and data validation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


import numpy as np
import pandas as pd
import yfinance as yf
from loguru import logger

from src.utils.config import DATA_DIR, get_config


class MarketDataFetcher:
    """Fetches historical stock price data from Yahoo Finance.

    Downloads OHLCV data with configurable lookback period, validates
    data completeness, and computes basic derived fields (daily returns,
    log returns) needed for downstream feature engineering.

    Attributes:
        tickers: List of stock ticker symbols.
        lookback_days: Number of historical days to fetch.
        interval: Data frequency (1d, 1h, 5m).
    """

    def __init__(self) -> None:
        cfg = get_config()
        self.tickers: list[str] = cfg.data.tickers
        self.lookback_days: int = cfg.data.lookback_days
        self.interval: str = cfg.data.market.interval

    def fetch(self, ticker: str) -> pd.DataFrame:
        """Fetch OHLCV data for a single ticker.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL").

        Returns:
            DataFrame with columns: [open, high, low, close, volume,
            daily_return, log_return, ticker, date]
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=self.lookback_days)

        logger.info(
            "Fetching {ticker} data: {start} → {end} ({interval})",
            ticker=ticker,
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            interval=self.interval,
        )

        try:
            stock = yf.Ticker(ticker)
            df = stock.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval=self.interval,
            )
        except Exception as e:
            logger.error("Failed to fetch {ticker}: {err}", ticker=ticker, err=e)
            return pd.DataFrame()

        if df.empty:
            logger.warning("No data returned for {ticker}", ticker=ticker)
            return pd.DataFrame()

        # Standardize column names
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]

        # Ensure we have the expected columns
        expected_cols = ["open", "high", "low", "close", "volume"]
        for col in expected_cols:
            if col not in df.columns:
                logger.warning("Missing column {col} for {ticker}", col=col, ticker=ticker)

        # Compute derived fields
        df["daily_return"] = df["close"].pct_change()
        df["log_return"] = np.log(df["close"] / df["close"].shift(1))
        df["ticker"] = ticker

        # Reset index to get date as a column
        df = df.reset_index()
        if "Date" in df.columns:
            df = df.rename(columns={"Date": "date"})
        elif "Datetime" in df.columns:
            df = df.rename(columns={"Datetime": "date"})

        # Remove timezone info for easier merging
        if "date" in df.columns and hasattr(df["date"].dtype, "tz"):
            df["date"] = df["date"].dt.tz_localize(None)

        # Drop rows with NaN returns (first row)
        df = df.dropna(subset=["daily_return"])

        # Validate data quality
        self._validate(df, ticker)

        logger.info(
            "Fetched {n} rows for {ticker} | "
            "Date range: {start} to {end}",
            n=len(df),
            ticker=ticker,
            start=df["date"].min().strftime("%Y-%m-%d"),
            end=df["date"].max().strftime("%Y-%m-%d"),
        )

        return df

    def fetch_all(self) -> pd.DataFrame:
        """Fetch data for all configured tickers.

        Returns:
            Combined DataFrame with all tickers' OHLCV data.
        """
        all_dfs = []
        for ticker in self.tickers:
            df = self.fetch(ticker)
            if not df.empty:
                all_dfs.append(df)

        if not all_dfs:
            logger.error("Failed to fetch data for any ticker")
            return pd.DataFrame()

        combined = pd.concat(all_dfs, ignore_index=True)
        logger.info(
            "Total market data: {n} rows across {t} tickers",
            n=len(combined),
            t=len(all_dfs),
        )
        return combined

    def _validate(self, df: pd.DataFrame, ticker: str) -> None:
        """Run data quality checks.

        Args:
            df: Fetched DataFrame.
            ticker: Ticker symbol for logging.
        """
        # Check for missing values
        missing = df[["open", "high", "low", "close", "volume"]].isnull().sum()
        if missing.any():
            logger.warning(
                "Missing values in {ticker} data: {cols}",
                ticker=ticker,
                cols=missing[missing > 0].to_dict(),
            )

        # Check for zero volume days
        zero_vol = (df["volume"] == 0).sum()
        if zero_vol > 0:
            logger.warning(
                "{ticker} has {n} zero-volume days",
                ticker=ticker,
                n=zero_vol,
            )

        # Check for extreme returns (potential data errors)
        extreme = (df["daily_return"].abs() > 0.20).sum()
        if extreme > 0:
            logger.warning(
                "{ticker} has {n} days with >20% return (possible data error)",
                ticker=ticker,
                n=extreme,
            )

    def save(self, df: pd.DataFrame, filename: str = "market_data.parquet") -> str:
        """Save market data to parquet file.

        Args:
            df: DataFrame of market data.
            filename: Output filename.

        Returns:
            Path to saved file.
        """
        path = DATA_DIR / "raw" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, index=False)
        logger.info("Saved market data to {path} ({n} rows)", path=path, n=len(df))
        return str(path)


def main() -> None:
    """CLI entry point for market data fetching."""
    from src.utils.logger import setup_logger

    setup_logger()
    fetcher = MarketDataFetcher()
    df = fetcher.fetch_all()
    fetcher.save(df)


if __name__ == "__main__":
    main()
