"""
Shared execution context for AI workflows.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    """
    Lifecycle stage of a workflow's orchestration, distinct from any
    single engine's result quality (see `result.ExecutionStatus`).
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowState(BaseModel):
    """
    Orchestration/runtime state for a workflow, kept separate from the
    business data engines produce.

    This is mutated by the AIOrchestrator as it runs registered engines
    against a context, so any code holding a reference to the context
    can observe workflow progress in real time (e.g. which engine is
    currently running), independent of the final WorkflowResult that
    is only available once the workflow completes.
    """

    workflow_status: WorkflowStatus = Field(
        default=WorkflowStatus.PENDING,
        description="Current lifecycle stage of the workflow.",
    )
    current_engine: Optional[str] = Field(
        default=None,
        description="Name of the engine currently executing, if any.",
    )
    completed_engines: List[str] = Field(
        default_factory=list,
        description="Names of engines that have completed successfully, in execution order.",
    )
    failed_engine: Optional[str] = Field(
        default=None,
        description="Name of the engine that failed, if the workflow halted due to a failure.",
    )
    progress: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of the workflow's engines completed so far, 0.0-1.0.",
    )


class AIContext(BaseModel):
    """
    Represents the execution context of a single AI workflow.

    An AIContext is created once per workflow invocation and passed by
    reference to every engine the AIOrchestrator runs in sequence. It is
    a mutable Pydantic model with three distinct areas:

        metadata -> workflow identity/tracing info (who, when, why)
        state    -> orchestration/runtime state (what's happening now),
                    owned and mutated by the AIOrchestrator
        data     -> business data engines read from and extend

    Engines are expected to extend `data` with their own structured
    output as the workflow progresses, rather than replacing the
    context outright, so that later engines in the same workflow can
    build on earlier results. Engines should not write to `state`;
    that is the orchestrator's responsibility.

    This model intentionally contains no recruitment-specific fields.
    All domain-specific values belong inside `data`, keyed by whatever
    convention the owning Intelligence System defines.
    """

    workflow_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this workflow execution.",
    )
    workflow_name: Optional[str] = Field(
        default=None,
        description="Human-readable name of the workflow being executed, if known.",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp the context was created, in UTC.",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Free-form workflow metadata, such as trace or caller "
            "information. Not treated as engine output or runtime state."
        ),
    )
    state: WorkflowState = Field(
        default_factory=WorkflowState,
        description=(
            "Orchestration/runtime state for this workflow, distinct "
            "from business data. Owned and mutated by the AIOrchestrator."
        ),
    )
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Structured, engine-populated workflow data. Each engine "
            "reads from and extends this dictionary as the workflow "
            "progresses through the orchestrator's sequence."
        ),
    )