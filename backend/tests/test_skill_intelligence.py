"""
Unit tests for the Skill Intelligence engine (HIRE-AI-103).

Follows the same testing style as HIRE-AI-102: plain `def test_...()`
functions with `asyncio.run()` internally, rather than adding a
pytest-asyncio dependency.
"""

import asyncio

import pytest

from app.ai.context import AIContext, WorkflowStatus
from app.ai.engines.skill_intelligence import SkillIntelligenceEngine
from app.ai.exceptions import ContextValidationException
from app.ai.orchestrator import AIOrchestrator
from app.ai.registry import EngineRegistry
from app.ai.result import ExecutionStatus
from app.models.candidate import CandidateProfile, Skills


def run_async(coro):
    """Run an async coroutine from a synchronous pytest test function."""
    return asyncio.run(coro)


def make_context(technical=None, soft=None) -> AIContext:
    profile = CandidateProfile(
        skills=Skills(technical_skills=technical or [], soft_skills=soft or [])
    )
    return AIContext(data={"candidate_profile": profile})


# ---------------------------------------------------------------------------
# Complete candidate profile
# ---------------------------------------------------------------------------


def test_complete_profile_produces_full_skill_intelligence():
    context = make_context(
        technical=["Python", "FastAPI", "PostgreSQL", "AWS", "Git"],
        soft=["Leadership", "Communication"],
    )
    engine = SkillIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.engine_name == "skill_intelligence"
    assert result.status == ExecutionStatus.SUCCESS
    assert 0.0 <= result.confidence <= 1.0
    output = result.output
    assert len(output["categories"]) == 6  # all 6 known categories represented
    assert output["metrics"]["technical_skill_count"] == 5
    assert output["metrics"]["soft_skill_count"] == 2
    assert output["gaps"]["missing_categories"] == []
    assert result.warnings == []


# ---------------------------------------------------------------------------
# Empty skills
# ---------------------------------------------------------------------------


def test_empty_skills_does_not_crash():
    context = make_context(technical=[], soft=[])
    engine = SkillIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.status == ExecutionStatus.SUCCESS
    assert result.confidence == 0.0
    output = result.output
    assert output["categories"] == []
    assert output["metrics"]["total_skills"] == 0
    assert len(output["gaps"]["missing_categories"]) == 6  # all categories missing


# ---------------------------------------------------------------------------
# Technical skills only
# ---------------------------------------------------------------------------


def test_technical_skills_only():
    context = make_context(technical=["Python", "Docker"], soft=[])
    engine = SkillIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["metrics"]["technical_skill_count"] == 2
    assert output["metrics"]["soft_skill_count"] == 0
    assert "Soft Skills" in output["gaps"]["missing_categories"]
    category_names = {c["name"] for c in output["categories"]}
    assert "Soft Skills" not in category_names


# ---------------------------------------------------------------------------
# Soft skills only
# ---------------------------------------------------------------------------


def test_soft_skills_only():
    context = make_context(technical=[], soft=["Leadership", "Teamwork"])
    engine = SkillIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["metrics"]["technical_skill_count"] == 0
    assert output["metrics"]["soft_skill_count"] == 2
    category_names = {c["name"] for c in output["categories"]}
    assert category_names == {"Soft Skills"}
    assert "Programming Languages" in output["gaps"]["missing_categories"]


# ---------------------------------------------------------------------------
# Duplicate skills
# ---------------------------------------------------------------------------


def test_duplicate_skills_are_detected_and_normalized():
    context = make_context(technical=["Python", "python", "Python3"], soft=[])
    engine = SkillIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["normalized_skills"] == ["Python"]
    assert set(output["duplicate_skills"]) == {"python", "Python3"}


# ---------------------------------------------------------------------------
# Synonym normalization
# ---------------------------------------------------------------------------


def test_synonym_normalization_js_variants():
    context = make_context(technical=["JS", "Javascript", "Java Script"], soft=[])
    engine = SkillIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["normalized_skills"] == ["JavaScript"]
    assert set(output["duplicate_skills"]) == {"Javascript", "Java Script"}


# ---------------------------------------------------------------------------
# Unknown skills
# ---------------------------------------------------------------------------


def test_unknown_skills_remain_uncategorized():
    context = make_context(technical=["Python", "Quantum Computing"], soft=[])
    engine = SkillIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert "Quantum Computing" in output["normalized_skills"]  # passed through unchanged
    assert output["metrics"]["uncategorized_skills"] == 1
    all_categorized = {s for c in output["categories"] for s in c["skills"]}
    assert "Quantum Computing" not in all_categorized


# ---------------------------------------------------------------------------
# Missing candidate_profile
# ---------------------------------------------------------------------------


def test_missing_candidate_profile_key_raises_context_validation_exception():
    engine = SkillIntelligenceEngine()
    context = AIContext(data={})  # no 'candidate_profile' key at all

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_none_candidate_profile_raises_context_validation_exception():
    engine = SkillIntelligenceEngine()
    context = AIContext(data={"candidate_profile": None})

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


# ---------------------------------------------------------------------------
# Invalid candidate_profile type
# ---------------------------------------------------------------------------


def test_wrong_type_candidate_profile_raises_context_validation_exception():
    engine = SkillIntelligenceEngine()
    context = AIContext(data={"candidate_profile": {"skills": ["Python"]}})  # plain dict, not CandidateProfile

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_string_candidate_profile_raises_context_validation_exception():
    engine = SkillIntelligenceEngine()
    context = AIContext(data={"candidate_profile": "not a profile"})

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


# ---------------------------------------------------------------------------
# Engine integration (registry + orchestrator)
# ---------------------------------------------------------------------------


def test_engine_integrates_with_registry_and_orchestrator():
    registry = EngineRegistry()
    registry.register(SkillIntelligenceEngine())
    orchestrator = AIOrchestrator(registry)
    context = make_context(technical=["Python", "FastAPI"], soft=["Leadership"])

    workflow_result = run_async(orchestrator.run(context, ["skill_intelligence"]))

    assert workflow_result.workflow_id == context.workflow_id
    assert len(workflow_result.results) == 1
    assert workflow_result.results[0].engine_name == "skill_intelligence"


# ---------------------------------------------------------------------------
# Engine never mutates context.state
# ---------------------------------------------------------------------------


def test_engine_never_mutates_context_state_directly():
    context = make_context(technical=["Python", "FastAPI"], soft=["Leadership"])
    engine = SkillIntelligenceEngine()

    run_async(engine.run(context))

    # WorkflowState is owned exclusively by the AIOrchestrator; running
    # the engine standalone (bypassing the orchestrator) must leave
    # context.state untouched.
    assert context.state.workflow_status == WorkflowStatus.PENDING
    assert context.state.current_engine is None
    assert context.state.completed_engines == []
    assert context.state.progress == 0.0


def test_state_is_updated_when_run_through_orchestrator():
    registry = EngineRegistry()
    registry.register(SkillIntelligenceEngine())
    orchestrator = AIOrchestrator(registry)
    context = make_context(technical=["Python"], soft=[])

    run_async(orchestrator.run(context, ["skill_intelligence"]))

    # Going through the orchestrator, state IS updated (by the
    # orchestrator, not the engine).
    assert context.state.workflow_status == WorkflowStatus.COMPLETED
    assert context.state.completed_engines == ["skill_intelligence"]


def test_metrics_reflect_normalized_deduplicated_counts():
    """
    Regression test for the HIRE-AI-103 metrics refinement: counts must
    reflect the normalized/deduplicated pipeline output, not the raw
    (pre-dedup) CandidateProfile.skills lists.
    """
    context = make_context(
        technical=["Python", "python", "Python3", "FastAPI"],  # 4 raw, 2 unique
        soft=["Leadership", "Leadership"],  # 2 raw, 1 unique
    )
    engine = SkillIntelligenceEngine()

    result = run_async(engine.run(context))

    metrics = result.output["metrics"]
    # Raw counts would have been technical=4, soft=2 — the normalized/
    # deduplicated counts must be lower and internally consistent.
    assert metrics["technical_skill_count"] == 2  # Python, FastAPI
    assert metrics["soft_skill_count"] == 1  # Leadership
    assert metrics["total_skills"] == 3
    assert metrics["technical_skill_count"] + metrics["soft_skill_count"] == metrics["total_skills"]


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


def test_performance_under_100ms():
    context = make_context(
        technical=["Python", "FastAPI", "PostgreSQL", "AWS", "Git", "Docker", "React"],
        soft=["Leadership", "Communication", "Teamwork"],
    )
    engine = SkillIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.execution_time_ms is not None
    assert result.execution_time_ms < 100.0