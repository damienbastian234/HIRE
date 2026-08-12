"""
Unit tests for the Candidate Matching engine (HIRE-AI-105).

Follows the same testing style as the other intelligence-engine tests:
plain `def test_...()` functions with `asyncio.run()` internally, rather
than adding a pytest-asyncio dependency.
"""

import asyncio

import pytest

from app.ai.context import AIContext, WorkflowStatus
from app.ai.engines.candidate_matching import CandidateMatchingEngine
from app.ai.exceptions import ContextValidationException
from app.ai.orchestrator import AIOrchestrator
from app.ai.registry import EngineRegistry
from app.ai.result import ExecutionStatus
from app.models.candidate import CandidateProfile, Education, Experience, Skills
from app.models.job_requirement import (
    EducationRequirement,
    ExperienceRequirement,
    JobRequirement,
    SkillRequirement,
)


def run_async(coro):
    """Run an async coroutine from a synchronous pytest test function."""
    return asyncio.run(coro)


def make_candidate(
    *,
    technical=None,
    soft=None,
    experience_years=3.0,
    degree="B.Tech",
) -> CandidateProfile:
    return CandidateProfile(
        personal_info={"full_name": "Jane Doe"},
        education=[Education(degree=degree, institution="Example University")],
        experience=[
            Experience(
                company="Example Corp",
                position="Software Engineer",
                duration=str(experience_years),
            )
        ],
        skills=Skills(
            technical_skills=technical or [],
            soft_skills=soft or [],
        ),
    )


def make_job(
    *,
    required_skills=None,
    preferred_skills=None,
    experience_years=2.0,
    degree="B.Tech",
) -> JobRequirement:
    return JobRequirement(
        title="Backend Engineer",
        required_skills=[
            SkillRequirement(name=skill)
            for skill in (required_skills or [])
        ],
        preferred_skills=[
            SkillRequirement(name=skill, required=False)
            for skill in (preferred_skills or [])
        ],
        experience=ExperienceRequirement(minimum_years=experience_years),
        education=EducationRequirement(degrees=[degree]),
    )


def make_context(*, candidate_profile=None, job_requirement=None) -> AIContext:
    return AIContext(
        data={
            "candidate_profile": candidate_profile,
            "job_requirement": job_requirement,
        }
    )


# ---------------------------------------------------------------------------
# Successful matching
# ---------------------------------------------------------------------------


def test_successful_candidate_matching():
    context = make_context(
        candidate_profile=make_candidate(
            technical=["Python", "FastAPI", "SQL"],
            soft=["Communication"],
            experience_years=3.0,
            degree="B.Tech",
        ),
        job_requirement=make_job(
            required_skills=["Python", "FastAPI"],
            preferred_skills=["SQL"],
            experience_years=2.0,
            degree="B.Tech",
        ),
    )
    engine = CandidateMatchingEngine()

    result = run_async(engine.run(context))

    assert result.engine_name == "candidate_matching"
    assert result.status == ExecutionStatus.SUCCESS
    assert result.output["candidate_matching"].overall_score.overall_score >= 0.0
    assert result.output["candidate_matching"].confidence >= 0.0
    assert result.output["candidate_matching"].recommendation is not None


# ---------------------------------------------------------------------------
# Context validation errors
# ---------------------------------------------------------------------------


def test_missing_candidate_profile_key_raises_context_validation_exception():
    engine = CandidateMatchingEngine()
    context = make_context(job_requirement=make_job())
    context.data.pop("candidate_profile")

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_missing_job_requirement_key_raises_context_validation_exception():
    engine = CandidateMatchingEngine()
    context = make_context(candidate_profile=make_candidate())
    context.data.pop("job_requirement")

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_none_candidate_profile_raises_context_validation_exception():
    engine = CandidateMatchingEngine()
    context = make_context(
        candidate_profile=None,
        job_requirement=make_job(),
    )

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_none_job_requirement_raises_context_validation_exception():
    engine = CandidateMatchingEngine()
    context = make_context(
        candidate_profile=make_candidate(),
        job_requirement=None,
    )

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_wrong_candidate_profile_type_raises_context_validation_exception():
    engine = CandidateMatchingEngine()
    context = make_context(
        candidate_profile={"skills": ["Python"]},
        job_requirement=make_job(),
    )

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_wrong_job_requirement_type_raises_context_validation_exception():
    engine = CandidateMatchingEngine()
    context = make_context(
        candidate_profile=make_candidate(),
        job_requirement={"title": "Backend Engineer"},
    )

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


# ---------------------------------------------------------------------------
# Empty or incomplete inputs
# ---------------------------------------------------------------------------


def test_candidate_with_no_skills():
    context = make_context(
        candidate_profile=make_candidate(technical=[], soft=[]),
        job_requirement=make_job(required_skills=["Python"]),
    )
    engine = CandidateMatchingEngine()

    result = run_async(engine.run(context))

    matching = result.output["candidate_matching"]
    assert matching.skill_match.matched_required_skills == []
    assert matching.skill_match.missing_required_skills == ["python"]
    assert matching.overall_score.overall_score < 100.0


def test_job_with_no_required_skills():
    context = make_context(
        candidate_profile=make_candidate(technical=["Python"]),
        job_requirement=make_job(required_skills=[], preferred_skills=[]),
    )
    engine = CandidateMatchingEngine()

    result = run_async(engine.run(context))

    matching = result.output["candidate_matching"]
    assert matching.skill_match.required_match_percentage == 100.0
    assert matching.skill_match.missing_required_skills == []


# ---------------------------------------------------------------------------
# Requirement checks
# ---------------------------------------------------------------------------


def test_candidate_meets_all_requirements():
    context = make_context(
        candidate_profile=make_candidate(
            technical=["Python", "FastAPI", "Docker"],
            soft=["Communication"],
            experience_years=5.0,
            degree="B.Tech",
        ),
        job_requirement=make_job(
            required_skills=["Python", "FastAPI"],
            preferred_skills=["Docker"],
            experience_years=2.0,
            degree="B.Tech",
        ),
    )
    engine = CandidateMatchingEngine()

    result = run_async(engine.run(context))

    matching = result.output["candidate_matching"]
    assert matching.skill_match.required_match_percentage == 100.0
    assert matching.experience_match.meets_requirement is True
    assert matching.education_match.meets_requirement is True


def test_candidate_misses_required_skills():
    context = make_context(
        candidate_profile=make_candidate(
            technical=["Java"],
            soft=["Communication"],
            experience_years=5.0,
        ),
        job_requirement=make_job(
            required_skills=["Python", "FastAPI"],
            preferred_skills=["Docker"],
            experience_years=2.0,
            degree="B.Tech",
        ),
    )
    engine = CandidateMatchingEngine()

    result = run_async(engine.run(context))

    matching = result.output["candidate_matching"]
    assert set(matching.skill_match.missing_required_skills) == {"fastapi", "python"}
    assert matching.skill_match.required_match_percentage < 100.0


def test_experience_requirement_met():
    context = make_context(
        candidate_profile=make_candidate(experience_years=5.0),
        job_requirement=make_job(experience_years=2.0),
    )
    engine = CandidateMatchingEngine()

    result = run_async(engine.run(context))

    matching = result.output["candidate_matching"]
    assert matching.experience_match.meets_requirement is True
    assert matching.experience_match.candidate_years >= matching.experience_match.required_years


def test_experience_requirement_not_met():
    context = make_context(
        candidate_profile=make_candidate(experience_years=1.0),
        job_requirement=make_job(experience_years=2.0),
    )
    engine = CandidateMatchingEngine()

    result = run_async(engine.run(context))

    matching = result.output["candidate_matching"]
    assert matching.experience_match.meets_requirement is False
    assert matching.experience_match.candidate_years < matching.experience_match.required_years


def test_education_requirement_met():
    context = make_context(
        candidate_profile=make_candidate(degree="B.Tech"),
        job_requirement=make_job(degree="B.Tech"),
    )
    engine = CandidateMatchingEngine()

    result = run_async(engine.run(context))

    matching = result.output["candidate_matching"]
    assert matching.education_match.meets_requirement is True
    assert matching.education_match.candidate_degree == "B.Tech"


def test_education_requirement_not_met():
    context = make_context(
        candidate_profile=make_candidate(degree="M.Sc"),
        job_requirement=make_job(degree="B.Tech"),
    )
    engine = CandidateMatchingEngine()

    result = run_async(engine.run(context))

    matching = result.output["candidate_matching"]
    assert matching.education_match.meets_requirement is False
    assert matching.education_match.candidate_degree == "M.Sc"


# ---------------------------------------------------------------------------
# Recommendation and confidence
# ---------------------------------------------------------------------------


def test_recommendation_value_is_returned():
    context = make_context(
        candidate_profile=make_candidate(
            technical=["Python", "FastAPI"],
            soft=["Communication"],
            experience_years=5.0,
            degree="B.Tech",
        ),
        job_requirement=make_job(
            required_skills=["Python", "FastAPI"],
            preferred_skills=[],
            experience_years=2.0,
            degree="B.Tech",
        ),
    )
    engine = CandidateMatchingEngine()

    result = run_async(engine.run(context))

    matching = result.output["candidate_matching"]
    assert matching.recommendation is not None
    assert str(matching.recommendation) in {
        "Strong Match",
        "Good Match",
        "Possible Match",
        "Weak Match",
        "Not Recommended",
    }


def test_confidence_value_is_between_0_and_100():
    context = make_context(
        candidate_profile=make_candidate(
            technical=["Python", "FastAPI"],
            soft=["Communication"],
            experience_years=4.0,
        ),
        job_requirement=make_job(
            required_skills=["Python", "FastAPI"],
            preferred_skills=["Docker"],
            experience_years=2.0,
            degree="B.Tech",
        ),
    )
    engine = CandidateMatchingEngine()

    result = run_async(engine.run(context))

    matching = result.output["candidate_matching"]
    assert 0.0 <= matching.confidence <= 100.0


# ---------------------------------------------------------------------------
# Engine integration
# ---------------------------------------------------------------------------


def test_engine_integrates_with_registry():
    registry = EngineRegistry()
    registry.register(CandidateMatchingEngine())

    assert registry.is_registered("candidate_matching") is True
    assert registry.get("candidate_matching").name == "candidate_matching"


def test_engine_integrates_with_orchestrator():
    registry = EngineRegistry()
    registry.register(CandidateMatchingEngine())
    orchestrator = AIOrchestrator(registry)
    context = make_context(
        candidate_profile=make_candidate(
            technical=["Python", "FastAPI"],
            soft=["Communication"],
            experience_years=3.0,
        ),
        job_requirement=make_job(
            required_skills=["Python", "FastAPI"],
            preferred_skills=[],
            experience_years=2.0,
            degree="B.Tech",
        ),
    )

    workflow_result = run_async(orchestrator.run(context, ["candidate_matching"]))

    assert workflow_result.workflow_id == context.workflow_id
    assert len(workflow_result.results) == 1
    assert workflow_result.results[0].engine_name == "candidate_matching"


def test_context_state_is_unchanged_when_running_the_engine_directly():
    context = make_context(
        candidate_profile=make_candidate(
            technical=["Python"],
            soft=["Communication"],
        ),
        job_requirement=make_job(required_skills=["Python"]),
    )
    engine = CandidateMatchingEngine()

    run_async(engine.run(context))

    assert context.state.workflow_status == WorkflowStatus.PENDING
    assert context.state.current_engine is None
    assert context.state.completed_engines == []
    assert context.state.progress == 0.0


def test_context_state_updates_correctly_when_run_through_orchestrator():
    registry = EngineRegistry()
    registry.register(CandidateMatchingEngine())
    orchestrator = AIOrchestrator(registry)
    context = make_context(
        candidate_profile=make_candidate(technical=["Python"]),
        job_requirement=make_job(required_skills=["Python"]),
    )

    run_async(orchestrator.run(context, ["candidate_matching"]))

    assert context.state.workflow_status == WorkflowStatus.COMPLETED
    assert context.state.completed_engines == ["candidate_matching"]
    assert context.state.progress == 1.0


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


def test_performance_under_100ms():
    context = make_context(
        candidate_profile=make_candidate(
            technical=["Python", "FastAPI", "SQL", "Docker", "Git"],
            soft=["Communication", "Leadership"],
            experience_years=4.0,
        ),
        job_requirement=make_job(
            required_skills=["Python", "FastAPI", "SQL"],
            preferred_skills=["Docker"],
            experience_years=2.0,
            degree="B.Tech",
        ),
    )
    engine = CandidateMatchingEngine()

    result = run_async(engine.run(context))

    assert result.execution_time_ms is not None
    assert result.execution_time_ms < 100.0
