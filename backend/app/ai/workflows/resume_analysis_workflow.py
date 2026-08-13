"""
Resume Analysis workflow (HIRE-AI-106).

This module contains AI application-layer orchestration ONLY. It
defers all parsing, scoring, and matching logic to the existing
Intelligence engines and keeps the workflow responsible only for
coordinating the request context and results.
"""

from typing import Any

from app.ai.context import AIContext
from app.ai.engines.candidate_matching import CandidateMatchingEngine
from app.ai.engines.experience_intelligence import ExperienceIntelligenceEngine
from app.ai.engines.resume_intelligence import ResumeIntelligenceEngine
from app.ai.engines.skill_intelligence import SkillIntelligenceEngine
from app.ai.orchestrator import AIOrchestrator
from app.ai.registry import EngineRegistry
from app.models.candidate import CandidateProfile
from app.models.candidate_matching_model import CandidateMatching
from app.models.experience_intelligence_model import ExperienceIntelligence
from app.models.job_requirement import JobRequirement
from app.models.skill_intelligence import SkillIntelligence
from app.schemas.resume_analysis import ResumeAnalysisData

_DOWNSTREAM_ENGINE_NAMES: list[str] = [
    "skill_intelligence",
    "experience_intelligence",
    "candidate_matching",
]


def _default_registry() -> EngineRegistry:
    """Return a fresh registry for each workflow invocation."""
    registry = EngineRegistry()
    registry.register(ResumeIntelligenceEngine())
    registry.register(SkillIntelligenceEngine())
    registry.register(ExperienceIntelligenceEngine())
    registry.register(CandidateMatchingEngine())
    return registry


# Compatibility alias for older import paths that expect the no-cache
# default registry factory naming.
_build_default_registry = _default_registry


def _coerce_model(model_cls: type, value: Any):
    """Reuse model instances when the engine already returns them; otherwise rebuild from dict."""
    if isinstance(value, model_cls):
        return value
    if isinstance(value, dict):
        return model_cls(**value)
    raise TypeError(f"Expected {model_cls.__name__} instance or dict, got {type(value).__name__}")


async def run_resume_analysis(
    resume_text: str,
    job_requirement: JobRequirement,
    *,
    registry: EngineRegistry | None = None,
) -> ResumeAnalysisData:
    """Run the full resume analysis pipeline and aggregate the engine outputs."""
    active_registry = registry if registry is not None else _default_registry()
    context = AIContext(workflow_name="resume_analysis")

    context.data["resume_text"] = resume_text
    resume_engine = active_registry.get("resume_intelligence")
    resume_result = await resume_engine.run(context)

    candidate_profile = _coerce_model(CandidateProfile, resume_result.output)
    context.data["candidate_profile"] = candidate_profile
    context.data["job_requirement"] = job_requirement

    orchestrator = AIOrchestrator(active_registry)
    workflow_result = await orchestrator.run(context, _DOWNSTREAM_ENGINE_NAMES)

    results_by_engine = {result.engine_name: result for result in workflow_result.results}

    skill_intelligence = _coerce_model(
        SkillIntelligence,
        results_by_engine["skill_intelligence"].output,
    )
    experience_intelligence = _coerce_model(
        ExperienceIntelligence,
        results_by_engine["experience_intelligence"].output,
    )

    candidate_matching_output = results_by_engine["candidate_matching"].output.get(
        "candidate_matching"
    )
    candidate_matching = _coerce_model(CandidateMatching, candidate_matching_output)

    return ResumeAnalysisData(
        candidate_profile=candidate_profile,
        skill_intelligence=skill_intelligence,
        experience_intelligence=experience_intelligence,
        candidate_matching=candidate_matching,
    )
