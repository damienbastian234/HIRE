"""
Standardized result model returned by every Intelligence System (Engine).
"""

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    """Possible outcomes of an engine's execution lifecycle."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"


class IntelligenceResult(BaseModel):
    """
    Standardized output contract returned by every Intelligence System.

    Every engine, regardless of what it does internally, returns an
    IntelligenceResult so the orchestrator — and eventually API layers —
    can handle any engine's output generically, without needing to know
    that engine's specific implementation details.
    """

    engine_name: str = Field(
        ...,
        description="String identifier of the engine that produced this result.",
    )
    status: ExecutionStatus = Field(
        ...,
        description="Outcome of the engine's execution.",
    )
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Normalized confidence score for the result, 0.0-1.0. "
            "None if not applicable."
        ),
    )
    output: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured output produced by the engine.",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal warning messages produced during execution.",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Error messages produced during execution, if any.",
    )
    execution_time_ms: float | None = Field(
        default=None,
        ge=0.0,
        description="Wall-clock execution time in milliseconds.",
    )


class WorkflowResult(BaseModel):
    """
    Standardized output returned by the AIOrchestrator for a completed
    workflow, replacing a raw `List[IntelligenceResult]`.

    Kept intentionally minimal for now — `workflow_id` and `results`
    only. Because this is a Pydantic model, future fields (overall
    workflow status, total execution time, aggregated warnings/errors,
    metadata, etc.) can be added later as optional fields with
    defaults, without breaking existing callers that construct or
    consume a WorkflowResult today.
    """

    workflow_id: UUID = Field(
        ...,
        description="Identifier of the AIContext workflow this result belongs to.",
    )
    results: list[IntelligenceResult] = Field(
        default_factory=list,
        description="Per-engine results, in the order the engines were executed.",
    )