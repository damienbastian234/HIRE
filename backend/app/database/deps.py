"""
FastAPI database session dependency for H.I.R.E.

Yields a scoped SQLAlchemy session that is committed on success
and rolled back + closed on any exception.

Usage:
    from app.database.deps import get_db

    @router.get("/example")
    def example(db: Session = Depends(get_db)):
        ...
"""

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.database.base import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
