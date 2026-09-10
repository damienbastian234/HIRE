"""User ORM model for authentication and account metadata.

Defines the `user` table according to H.I.R.E. database specifications
in `docs/04_DATABASE_DESIGN.md`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.profile import Profile
    from app.models.resume import Resume


class User(Base):
    """Stores user authentication information, credentials, and role."""

    __tablename__ = "user"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Unique identifier for the user.",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        doc="User email address, unique across the platform.",
    )
    password_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Hashed account password.",
    )
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="candidate",
        doc="User permission role (e.g., candidate, recruiter, admin).",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        doc="Timestamp when the user registered, in UTC.",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        doc="Timestamp when the user account was last updated, in UTC.",
    )

    # Relationships
    profile: Mapped[Optional[Profile]] = relationship(
        "Profile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    resumes: Mapped[List[Resume]] = relationship(
        "Resume",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
