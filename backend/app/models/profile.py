"""Profile ORM model for candidate personal and educational information.

Defines the `profile` table according to H.I.R.E. database specifications
in `docs/04_DATABASE_DESIGN.md`.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Profile(Base):
    """Stores candidate personal, academic, and career aspiration details."""

    __tablename__ = "profile"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Unique identifier for the profile.",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("user.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
        doc="Foreign key reference to user.id (one-to-one relationship).",
    )
    first_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Candidate first name.",
    )
    last_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Candidate last name.",
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Candidate phone contact number.",
    )
    college: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Attended college or university.",
    )
    degree: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Academic degree or qualification obtained.",
    )
    graduation_year: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Year of graduation.",
    )
    career_goal: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Candidate statement of career aspirations and goals.",
    )

    # Relationship back to User
    user: Mapped[User] = relationship(
        "User",
        back_populates="profile",
    )

    def __repr__(self) -> str:
        return (
            f"<Profile(id={self.id}, user_id={self.user_id}, "
            f"name='{self.first_name} {self.last_name}')>"
        )
