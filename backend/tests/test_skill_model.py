"""Unit tests for the Skill ORM model.

Tests verify:
- Table registration in Base.metadata with expected schema
- Skill model creation with required and optional fields
- Numeric/Decimal confidence score handling
- Foreign-key constraint enforcement linking Skill to Resume
- Bidirectional ORM relationship integration (Skill.resume and Resume.skills)
- Multi-skill association with a single resume
- Isolation of skills between different resumes
- Cascading delete behavior: deleting a Resume deletes its associated Skills
- Deep cascade: deleting a User cascades through Resume to remove Skills
- String representation (__repr__) formatting
"""

from __future__ import annotations

from decimal import Decimal
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.base import Base
from app.models import Profile, Resume, Skill, User


# =========================================================================== #
# 1. Metadata and Table Registration Tests
# =========================================================================== #


class TestSkillMetadata:
    """Verify table and columns match the H.I.R.E. database design specification."""

    def test_skill_table_registered_in_base_metadata(self) -> None:
        """Verify the 'skill' table is registered in Base.metadata."""
        registered_tables = set(Base.metadata.tables.keys())
        assert "skill" in registered_tables

    def test_skill_table_columns_match_spec(self) -> None:
        """Verify columns on the skill table match docs/04_DATABASE_DESIGN.md."""
        columns = Base.metadata.tables["skill"].columns.keys()
        expected = {
            "id",
            "resume_id",
            "skill_name",
            "skill_category",
            "confidence_score",
        }
        assert expected.issubset(set(columns))

    def test_resume_id_column_is_indexed(self) -> None:
        """Verify resume_id has an index according to the indexing strategy."""
        skill_table = Base.metadata.tables["skill"]
        indexed_columns = set()
        for idx in skill_table.indexes:
            for col in idx.columns:
                indexed_columns.add(col.name)

        assert "resume_id" in indexed_columns

    def test_resume_id_foreign_key_definition(self) -> None:
        """Verify foreign key references resume.id with CASCADE deletion."""
        skill_table = Base.metadata.tables["skill"]
        fks = list(skill_table.foreign_keys)
        assert len(fks) == 1
        fk = fks[0]
        assert fk.column.table.name == "resume"
        assert fk.column.name == "id"
        assert fk.ondelete == "CASCADE"


# =========================================================================== #
# 2. Skill Model Creation & Field Validation Tests
# =========================================================================== #


class TestSkillModelCreation:
    """Tests for Skill instantiation, persistence, and field constraints."""

    def test_create_skill_with_required_fields_only(self, db_session: Session) -> None:
        """Verify creating a skill with minimal required fields generates UUID and defaults."""
        user = User(email="skill_min@hire.ai", password_hash="hash")
        db_session.add(user)
        db_session.commit()

        resume = Resume(
            user_id=user.id,
            file_name="resume.pdf",
            file_path="/uploads/resume.pdf",
        )
        db_session.add(resume)
        db_session.commit()

        skill = Skill(
            resume_id=resume.id,
            skill_name="Python",
        )
        db_session.add(skill)
        db_session.commit()
        db_session.refresh(skill)

        assert isinstance(skill.id, uuid.UUID)
        assert skill.resume_id == resume.id
        assert skill.skill_name == "Python"
        assert skill.skill_category is None
        assert skill.confidence_score is None

    def test_create_skill_with_all_fields(self, db_session: Session) -> None:
        """Verify creating a skill with all fields populated."""
        user = User(email="skill_full@hire.ai", password_hash="hash")
        db_session.add(user)
        db_session.commit()

        resume = Resume(
            user_id=user.id,
            file_name="resume.pdf",
            file_path="/uploads/resume.pdf",
        )
        db_session.add(resume)
        db_session.commit()

        skill = Skill(
            resume_id=resume.id,
            skill_name="FastAPI",
            skill_category="Backend Framework",
            confidence_score=Decimal("0.95"),
        )
        db_session.add(skill)
        db_session.commit()
        db_session.refresh(skill)

        assert skill.skill_name == "FastAPI"
        assert skill.skill_category == "Backend Framework"
        assert skill.confidence_score == Decimal("0.95")

    def test_confidence_score_decimal_and_float_handling(
        self, db_session: Session
    ) -> None:
        """Verify confidence_score accurately persists decimal and float inputs."""
        user = User(email="score_test@hire.ai", password_hash="hash")
        db_session.add(user)
        db_session.commit()

        resume = Resume(
            user_id=user.id,
            file_name="resume.pdf",
            file_path="/uploads/resume.pdf",
        )
        db_session.add(resume)
        db_session.commit()

        # Decimal input
        s1 = Skill(
            resume_id=resume.id,
            skill_name="PostgreSQL",
            confidence_score=Decimal("0.925"),
        )
        # Float input
        s2 = Skill(
            resume_id=resume.id,
            skill_name="Docker",
            confidence_score=0.88,
        )
        db_session.add_all([s1, s2])
        db_session.commit()

        db_session.refresh(s1)
        db_session.refresh(s2)

        assert float(s1.confidence_score) == pytest.approx(0.925)
        assert float(s2.confidence_score) == pytest.approx(0.88)

    def test_skill_required_fields_enforced(self, db_session: Session) -> None:
        """Verify nullable=False constraint on skill_name is enforced."""
        user = User(email="null_skill@hire.ai", password_hash="hash")
        db_session.add(user)
        db_session.commit()

        resume = Resume(
            user_id=user.id,
            file_name="resume.pdf",
            file_path="/uploads/resume.pdf",
        )
        db_session.add(resume)
        db_session.commit()

        invalid_skill = Skill(
            resume_id=resume.id,
            skill_name=None,  # type: ignore[arg-type]
        )
        db_session.add(invalid_skill)
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

    def test_foreign_key_to_resume_enforced(self, db_session: Session) -> None:
        """Verify foreign key constraint on resume_id rejects non-existent resume."""
        invalid_skill = Skill(
            resume_id=uuid.uuid4(),
            skill_name="Orphan Skill",
        )
        db_session.add(invalid_skill)
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

    def test_skill_repr(self) -> None:
        """Verify __repr__ formats skill identity cleanly."""
        dummy_id = uuid.uuid4()
        dummy_resume_id = uuid.uuid4()
        skill = Skill(
            id=dummy_id,
            resume_id=dummy_resume_id,
            skill_name="PyTorch",
            skill_category="Machine Learning",
        )
        representation = repr(skill)
        assert "PyTorch" in representation
        assert "Machine Learning" in representation
        assert str(dummy_id) in representation


# =========================================================================== #
# 3. Relationships and Uniqueness Tests
# =========================================================================== #


class TestSkillRelationships:
    """Tests for ORM relationships between Skill and Resume."""

    def test_skill_to_resume_relationship_navigation(
        self, db_session: Session
    ) -> None:
        """Verify skill.resume accesses parent Resume object."""
        user = User(email="nav_test@hire.ai", password_hash="hash")
        db_session.add(user)
        db_session.commit()

        resume = Resume(
            user_id=user.id,
            file_name="cv.pdf",
            file_path="/uploads/cv.pdf",
        )
        db_session.add(resume)
        db_session.commit()

        skill = Skill(
            resume_id=resume.id,
            skill_name="TypeScript",
            skill_category="Language",
        )
        db_session.add(skill)
        db_session.commit()
        db_session.refresh(skill)

        assert skill.resume is not None
        assert skill.resume.id == resume.id
        assert skill.resume.file_name == "cv.pdf"

    def test_resume_to_skills_bidirectional_relationship(
        self, db_session: Session
    ) -> None:
        """Verify resume.skills collection contains all associated skills."""
        user = User(email="bidi_test@hire.ai", password_hash="hash")
        db_session.add(user)
        db_session.commit()

        resume = Resume(
            user_id=user.id,
            file_name="cv.pdf",
            file_path="/uploads/cv.pdf",
        )
        db_session.add(resume)
        db_session.commit()

        s1 = Skill(resume_id=resume.id, skill_name="SQL")
        s2 = Skill(resume_id=resume.id, skill_name="Git")
        db_session.add_all([s1, s2])
        db_session.commit()
        db_session.refresh(resume)

        assert len(resume.skills) == 2
        skill_names = {s.skill_name for s in resume.skills}
        assert skill_names == {"SQL", "Git"}

    def test_skills_isolated_between_different_resumes(
        self, db_session: Session
    ) -> None:
        """Verify skills associated with Resume A do not leak into Resume B."""
        user = User(email="multi_cv@hire.ai", password_hash="hash")
        db_session.add(user)
        db_session.commit()

        resume1 = Resume(user_id=user.id, file_name="cv1.pdf", file_path="/p1")
        resume2 = Resume(user_id=user.id, file_name="cv2.pdf", file_path="/p2")
        db_session.add_all([resume1, resume2])
        db_session.commit()

        s1 = Skill(resume_id=resume1.id, skill_name="Rust")
        s2 = Skill(resume_id=resume2.id, skill_name="Go")
        db_session.add_all([s1, s2])
        db_session.commit()

        db_session.refresh(resume1)
        db_session.refresh(resume2)

        assert len(resume1.skills) == 1
        assert resume1.skills[0].skill_name == "Rust"
        assert len(resume2.skills) == 1
        assert resume2.skills[0].skill_name == "Go"

    def test_multiple_skills_with_same_name_allowed_unless_restricted(
        self, db_session: Session
    ) -> None:
        """Verify docs/04_DATABASE_DESIGN.md does not enforce artificial uniqueness on skill_name."""
        user = User(email="dup_skill@hire.ai", password_hash="hash")
        db_session.add(user)
        db_session.commit()

        resume = Resume(user_id=user.id, file_name="cv.pdf", file_path="/p")
        db_session.add(resume)
        db_session.commit()

        # In case extraction produces identical names with different contexts/confidence
        s1 = Skill(resume_id=resume.id, skill_name="Python", confidence_score=Decimal("0.90"))
        s2 = Skill(resume_id=resume.id, skill_name="Python", confidence_score=Decimal("0.75"))
        db_session.add_all([s1, s2])
        db_session.commit()

        assert s1.id != s2.id
        db_session.refresh(resume)
        assert len(resume.skills) == 2


# =========================================================================== #
# 4. Cascade Behavior Tests
# =========================================================================== #


class TestSkillCascadeBehavior:
    """Verify cascading deletes remove skills when parent records are deleted."""

    def test_delete_resume_cascades_to_skills(self, db_session: Session) -> None:
        """Verify deleting a resume deletes all its associated skills."""
        user = User(email="casc_res@hire.ai", password_hash="hash")
        db_session.add(user)
        db_session.commit()

        resume = Resume(user_id=user.id, file_name="cv.pdf", file_path="/p")
        db_session.add(resume)
        db_session.commit()

        skill1 = Skill(resume_id=resume.id, skill_name="Kubernetes")
        skill2 = Skill(resume_id=resume.id, skill_name="Terraform")
        db_session.add_all([skill1, skill2])
        db_session.commit()

        s1_id = skill1.id
        s2_id = skill2.id

        # Delete resume
        db_session.delete(resume)
        db_session.commit()

        # Query skills directly to ensure they were removed
        stmt1 = select(Skill).where(Skill.id == s1_id)
        stmt2 = select(Skill).where(Skill.id == s2_id)
        assert db_session.scalars(stmt1).first() is None
        assert db_session.scalars(stmt2).first() is None

    def test_delete_user_cascades_through_resume_to_skills(
        self, db_session: Session
    ) -> None:
        """Verify deleting a user cascades through resume to remove skills."""
        user = User(email="casc_user@hire.ai", password_hash="hash")
        db_session.add(user)
        db_session.commit()

        resume = Resume(user_id=user.id, file_name="cv.pdf", file_path="/p")
        db_session.add(resume)
        db_session.commit()

        skill = Skill(resume_id=resume.id, skill_name="GraphQL")
        db_session.add(skill)
        db_session.commit()

        skill_id = skill.id
        resume_id = resume.id

        # Delete user
        db_session.delete(user)
        db_session.commit()

        # Verify resume and skill are both deleted
        assert db_session.scalars(select(Resume).where(Resume.id == resume_id)).first() is None
        assert db_session.scalars(select(Skill).where(Skill.id == skill_id)).first() is None
