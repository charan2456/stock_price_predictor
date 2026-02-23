"""Data ingestion modules."""

from src.data.data_pipeline import DataPipeline
from src.data.market_data import MarketDataFetcher
from src.data.news_scraper import NewsScraper
from src.data.reddit_scraper import RedditScraper

__all__ = ["DataPipeline", "MarketDataFetcher", "NewsScraper", "RedditScraper"]
