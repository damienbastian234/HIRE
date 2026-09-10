"""Unit tests for the H.I.R.E. database core infrastructure and session management.

Tests cover:
- Engine and session configuration (app/database/session.py)
- Base declarative class and model subclassing (app/database/base.py)
- SessionLocal creation and get_db() lifecycle & cleanup
- Transaction commit and rollback
- SQLite in-memory test isolation (no external PostgreSQL server required)
"""

from __future__ import annotations

from typing import Optional
from unittest.mock import patch

import pytest
from sqlalchemy import Engine, Integer, String, create_engine, select
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, SessionLocal, create_db_engine, get_db
from app.database.session import get_engine_args


# --------------------------------------------------------------------------- #
# Test-Only ORM Model (SampleItem)
# --------------------------------------------------------------------------- #


class SampleItem(Base):
    """Test-only model to verify Base subclassing, table creation, and transactions."""

    __tablename__ = "sample_items"
    __test__ = False  # Prevent pytest from treating this model as a test class

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)


# --------------------------------------------------------------------------- #
# 1. Engine & Session Setup Tests
# --------------------------------------------------------------------------- #


class TestEngineAndSessionSetup:
    """Tests for database engine creation, URL handling, and connection arguments."""

    def test_get_engine_args_sqlite(self) -> None:
        """Verify SQLite URLs receive check_same_thread=False and pool_pre_ping."""
        args = get_engine_args("sqlite:///:memory:")
        assert args["pool_pre_ping"] is True
        assert args["connect_args"]["check_same_thread"] is False

    def test_get_engine_args_postgresql(self) -> None:
        """Verify PostgreSQL URLs receive pool_pre_ping without SQLite connect_args."""
        args = get_engine_args("postgresql://user:pass@localhost:5432/hire_db")
        assert args["pool_pre_ping"] is True
        assert "connect_args" not in args

    def test_create_db_engine_with_sqlite_url(self) -> None:
        """Verify create_db_engine builds an Engine instance for SQLite."""
        test_engine = create_db_engine("sqlite:///:memory:")
        assert isinstance(test_engine, Engine)
        test_engine.dispose()

    def test_create_db_engine_missing_url_raises(self) -> None:
        """Verify create_db_engine raises ValueError when no URL is provided and DATABASE_URL is unset."""
        with patch("app.database.session.settings.DATABASE_URL", None):
            with pytest.raises(ValueError) as exc_info:
                create_db_engine(None)
            assert "DATABASE_URL is not set" in str(exc_info.value)

    def test_sessionlocal_creation_with_engine(self, db_engine: Engine) -> None:
        """Verify SessionLocal factory creates valid Session instances when bound."""
        factory = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
        session = factory()
        assert isinstance(session, Session)
        session.close()


# --------------------------------------------------------------------------- #
# 2. get_db() Lifecycle & Session Cleanup Tests
# --------------------------------------------------------------------------- #


class TestGetDbLifecycle:
    """Tests for the get_db() FastAPI generator dependency and cleanup behavior."""

    def test_get_db_yields_session_and_closes(
        self, bound_session_local: sessionmaker[Session]
    ) -> None:
        """Verify get_db yields an active Session and closes it upon generator completion."""
        gen = get_db()
        session = next(gen)

        assert isinstance(session, Session)

        with patch.object(session, "close", wraps=session.close) as mock_close:
            # Advance generator to trigger the finally block
            with pytest.raises(StopIteration):
                next(gen)
            mock_close.assert_called_once()

    def test_get_db_unbound_raises_runtime_error(self) -> None:
        """Verify get_db raises RuntimeError when SessionLocal is not bound and engine is None."""
        unbound_factory = sessionmaker(autocommit=False, autoflush=False)
        with patch("app.database.session.SessionLocal", unbound_factory):
            with patch("app.database.session.engine", None):
                gen = get_db()
                with pytest.raises(RuntimeError) as exc_info:
                    next(gen)
                assert "Database session is not bound" in str(exc_info.value)


# --------------------------------------------------------------------------- #
# 3. Base Subclassing & Transaction Tests
# --------------------------------------------------------------------------- #


class TestBaseAndTransactions:
    """Tests for DeclarativeBase subclassing, table creation, commit, and rollback."""

    def test_base_can_be_subclassed_by_test_model(self) -> None:
        """Verify SampleItem successfully inherits from Base and registers table metadata."""
        assert issubclass(SampleItem, Base)
        assert SampleItem.__tablename__ == "sample_items"
        assert "sample_items" in Base.metadata.tables

    def test_transaction_commit(self, db_engine: Engine) -> None:
        """Verify basic transaction commit persists data across separate sessions."""
        # Session 1: Insert and commit
        session_factory = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
        session1 = session_factory()
        item = SampleItem(name="Committed Item", description="Will persist")
        session1.add(item)
        session1.commit()
        session1.close()

        # Session 2: Query committed data
        session2 = session_factory()
        stmt = select(SampleItem).where(SampleItem.name == "Committed Item")
        retrieved = session2.scalars(stmt).first()
        assert retrieved is not None
        assert retrieved.name == "Committed Item"
        assert retrieved.description == "Will persist"
        session2.close()

    def test_transaction_rollback(self, db_engine: Engine) -> None:
        """Verify basic transaction rollback discards uncommitted data."""
        session_factory = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
        session = session_factory()
        item = SampleItem(name="Rollback Item", description="Should not persist")
        session.add(item)
        session.flush()

        # Item is flushed in-transaction
        assert (
            session.scalars(
                select(SampleItem).where(SampleItem.name == "Rollback Item")
            ).first()
            is not None
        )

        # Rollback
        session.rollback()

        # Item is no longer in session
        retrieved = session.scalars(
            select(SampleItem).where(SampleItem.name == "Rollback Item")
        ).first()
        assert retrieved is None
        session.close()


# --------------------------------------------------------------------------- #
# 4. SQLite In-Memory Isolation Tests (Hermetic Testing)
# --------------------------------------------------------------------------- #


class TestDatabaseIsolation:
    """Tests verifying SQLite in-memory database isolation between test cases."""

    def test_sqlite_isolation_step_1(self, db_engine: Engine) -> None:
        """Insert a record; verify it exists within this test's isolated engine."""
        session = Session(bind=db_engine)
        session.add(SampleItem(name="Isolated Item 1"))
        session.commit()

        count = len(session.scalars(select(SampleItem)).all())
        assert count == 1
        session.close()

    def test_sqlite_isolation_step_2(self, db_engine: Engine) -> None:
        """Verify the database is completely empty, proving fresh engine isolation per test."""
        session = Session(bind=db_engine)
        count = len(session.scalars(select(SampleItem)).all())
        assert count == 0
        session.close()

    def test_no_dependency_on_external_postgresql(self) -> None:
        """Verify the entire ORM flow executes successfully with zero network/PostgreSQL dependency."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)

        with Session(bind=engine) as session:
            session.add(SampleItem(name="Offline Item", description="No Postgres needed"))
            session.commit()
            item = session.scalars(select(SampleItem)).first()
            assert item is not None
            assert item.name == "Offline Item"

        Base.metadata.drop_all(bind=engine)
        engine.dispose()
