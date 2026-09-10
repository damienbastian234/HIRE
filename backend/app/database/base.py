"""SQLAlchemy 2.0 Declarative Base for H.I.R.E.

All ORM models must inherit from `Base`.
Domain models (User, Resume, Profile, Skill, etc.) will be introduced in their
respective feature tickets and will inherit from this class.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base class for all database models in the H.I.R.E. platform."""

    pass
