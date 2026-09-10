"""
Repository layer for H.I.R.E. database access.

Keeps SQL queries out of routes and makes them testable in isolation.
All methods accept an SQLAlchemy Session as the first argument.
"""

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.database.models import Application, Profile, User


# ---------------------------------------------------------------------------
# User repository
# ---------------------------------------------------------------------------

class UserRepository:

    @staticmethod
    def get_by_email(db: Session, email: str) -> User | None:
        return db.query(User).filter(User.email == email.strip().lower()).first()

    @staticmethod
    def get_by_id(db: Session, user_id: str) -> User | None:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def create(
        db: Session,
        *,
        name: str,
        email: str,
        password_hash: str,
        role: str = "candidate",
    ) -> User:
        user = User(
            name=name.strip(),
            email=email.strip().lower(),
            password_hash=password_hash,
            role=role,
        )
        db.add(user)
        db.flush()   # get the auto-generated id before commit
        return user

    @staticmethod
    def update_name(db: Session, user: User, name: str) -> User:
        user.name = name.strip()
        db.flush()
        return user


# ---------------------------------------------------------------------------
# Profile repository
# ---------------------------------------------------------------------------

class ProfileRepository:

    @staticmethod
    def get_by_user_id(db: Session, user_id: str) -> Profile | None:
        return db.query(Profile).filter(Profile.user_id == user_id).first()

    @staticmethod
    def get_or_create(db: Session, user: User) -> Profile:
        profile = ProfileRepository.get_by_user_id(db, user.id)
        if profile is None:
            profile = Profile(user_id=user.id)
            db.add(profile)
            db.flush()
        return profile

    @staticmethod
    def update(db: Session, profile: Profile, updates: dict) -> Profile:
        # Only update whitelisted, non-role fields.
        allowed = {"title", "location", "bio", "phone", "linkedin", "github", "portfolio"}
        for field, value in updates.items():
            if field in allowed and value is not None:
                setattr(profile, field, value)
        db.flush()
        return profile


# ---------------------------------------------------------------------------
# Application repository
# ---------------------------------------------------------------------------

class ApplicationRepository:

    @staticmethod
    def exists(db: Session, user_id: str, job_id: str) -> bool:
        return (
            db.query(Application)
            .filter(and_(Application.user_id == user_id, Application.job_id == job_id))
            .first()
        ) is not None

    @staticmethod
    def create(
        db: Session,
        *,
        user_id: str,
        job_id: str,
        job_title: str,
        company: str,
    ) -> Application:
        app = Application(
            user_id=user_id,
            job_id=job_id,
            job_title=job_title,
            company=company,
        )
        db.add(app)
        db.flush()
        return app

    @staticmethod
    def list_by_user(db: Session, user_id: str) -> list[Application]:
        return (
            db.query(Application)
            .filter(Application.user_id == user_id)
            .order_by(Application.applied_at.desc())
            .all()
        )

    @staticmethod
    def count_all(db: Session) -> int:
        return db.query(Application).count()
