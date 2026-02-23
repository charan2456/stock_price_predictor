"""Financial news scraper via RSS feeds.

Aggregates financial news articles from multiple RSS sources (Reuters,
Yahoo Finance, MarketWatch) for sentiment analysis. Extracts headlines,
summaries, and publication dates.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import feedparser
import pandas as pd
from loguru import logger

from src.utils.config import DATA_DIR, get_config


class NewsScraper:
    """Aggregates financial news from multiple RSS feeds.

    Parses RSS/Atom feeds to collect article headlines and summaries
    for downstream FinBERT sentiment analysis. Supports configurable
    feed sources and per-ticker keyword filtering.

    Attributes:
        feeds: List of feed configurations (name, url).
        max_articles: Maximum articles to collect per feed.
    """

    def __init__(self) -> None:
        cfg = get_config()
        self.feeds: list[dict[str, str]] = cfg.data.news.feeds
        self.max_articles: int = cfg.data.news.max_articles

    def scrape(self, ticker: str | None = None) -> pd.DataFrame:
        """Scrape all configured RSS feeds.

        Args:
            ticker: Optional ticker to filter articles by keyword.

        Returns:
            DataFrame with columns: [title, summary, published,
            source, link, ticker]
        """
        all_articles: list[dict[str, Any]] = []

        for feed_config in self.feeds:
            try:
                articles = self._parse_feed(feed_config, ticker)
                all_articles.extend(articles)
                logger.info(
                    "Parsed {n} articles from {src}",
                    n=len(articles),
                    src=feed_config["name"],
                )
            except Exception as e:
                logger.error(
                    "Failed to parse feed {src}: {err}",
                    src=feed_config["name"],
                    err=e,
                )

        if not all_articles:
            logger.warning("No articles collected from any feed")
            return pd.DataFrame()

        df = pd.DataFrame(all_articles)
        df = df.drop_duplicates(subset=["link"], keep="first")
        df = df.sort_values("published", ascending=False).reset_index(drop=True)

        logger.info("Total news articles collected: {n}", n=len(df))
        return df

    def _parse_feed(
        self, feed_config: dict[str, str], ticker: str | None
    ) -> list[dict[str, Any]]:
        """Parse a single RSS feed.

        Args:
            feed_config: Dict with 'name' and 'url' keys.
            ticker: Optional ticker filter.

        Returns:
            List of article dictionaries.
        """
        feed = feedparser.parse(feed_config["url"])
        articles = []

        for entry in feed.entries[: self.max_articles]:
            title = entry.get("title", "")
            summary = entry.get("summary", entry.get("description", ""))

            # Clean HTML tags from summary
            if summary:
                summary = re.sub(r"<[^>]+>", "", summary)[:500]

            # Ticker filter
            if ticker:
                search_text = f"{title} {summary}".upper()
                # Check for ticker symbol or common company name patterns
                if ticker.upper() not in search_text:
                    continue

            # Parse publication date
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                except (TypeError, ValueError):
                    published = datetime.now(timezone.utc)
            else:
                published = datetime.now(timezone.utc)

            articles.append(
                {
                    "title": title,
                    "summary": summary,
                    "published": published,
                    "source": feed_config["name"],
                    "link": entry.get("link", ""),
                    "ticker": ticker or "GENERAL",
                }
            )

        return articles

    def save(self, df: pd.DataFrame, filename: str = "news_articles.parquet") -> str:
        """Save scraped articles to parquet file.

        Args:
            df: DataFrame of scraped articles.
            filename: Output filename.

        Returns:
            Path to saved file.
        """
        path = DATA_DIR / "raw" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, index=False)
        logger.info("Saved news data to {path} ({n} rows)", path=path, n=len(df))
        return str(path)


def main() -> None:
    """CLI entry point for news scraping."""
    from src.utils.logger import setup_logger

    setup_logger()
    cfg = get_config()
    scraper = NewsScraper()

    all_dfs = []
    for ticker in cfg.data.tickers:
        logger.info("Scraping news for ticker: {t}", t=ticker)
        df = scraper.scrape(ticker=ticker)
        all_dfs.append(df)

    combined = pd.concat(all_dfs, ignore_index=True).drop_duplicates(subset=["link"])
    scraper.save(combined)


if __name__ == "__main__":
    main()
