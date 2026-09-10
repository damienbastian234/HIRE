"""Database session management and engine configuration for H.I.R.E.

Configures the SQLAlchemy engine, sessionmaker factory, and the standard
FastAPI `get_db` generator dependency.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any, Dict, Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def get_engine_args(url: str) -> Dict[str, Any]:
    """Return appropriate connection arguments for the database engine based on the URL scheme."""
    engine_kwargs: Dict[str, Any] = {
        "pool_pre_ping": True,
    }
    if url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    return engine_kwargs


def create_db_engine(url: Optional[str] = None, **kwargs: Any) -> Engine:
    """Create a new SQLAlchemy engine using the specified URL or settings.DATABASE_URL.

    Raises:
        ValueError: If no database URL is provided and settings.DATABASE_URL is not set.
    """
    target_url = url or settings.DATABASE_URL
    if not target_url:
        raise ValueError(
            "DATABASE_URL is not set. Please configure DATABASE_URL in your environment or .env file."
        )

    engine_args = get_engine_args(target_url)
    engine_args.update(kwargs)
    return create_engine(target_url, **engine_args)


# Initialize global engine and SessionLocal factory if DATABASE_URL is configured
engine: Optional[Engine] = None
SessionLocal: sessionmaker[Session]

if settings.DATABASE_URL:
    engine = create_db_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    # When DATABASE_URL is not configured at import time, SessionLocal is created unbound.
    # It can be bound dynamically or overridden by tests.
    SessionLocal = sessionmaker(autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per request and guarantees closing it."""
    if SessionLocal.kw.get("bind") is None:
        if engine is not None:
            SessionLocal.configure(bind=engine)
        else:
            raise RuntimeError(
                "Database session is not bound to an engine. "
                "Ensure DATABASE_URL is configured before accessing the database."
            )

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
