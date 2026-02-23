"""Unified data ingestion pipeline orchestrator.

Coordinates Reddit scraping, news aggregation, and market data fetching
into a single pipeline run. Merges all raw data sources by ticker and
date for downstream feature engineering.
"""

from __future__ import annotations

import pandas as pd
from loguru import logger

from src.data.market_data import MarketDataFetcher
from src.data.news_scraper import NewsScraper
from src.data.reddit_scraper import RedditScraper
from src.utils.config import DATA_DIR, get_config


class DataPipeline:
    """Orchestrates multi-source data ingestion and merging.

    Runs all data scrapers in sequence, aligns data by ticker and date,
    and produces a unified dataset ready for feature engineering.

    Pipeline Flow:
        1. Fetch market OHLCV data (yfinance)
        2. Scrape Reddit posts (PRAW)
        3. Scrape financial news (RSS feeds)
        4. Aggregate text data by ticker × date
        5. Merge all sources into unified dataset
        6. Save raw + merged outputs
    """

    def __init__(self) -> None:
        self.cfg = get_config()
        self.market_fetcher = MarketDataFetcher()
        self.reddit_scraper = RedditScraper()
        self.news_scraper = NewsScraper()

    def run(self) -> pd.DataFrame:
        """Execute the full data ingestion pipeline.

        Returns:
            Merged DataFrame with market data + aggregated sentiment text
            aligned by ticker and date.
        """
        logger.info("=" * 60)
        logger.info("Starting data ingestion pipeline")
        logger.info("=" * 60)

        # Step 1: Market Data
        logger.info("Step 1/4: Fetching market data...")
        market_df = self.market_fetcher.fetch_all()
        if market_df.empty:
            raise ValueError("Market data fetch failed — cannot proceed")
        self.market_fetcher.save(market_df)

        # Step 2: Reddit Data
        logger.info("Step 2/4: Scraping Reddit...")
        reddit_dfs = []
        for ticker in self.cfg.data.tickers:
            df = self.reddit_scraper.scrape(ticker=ticker)
            if not df.empty:
                reddit_dfs.append(df)
        if reddit_dfs:
            reddit_df = pd.concat(reddit_dfs, ignore_index=True).drop_duplicates(subset=["url"])
        else:
            reddit_df = pd.DataFrame()
        self.reddit_scraper.save(reddit_df) if not reddit_df.empty else None

        # Step 3: News Data
        logger.info("Step 3/4: Scraping financial news...")
        news_dfs = []
        for ticker in self.cfg.data.tickers:
            df = self.news_scraper.scrape(ticker=ticker)
            if not df.empty:
                news_dfs.append(df)
        if news_dfs:
            news_df = pd.concat(news_dfs, ignore_index=True).drop_duplicates(subset=["link"])
        else:
            news_df = pd.DataFrame()
        self.news_scraper.save(news_df) if not news_df.empty else None

        # Step 4: Merge
        logger.info("Step 4/4: Merging data sources...")
        merged = self._merge_sources(market_df, reddit_df, news_df)

        # Save merged dataset
        output_path = DATA_DIR / "processed" / "merged_dataset.parquet"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        merged.to_parquet(output_path, index=False)

        logger.info("=" * 60)
        logger.info(
            "Pipeline complete | {n} rows | {t} tickers | saved to {p}",
            n=len(merged),
            t=merged["ticker"].nunique(),
            p=output_path,
        )
        logger.info("=" * 60)

        return merged

    def _merge_sources(
        self,
        market_df: pd.DataFrame,
        reddit_df: pd.DataFrame,
        news_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Merge market data with aggregated text data by ticker × date.

        Aggregates Reddit and news text per ticker per day, then joins
        with market OHLCV data.

        Args:
            market_df: Market OHLCV DataFrame.
            reddit_df: Reddit posts DataFrame.
            news_df: News articles DataFrame.

        Returns:
            Merged DataFrame.
        """
        # Normalize dates
        market_df["date"] = pd.to_datetime(market_df["date"]).dt.date

        # Aggregate Reddit text by ticker × date
        reddit_agg = pd.DataFrame()
        if not reddit_df.empty and "created_utc" in reddit_df.columns:
            reddit_df["date"] = pd.to_datetime(reddit_df["created_utc"]).dt.date
            reddit_agg = (
                reddit_df.groupby(["ticker", "date"])
                .agg(
                    reddit_text=("title", lambda x: " [SEP] ".join(x)),
                    reddit_post_count=("title", "count"),
                    reddit_avg_score=("score", "mean"),
                    reddit_total_comments=("num_comments", "sum"),
                )
                .reset_index()
            )

        # Aggregate news text by ticker × date
        news_agg = pd.DataFrame()
        if not news_df.empty and "published" in news_df.columns:
            news_df["date"] = pd.to_datetime(news_df["published"]).dt.date
            news_agg = (
                news_df.groupby(["ticker", "date"])
                .agg(
                    news_text=(
                        "title",
                        lambda x: " [SEP] ".join(x),
                    ),
                    news_article_count=("title", "count"),
                )
                .reset_index()
            )

        # Merge with market data
        merged = market_df.copy()

        if not reddit_agg.empty:
            merged = merged.merge(reddit_agg, on=["ticker", "date"], how="left")

        if not news_agg.empty:
            merged = merged.merge(news_agg, on=["ticker", "date"], how="left")

        # Fill missing text data
        text_cols = [
            "reddit_text", "news_text",
            "reddit_post_count", "reddit_avg_score",
            "reddit_total_comments", "news_article_count",
        ]
        for col in text_cols:
            if col in merged.columns:
                if "text" in col:
                    merged[col] = merged[col].fillna("")
                else:
                    merged[col] = merged[col].fillna(0)

        # Combine all text for unified sentiment scoring
        combined_text_parts = []
        if "reddit_text" in merged.columns:
            combined_text_parts.append(merged["reddit_text"])
        if "news_text" in merged.columns:
            combined_text_parts.append(merged["news_text"])

        if combined_text_parts:
            merged["combined_text"] = combined_text_parts[0]
            for part in combined_text_parts[1:]:
                merged["combined_text"] = merged["combined_text"] + " [SEP] " + part
            merged["combined_text"] = merged["combined_text"].str.strip(" [SEP] ")
        else:
            merged["combined_text"] = ""

        return merged


def main() -> None:
    """CLI entry point for full data pipeline."""
    from src.utils.logger import setup_logger

    setup_logger()
    pipeline = DataPipeline()
    pipeline.run()


if __name__ == "__main__":
    main()
