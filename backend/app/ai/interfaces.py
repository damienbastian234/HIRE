"""
Structural interfaces for the AI subsystem.

These define expected behavior only — no implementation logic lives
here. Concrete engines should inherit from `app.ai.base_engine.BaseEngine`,
which implements the lifecycle described by `EngineInterface` below;
these Protocols exist so other components (e.g. the registry) can be
typed against expected behavior rather than a specific class hierarchy.
"""

from typing import List, Protocol, runtime_checkable

from app.ai.context import AIContext
from app.ai.result import IntelligenceResult, WorkflowResult


@runtime_checkable
class EngineInterface(Protocol):
    """
    Structural contract that every Intelligence System engine must
    satisfy: a stable string `name`, and an async `run()` method that
    executes the engine's full lifecycle against a given context.
    """

    name: str

    async def run(self, context: AIContext) -> IntelligenceResult:
        """Execute this engine's full lifecycle against the given context."""
        ...


@runtime_checkable
class OrchestratorInterface(Protocol):
    """
    Structural contract for a component that coordinates a sequence of
    engines against a shared AIContext and returns their aggregated
    results as a WorkflowResult.
    """

    async def run(
        self, context: AIContext, engine_names: List[str]
    ) -> WorkflowResult:
        """Execute the named engines, in order, against the given context."""
        ...