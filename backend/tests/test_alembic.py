"""Unit tests for Alembic migration configuration and the initial migration.

Tests verify:
- Alembic configuration file (alembic.ini) loads correctly
- Target metadata connects to H.I.R.E. Base.metadata with expected models
- Initial migration file exists and is registered as head revision
- Migration targets strictly the three implemented tables: user, profile, resume
- Unimplemented models (skill, career_report, etc.) are NOT in the migration
- Upgrade to head and downgrade to base succeed cleanly against an isolated SQLite test database
- Offline SQL generation succeeds without requiring an external PostgreSQL server
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, inspect
from sqlalchemy.pool import StaticPool

from app.database.base import Base


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
# 1. Configuration & Metadata Tests
# --------------------------------------------------------------------------- #


class TestAlembicConfiguration:
    """Verify Alembic setup, directory structure, and metadata discovery."""

    def test_alembic_config_loads_successfully(self, alembic_config: Config) -> None:
        """Verify alembic.ini loads and configures the script directory."""
        script_dir = ScriptDirectory.from_config(alembic_config)
        assert script_dir is not None
        assert script_dir.dir.endswith("alembic")

    def test_alembic_locates_base_metadata(self) -> None:
        """Verify Base.metadata has the three active models registered."""
        table_names = set(Base.metadata.tables.keys())
        assert "user" in table_names
        assert "profile" in table_names
        assert "resume" in table_names

    def test_initial_migration_exists_and_is_registered(self, alembic_config: Config) -> None:
        """Verify the initial migration revision exists with revision 729e24449128."""
        script_dir = ScriptDirectory.from_config(alembic_config)
        init_rev = script_dir.get_revision("729e24449128")
        assert init_rev is not None
        assert init_rev.revision == "729e24449128"
        assert init_rev.down_revision is None
        assert "create_user_profile_resume_tables" in init_rev.doc


# --------------------------------------------------------------------------- #
# 2. Migration Scope & Content Restrictions
# --------------------------------------------------------------------------- #


class TestMigrationScope:
    """Verify that only the approved three models are included in the initial migration."""

    def test_migration_contains_expected_tables(self, alembic_config: Config) -> None:
        """Inspect the initial migration file to confirm user, profile, and resume are created."""
        script_dir = ScriptDirectory.from_config(alembic_config)
        init_rev = script_dir.get_revision("729e24449128")
        assert init_rev is not None

        migration_file_path = init_rev.path
        content = Path(migration_file_path).read_text(encoding="utf-8")

        assert 'op.create_table(\n        "user",' in content or 'op.create_table(\n        \'user\',' in content or '"user"' in content
        assert '"profile"' in content
        assert '"resume"' in content

    def test_migration_excludes_unimplemented_tables(self, alembic_config: Config) -> None:
        """Ensure future models not yet implemented are NOT in the initial migration."""
        script_dir = ScriptDirectory.from_config(alembic_config)
        init_rev = script_dir.get_revision("729e24449128")
        assert init_rev is not None

        migration_file_path = init_rev.path
        content = Path(migration_file_path).read_text(encoding="utf-8")

        unimplemented_tables = [
            "skill",
            "career_report",
            "recommendation",
            "interview_session",
            "interview_question",
            "interview_response",
        ]
        for table in unimplemented_tables:
            assert f'create_table("{table}"' not in content
            assert f"create_table('{table}'" not in content


# --------------------------------------------------------------------------- #
# 3. Upgrade & Downgrade Execution Tests (SQLite Isolation)
# --------------------------------------------------------------------------- #


class TestMigrationExecution:
    """Verify applying upgrade to head and downgrade to base in an isolated database."""

    def test_upgrade_creates_expected_tables_and_indexes(
        self, alembic_config: Config, migration_engine: Engine
    ) -> None:
        """Verify upgrading to head creates user, profile, resume, and version tracking."""
        with migration_engine.begin() as connection:
            alembic_config.attributes["connection"] = connection
            command.upgrade(alembic_config, "head")

        inspector = inspect(migration_engine)
        tables = set(inspector.get_table_names())

        # Expected tables
        assert "alembic_version" in tables
        assert "user" in tables
        assert "profile" in tables
        assert "resume" in tables

        # Inspect 'user' columns
        user_cols = {col["name"] for col in inspector.get_columns("user")}
        assert {"id", "email", "password_hash", "role", "created_at", "updated_at"}.issubset(user_cols)

        # Inspect 'profile' columns & foreign keys
        profile_cols = {col["name"] for col in inspector.get_columns("profile")}
        assert {"id", "user_id", "first_name", "last_name", "college", "degree"}.issubset(profile_cols)
        profile_fks = inspector.get_foreign_keys("profile")
        assert len(profile_fks) == 1
        assert profile_fks[0]["referred_table"] == "user"

        # Inspect 'resume' columns & foreign keys
        resume_cols = {col["name"] for col in inspector.get_columns("resume")}
        assert {"id", "user_id", "file_name", "file_path", "upload_date", "parsing_status"}.issubset(resume_cols)
        resume_fks = inspector.get_foreign_keys("resume")
        assert len(resume_fks) == 1
        assert resume_fks[0]["referred_table"] == "user"

    def test_downgrade_drops_all_tables_in_reverse_order(
        self, alembic_config: Config, migration_engine: Engine
    ) -> None:
        """Verify downgrading to base safely removes user, profile, and resume tables."""
        # 1. Upgrade first
        with migration_engine.begin() as connection:
            alembic_config.attributes["connection"] = connection
            command.upgrade(alembic_config, "head")

        inspector_pre = inspect(migration_engine)
        assert "user" in inspector_pre.get_table_names()

        # 2. Downgrade to base
        with migration_engine.begin() as connection:
            alembic_config.attributes["connection"] = connection
            command.downgrade(alembic_config, "base")

        # 3. Verify all models dropped, only alembic_version remains
        inspector_post = inspect(migration_engine)
        post_tables = set(inspector_post.get_table_names())

        assert "user" not in post_tables
        assert "profile" not in post_tables
        assert "resume" not in post_tables


# --------------------------------------------------------------------------- #
# 4. Offline SQL Generation (No PostgreSQL Server Dependency)
# --------------------------------------------------------------------------- #


class TestOfflineMigration:
    """Verify Alembic can generate PostgreSQL DDL statically without a running server."""

    def test_offline_sql_generation_without_server(self, alembic_config: Config) -> None:
        """Verify offline SQL generation produces expected PostgreSQL DDL."""
        # Run upgrade in SQL (offline) mode and capture output
        import io
        from contextlib import redirect_stdout

        output_buffer = io.StringIO()
        with redirect_stdout(output_buffer):
            command.upgrade(alembic_config, "base:head", sql=True)

        generated_sql = output_buffer.getvalue()

        assert "CREATE TABLE" in generated_sql
        assert "user" in generated_sql
        assert "profile" in generated_sql
        assert "resume" in generated_sql
        assert "729e24449128" in generated_sql
