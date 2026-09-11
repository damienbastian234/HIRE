"""Skill ORM model for candidate extracted skills.

Defines the `skill` table according to H.I.R.E. database specifications
in `docs/04_DATABASE_DESIGN.md`.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.resume import Resume


class Skill(Base):
    """Stores extracted skills associated with candidate resumes."""

    __tablename__ = "skill"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Unique identifier for the extracted skill record.",
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("resume.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        doc="Foreign key reference to resume.id (parent resume).",
    )
    skill_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Name of the skill (e.g., Python, Docker, Machine Learning).",
    )
    skill_category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Category of the skill (e.g., Programming Language, Cloud, Soft Skill).",
    )
    confidence_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric,
        nullable=True,
        doc="Confidence score of skill extraction from 0.0 to 1.0.",
    )

    # Relationship back to Resume (with bidirectional collection backref)
    resume: Mapped[Resume] = relationship(
        "Resume",
        backref=backref(
            "skills",
            cascade="all, delete-orphan",
            passive_deletes=True,
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Skill(id={self.id}, resume_id={self.resume_id}, "
            f"skill_name='{self.skill_name}', category='{self.skill_category}')>"
        )
