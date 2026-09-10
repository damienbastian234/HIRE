"""Comprehensive pytest test suite for the H.I.R.E. AI Orchestration Framework.

Tests cover all components under app/ai/:
- Interfaces & Protocols (interfaces.py)
- Execution Context & Runtime State (context.py)
- Intelligence & Workflow Results (result.py)
- AI Exception Hierarchy (exceptions.py)
- Base Engine Lifecycle (base_engine.py)
- Engine Registry (registry.py)
- AI Orchestrator (orchestrator.py)
"""

from __future__ import annotations

import asyncio
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.ai.base_engine import BaseEngine
from app.ai.context import AIContext, WorkflowState, WorkflowStatus
from app.ai.exceptions import (
    AIException,
    ContextValidationException,
    EngineExecutionException,
    EngineRegistrationException,
    OrchestrationException,
)
from app.ai.interfaces import EngineInterface, OrchestratorInterface
from app.ai.orchestrator import AIOrchestrator
from app.ai.registry import EngineRegistry
from app.ai.result import ExecutionStatus, IntelligenceResult, WorkflowResult
from app.core.exceptions import HireException
from tests.conftest import (
    FailingEngine,
    MismatchNameEngine,
    StepTwoEngine,
    SuccessEchoEngine,
    ValidatingEngine,
)


# =========================================================================== #
# 1. AIContext & WorkflowState Tests
# =========================================================================== #


class TestAIContextAndWorkflowState:
    """Tests for AIContext, WorkflowState, and WorkflowStatus."""

    def test_context_default_initialization(self, fresh_context: AIContext) -> None:
        """Verify default values of an initialized AIContext."""
        assert isinstance(fresh_context.workflow_id, UUID)
        assert fresh_context.workflow_name is None
        assert fresh_context.created_at is not None
        assert fresh_context.metadata == {}
        assert fresh_context.data == {}
        assert isinstance(fresh_context.state, WorkflowState)
        assert fresh_context.state.workflow_status == WorkflowStatus.PENDING
        assert fresh_context.state.current_engine is None
        assert fresh_context.state.completed_engines == []
        assert fresh_context.state.failed_engine is None
        assert fresh_context.state.progress == 0.0

    def test_context_custom_initialization(self) -> None:
        """Verify AIContext accepts custom initial metadata and data."""
        ctx = AIContext(
            workflow_name="candidate_evaluation",
            metadata={"source": "api_upload", "user_id": "u123"},
            data={"candidate_name": "Jane Doe"},
        )
        assert ctx.workflow_name == "candidate_evaluation"
        assert ctx.metadata["source"] == "api_upload"
        assert ctx.data["candidate_name"] == "Jane Doe"

    def test_workflow_state_progress_bounds(self) -> None:
        """Verify progress field enforces 0.0 <= progress <= 1.0."""
        valid_state = WorkflowState(progress=0.75)
        assert valid_state.progress == 0.75

        with pytest.raises(ValidationError):
            WorkflowState(progress=-0.1)

        with pytest.raises(ValidationError):
            WorkflowState(progress=1.1)

    def test_workflow_status_enum_values(self) -> None:
        """Verify all expected enum stages exist with proper string values."""
        assert WorkflowStatus.PENDING.value == "pending"
        assert WorkflowStatus.RUNNING.value == "running"
        assert WorkflowStatus.COMPLETED.value == "completed"
        assert WorkflowStatus.FAILED.value == "failed"


# =========================================================================== #
# 2. IntelligenceResult & WorkflowResult Tests
# =========================================================================== #


class TestIntelligenceResultAndWorkflowResult:
    """Tests for IntelligenceResult, WorkflowResult, and ExecutionStatus."""

    def test_intelligence_result_valid_construction(self) -> None:
        """Verify constructing a valid IntelligenceResult."""
        res = IntelligenceResult(
            engine_name="test_engine",
            status=ExecutionStatus.SUCCESS,
            confidence=0.92,
            output={"key": "val"},
            warnings=["test warning"],
            errors=[],
            execution_time_ms=15.5,
        )
        assert res.engine_name == "test_engine"
        assert res.status == ExecutionStatus.SUCCESS
        assert res.confidence == 0.92
        assert res.output == {"key": "val"}
        assert res.warnings == ["test warning"]
        assert res.errors == []
        assert res.execution_time_ms == 15.5

    def test_intelligence_result_confidence_bounds(self) -> None:
        """Verify confidence score must be within 0.0 and 1.0 (or None)."""
        res_none = IntelligenceResult(
            engine_name="test_engine",
            status=ExecutionStatus.SUCCESS,
            confidence=None,
        )
        assert res_none.confidence is None

        with pytest.raises(ValidationError):
            IntelligenceResult(
                engine_name="test_engine",
                status=ExecutionStatus.SUCCESS,
                confidence=1.5,
            )

        with pytest.raises(ValidationError):
            IntelligenceResult(
                engine_name="test_engine",
                status=ExecutionStatus.SUCCESS,
                confidence=-0.01,
            )

    def test_execution_status_enum_values(self) -> None:
        """Verify ExecutionStatus enum members."""
        assert ExecutionStatus.SUCCESS.value == "success"
        assert ExecutionStatus.PARTIAL_SUCCESS.value == "partial_success"
        assert ExecutionStatus.FAILURE.value == "failure"

    def test_workflow_result_construction(self, fresh_context: AIContext) -> None:
        """Verify WorkflowResult models workflow_id and list of engine results."""
        engine_res = IntelligenceResult(
            engine_name="engine_a",
            status=ExecutionStatus.SUCCESS,
            output={"done": True},
        )
        wf_res = WorkflowResult(
            workflow_id=fresh_context.workflow_id,
            results=[engine_res],
        )
        assert wf_res.workflow_id == fresh_context.workflow_id
        assert len(wf_res.results) == 1
        assert wf_res.results[0].engine_name == "engine_a"


# =========================================================================== #
# 3. AI Exceptions Hierarchy Tests
# =========================================================================== #


class TestAIExceptions:
    """Tests for the AI exception hierarchy and error status codes."""

    def test_ai_exception_inherits_hire_exception(self) -> None:
        """Verify all AI exceptions integrate with core HireException."""
        assert issubclass(AIException, HireException)

    def test_subclasses_inherit_ai_exception(self) -> None:
        """Verify specific AI exceptions inherit from AIException."""
        assert issubclass(ContextValidationException, AIException)
        assert issubclass(EngineRegistrationException, AIException)
        assert issubclass(EngineExecutionException, AIException)
        assert issubclass(OrchestrationException, AIException)

    def test_exception_status_codes_and_types(self) -> None:
        """Verify status codes and error type mappings for standard AI exceptions."""
        exc_ctx = ContextValidationException("bad context")
        assert exc_ctx.status_code == 422
        assert exc_ctx.error_type == "ContextValidationError"

        exc_reg = EngineRegistrationException("bad registration")
        assert exc_reg.status_code == 409
        assert exc_reg.error_type == "EngineRegistrationError"

        exc_exec = EngineExecutionException("bad execution")
        assert exc_exec.status_code == 500
        assert exc_exec.error_type == "EngineExecutionError"

        exc_orch = OrchestrationException("orchestration failed")
        assert exc_orch.status_code == 500
        assert exc_orch.error_type == "OrchestrationError"


# =========================================================================== #
# 4. BaseEngine Lifecycle Tests
# =========================================================================== #


class TestBaseEngineLifecycle:
    """Tests for the standardized BaseEngine lifecycle."""

    @pytest.mark.anyio
    async def test_base_engine_run_lifecycle_success(
        self, fresh_context: AIContext
    ) -> None:
        """Verify run() executes validate_context, execute, and populates timing."""
        engine = SuccessEchoEngine("test_echo")
        fresh_context.data["input_message"] = "test payload"

        result = await engine.run(fresh_context)

        assert result.engine_name == "test_echo"
        assert result.status == ExecutionStatus.SUCCESS
        assert result.output == {"echo": "echo: test payload"}
        assert fresh_context.data["echo_result"] == "echo: test payload"
        # BaseEngine automatically populates execution_time_ms if not provided
        assert result.execution_time_ms is not None
        assert result.execution_time_ms >= 0.0

    @pytest.mark.anyio
    async def test_base_engine_preserves_explicit_execution_time(
        self, fresh_context: AIContext
    ) -> None:
        """Verify run() does not overwrite execution_time_ms if already set by engine."""

        class PreservedTimeEngine(BaseEngine):
            async def execute(self, context: AIContext) -> IntelligenceResult:
                return IntelligenceResult(
                    engine_name=self.name,
                    status=ExecutionStatus.SUCCESS,
                    execution_time_ms=99.9,
                )

        engine = PreservedTimeEngine("time_engine")
        result = await engine.run(fresh_context)
        assert result.execution_time_ms == 99.9

    @pytest.mark.anyio
    async def test_base_engine_validate_context_failure_raises(
        self, fresh_context: AIContext
    ) -> None:
        """Verify validate_context failure prevents execution and raises exception."""
        engine = ValidatingEngine("val_engine")
        # required_field is missing from fresh_context.data
        with pytest.raises(ContextValidationException) as exc_info:
            await engine.run(fresh_context)

        assert "Missing 'required_field'" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_base_engine_validate_result_engine_name_mismatch_raises(
        self, fresh_context: AIContext
    ) -> None:
        """Verify validate_result catches mismatched result engine names."""
        engine = MismatchNameEngine("declared_engine")
        with pytest.raises(EngineExecutionException) as exc_info:
            await engine.run(fresh_context)

        assert "attributed to 'different_engine_name'" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_base_engine_execute_exception_propagates(
        self, fresh_context: AIContext
    ) -> None:
        """Verify exceptions in execute() are re-raised to the caller."""
        engine = FailingEngine("fail_engine", ValueError("Inner error"))
        with pytest.raises(ValueError) as exc_info:
            await engine.run(fresh_context)

        assert "Inner error" in str(exc_info.value)


# =========================================================================== #
# 5. EngineRegistry Tests
# =========================================================================== #


class TestEngineRegistry:
    """Tests for EngineRegistry registration, lookup, and lifecycle."""

    def test_register_and_get(self, empty_registry: EngineRegistry) -> None:
        """Verify engine registration and successful retrieval."""
        engine = SuccessEchoEngine("echo")
        empty_registry.register(engine)

        assert empty_registry.is_registered("echo")
        assert empty_registry.get("echo") is engine

    def test_register_duplicate_raises(self, empty_registry: EngineRegistry) -> None:
        """Verify registering duplicate engine names raises EngineRegistrationException."""
        engine1 = SuccessEchoEngine("duplicate_name")
        engine2 = SuccessEchoEngine("duplicate_name")

        empty_registry.register(engine1)
        with pytest.raises(EngineRegistrationException) as exc_info:
            empty_registry.register(engine2)

        assert "already registered" in str(exc_info.value)

    def test_get_unregistered_engine_raises(
        self, empty_registry: EngineRegistry
    ) -> None:
        """Verify getting an unknown engine raises EngineRegistrationException."""
        with pytest.raises(EngineRegistrationException) as exc_info:
            empty_registry.get("nonexistent_engine")

        assert "No engine named 'nonexistent_engine' is registered" in str(
            exc_info.value
        )

    def test_is_registered(self, empty_registry: EngineRegistry) -> None:
        """Verify is_registered correctly checks presence."""
        assert not empty_registry.is_registered("test_engine")
        empty_registry.register(SuccessEchoEngine("test_engine"))
        assert empty_registry.is_registered("test_engine")

    def test_unregister(self, empty_registry: EngineRegistry) -> None:
        """Verify unregistering removes an engine and handles nonexistent keys safely."""
        empty_registry.register(SuccessEchoEngine("to_remove"))
        assert empty_registry.is_registered("to_remove")

        empty_registry.unregister("to_remove")
        assert not empty_registry.is_registered("to_remove")

        # Unregistering nonexistent key should be a silent no-op
        empty_registry.unregister("never_existed")

    def test_list_engines(self, empty_registry: EngineRegistry) -> None:
        """Verify list_engines returns all registered names."""
        assert empty_registry.list_engines() == []

        empty_registry.register(SuccessEchoEngine("engine_1"))
        empty_registry.register(StepTwoEngine("engine_2"))

        names = empty_registry.list_engines()
        assert set(names) == {"engine_1", "engine_2"}


# =========================================================================== #
# 6. AIOrchestrator Tests
# =========================================================================== #


class TestAIOrchestrator:
    """Tests for AIOrchestrator execution, progress tracking, and error handling."""

    @pytest.mark.anyio
    async def test_empty_engine_list_workflow(
        self, orchestrator: AIOrchestrator, fresh_context: AIContext
    ) -> None:
        """Verify empty workflow trivially completes and updates state."""
        result = await orchestrator.run(fresh_context, [])

        assert isinstance(result, WorkflowResult)
        assert result.workflow_id == fresh_context.workflow_id
        assert result.results == []
        assert fresh_context.state.workflow_status == WorkflowStatus.COMPLETED
        assert fresh_context.state.progress == 1.0

    @pytest.mark.anyio
    async def test_sequential_execution_and_data_propagation(
        self, orchestrator: AIOrchestrator, fresh_context: AIContext
    ) -> None:
        """Verify engines execute sequentially and share state via context.data."""
        fresh_context.data["input_message"] = "workflow_test"

        result = await orchestrator.run(
            fresh_context, ["echo_engine", "step_two_engine"]
        )

        assert len(result.results) == 2
        assert result.results[0].engine_name == "echo_engine"
        assert result.results[1].engine_name == "step_two_engine"

        # Verify data propagation: step_two_engine read what echo_engine produced
        assert fresh_context.data["echo_result"] == "echo: workflow_test"
        assert fresh_context.data["step_two_completed"] is True
        assert result.results[1].output["derived_from"] == "echo: workflow_test"

        # Verify final workflow state
        assert fresh_context.state.workflow_status == WorkflowStatus.COMPLETED
        assert fresh_context.state.current_engine is None
        assert fresh_context.state.completed_engines == [
            "echo_engine",
            "step_two_engine",
        ]
        assert fresh_context.state.failed_engine is None
        assert fresh_context.state.progress == 1.0

    @pytest.mark.anyio
    async def test_fail_fast_on_ai_exception(
        self, populated_registry: EngineRegistry, fresh_context: AIContext
    ) -> None:
        """Verify workflow halts immediately when an engine raises an AIException."""
        orchestrator = AIOrchestrator(populated_registry)

        # 'validating_engine' requires 'required_field' in context.data, which is missing.
        # step_two_engine should NEVER run.
        with pytest.raises(ContextValidationException):
            await orchestrator.run(
                fresh_context, ["echo_engine", "validating_engine", "step_two_engine"]
            )

        # echo_engine succeeded, validating_engine failed, step_two_engine never ran
        assert fresh_context.state.workflow_status == WorkflowStatus.FAILED
        assert fresh_context.state.completed_engines == ["echo_engine"]
        assert fresh_context.state.failed_engine == "validating_engine"
        assert fresh_context.state.current_engine is None
        assert "step_two_completed" not in fresh_context.data

    @pytest.mark.anyio
    async def test_fail_fast_on_unexpected_exception(
        self, populated_registry: EngineRegistry, fresh_context: AIContext
    ) -> None:
        """Verify unexpected errors are wrapped into OrchestrationException and halt workflow."""
        populated_registry.register(
            FailingEngine("crash_engine", RuntimeError("Fatal unexpected bug"))
        )
        orchestrator = AIOrchestrator(populated_registry)

        with pytest.raises(OrchestrationException) as exc_info:
            await orchestrator.run(fresh_context, ["echo_engine", "crash_engine"])

        assert "failed unexpectedly during orchestration" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, RuntimeError)
        assert fresh_context.state.workflow_status == WorkflowStatus.FAILED
        assert fresh_context.state.failed_engine == "crash_engine"
        assert fresh_context.state.current_engine is None

    @pytest.mark.anyio
    async def test_unregistered_engine_raises_engine_registration_exception(
        self, orchestrator: AIOrchestrator, fresh_context: AIContext
    ) -> None:
        """Verify looking up an unregistered engine raises EngineRegistrationException."""
        with pytest.raises(EngineRegistrationException):
            await orchestrator.run(fresh_context, ["unregistered_engine"])


# =========================================================================== #
# 7. Structural Interfaces / Protocols Conformance Tests
# =========================================================================== #


class TestInterfacesAndProtocols:
    """Tests for protocol conformance via typing.runtime_checkable."""

    def test_engine_interface_protocol_conformance(self) -> None:
        """Verify BaseEngine subclasses satisfy EngineInterface protocol."""
        engine = SuccessEchoEngine("test_protocol")
        assert isinstance(engine, EngineInterface)

    def test_orchestrator_interface_protocol_conformance(
        self, populated_registry: EngineRegistry
    ) -> None:
        """Verify AIOrchestrator satisfies OrchestratorInterface protocol."""
        orchestrator = AIOrchestrator(populated_registry)
        assert isinstance(orchestrator, OrchestratorInterface)