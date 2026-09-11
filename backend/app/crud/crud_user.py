"""CRUD repository for User model.

Manages user creation, queries by ID or email, and credential persistence.
"""

from __future__ import annotations

from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException
from app.crud.base import CRUDBase
from app.models.user import User


class CRUDUser(CRUDBase[User]):
    """Repository managing User entity persistence and queries."""

    def __init__(self) -> None:
        """Initialize repository bound to the User model."""
        super().__init__(User)

    def get_by_id(self, db: Session, user_id: uuid.UUID) -> Optional[User]:
        """Retrieve a user by their UUID primary key.

        Args:
            db: Active database session.
            user_id: User UUID.

        Returns:
            The User instance if found, or None.
        """
        stmt = select(User).where(User.id == user_id)
        return db.scalars(stmt).first()

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """Retrieve a user by their unique email address.

        Args:
            db: Active database session.
            email: Email address string.

        Returns:
            The User instance if found, or None.
        """
        stmt = select(User).where(User.email == email)
        return db.scalars(stmt).first()

    def create(
        self,
        db: Session,
        email: str,
        password_hash: str,
        role: str = "candidate",
    ) -> User:
        """Create and persist a new User record.

        Args:
            db: Active database session.
            email: Unique user email address.
            password_hash: Pre-computed password hash string.
            role: Permission role (defaults to 'candidate').

        Returns:
            The newly created and refreshed User instance.

        Raises:
            ConflictException: If a user with the specified email already exists.
        """
        # Pre-check unique constraint
        if self.get_by_email(db, email=email) is not None:
            raise ConflictException(f"User with email '{email}' already exists.")

        user = User(
            email=email,
            password_hash=password_hash,
            role=role,
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ConflictException(f"User with email '{email}' already exists.") from exc
        except Exception:
            db.rollback()
            raise

        db.refresh(user)
        return user


crud_user = CRUDUser()
