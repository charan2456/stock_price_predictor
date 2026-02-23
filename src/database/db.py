"""PostgreSQL database engine and session management.

Uses PostgreSQL via psycopg2. Connection URL comes from config
or environment variable DATABASE_URL.

Usage:
    from src.database.db import get_db, init_db

    init_db()  # Create tables on startup
    db = get_db()  # Get a session
"""

from __future__ import annotations

import os

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.database.models import Base
from src.utils.config import get_config

_engine = None
_SessionLocal = None


def _get_database_url() -> str:
    """Resolve the PostgreSQL database URL.

    Priority: DATABASE_URL env var > config file > default local pg.
    """
    # 1. Environment variable (highest priority, used by Docker)
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    # 2. Config file
    cfg = get_config()
    if hasattr(cfg, "database") and hasattr(cfg.database, "url"):
        return cfg.database.url

    # 3. Default: local PostgreSQL
    return "postgresql://sentinel:sentinel@localhost:5432/market_sentinel"


def init_db() -> None:
    """Initialize PostgreSQL engine and create all tables."""
    global _engine, _SessionLocal

    url = _get_database_url()

    _engine = create_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        echo=False,
    )
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)

    # Create tables if they don't exist
    Base.metadata.create_all(bind=_engine)
    logger.info("PostgreSQL initialized | {url}", url=url.split("@")[-1])


def get_db() -> Session:
    """Get a new database session.

    Usage:
        db = get_db()
        try:
            # ... do work ...
            db.commit()
        finally:
            db.close()
    """
    if _SessionLocal is None:
        init_db()

    return _SessionLocal()  # type: ignore[misc]


def close_db() -> None:
    """Close the database engine and connection pool."""
    global _engine, _SessionLocal

    if _engine is not None:
        _engine.dispose()
        _engine = None
        _SessionLocal = None
        logger.info("PostgreSQL connection pool closed")
