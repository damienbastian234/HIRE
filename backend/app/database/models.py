"""
SQLAlchemy ORM models for H.I.R.E.

Three tables:
  users        — identity, credentials, role
  profiles     — extended candidate/recruiter profile (1-to-1 with users)
  applications — job application records (many-to-one with users)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="candidate")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    profile: Mapped["Profile"] = relationship(
        "Profile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    applications: Mapped[list["Application"]] = relationship(
        "Application", back_populates="user", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        """Return a safe public representation (no password_hash)."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
        }


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # Extended info
    title: Mapped[str | None] = mapped_column(String(120))
    location: Mapped[str | None] = mapped_column(String(120))
    bio: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(30))
    linkedin: Mapped[str | None] = mapped_column(String(255))
    github: Mapped[str | None] = mapped_column(String(255))
    portfolio: Mapped[str | None] = mapped_column(String(255))

    user: Mapped[User] = relationship("User", back_populates="profile")

    def to_dict(self, user: "User") -> dict:
        return {
            "userId": self.user_id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "title": self.title or "",
            "location": self.location or "",
            "bio": self.bio or "",
            "phone": self.phone or "",
            "linkedin": self.linkedin or "",
            "github": self.github or "",
            "portfolio": self.portfolio or "",
        }


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[str] = mapped_column(String(100), nullable=False)
    job_title: Mapped[str] = mapped_column(String(120), nullable=False)
    company: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="In review")
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped[User] = relationship("User", back_populates="applications")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "jobId": self.job_id,
            "jobTitle": self.job_title,
            "company": self.company,
            "status": self.status,
            "updatedAt": self.applied_at.strftime("%b %d, %Y"),
        }
