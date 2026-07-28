"""
Abstract base class defining the lifecycle every Intelligence System
engine must follow.
"""

import time
from abc import ABC, abstractmethod

from app.ai.context import AIContext
from app.ai.exceptions import EngineExecutionException
from app.ai.result import IntelligenceResult
from app.core.logging import get_logger

logger = get_logger(__name__)


class BaseEngine(ABC):
    """
    Abstract base class for every Intelligence System engine.

    Subclasses implement only their engine-specific logic by overriding
    `execute` (required) and optionally `validate_context` /
    `validate_result`. `run()` is the single public entry point and
    should not be overridden — it enforces the standard lifecycle:

        Initialize -> Validate Context -> Execute -> Validate Result -> Return

    Engines must never import or reference `AIOrchestrator`. The
    dependency between orchestration and engines is one-directional:
    the orchestrator depends on engines, never the reverse.
    """

    def __init__(self, name: str) -> None:
        """
        Args:
            name: Stable string identifier for this engine, used for
                registration, lookup, and result attribution. This is
                the "Initialize" step of the engine lifecycle.
        """
        self.name = name

    def validate_context(self, context: AIContext) -> None:
        """
        Validate that the given context contains what this engine needs.

        The default implementation performs no validation and simply
        passes. Subclasses that require specific fields in
        `context.data` should override this and raise
        `ContextValidationException` when validation fails.
        """
        return None

    @abstractmethod
    async def execute(self, context: AIContext) -> IntelligenceResult:
        """
        Perform this engine's core work and return an IntelligenceResult.

        Subclasses must implement this method. It should not be called
        directly by external code — call `run()` instead, which wraps
        this with the full lifecycle (context validation, result
        validation, and execution timing).
        """
        raise NotImplementedError

    def validate_result(self, result: IntelligenceResult) -> None:
        """
        Validate the IntelligenceResult produced by `execute`.

        The default implementation checks that the result's
        `engine_name` matches this engine's own `name`, so an engine
        cannot accidentally (or incorrectly) attribute its result to a
        different engine. Subclasses may override to add stricter
        checks, raising `EngineExecutionException` on failure.
        """
        if result.engine_name != self.name:
            raise EngineExecutionException(
                f"Engine '{self.name}' returned a result attributed to "
                f"'{result.engine_name}'."
            )

    async def run(self, context: AIContext) -> IntelligenceResult:
        """
        Execute the full engine lifecycle against the given context.

        Lifecycle:
            1. Validate the context via `validate_context`.
            2. Execute engine-specific logic via `execute`.
            3. Validate the resulting IntelligenceResult via `validate_result`.
            4. Return the result, with `execution_time_ms` populated if
               the engine did not already set it.

        Any exception raised during validation or execution is logged
        with full traceback and then re-raised to the caller (typically
        the AIOrchestrator).

        Args:
            context: The shared AIContext for the current workflow.

        Returns:
            The validated IntelligenceResult produced by this engine.
        """
        start_time = time.perf_counter()

        try:
            self.validate_context(context)
            result = await self.execute(context)
            self.validate_result(result)
        except Exception:
            logger.exception("Engine '%s' failed during execution.", self.name)
            raise

        if result.execution_time_ms is None:
            result.execution_time_ms = (time.perf_counter() - start_time) * 1000

        return result