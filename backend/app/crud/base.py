"""Generic minimal CRUD base class for SQLAlchemy 2.0 models.

Provides standard, type-safe read operations for ORM entities without
forcing domain-specific operations into unnatural abstractions.
"""

from __future__ import annotations

from typing import Any, Generic, List, Optional, Type, TypeVar
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class CRUDBase(Generic[ModelType]):
    """Generic base repository providing fundamental read and query operations."""

    def __init__(self, model: Type[ModelType]) -> None:
        """Initialize repository with a specific model class.

        Args:
            model: SQLAlchemy ORM model class bound to Base.
        """
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """Retrieve a single record by primary key identifier.

        Args:
            db: Active database session.
            id: Primary key value (typically UUID).

        Returns:
            The model instance if found, or None.
        """
        stmt = select(self.model).where(self.model.id == id)
        return db.scalars(stmt).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """Retrieve multiple records with offset and limit pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip from beginning.
            limit: Maximum number of records to return.

        Returns:
            List of retrieved model instances.
        """
        stmt = select(self.model).offset(skip).limit(limit)
        return list(db.scalars(stmt).all())
