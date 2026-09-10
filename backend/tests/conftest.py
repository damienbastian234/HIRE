"""Pytest configuration and shared fixtures for the H.I.R.E. test suite.

This module ensures that necessary test environment variables (such as
SECRET_KEY) are configured before any application modules are imported,
preventing validation errors during test discovery and execution.
It also provides isolated in-memory database fixtures for testing the
database layer without an external PostgreSQL dependency.
"""

from __future__ import annotations

import os

# Configure environment variables required by app.core.config.Settings
# before any module importing settings is loaded.
os.environ.setdefault(
    "SECRET_KEY", "hire_test_secret_key_minimum_32_characters_long_123456"
)

from collections.abc import Generator
from typing import Any, Dict
import pytest

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # Ensure all ORM models are registered with Base.metadata
from app.ai.base_engine import BaseEngine
from app.ai.context import AIContext
from app.ai.exceptions import ContextValidationException
from app.ai.orchestrator import AIOrchestrator
from app.ai.registry import EngineRegistry
from app.ai.result import ExecutionStatus, IntelligenceResult
from app.database.base import Base
from app.database.session import SessionLocal


# --------------------------------------------------------------------------- #
# Concrete Test Engines for Testing BaseEngine and AIOrchestrator
# --------------------------------------------------------------------------- #


class SuccessEchoEngine(BaseEngine):
    """Simple concrete engine that echoes a greeting and adds a key to context.data."""

    def __init__(self, name: str = "echo_engine") -> None:
        super().__init__(name)

    async def execute(self, context: AIContext) -> IntelligenceResult:
        message = context.data.get("input_message", "hello")
        context.data["echo_result"] = f"echo: {message}"

        return IntelligenceResult(
            engine_name=self.name,
            status=ExecutionStatus.SUCCESS,
            confidence=1.0,
            output={"echo": f"echo: {message}"},
        )


class StepTwoEngine(BaseEngine):
    """Engine that depends on output from an earlier engine in context.data."""

    def __init__(self, name: str = "step_two_engine") -> None:
        super().__init__(name)

    async def execute(self, context: AIContext) -> IntelligenceResult:
        prior = context.data.get("echo_result", "none")
        context.data["step_two_completed"] = True

        return IntelligenceResult(
            engine_name=self.name,
            status=ExecutionStatus.SUCCESS,
            confidence=0.95,
            output={"derived_from": prior},
        )


class ValidatingEngine(BaseEngine):
    """Engine that requires specific keys in context.data."""

    def __init__(self, name: str = "validating_engine") -> None:
        super().__init__(name)

    def validate_context(self, context: AIContext) -> None:
        if "required_field" not in context.data:
            raise ContextValidationException("Missing 'required_field' in context.data")

    async def execute(self, context: AIContext) -> IntelligenceResult:
        return IntelligenceResult(
            engine_name=self.name,
            status=ExecutionStatus.SUCCESS,
            confidence=1.0,
            output={"validated": context.data["required_field"]},
        )


class MismatchNameEngine(BaseEngine):
    """Engine whose execute method incorrectly attributes output to a different engine."""

    def __init__(self, name: str = "mismatch_engine") -> None:
        super().__init__(name)

    async def execute(self, context: AIContext) -> IntelligenceResult:
        return IntelligenceResult(
            engine_name="different_engine_name",
            status=ExecutionStatus.SUCCESS,
            confidence=1.0,
            output={},
        )


class FailingEngine(BaseEngine):
    """Engine that raises a specified exception during execution."""

    def __init__(
        self, name: str = "failing_engine", exception_to_raise: Exception | None = None
    ) -> None:
        super().__init__(name)
        self.exception_to_raise = exception_to_raise or RuntimeError("Simulated crash")

    async def execute(self, context: AIContext) -> IntelligenceResult:
        raise self.exception_to_raise


# --------------------------------------------------------------------------- #
# AI Framework Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def fresh_context() -> AIContext:
    """Returns a newly initialized AIContext."""
    return AIContext()


@pytest.fixture
def empty_registry() -> EngineRegistry:
    """Returns a newly initialized, empty EngineRegistry."""
    return EngineRegistry()


@pytest.fixture
def populated_registry() -> EngineRegistry:
    """Returns an EngineRegistry populated with standard test engines."""
    registry = EngineRegistry()
    registry.register(SuccessEchoEngine("echo_engine"))
    registry.register(StepTwoEngine("step_two_engine"))
    registry.register(ValidatingEngine("validating_engine"))
    return registry


@pytest.fixture
def orchestrator(populated_registry: EngineRegistry) -> AIOrchestrator:
    """Returns an AIOrchestrator wired with the populated test registry."""
    return AIOrchestrator(populated_registry)


# --------------------------------------------------------------------------- #
# Database Test Fixtures (SQLite In-Memory Isolation)
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="function")
def db_engine() -> Generator[Engine, None, None]:
    """Create an isolated in-memory SQLite engine with foreign keys enabled."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(test_engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    """Provide a transactional database session rolled back after each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = session_factory()

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def bound_session_local(
    db_engine: Engine,
) -> Generator[sessionmaker[Session], None, None]:
    """Configure SessionLocal to bind to db_engine for get_db testing, then restore."""
    original_bind = SessionLocal.kw.get("bind")
    SessionLocal.configure(bind=db_engine)
    yield SessionLocal
    SessionLocal.configure(bind=original_bind)
