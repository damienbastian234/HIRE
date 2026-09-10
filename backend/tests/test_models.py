"""Unit tests for H.I.R.E. database ORM models (User, Profile, Resume).

Tests verify:
- Table registration in Base.metadata
- Model instantiation and UUID primary key generation
- Required fields and unique constraints
- One-to-One relationship between User and Profile
- One-to-Many relationship between User and Resume
- Cascade deletion behavior (User deletion removes associated Profile and Resumes)
- Complete execution on SQLite in-memory without an external PostgreSQL server
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models import Profile, Resume, User


# =========================================================================== #
# 1. Metadata and Table Registration Tests
# =========================================================================== #


class TestModelMetadata:
    """Verify tables and columns match the H.I.R.E. database specification."""

    def test_tables_registered_in_base_metadata(self) -> None:
        """Verify user, profile, and resume tables are registered in Base.metadata."""
        registered_tables = set(Base.metadata.tables.keys())
        assert "user" in registered_tables
        assert "profile" in registered_tables
        assert "resume" in registered_tables

    def test_user_table_columns_match_spec(self) -> None:
        """Verify columns on the user table match docs/04_DATABASE_DESIGN.md."""
        columns = Base.metadata.tables["user"].columns.keys()
        expected = {"id", "email", "password_hash", "role", "created_at", "updated_at"}
        assert expected.issubset(set(columns))

    def test_profile_table_columns_match_spec(self) -> None:
        """Verify columns on the profile table match docs/04_DATABASE_DESIGN.md."""
        columns = Base.metadata.tables["profile"].columns.keys()
        expected = {
            "id",
            "user_id",
            "first_name",
            "last_name",
            "phone",
            "college",
            "degree",
            "graduation_year",
            "career_goal",
        }
        assert expected.issubset(set(columns))

    def test_resume_table_columns_match_spec(self) -> None:
        """Verify columns on the resume table match docs/04_DATABASE_DESIGN.md."""
        columns = Base.metadata.tables["resume"].columns.keys()
        expected = {"id", "user_id", "file_name", "file_path", "upload_date", "parsing_status"}
        assert expected.issubset(set(columns))


# =========================================================================== #
# 2. User Model Tests
# =========================================================================== #


class TestUserModel:
    """Tests for User model creation, UUIDs, constraints, and timestamps."""

    def test_create_user_with_uuid_pk(self, db_session: Session) -> None:
        """Verify a user can be created with an auto-generated UUID primary key."""
        user = User(
            email="candidate@hire.ai",
            password_hash="hashed_secret_123",
            role="candidate",
        )
        db_session.add(user)
        db_session.commit()

        assert isinstance(user.id, uuid.UUID)
        assert user.email == "candidate@hire.ai"
        assert user.role == "candidate"
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_user_email_unique_constraint(self, db_session: Session) -> None:
        """Verify duplicate email addresses are rejected by the unique constraint."""
        user1 = User(
            email="unique@hire.ai",
            password_hash="hash1",
            role="candidate",
        )
        user2 = User(
            email="unique@hire.ai",
            password_hash="hash2",
            role="candidate",
        )
        db_session.add(user1)
        db_session.commit()

        db_session.add(user2)
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

    def test_user_required_fields_enforced(self, db_session: Session) -> None:
        """Verify required fields (password_hash) cannot be null."""
        invalid_user = User(email="missing_hash@hire.ai", password_hash=None)  # type: ignore[arg-type]
        db_session.add(invalid_user)
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

    def test_user_repr(self) -> None:
        """Verify __repr__ formats user identity cleanly."""
        user = User(email="repr@hire.ai", role="admin")
        representation = repr(user)
        assert "repr@hire.ai" in representation
        assert "admin" in representation


# =========================================================================== #
# 3. Profile Model Tests & One-to-One Relationship
# =========================================================================== #


class TestProfileModel:
    """Tests for Profile model creation, fields, and 1:1 relationship with User."""

    def test_create_profile_associated_with_user(self, db_session: Session) -> None:
        """Verify Profile can be created and accessed via User.profile relationship."""
        user = User(
            email="profile_test@hire.ai",
            password_hash="hashed_pw",
            role="candidate",
        )
        db_session.add(user)
        db_session.commit()

        profile = Profile(
            user_id=user.id,
            first_name="Jane",
            last_name="Doe",
            phone="+1-555-0199",
            college="Stanford University",
            degree="M.S. Computer Science",
            graduation_year=2024,
            career_goal="Senior AI Architect",
        )
        db_session.add(profile)
        db_session.commit()

        # Refresh and verify relationship in both directions
        db_session.refresh(user)
        db_session.refresh(profile)

        assert isinstance(profile.id, uuid.UUID)
        assert user.profile is not None
        assert user.profile.first_name == "Jane"
        assert user.profile.college == "Stanford University"
        assert profile.user.email == "profile_test@hire.ai"

    def test_profile_one_to_one_uniqueness_enforced(self, db_session: Session) -> None:
        """Verify that a single User cannot have more than one Profile."""
        user = User(
            email="single_profile@hire.ai",
            password_hash="hash",
            role="candidate",
        )
        db_session.add(user)
        db_session.commit()

        profile1 = Profile(user_id=user.id, first_name="First")
        profile2 = Profile(user_id=user.id, first_name="Second")

        db_session.add(profile1)
        db_session.commit()

        db_session.add(profile2)
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

    def test_profile_optional_fields_default_to_none(self, db_session: Session) -> None:
        """Verify that optional profile fields default to None without errors."""
        user = User(email="sparse@hire.ai", password_hash="hash")
        db_session.add(user)
        db_session.commit()

        profile = Profile(user_id=user.id)
        db_session.add(profile)
        db_session.commit()

        assert profile.first_name is None
        assert profile.last_name is None
        assert profile.phone is None
        assert profile.college is None
        assert profile.graduation_year is None

    def test_profile_repr(self) -> None:
        """Verify __repr__ formats profile cleanly."""
        profile = Profile(first_name="Alice", last_name="Smith")
        assert "Alice Smith" in repr(profile)


# =========================================================================== #
# 4. Resume Model Tests & One-to-Many Relationship
# =========================================================================== #


class TestResumeModel:
    """Tests for Resume model creation, upload metadata, and 1:N relationship with User."""

    def test_create_resume_associated_with_user(self, db_session: Session) -> None:
        """Verify Resume can be created and linked to a User."""
        user = User(email="resume_user@hire.ai", password_hash="hash")
        db_session.add(user)
        db_session.commit()

        resume = Resume(
            user_id=user.id,
            file_name="jane_doe_cv.pdf",
            file_path="/uploads/raw/jane_doe_cv.pdf",
            parsing_status="pending",
        )
        db_session.add(resume)
        db_session.commit()

        assert isinstance(resume.id, uuid.UUID)
        assert resume.file_name == "jane_doe_cv.pdf"
        assert resume.parsing_status == "pending"
        assert resume.upload_date is not None
        assert resume.user.email == "resume_user@hire.ai"

    def test_user_can_have_multiple_resumes(self, db_session: Session) -> None:
        """Verify One-to-Many relationship allows multiple resumes per user."""
        user = User(email="multi_resume@hire.ai", password_hash="hash")
        db_session.add(user)
        db_session.commit()

        resume1 = Resume(
            user_id=user.id,
            file_name="resume_v1.pdf",
            file_path="/uploads/resume_v1.pdf",
        )
        resume2 = Resume(
            user_id=user.id,
            file_name="resume_v2.pdf",
            file_path="/uploads/resume_v2.pdf",
        )
        db_session.add_all([resume1, resume2])
        db_session.commit()

        db_session.refresh(user)
        assert len(user.resumes) == 2
        file_names = {r.file_name for r in user.resumes}
        assert file_names == {"resume_v1.pdf", "resume_v2.pdf"}

    def test_resume_required_fields_enforced(self, db_session: Session) -> None:
        """Verify missing file_name or file_path raises IntegrityError."""
        user = User(email="invalid_resume@hire.ai", password_hash="hash")
        db_session.add(user)
        db_session.commit()

        invalid_resume = Resume(user_id=user.id, file_name=None, file_path="path")  # type: ignore[arg-type]
        db_session.add(invalid_resume)
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

    def test_resume_repr(self) -> None:
        """Verify __repr__ formats resume cleanly."""
        resume = Resume(file_name="test.pdf", parsing_status="completed")
        assert "test.pdf" in repr(resume)
        assert "completed" in repr(resume)


# =========================================================================== #
# 5. Cascading Deletion Tests
# =========================================================================== #


class TestCascadeBehavior:
    """Verify that deleting a User cascades to delete their Profile and Resumes."""

    def test_delete_user_cascades_to_profile(self, db_session: Session) -> None:
        """Verify deleting a User automatically removes their associated Profile."""
        user = User(email="cascade_profile@hire.ai", password_hash="hash")
        db_session.add(user)
        db_session.commit()

        profile = Profile(user_id=user.id, first_name="Cascade", last_name="Test")
        db_session.add(profile)
        db_session.commit()

        profile_id = profile.id

        # Delete the user
        db_session.delete(user)
        db_session.commit()

        # Verify profile is also deleted
        retrieved_profile = db_session.scalars(
            select(Profile).where(Profile.id == profile_id)
        ).first()
        assert retrieved_profile is None

    def test_delete_user_cascades_to_resumes(self, db_session: Session) -> None:
        """Verify deleting a User automatically removes all their associated Resumes."""
        user = User(email="cascade_resume@hire.ai", password_hash="hash")
        db_session.add(user)
        db_session.commit()

        resume1 = Resume(
            user_id=user.id,
            file_name="cv1.pdf",
            file_path="/path/cv1.pdf",
        )
        resume2 = Resume(
            user_id=user.id,
            file_name="cv2.pdf",
            file_path="/path/cv2.pdf",
        )
        db_session.add_all([resume1, resume2])
        db_session.commit()

        resume1_id = resume1.id
        resume2_id = resume2.id

        # Delete the user
        db_session.delete(user)
        db_session.commit()

        # Verify both resumes are deleted
        remaining_resumes = db_session.scalars(
            select(Resume).where(Resume.id.in_([resume1_id, resume2_id]))
        ).all()
        assert len(remaining_resumes) == 0


# =========================================================================== #
# 6. Complete Offline Execution Test
# =========================================================================== #


class TestOfflineDatabaseExecution:
    """Verify all ORM operations execute cleanly in SQLite with no external services."""

    def test_end_to_end_user_lifecycle_offline(self, db_session: Session) -> None:
        """Execute full User + Profile + Resume lifecycle in isolated SQLite memory."""
        # 1. Create User
        user = User(
            email="offline_candidate@hire.ai",
            password_hash="pw_hash_secure",
            role="candidate",
        )
        db_session.add(user)
        db_session.commit()

        # 2. Attach Profile
        profile = Profile(
            user_id=user.id,
            first_name="Ada",
            last_name="Lovelace",
            degree="Mathematics",
        )
        db_session.add(profile)

        # 3. Attach Resume
        resume = Resume(
            user_id=user.id,
            file_name="ada_cv.pdf",
            file_path="/storage/ada_cv.pdf",
            parsing_status="completed",
        )
        db_session.add(resume)
        db_session.commit()

        # 4. Query through relationships
        db_session.refresh(user)
        assert user.profile.first_name == "Ada"
        assert len(user.resumes) == 1
        assert user.resumes[0].file_name == "ada_cv.pdf"

        # 5. Update
        user.profile.career_goal = "Build First Computer Program"
        db_session.commit()

        retrieved_profile = db_session.scalars(
            select(Profile).where(Profile.user_id == user.id)
        ).first()
        assert retrieved_profile is not None
        assert retrieved_profile.career_goal == "Build First Computer Program"
