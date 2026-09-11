"""Unit tests for the Skill table Alembic migration (767028913f6e).

Tests verify:
- Migration revision ID and down_revision linkage (729e24449128 -> 767028913f6e)
- Incremental upgrade after initial migration
- Accurate column definitions (id, resume_id, skill_name, skill_category, confidence_score)
- Primary key on id
- Required (NOT NULL) and optional (nullable) constraints
- Foreign key referencing resume.id with ON DELETE CASCADE
- Single-column index on resume_id
- Absence of unintended uniqueness constraints (e.g. allowing duplicate skills per resume)
- Downgrade removes skill table cleanly while preserving earlier tables
- Offline PostgreSQL SQL generation succeeds without live database server
"""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from pathlib import Path
from typing import Generator

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, inspect
from sqlalchemy.pool import StaticPool


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def alembic_config() -> Config:
    """Load the project's alembic.ini configuration."""
    backend_dir = Path(__file__).resolve().parent.parent
    ini_path = backend_dir / "alembic.ini"
    assert ini_path.exists(), f"alembic.ini not found at {ini_path}"

    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    return cfg


@pytest.fixture
def migration_engine() -> Generator[Engine, None, None]:
    """Create a dedicated, isolated in-memory SQLite engine for migration testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine
    engine.dispose()


# --------------------------------------------------------------------------- #
# 1. Metadata and Revision Linkage Tests
# --------------------------------------------------------------------------- #


class TestSkillMigrationMetadata:
    """Verify revision chain, metadata, and down_revision linkage."""

    def test_skill_migration_revision_metadata(self, alembic_config: Config) -> None:
        """Verify the skill migration revision ID and down_revision."""
        script_dir = ScriptDirectory.from_config(alembic_config)
        skill_rev = script_dir.get_revision("767028913f6e")

        assert skill_rev is not None
        assert skill_rev.revision == "767028913f6e"
        assert skill_rev.down_revision == "729e24449128"
        assert "create_skill_table" in skill_rev.doc

    def test_migration_chain_ordering(self, alembic_config: Config) -> None:
        """Verify the linear chain: base -> initial migration -> skill migration (head)."""
        script_dir = ScriptDirectory.from_config(alembic_config)
        heads = script_dir.get_heads()

        assert len(heads) == 1
        head_rev = script_dir.get_revision(heads[0])
        assert head_rev is not None
        assert head_rev.revision == "767028913f6e"

        # Parent revision is the initial migration
        initial_rev = script_dir.get_revision(head_rev.down_revision)
        assert initial_rev is not None
        assert initial_rev.revision == "729e24449128"
        assert initial_rev.down_revision is None

    def test_offline_sql_generation_for_skill_migration(
        self, alembic_config: Config
    ) -> None:
        """Verify offline SQL generation for the skill migration produces valid PostgreSQL DDL."""
        output_buffer = io.StringIO()
        with redirect_stdout(output_buffer):
            command.upgrade(alembic_config, "729e24449128:head", sql=True)

        generated_sql = output_buffer.getvalue()

        assert "CREATE TABLE skill" in generated_sql
        assert "resume_id" in generated_sql
        assert "skill_name" in generated_sql
        assert "REFERENCES resume (id)" in generated_sql
        assert "ON DELETE CASCADE" in generated_sql
        assert "CREATE INDEX" in generated_sql
        assert "ix_skill_resume_id" in generated_sql
        assert "767028913f6e" in generated_sql


# --------------------------------------------------------------------------- #
# 2. Execution, Schema Inspection, and Constraint Tests
# --------------------------------------------------------------------------- #


class TestSkillMigrationExecution:
    """Verify execution of upgrade and downgrade against an isolated SQLite test database."""

    def test_incremental_upgrade_after_initial_migration(
        self, alembic_config: Config, migration_engine: Engine
    ) -> None:
        """Verify upgrading step-by-step: initial migration first, then skill migration."""
        # 1. Upgrade to initial migration only
        with migration_engine.begin() as connection:
            alembic_config.attributes["connection"] = connection
            command.upgrade(alembic_config, "729e24449128")

        inspector = inspect(migration_engine)
        initial_tables = set(inspector.get_table_names())
        assert {"user", "profile", "resume"}.issubset(initial_tables)
        assert "skill" not in initial_tables

        # 2. Upgrade to head (applies skill migration)
        with migration_engine.begin() as connection:
            alembic_config.attributes["connection"] = connection
            command.upgrade(alembic_config, "head")

        inspector_head = inspect(migration_engine)
        head_tables = set(inspector_head.get_table_names())
        assert "skill" in head_tables

    def test_skill_table_columns_and_nullability(
        self, alembic_config: Config, migration_engine: Engine
    ) -> None:
        """Verify skill columns, nullability constraints, and types match specification."""
        with migration_engine.begin() as connection:
            alembic_config.attributes["connection"] = connection
            command.upgrade(alembic_config, "head")

        inspector = inspect(migration_engine)
        columns = {col["name"]: col for col in inspector.get_columns("skill")}

        # Expected columns
        assert {"id", "resume_id", "skill_name", "skill_category", "confidence_score"}.issubset(
            set(columns.keys())
        )

        # Nullability enforcement
        assert columns["id"]["nullable"] is False
        assert columns["resume_id"]["nullable"] is False
        assert columns["skill_name"]["nullable"] is False
        assert columns["skill_category"]["nullable"] is True
        assert columns["confidence_score"]["nullable"] is True

    def test_skill_primary_key(
        self, alembic_config: Config, migration_engine: Engine
    ) -> None:
        """Verify primary key constraint on skill.id."""
        with migration_engine.begin() as connection:
            alembic_config.attributes["connection"] = connection
            command.upgrade(alembic_config, "head")

        inspector = inspect(migration_engine)
        pk_constraint = inspector.get_pk_constraint("skill")
        assert pk_constraint["constrained_columns"] == ["id"]

    def test_skill_foreign_key_and_cascade(
        self, alembic_config: Config, migration_engine: Engine
    ) -> None:
        """Verify resume_id references resume.id with ON DELETE CASCADE."""
        with migration_engine.begin() as connection:
            alembic_config.attributes["connection"] = connection
            command.upgrade(alembic_config, "head")

        inspector = inspect(migration_engine)
        fks = inspector.get_foreign_keys("skill")
        assert len(fks) == 1
        fk = fks[0]
        assert fk["referred_table"] == "resume"
        assert fk["referred_columns"] == ["id"]
        assert fk["constrained_columns"] == ["resume_id"]
        assert fk["options"].get("ondelete", "").upper() == "CASCADE"

    def test_skill_resume_id_index_exists(
        self, alembic_config: Config, migration_engine: Engine
    ) -> None:
        """Verify documented single-column index on skill.resume_id exists."""
        with migration_engine.begin() as connection:
            alembic_config.attributes["connection"] = connection
            command.upgrade(alembic_config, "head")

        inspector = inspect(migration_engine)
        indexes = inspector.get_indexes("skill")
        resume_id_indexes = [
            idx for idx in indexes if idx["column_names"] == ["resume_id"]
        ]
        assert bool(resume_id_indexes[0]["unique"]) is False

    def test_no_unintended_unique_constraint(
        self, alembic_config: Config, migration_engine: Engine
    ) -> None:
        """Verify no unique constraint is enforced on (resume_id, skill_name)."""
        with migration_engine.begin() as connection:
            alembic_config.attributes["connection"] = connection
            command.upgrade(alembic_config, "head")

        inspector = inspect(migration_engine)
        unique_constraints = inspector.get_unique_constraints("skill")

        # Confirm neither skill_name nor (resume_id, skill_name) has a unique constraint
        for uq in unique_constraints:
            cols = set(uq.get("column_names", []))
            assert cols != {"skill_name"}
            assert cols != {"resume_id", "skill_name"}

    def test_downgrade_removes_skill_table_preserving_initial_tables(
        self, alembic_config: Config, migration_engine: Engine
    ) -> None:
        """Verify downgrading to 729e24449128 removes skill while preserving user/profile/resume."""
        # 1. Upgrade to head
        with migration_engine.begin() as connection:
            alembic_config.attributes["connection"] = connection
            command.upgrade(alembic_config, "head")

        inspector = inspect(migration_engine)
        assert "skill" in inspector.get_table_names()

        # 2. Downgrade to initial migration
        with migration_engine.begin() as connection:
            alembic_config.attributes["connection"] = connection
            command.downgrade(alembic_config, "729e24449128")

        inspector_downgraded = inspect(migration_engine)
        tables = set(inspector_downgraded.get_table_names())

        assert "skill" not in tables
        assert "user" in tables
        assert "profile" in tables
        assert "resume" in tables
