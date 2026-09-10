"""
SQLAlchemy database engine, session factory, and declarative base for H.I.R.E.

Default: SQLite file at  backend/hire.db  (no external server required).
Override: set DATABASE_URL in .env for PostgreSQL or any other supported backend.

    DATABASE_URL=postgresql+psycopg2://user:pass@localhost/hire
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# Resolve the database URL — fall back to a local SQLite file.
_db_url: str = settings.DATABASE_URL or "sqlite:///./hire.db"

# connect_args is SQLite-specific; ignored by other drivers.
_connect_args = {"check_same_thread": False} if _db_url.startswith("sqlite") else {}

engine = create_engine(
    _db_url,
    connect_args=_connect_args,
    # Reasonable pool settings for development; tune for production.
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


def create_tables() -> None:
    """Create all tables that don't already exist.  Called at app startup."""
    Base.metadata.create_all(bind=engine)
