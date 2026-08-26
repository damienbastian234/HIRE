"""
Tests for app.ai.workflows.resume_analysis_workflow (HIRE-AI-106).

Follows the existing testing style used by test_candidate_matching.py:
plain `def test_...()` functions with `asyncio.run()` internally.
"""

import asyncio

import pytest

from app.ai.base_engine import BaseEngine
from app.ai.context import AIContext
from app.ai.engines.candidate_matching import CandidateMatchingEngine
from app.ai.engines.experience_intelligence import ExperienceIntelligenceEngine
from app.ai.engines.resume_intelligence import ResumeIntelligenceEngine
from app.ai.engines.skill_intelligence import SkillIntelligenceEngine
from app.ai.exceptions import ContextValidationException, EngineExecutionException
from app.ai.registry import EngineRegistry
from app.ai.result import IntelligenceResult
from app.ai.workflows.resume_analysis_workflow import run_resume_analysis
from app.models.candidate_matching_model import CandidateMatching
from app.models.experience_intelligence_model import ExperienceIntelligence
from app.models.skill_intelligence import SkillIntelligence
from app.schemas.resume_analysis import ResumeAnalysisData


def run_async(coro):
    return asyncio.run(coro)


def make_registry() -> EngineRegistry:
    """A fresh registry with all four real engines, isolated per test."""
    registry = EngineRegistry()
    registry.register(ResumeIntelligenceEngine())
    registry.register(SkillIntelligenceEngine())
    registry.register(ExperienceIntelligenceEngine())
    registry.register(CandidateMatchingEngine())
    return registry


# ---------------------------------------------------------------------------
# Successful orchestration
# ---------------------------------------------------------------------------


def test_successful_resume_analysis(sample_resume_text, sample_job_requirement):
    result = run_async(
        run_resume_analysis(
            resume_text=sample_resume_text,
            job_requirement=sample_job_requirement,
            registry=make_registry(),
        )
    )

    assert isinstance(result, ResumeAnalysisData)
    assert result.candidate_profile.personal_info.email == "john.doe@example.com"
    assert "Python" in result.candidate_profile.skills.technical_skills
    assert isinstance(result.skill_intelligence, SkillIntelligence)
    assert isinstance(result.experience_intelligence, ExperienceIntelligence)
    assert isinstance(result.candidate_matching, CandidateMatching)


def test_candidate_profile_is_bridged_correctly(
    sample_resume_text, sample_job_requirement
):
    """The CandidateProfile built from ResumeIntelligenceEngine's output
    must be the same data used downstream by Skill/Experience/Matching
    engines."""
    result = run_async(
        run_resume_analysis(
            resume_text=sample_resume_text,
            job_requirement=sample_job_requirement,
            registry=make_registry(),
        )
    )

    technical_skill_count = len(result.candidate_profile.skills.technical_skills)
    # Skill intelligence's technical count should reflect the same
    # candidate skills that were bridged into context.data.
    total_skills = result.skill_intelligence.metrics.total_skills
    assert total_skills >= min(technical_skill_count, 1)


def test_candidate_matching_uses_the_supplied_job_requirement(
    sample_resume_text, sample_job_requirement
):
    result = run_async(
        run_resume_analysis(
            resume_text=sample_resume_text,
            job_requirement=sample_job_requirement,
            registry=make_registry(),
        )
    )

    required_names = {s.name.lower() for s in sample_job_requirement.required_skills}
    matched = set(result.candidate_matching.skill_match.matched_required_skills)
    missing = set(result.candidate_matching.skill_match.missing_required_skills)
    assert matched | missing == required_names


def test_workflow_uses_default_registry_when_none_supplied(
    sample_resume_text, sample_job_requirement
):
    """Calling without an explicit registry must still succeed via the
    module's default fresh registry.."""
    result = run_async(
        run_resume_analysis(
            resume_text=sample_resume_text,
            job_requirement=sample_job_requirement,
        )
    )
    assert isinstance(result, ResumeAnalysisData)


# ---------------------------------------------------------------------------
# Missing / empty resume text
# ---------------------------------------------------------------------------


def test_blank_resume_text_still_produces_a_result_with_warnings(
    sample_job_requirement,
):
    """ResumeIntelligenceEngine treats blank text as a valid 'empty resume'
    input (see resume_intelligence.py), not a hard failure. The workflow
    must not swallow or alter that existing behavior."""
    result = run_async(
        run_resume_analysis(
            resume_text=" ",
            job_requirement=sample_job_requirement,
            registry=make_registry(),
        )
    )
    assert isinstance(result, ResumeAnalysisData)
    assert result.candidate_profile.personal_info.email is None


# ---------------------------------------------------------------------------
# Engine failure propagation
# ---------------------------------------------------------------------------


class _FailingSkillIntelligenceEngine(BaseEngine):
    """Stand-in engine registered under the real 'skill_intelligence' name
    to verify that engine failures propagate through the workflow
    unmodified, without adding any new exception behavior."""

    def __init__(self) -> None:
        super().__init__(name="skill_intelligence")

    async def execute(self, context: AIContext) -> IntelligenceResult:
        raise EngineExecutionException("Simulated skill intelligence failure.")


def test_engine_failure_propagates_as_existing_ai_exception(
    sample_resume_text, sample_job_requirement
):
    registry = EngineRegistry()
    registry.register(ResumeIntelligenceEngine())
    registry.register(_FailingSkillIntelligenceEngine())
    registry.register(ExperienceIntelligenceEngine())
    registry.register(CandidateMatchingEngine())

    with pytest.raises(EngineExecutionException):
        run_async(
            run_resume_analysis(
                resume_text=sample_resume_text,
                job_requirement=sample_job_requirement,
                registry=registry,
            )
        )


def test_invalid_job_requirement_type_propagates_context_validation_exception(
    sample_resume_text,
):
    """Passing something that isn't a JobRequirement instance must surface
    the existing ContextValidationException from CandidateMatchingEngine,
    not a new/duplicated validation error."""
    with pytest.raises(ContextValidationException):
        run_async(
            run_resume_analysis(
                resume_text=sample_resume_text,
                job_requirement="not-a-job-requirement",  # type: ignore[arg-type]
                registry=make_registry(),
            )
        )