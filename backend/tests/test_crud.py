"""Unit tests for the H.I.R.E. database repository / CRUD layer.

Tests verify:
- User CRUD: create, get_by_id, get_by_email, duplicate email rejection, role defaults, isolation
- Profile CRUD: create, get_by_user_id, update, partial update field preservation, 1:1 constraint, None on nonexistent
- Resume CRUD: create, default 'pending' status, get_by_id, list_by_user_id, cross-user isolation, status update, delete
- Relationship & Cascade integration: ORM navigation, cascading deletion
- Transaction behavior: persistence and clean rollback without session corruption
- CRUDBase generic functionality: get and get_multi pagination
"""

from __future__ import annotations

import uuid
import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException
from app.crud import (
    CRUDBase,
    CRUDProfile,
    CRUDResume,
    CRUDUser,
    crud_profile,
    crud_resume,
    crud_user,
)
from app.models import Profile, Resume, User


# =========================================================================== #
# 1. User CRUD Tests
# =========================================================================== #


class TestUserCRUD:
    """Tests for User repository operations."""

    def test_create_user(self, db_session: Session) -> None:
        """Verify user creation with required fields, UUID, and timestamps."""
        user = crud_user.create(
            db=db_session,
            email="candidate1@hire.ai",
            password_hash="hashed_pw_123",
            role="candidate",
        )
        assert isinstance(user.id, uuid.UUID)
        assert user.email == "candidate1@hire.ai"
        assert user.password_hash == "hashed_pw_123"
        assert user.role == "candidate"
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_get_user_by_id(self, db_session: Session) -> None:
        """Verify user retrieval by UUID."""
        user = crud_user.create(
            db=db_session,
            email="find_id@hire.ai",
            password_hash="hash_abc",
        )
        retrieved = crud_user.get_by_id(db=db_session, user_id=user.id)
        assert retrieved is not None
        assert retrieved.id == user.id
        assert retrieved.email == "find_id@hire.ai"

    def test_get_user_by_id_nonexistent_returns_none(self, db_session: Session) -> None:
        """Verify get_by_id returns None for non-existent UUID."""
        random_id = uuid.uuid4()
        result = crud_user.get_by_id(db=db_session, user_id=random_id)
        assert result is None

    def test_get_user_by_email(self, db_session: Session) -> None:
        """Verify user retrieval by email."""
        user = crud_user.create(
            db=db_session,
            email="find_email@hire.ai",
            password_hash="hash_xyz",
        )
        retrieved = crud_user.get_by_email(db=db_session, email="find_email@hire.ai")
        assert retrieved is not None
        assert retrieved.id == user.id
        assert retrieved.email == "find_email@hire.ai"

    def test_get_user_by_email_nonexistent_returns_none(
        self, db_session: Session
    ) -> None:
        """Verify get_by_email returns None for unknown email."""
        result = crud_user.get_by_email(db=db_session, email="unknown@hire.ai")
        assert result is None

    def test_duplicate_email_raises_conflict_exception(
        self, db_session: Session
    ) -> None:
        """Verify creating a duplicate email raises ConflictException."""
        crud_user.create(
            db=db_session,
            email="duplicate@hire.ai",
            password_hash="hash1",
        )
        with pytest.raises(ConflictException) as exc_info:
            crud_user.create(
                db=db_session,
                email="duplicate@hire.ai",
                password_hash="hash2",
            )
        assert "already exists" in str(exc_info.value.message)

    def test_default_role_is_candidate(self, db_session: Session) -> None:
        """Verify default role is 'candidate' when role is not specified."""
        user = crud_user.create(
            db=db_session,
            email="default_role@hire.ai",
            password_hash="hash_default",
        )
        assert user.role == "candidate"

    def test_custom_role_assignment(self, db_session: Session) -> None:
        """Verify custom role assignment (e.g. recruiter, admin)."""
        admin = crud_user.create(
            db=db_session,
            email="admin@hire.ai",
            password_hash="hash_admin",
            role="admin",
        )
        assert admin.role == "admin"

    def test_multiple_users_remain_isolated(self, db_session: Session) -> None:
        """Verify multiple created users remain distinct without cross-talk."""
        user1 = crud_user.create(
            db=db_session, email="user1@hire.ai", password_hash="hash1"
        )
        user2 = crud_user.create(
            db=db_session, email="user2@hire.ai", password_hash="hash2"
        )

        assert user1.id != user2.id
        assert crud_user.get_by_id(db_session, user1.id).email == "user1@hire.ai"
        assert crud_user.get_by_id(db_session, user2.id).email == "user2@hire.ai"


# =========================================================================== #
# 2. Profile CRUD Tests
# =========================================================================== #


class TestProfileCRUD:
    """Tests for Profile repository operations."""

    def test_create_profile(self, db_session: Session) -> None:
        """Verify candidate profile creation with all supplied attributes."""
        user = crud_user.create(
            db=db_session, email="profile_cand@hire.ai", password_hash="hash"
        )
        profile = crud_profile.create(
            db=db_session,
            user_id=user.id,
            first_name="Jane",
            last_name="Doe",
            phone="+1-555-0144",
            college="UC Berkeley",
            degree="B.S. Electrical Engineering & CS",
            graduation_year=2024,
            career_goal="Full-Stack AI Engineer",
        )
        assert isinstance(profile.id, uuid.UUID)
        assert profile.user_id == user.id
        assert profile.first_name == "Jane"
        assert profile.last_name == "Doe"
        assert profile.phone == "+1-555-0144"
        assert profile.college == "UC Berkeley"
        assert profile.degree == "B.S. Electrical Engineering & CS"
        assert profile.graduation_year == 2024
        assert profile.career_goal == "Full-Stack AI Engineer"

    def test_get_profile_by_user_id(self, db_session: Session) -> None:
        """Verify profile retrieval by user UUID."""
        user = crud_user.create(
            db=db_session, email="prof_get@hire.ai", password_hash="hash"
        )
        created = crud_profile.create(
            db=db_session,
            user_id=user.id,
            first_name="Alex",
            last_name="Smith",
        )
        retrieved = crud_profile.get_by_user_id(db=db_session, user_id=user.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.first_name == "Alex"

    def test_get_profile_by_user_id_nonexistent_returns_none(
        self, db_session: Session
    ) -> None:
        """Verify get_by_user_id returns None when user has no profile."""
        random_user_id = uuid.uuid4()
        result = crud_profile.get_by_user_id(db=db_session, user_id=random_user_id)
        assert result is None

    def test_update_profile(self, db_session: Session) -> None:
        """Verify updating existing profile fields."""
        user = crud_user.create(
            db=db_session, email="prof_update@hire.ai", password_hash="hash"
        )
        crud_profile.create(
            db=db_session,
            user_id=user.id,
            first_name="Initial",
            last_name="Name",
            career_goal="Junior Developer",
        )
        updated = crud_profile.update(
            db=db_session,
            user_id=user.id,
            first_name="Updated",
            career_goal="Senior Architect",
        )
        assert updated is not None
        assert updated.first_name == "Updated"
        assert updated.last_name == "Name"
        assert updated.career_goal == "Senior Architect"

    def test_partial_update_preserves_unspecified_fields(
        self, db_session: Session
    ) -> None:
        """Verify updating a single field does not overwrite other fields with None."""
        user = crud_user.create(
            db=db_session, email="partial_test@hire.ai", password_hash="hash"
        )
        crud_profile.create(
            db=db_session,
            user_id=user.id,
            first_name="Alice",
            last_name="Wonderland",
            phone="+1-555-0111",
            college="Oxford",
            degree="M.Sc.",
            graduation_year=2023,
            career_goal="ML Engineer",
        )

        # Update ONLY phone number
        updated = crud_profile.update(
            db=db_session,
            user_id=user.id,
            phone="+1-555-9999",
        )
        assert updated is not None
        assert updated.phone == "+1-555-9999"
        # Confirm all other fields were preserved intact
        assert updated.first_name == "Alice"
        assert updated.last_name == "Wonderland"
        assert updated.college == "Oxford"
        assert updated.degree == "M.Sc."
        assert updated.graduation_year == 2023
        assert updated.career_goal == "ML Engineer"

    def test_update_nonexistent_profile_returns_none(
        self, db_session: Session
    ) -> None:
        """Verify update returns None when the user has no profile."""
        random_user_id = uuid.uuid4()
        result = crud_profile.update(
            db=db_session, user_id=random_user_id, first_name="Ghost"
        )
        assert result is None

    def test_one_profile_per_user_enforced(self, db_session: Session) -> None:
        """Verify creating a second profile for the same user raises ConflictException."""
        user = crud_user.create(
            db=db_session, email="single_profile@hire.ai", password_hash="hash"
        )
        crud_profile.create(
            db=db_session, user_id=user.id, first_name="First"
        )
        with pytest.raises(ConflictException) as exc_info:
            crud_profile.create(
                db=db_session, user_id=user.id, first_name="Second"
            )
        assert "already exists" in str(exc_info.value.message)

    def test_create_or_update_profile(self, db_session: Session) -> None:
        """Verify create_or_update handles both create and update scenarios."""
        user = crud_user.create(
            db=db_session, email="upsert@hire.ai", password_hash="hash"
        )
        # First call creates
        prof1 = crud_profile.create_or_update(
            db=db_session, user_id=user.id, first_name="Initial", college="MIT"
        )
        assert prof1.first_name == "Initial"
        assert prof1.college == "MIT"

        # Second call updates
        prof2 = crud_profile.create_or_update(
            db=db_session, user_id=user.id, first_name="Changed"
        )
        assert prof2.id == prof1.id
        assert prof2.first_name == "Changed"
        assert prof2.college == "MIT"


# =========================================================================== #
# 3. Resume CRUD Tests
# =========================================================================== #


class TestResumeCRUD:
    """Tests for Resume repository operations."""

    def test_create_resume(self, db_session: Session) -> None:
        """Verify resume creation with file path and default status."""
        user = crud_user.create(
            db=db_session, email="resume_owner@hire.ai", password_hash="hash"
        )
        resume = crud_resume.create(
            db=db_session,
            user_id=user.id,
            file_name="resume_jane_doe.pdf",
            file_path="/uploads/resumes/resume_jane_doe.pdf",
        )
        assert isinstance(resume.id, uuid.UUID)
        assert resume.user_id == user.id
        assert resume.file_name == "resume_jane_doe.pdf"
        assert resume.file_path == "/uploads/resumes/resume_jane_doe.pdf"
        assert resume.parsing_status == "pending"
        assert resume.upload_date is not None

    def test_default_parsing_status_is_pending(self, db_session: Session) -> None:
        """Verify parsing_status defaults to 'pending' if not explicitly passed."""
        user = crud_user.create(
            db=db_session, email="resume_pending@hire.ai", password_hash="hash"
        )
        resume = crud_resume.create(
            db=db_session,
            user_id=user.id,
            file_name="cv.pdf",
            file_path="/path/cv.pdf",
        )
        assert resume.parsing_status == "pending"

    def test_create_resume_with_custom_status(self, db_session: Session) -> None:
        """Verify parsing_status can be initialized to a custom value."""
        user = crud_user.create(
            db=db_session, email="custom_status@hire.ai", password_hash="hash"
        )
        resume = crud_resume.create(
            db=db_session,
            user_id=user.id,
            file_name="cv.pdf",
            file_path="/path/cv.pdf",
            parsing_status="uploaded",
        )
        assert resume.parsing_status == "uploaded"

    def test_get_resume_by_id(self, db_session: Session) -> None:
        """Verify resume retrieval by UUID."""
        user = crud_user.create(
            db=db_session, email="resume_get@hire.ai", password_hash="hash"
        )
        resume = crud_resume.create(
            db=db_session,
            user_id=user.id,
            file_name="cv.pdf",
            file_path="/path/cv.pdf",
        )
        retrieved = crud_resume.get_by_id(db=db_session, resume_id=resume.id)
        assert retrieved is not None
        assert retrieved.id == resume.id
        assert retrieved.file_name == "cv.pdf"

    def test_get_resume_by_id_nonexistent_returns_none(
        self, db_session: Session
    ) -> None:
        """Verify get_by_id returns None for non-existent UUID."""
        result = crud_resume.get_by_id(db=db_session, resume_id=uuid.uuid4())
        assert result is None

    def test_list_resumes_by_user_id(self, db_session: Session) -> None:
        """Verify listing multiple resumes for a single user."""
        user = crud_user.create(
            db=db_session, email="multi_resume@hire.ai", password_hash="hash"
        )
        r1 = crud_resume.create(
            db=db_session, user_id=user.id, file_name="cv_v1.pdf", file_path="/p1"
        )
        r2 = crud_resume.create(
            db=db_session, user_id=user.id, file_name="cv_v2.pdf", file_path="/p2"
        )

        resumes = crud_resume.list_by_user_id(db=db_session, user_id=user.id)
        assert len(resumes) == 2
        file_names = {r.file_name for r in resumes}
        assert file_names == {"cv_v1.pdf", "cv_v2.pdf"}

    def test_users_cannot_see_each_others_resumes(self, db_session: Session) -> None:
        """Verify list_by_user_id isolates resumes strictly to the owner."""
        user_a = crud_user.create(
            db=db_session, email="owner_a@hire.ai", password_hash="hash"
        )
        user_b = crud_user.create(
            db=db_session, email="owner_b@hire.ai", password_hash="hash"
        )

        crud_resume.create(
            db=db_session, user_id=user_a.id, file_name="resume_a.pdf", file_path="/a"
        )
        crud_resume.create(
            db=db_session, user_id=user_b.id, file_name="resume_b.pdf", file_path="/b"
        )

        resumes_a = crud_resume.list_by_user_id(db=db_session, user_id=user_a.id)
        resumes_b = crud_resume.list_by_user_id(db=db_session, user_id=user_b.id)

        assert len(resumes_a) == 1
        assert resumes_a[0].file_name == "resume_a.pdf"
        assert len(resumes_b) == 1
        assert resumes_b[0].file_name == "resume_b.pdf"

    def test_update_resume_status(self, db_session: Session) -> None:
        """Verify updating resume status persists through database session."""
        user = crud_user.create(
            db=db_session, email="status_trans@hire.ai", password_hash="hash"
        )
        resume = crud_resume.create(
            db=db_session, user_id=user.id, file_name="cv.pdf", file_path="/path"
        )
        assert resume.parsing_status == "pending"

        updated = crud_resume.update_status(
            db=db_session, resume_id=resume.id, status="processing"
        )
        assert updated is not None
        assert updated.parsing_status == "processing"

        # Further transition to completed
        completed = crud_resume.update_status(
            db=db_session, resume_id=resume.id, status="completed"
        )
        assert completed is not None
        assert completed.parsing_status == "completed"

    def test_update_resume_status_nonexistent_returns_none(
        self, db_session: Session
    ) -> None:
        """Verify update_status returns None for nonexistent resume."""
        result = crud_resume.update_status(
            db=db_session, resume_id=uuid.uuid4(), status="failed"
        )
        assert result is None

    def test_delete_existing_resume(self, db_session: Session) -> None:
        """Verify deleting an existing resume returns True and removes it."""
        user = crud_user.create(
            db=db_session, email="del_resume@hire.ai", password_hash="hash"
        )
        resume = crud_resume.create(
            db=db_session, user_id=user.id, file_name="cv.pdf", file_path="/path"
        )
        result = crud_resume.delete(db=db_session, resume_id=resume.id)
        assert result is True

        # Verify removal
        retrieved = crud_resume.get_by_id(db=db_session, resume_id=resume.id)
        assert retrieved is None

    def test_delete_nonexistent_resume_returns_false(
        self, db_session: Session
    ) -> None:
        """Verify deleting a nonexistent resume returns False."""
        result = crud_resume.delete(db=db_session, resume_id=uuid.uuid4())
        assert result is False

    def test_delete_resume_with_mismatched_user_id_returns_false(
        self, db_session: Session
    ) -> None:
        """Verify deleting with owner user_id check prevents cross-user deletion."""
        user_a = crud_user.create(
            db=db_session, email="owner_del_a@hire.ai", password_hash="hash"
        )
        user_b = crud_user.create(
            db=db_session, email="owner_del_b@hire.ai", password_hash="hash"
        )
        resume_a = crud_resume.create(
            db=db_session, user_id=user_a.id, file_name="cv_a.pdf", file_path="/a"
        )

        # User B attempts to delete User A's resume
        deleted = crud_resume.delete(
            db=db_session, resume_id=resume_a.id, user_id=user_b.id
        )
        assert deleted is False

        # Verify resume A still exists
        assert crud_resume.get_by_id(db=db_session, resume_id=resume_a.id) is not None


# =========================================================================== #
# 4. Relationships and Cascade Behavior Tests
# =========================================================================== #


class TestCRUDRelationshipsAndCascade:
    """Tests verifying CRUD records interact properly with ORM relationships & cascades."""

    def test_crud_records_integrate_with_orm_relationships(
        self, db_session: Session
    ) -> None:
        """Verify user created via CRUD navigates to profile and resumes."""
        user = crud_user.create(
            db=db_session, email="rel_test@hire.ai", password_hash="hash"
        )
        profile = crud_profile.create(
            db=db_session, user_id=user.id, first_name="Samantha", last_name="Ray"
        )
        resume1 = crud_resume.create(
            db=db_session, user_id=user.id, file_name="cv1.pdf", file_path="/p1"
        )
        resume2 = crud_resume.create(
            db=db_session, user_id=user.id, file_name="cv2.pdf", file_path="/p2"
        )

        # Refresh user from database
        db_session.refresh(user)

        assert user.profile is not None
        assert user.profile.id == profile.id
        assert user.profile.first_name == "Samantha"
        assert len(user.resumes) == 2
        assert {r.id for r in user.resumes} == {resume1.id, resume2.id}

    def test_delete_user_cascades_to_profile_and_resumes(
        self, db_session: Session
    ) -> None:
        """Verify deleting a user cascades to remove associated profile and resumes."""
        user = crud_user.create(
            db=db_session, email="cascade_del@hire.ai", password_hash="hash"
        )
        profile = crud_profile.create(
            db=db_session, user_id=user.id, first_name="Cascade", last_name="Target"
        )
        resume = crud_resume.create(
            db=db_session, user_id=user.id, file_name="cascade_cv.pdf", file_path="/c"
        )

        profile_id = profile.id
        resume_id = resume.id

        # Delete user
        db_session.delete(user)
        db_session.commit()

        # Verify cascading deletion
        assert crud_profile.get_by_user_id(db_session, user.id) is None
        assert crud_profile.get(db_session, profile_id) is None
        assert crud_resume.get_by_id(db_session, resume_id) is None


# =========================================================================== #
# 5. Transaction Behavior Tests
# =========================================================================== #


class TestCRUDTransactions:
    """Tests verifying transaction persistence and clean rollback."""

    def test_successful_operations_persist(self, db_session: Session) -> None:
        """Verify operations are properly committed and survive subsequent reads."""
        user = crud_user.create(
            db=db_session, email="persist@hire.ai", password_hash="hash"
        )
        # Clear identity map cache to force reading fresh from SQLite
        db_session.expire_all()

        retrieved = crud_user.get_by_id(db=db_session, user_id=user.id)
        assert retrieved is not None
        assert retrieved.email == "persist@hire.ai"

    def test_failed_operation_rolls_back_cleanly(self, db_session: Session) -> None:
        """Verify a failed operation does not leave the session in a broken state."""
        crud_user.create(
            db=db_session, email="clean_rollback@hire.ai", password_hash="hash"
        )

        # Attempting duplicate triggers exception and internal rollback
        with pytest.raises(ConflictException):
            crud_user.create(
                db=db_session, email="clean_rollback@hire.ai", password_hash="hash2"
            )

        # Verify subsequent operations on the session succeed cleanly
        subsequent_user = crud_user.create(
            db=db_session, email="subsequent@hire.ai", password_hash="hash3"
        )
        assert subsequent_user.id is not None
        assert crud_user.get_by_email(db_session, "subsequent@hire.ai") is not None


# =========================================================================== #
# 6. CRUDBase Generic Tests
# =========================================================================== #


class TestCRUDBaseGeneric:
    """Tests for CRUDBase generic get and get_multi methods."""

    def test_crud_base_get_and_get_multi(self, db_session: Session) -> None:
        """Verify generic get and get_multi pagination on User repository."""
        u1 = crud_user.create(
            db=db_session, email="base1@hire.ai", password_hash="hash"
        )
        u2 = crud_user.create(
            db=db_session, email="base2@hire.ai", password_hash="hash"
        )
        u3 = crud_user.create(
            db=db_session, email="base3@hire.ai", password_hash="hash"
        )

        # Test generic get
        fetched = crud_user.get(db_session, u1.id)
        assert fetched is not None
        assert fetched.id == u1.id

        # Test get_multi with skip and limit
        page = crud_user.get_multi(db_session, skip=0, limit=2)
        assert len(page) == 2

        all_records = crud_user.get_multi(db_session, skip=0, limit=100)
        user_ids = {u.id for u in all_records}
        assert {u1.id, u2.id, u3.id}.issubset(user_ids)
