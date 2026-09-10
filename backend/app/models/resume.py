"""Resume ORM model for candidate resume file metadata.

Defines the `resume` table according to H.I.R.E. database specifications
in `docs/04_DATABASE_DESIGN.md`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Resume(Base):
    """Stores uploaded resume file paths, metadata, and ingestion processing status."""

    __tablename__ = "resume"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Unique identifier for the resume record.",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("user.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        doc="Foreign key reference to user.id (owner of this resume).",
    )
    file_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Original uploaded file name.",
    )
    file_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Server storage path or URI where the resume file is stored.",
    )
    upload_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Timestamp when the file was uploaded, in UTC.",
    )
    parsing_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        doc="Status of resume parsing and AI processing (e.g., pending, processing, completed, failed).",
    )

    # Relationship back to User
    user: Mapped[User] = relationship(
        "User",
        back_populates="resumes",
    )

    def __repr__(self) -> str:
        return (
            f"<Resume(id={self.id}, user_id={self.user_id}, "
            f"file_name='{self.file_name}', status='{self.parsing_status}')>"
        )
