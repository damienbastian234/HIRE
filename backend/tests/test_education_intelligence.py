"""
Unit tests for the Education Intelligence engine (HIRE-AI-107).

Follows the same testing style as the other intelligence-engine tests:
plain `def test_...()` functions with `asyncio.run()` internally, rather
than adding a pytest-asyncio dependency (see test_candidate_matching.py).
"""

import asyncio
import time

import pytest

from app.ai.context import AIContext
from app.ai.engines.education_intelligence import EducationIntelligenceEngine
from app.ai.exceptions import ContextValidationException
from app.ai.result import ExecutionStatus
from app.models.candidate import CandidateProfile, Education
from app.models.education_intelligence import EducationIntelligence


def run_async(coro):
    """Run an async coroutine from a synchronous pytest test function."""
    return asyncio.run(coro)


def make_candidate(*, education: list[Education] | None = None) -> CandidateProfile:
    return CandidateProfile(
        personal_info={"full_name": "Jane Doe"},
        education=education or [],
    )


def make_context(*, candidate_profile=None) -> AIContext:
    return AIContext(data={"candidate_profile": candidate_profile})


# ---------------------------------------------------------------------------
# Context validation
# ---------------------------------------------------------------------------


def test_missing_candidate_profile_key_raises_context_validation_exception():
    engine = EducationIntelligenceEngine()
    context = AIContext(data={})

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_none_candidate_profile_raises_context_validation_exception():
    engine = EducationIntelligenceEngine()
    context = make_context(candidate_profile=None)

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_wrong_candidate_profile_type_raises_context_validation_exception():
    engine = EducationIntelligenceEngine()
    context = make_context(candidate_profile={"education": []})

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_valid_candidate_profile_passes_context_validation():
    engine = EducationIntelligenceEngine()
    context = make_context(
        candidate_profile=make_candidate(
            education=[Education(degree="B.Tech", institution="Example University")]
        )
    )

    result = run_async(engine.run(context))

    assert result.status == ExecutionStatus.SUCCESS


# ---------------------------------------------------------------------------
# Education data — single / multiple records
# ---------------------------------------------------------------------------


def test_single_education_record():
    context = make_context(
        candidate_profile=make_candidate(
            education=[
                Education(
                    degree="B.Tech Computer Science",
                    institution="Example University",
                    specialization="Computer Science",
                    gpa="8.5",
                    graduation_year="2020",
                )
            ]
        )
    )
    engine = EducationIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["education_count"] == 1
    assert output["highest_qualification"] == "B.Tech Computer Science"
    assert output["degrees"] == ["B.Tech Computer Science"]
    assert output["institutions"] == ["Example University"]
    assert output["fields_of_study"] == ["Computer Science"]
    assert output["academic_performance"] == ["8.5"]


def test_multiple_education_records():
    context = make_context(
        candidate_profile=make_candidate(
            education=[
                Education(
                    degree="B.Tech",
                    institution="University A",
                    graduation_year="2018",
                ),
                Education(
                    degree="M.Tech",
                    institution="University B",
                    graduation_year="2020",
                ),
            ]
        )
    )
    engine = EducationIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["education_count"] == 2
    assert output["degrees"] == ["B.Tech", "M.Tech"]
    assert output["institutions"] == ["University A", "University B"]


# ---------------------------------------------------------------------------
# Highest qualification (deterministic, recency-based)
# ---------------------------------------------------------------------------


def test_highest_qualification_picks_most_recent_graduation_year():
    context = make_context(
        candidate_profile=make_candidate(
            education=[
                Education(degree="B.Tech", graduation_year="2018"),
                Education(degree="M.Tech", graduation_year="2020"),
                Education(degree="Diploma", graduation_year="2015"),
            ]
        )
    )
    engine = EducationIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.output["highest_qualification"] == "M.Tech"


def test_highest_qualification_falls_back_to_first_entry_without_dates():
    context = make_context(
        candidate_profile=make_candidate(
            education=[
                Education(degree="B.Tech"),
                Education(degree="M.Tech"),
            ]
        )
    )
    engine = EducationIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.output["highest_qualification"] == "B.Tech"


def test_highest_qualification_is_none_when_no_degree_present():
    context = make_context(
        candidate_profile=make_candidate(
            education=[Education(institution="University A", graduation_year="2020")]
        )
    )
    engine = EducationIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.output["highest_qualification"] is None


def test_highest_qualification_does_not_privilege_recognized_degree_names():
    """No hardcoded qualification-name ranking exists; an unusual/unknown
    degree string must be treated identically to a common one — recency
    is the only signal used."""
    context = make_context(
        candidate_profile=make_candidate(
            education=[
                Education(degree="PhD in Computer Science", graduation_year="2015"),
                Education(
                    degree="Underwater Basket Weaving Certificate",
                    graduation_year="2021",
                ),
            ]
        )
    )
    engine = EducationIntelligenceEngine()

    result = run_async(engine.run(context))

    expected = "Underwater Basket Weaving Certificate"
    assert result.output["highest_qualification"] == expected


def test_unresolvable_graduation_year_is_ignored_for_ranking():
    context = make_context(
        candidate_profile=make_candidate(
            education=[
                Education(degree="B.Tech", graduation_year="not-a-year"),
                Education(degree="M.Tech", graduation_year="2020"),
            ]
        )
    )
    engine = EducationIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.output["highest_qualification"] == "M.Tech"


# ---------------------------------------------------------------------------
# Empty / missing / incomplete / duplicate data
# ---------------------------------------------------------------------------


def test_empty_education_list():
    context = make_context(candidate_profile=make_candidate(education=[]))
    engine = EducationIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["education_count"] == 0
    assert output["highest_qualification"] is None
    assert output["degrees"] == []
    assert output["institutions"] == []
    assert output["fields_of_study"] == []
    assert output["academic_performance"] == []
    assert result.confidence == 0.0


def test_education_record_with_all_optional_fields_none():
    context = make_context(candidate_profile=make_candidate(education=[Education()]))
    engine = EducationIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["education_count"] == 1
    assert output["highest_qualification"] is None
    assert output["degrees"] == []
    assert output["institutions"] == []
    assert output["fields_of_study"] == []
    assert output["academic_performance"] == []


def test_incomplete_education_records_are_handled_gracefully():
    context = make_context(
        candidate_profile=make_candidate(
            education=[
                Education(degree="B.Tech"),
                Education(institution="Some College"),
                Education(gpa="7.9"),
            ]
        )
    )
    engine = EducationIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["education_count"] == 3
    assert output["degrees"] == ["B.Tech"]
    assert output["institutions"] == ["Some College"]
    assert output["academic_performance"] == ["7.9"]


def test_duplicate_degrees_are_deduplicated_case_insensitively():
    context = make_context(
        candidate_profile=make_candidate(
            education=[
                Education(degree="B.Tech", institution="University A"),
                Education(degree="b.tech", institution="University A"),
            ]
        )
    )
    engine = EducationIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["education_count"] == 2
    assert output["degrees"] == ["B.Tech"]
    assert output["institutions"] == ["University A"]


# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------


def test_result_is_intelligence_result_with_correct_engine_name():
    context = make_context(
        candidate_profile=make_candidate(education=[Education(degree="B.Tech")])
    )
    engine = EducationIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.engine_name == "education_intelligence"
    assert result.status == ExecutionStatus.SUCCESS


def test_output_is_json_serializable():
    import json

    context = make_context(
        candidate_profile=make_candidate(
            education=[Education(degree="B.Tech", institution="Example University")]
        )
    )
    engine = EducationIntelligenceEngine()

    result = run_async(engine.run(context))

    serialized = json.dumps(result.output)
    assert isinstance(serialized, str)


def test_output_can_be_reconstructed_as_education_intelligence():
    context = make_context(
        candidate_profile=make_candidate(
            education=[Education(degree="B.Tech", institution="Example University")]
        )
    )
    engine = EducationIntelligenceEngine()

    result = run_async(engine.run(context))
    reconstructed = EducationIntelligence.model_validate(result.output)

    assert reconstructed.degrees == ["B.Tech"]
    assert reconstructed.institutions == ["Example University"]


def test_confidence_is_between_0_and_1():
    context = make_context(
        candidate_profile=make_candidate(
            education=[
                Education(
                    degree="B.Tech",
                    institution="Example University",
                    gpa="8.5",
                    graduation_year="2020",
                )
            ]
        )
    )
    engine = EducationIntelligenceEngine()

    result = run_async(engine.run(context))

    assert 0.0 <= result.confidence <= 1.0


# ---------------------------------------------------------------------------
# Engine integration
# ---------------------------------------------------------------------------


def test_engine_integrates_with_registry():
    from app.ai.registry import EngineRegistry

    registry = EngineRegistry()
    registry.register(EducationIntelligenceEngine())

    assert registry.is_registered("education_intelligence") is True
    assert registry.get("education_intelligence").name == "education_intelligence"


def test_engine_integrates_with_orchestrator():
    from app.ai.orchestrator import AIOrchestrator
    from app.ai.registry import EngineRegistry

    registry = EngineRegistry()
    registry.register(EducationIntelligenceEngine())
    orchestrator = AIOrchestrator(registry)
    context = make_context(
        candidate_profile=make_candidate(education=[Education(degree="B.Tech")])
    )

    workflow_result = run_async(orchestrator.run(context, ["education_intelligence"]))

    assert len(workflow_result.results) == 1
    assert workflow_result.results[0].engine_name == "education_intelligence"


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


def test_performance_1000_executions_under_100ms():
    """1000 sequential engine executions against an already-constructed
    CandidateProfile stay comfortably under 100ms, matching the
    performance expectations set by test_candidate_matching.py's
    single-execution performance test, scaled to the ticket's ask."""
    context = make_context(
        candidate_profile=make_candidate(
            education=[
                Education(
                    degree="B.Tech",
                    institution="Example University",
                    specialization="Computer Science",
                    gpa="8.5",
                    graduation_year="2020",
                )
            ]
        )
    )
    engine = EducationIntelligenceEngine()

    async def run_many() -> float:
        start = time.perf_counter()
        for _ in range(1000):
            await engine.run(context)
        return time.perf_counter() - start

    elapsed_seconds = run_async(run_many())

    assert elapsed_seconds < 0.1
    