"""Reddit sentiment data scraper.

Scrapes posts from financial subreddits (stocks, wallstreetbets, investing)
and extracts titles, scores, comment counts, and timestamps for downstream
sentiment analysis via FinBERT.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import praw
from loguru import logger

from src.utils.config import DATA_DIR, get_config


class RedditScraper:
    """Scrapes financial subreddits for sentiment-relevant post data.

    Uses PRAW (Python Reddit API Wrapper) to collect post metadata
    from configurable subreddits. Outputs a structured DataFrame
    ready for FinBERT sentiment scoring.

    Attributes:
        reddit: Authenticated PRAW Reddit instance.
        subreddits: List of subreddit names to scrape.
        post_limit: Maximum posts per subreddit to collect.
    """

    def __init__(self) -> None:
        cfg = get_config()

        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID", ""),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
            user_agent=os.getenv("REDDIT_USER_AGENT", "MarketSentimentEngine/1.0"),
        )
        self.subreddits: list[str] = cfg.data.reddit.subreddits
        self.post_limit: int = cfg.data.reddit.post_limit
        self.sort_by: str = cfg.data.reddit.sort_by

    def scrape(self, ticker: str | None = None) -> pd.DataFrame:
        """Scrape posts from all configured subreddits.

        Args:
            ticker: Optional stock ticker to filter posts (e.g., "AAPL").
                    If None, scrapes all posts without filtering.

        Returns:
            DataFrame with columns: [title, text, score, num_comments,
            created_utc, subreddit, ticker, url]
        """
        all_posts: list[dict[str, Any]] = []

        for sub_name in self.subreddits:
            try:
                posts = self._scrape_subreddit(sub_name, ticker)
                all_posts.extend(posts)
                logger.info(
                    "Scraped {count} posts from r/{sub}",
                    count=len(posts),
                    sub=sub_name,
                )
            except Exception as e:
                logger.error("Failed to scrape r/{sub}: {err}", sub=sub_name, err=e)

        if not all_posts:
            logger.warning("No posts collected from any subreddit")
            return pd.DataFrame()

        df = pd.DataFrame(all_posts)
        df["created_utc"] = pd.to_datetime(df["created_utc"], unit="s", utc=True)
        df = df.sort_values("created_utc", ascending=False).reset_index(drop=True)

        # Deduplicate by URL
        df = df.drop_duplicates(subset=["url"], keep="first")

        logger.info("Total Reddit posts collected: {n}", n=len(df))
        return df

    def _scrape_subreddit(
        self, subreddit_name: str, ticker: str | None
    ) -> list[dict[str, Any]]:
        """Scrape a single subreddit.

        Args:
            subreddit_name: Name of the subreddit.
            ticker: Optional ticker filter.

        Returns:
            List of post dictionaries.
        """
        subreddit = self.reddit.subreddit(subreddit_name)

        # Select sort method
        if self.sort_by == "hot":
            submissions = subreddit.hot(limit=self.post_limit)
        elif self.sort_by == "new":
            submissions = subreddit.new(limit=self.post_limit)
        elif self.sort_by == "top":
            submissions = subreddit.top(limit=self.post_limit, time_filter="month")
        else:
            submissions = subreddit.hot(limit=self.post_limit)

        posts = []
        for submission in submissions:
            # Skip stickied/pinned posts
            if submission.stickied:
                continue

            title = submission.title
            text = submission.selftext[:1000] if submission.selftext else ""

            # If ticker filter is set, check if post mentions it
            if ticker and ticker.upper() not in (title + " " + text).upper():
                continue

            posts.append(
                {
                    "title": title,
                    "text": text,
                    "score": submission.score,
                    "upvote_ratio": submission.upvote_ratio,
                    "num_comments": submission.num_comments,
                    "created_utc": submission.created_utc,
                    "subreddit": subreddit_name,
                    "ticker": ticker or "GENERAL",
                    "url": submission.url,
                    "author": str(submission.author) if submission.author else "[deleted]",
                }
            )

        return posts

    def save(self, df: pd.DataFrame, filename: str = "reddit_posts.parquet") -> str:
        """Save scraped data to parquet file.

        Args:
            df: DataFrame of scraped posts.
            filename: Output filename.

        Returns:
            Path to saved file.
        """
        path = DATA_DIR / "raw" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, index=False)
        logger.info("Saved Reddit data to {path} ({n} rows)", path=path, n=len(df))
        return str(path)


def main() -> None:
    """CLI entry point for Reddit scraping."""
    from src.utils.logger import setup_logger

    setup_logger()
    cfg = get_config()
    scraper = RedditScraper()

    all_dfs = []
    for ticker in cfg.data.tickers:
        logger.info("Scraping Reddit for ticker: {t}", t=ticker)
        df = scraper.scrape(ticker=ticker)
        all_dfs.append(df)

    combined = pd.concat(all_dfs, ignore_index=True).drop_duplicates(subset=["url"])
    scraper.save(combined)


if __name__ == "__main__":
    main()
