"""CRUD repository for Profile model.

Manages candidate profile creation, retrieval by user ID, and partial updates.
"""

from __future__ import annotations

from typing import Any, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException
from app.crud.base import CRUDBase
from app.models.profile import Profile


class CRUDProfile(CRUDBase[Profile]):
    """Repository managing Profile entity persistence and queries."""

    # Set of updatable column names on the profile model
    _UPDATABLE_FIELDS = {
        "first_name",
        "last_name",
        "phone",
        "college",
        "degree",
        "graduation_year",
        "career_goal",
    }

    def __init__(self) -> None:
        """Initialize repository bound to the Profile model."""
        super().__init__(Profile)

    def get_by_user_id(self, db: Session, user_id: uuid.UUID) -> Optional[Profile]:
        """Retrieve a profile associated with a specific user UUID.

        Args:
            db: Active database session.
            user_id: User's UUID.

        Returns:
            The Profile instance if found, or None.
        """
        stmt = select(Profile).where(Profile.user_id == user_id)
        return db.scalars(stmt).first()

    def create(
        self,
        db: Session,
        user_id: uuid.UUID,
        **profile_data: Any,
    ) -> Profile:
        """Create and persist a new Profile record for a user.

        Args:
            db: Active database session.
            user_id: Foreign key reference to User.id.
            **profile_data: Profile attributes (first_name, last_name, etc.).

        Returns:
            The newly created and refreshed Profile instance.

        Raises:
            ConflictException: If a profile for this user already exists.
        """
        if self.get_by_user_id(db, user_id=user_id) is not None:
            raise ConflictException(f"Profile for user '{user_id}' already exists.")

        filtered_data = {
            key: value
            for key, value in profile_data.items()
            if key in self._UPDATABLE_FIELDS
        }

        profile = Profile(
            user_id=user_id,
            **filtered_data,
        )
        db.add(profile)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ConflictException(
                f"Failed to create profile for user '{user_id}': integrity constraint violated."
            ) from exc
        except Exception:
            db.rollback()
            raise

        db.refresh(profile)
        return profile

    def update(
        self,
        db: Session,
        user_id: uuid.UUID,
        **profile_data: Any,
    ) -> Optional[Profile]:
        """Update existing profile fields for a user.

        Only updates fields that are explicitly supplied in profile_data.
        Unspecified fields remain untouched and are not overwritten with None.

        Args:
            db: Active database session.
            user_id: User UUID whose profile should be updated.
            **profile_data: Fields to update.

        Returns:
            The updated Profile instance, or None if the profile was not found.
        """
        profile = self.get_by_user_id(db, user_id=user_id)
        if profile is None:
            return None

        for field, value in profile_data.items():
            if field in self._UPDATABLE_FIELDS:
                setattr(profile, field, value)

        db.add(profile)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        db.refresh(profile)
        return profile

    def create_or_update(
        self,
        db: Session,
        user_id: uuid.UUID,
        **profile_data: Any,
    ) -> Profile:
        """Create a profile if none exists, or update the existing one.

        Args:
            db: Active database session.
            user_id: Target user UUID.
            **profile_data: Profile attributes to set or update.

        Returns:
            The created or updated Profile instance.
        """
        existing = self.get_by_user_id(db, user_id=user_id)
        if existing is None:
            return self.create(db, user_id=user_id, **profile_data)
        updated = self.update(db, user_id=user_id, **profile_data)
        assert updated is not None
        return updated


crud_profile = CRUDProfile()
