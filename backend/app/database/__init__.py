"""Database layer package exports for H.I.R.E.

Exports SQLAlchemy 2.0 DeclarativeBase (`Base`), session factory (`SessionLocal`),
engine creation helper (`create_db_engine`), default engine instance (`engine`),
and the FastAPI session dependency (`get_db`).
"""

from __future__ import annotations

from app.database.base import Base
from app.database.session import SessionLocal, create_db_engine, engine, get_db

__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "create_db_engine",
]
