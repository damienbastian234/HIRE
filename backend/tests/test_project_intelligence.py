"""
Unit tests for the Project Intelligence engine (HIRE-AI-108).

Follows the same testing style as the other intelligence-engine tests:
plain `def test_...()` functions with `asyncio.run()` internally, rather
than adding a pytest-asyncio dependency (see test_candidate_matching.py,
test_education_intelligence.py).
"""

import asyncio
import json
import time

import pytest

from app.ai.context import AIContext
from app.ai.engines.project_intelligence import ProjectIntelligenceEngine
from app.ai.exceptions import ContextValidationException
from app.ai.orchestrator import AIOrchestrator
from app.ai.registry import EngineRegistry
from app.ai.result import ExecutionStatus
from app.models.candidate import CandidateProfile, Project
from app.models.project_intelligence import ProjectIntelligence


def run_async(coro):
    """Run an async coroutine from a synchronous pytest test function."""
    return asyncio.run(coro)


def make_candidate(*, projects: list[Project] | None = None) -> CandidateProfile:
    return CandidateProfile(
        personal_info={"full_name": "Jane Doe"},
        projects=projects or [],
    )


def make_context(*, candidate_profile=None) -> AIContext:
    return AIContext(data={"candidate_profile": candidate_profile})


# ---------------------------------------------------------------------------
# Context validation
# ---------------------------------------------------------------------------


def test_missing_candidate_profile_key_raises_context_validation_exception():
    engine = ProjectIntelligenceEngine()
    context = AIContext(data={})

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_none_candidate_profile_raises_context_validation_exception():
    engine = ProjectIntelligenceEngine()
    context = make_context(candidate_profile=None)

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_wrong_candidate_profile_type_raises_context_validation_exception():
    engine = ProjectIntelligenceEngine()
    context = make_context(candidate_profile={"projects": []})

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_valid_candidate_profile_passes_context_validation():
    engine = ProjectIntelligenceEngine()
    context = make_context(
        candidate_profile=make_candidate(projects=[Project(name="Resume Analyzer")])
    )

    result = run_async(engine.run(context))

    assert result.status == ExecutionStatus.SUCCESS


# ---------------------------------------------------------------------------
# Project data — counts, single/multiple, dedup
# ---------------------------------------------------------------------------


def test_empty_project_list():
    context = make_context(candidate_profile=make_candidate(projects=[]))
    engine = ProjectIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["project_count"] == 0
    assert output["project_names"] == []
    assert output["technologies"] == []


def test_single_project():
    context = make_context(
        candidate_profile=make_candidate(
            projects=[
                Project(
                    name="Resume Analyzer",
                    description="An AI-powered resume parsing tool.",
                    technologies=["Python", "FastAPI"],
                )
            ]
        )
    )
    engine = ProjectIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["project_count"] == 1
    assert output["project_names"] == ["Resume Analyzer"]
    assert output["technologies"] == ["Python", "FastAPI"]


def test_multiple_projects_with_different_values():
    context = make_context(
        candidate_profile=make_candidate(
            projects=[
                Project(name="Project A", technologies=["Python", "Docker"]),
                Project(name="Project B", technologies=["React", "TypeScript"]),
            ]
        )
    )
    engine = ProjectIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["project_count"] == 2
    assert output["project_names"] == ["Project A", "Project B"]
    assert output["technologies"] == ["Python", "Docker", "React", "TypeScript"]


def test_technologies_are_deduplicated_across_projects_case_insensitively():
    context = make_context(
        candidate_profile=make_candidate(
            projects=[
                Project(name="Project A", technologies=["Python", "FastAPI"]),
                Project(name="Project B", technologies=["python", "PostgreSQL"]),
            ]
        )
    )
    engine = ProjectIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["project_count"] == 2
    assert output["technologies"] == ["Python", "FastAPI", "PostgreSQL"]


def test_duplicate_project_names_are_deduplicated():
    context = make_context(
        candidate_profile=make_candidate(
            projects=[
                Project(name="Resume Analyzer", technologies=["Python"]),
                Project(name="resume analyzer", technologies=["Docker"]),
            ]
        )
    )
    engine = ProjectIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["project_count"] == 2
    assert output["project_names"] == ["Resume Analyzer"]
    assert output["technologies"] == ["Python", "Docker"]


# ---------------------------------------------------------------------------
# Incomplete / missing / whitespace edge cases
# ---------------------------------------------------------------------------


def test_project_with_all_optional_fields_missing():
    context = make_context(candidate_profile=make_candidate(projects=[Project()]))
    engine = ProjectIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["project_count"] == 1
    assert output["project_names"] == []
    assert output["technologies"] == []


def test_incomplete_project_records_are_handled_gracefully():
    context = make_context(
        candidate_profile=make_candidate(
            projects=[
                Project(name="Project A"),
                Project(technologies=["Python"]),
                Project(description="No name or technologies here."),
            ]
        )
    )
    engine = ProjectIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["project_count"] == 3
    assert output["project_names"] == ["Project A"]
    assert output["technologies"] == ["Python"]


def test_empty_technologies_list_does_not_error():
    context = make_context(
        candidate_profile=make_candidate(
            projects=[Project(name="Project A", technologies=[])]
        )
    )
    engine = ProjectIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.output["technologies"] == []


def test_whitespace_only_name_is_treated_as_absent():
    context = make_context(
        candidate_profile=make_candidate(projects=[Project(name="   ")])
    )
    engine = ProjectIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.output["project_names"] == []


def test_whitespace_is_trimmed_from_names_and_technologies():
    context = make_context(
        candidate_profile=make_candidate(
            projects=[Project(name="  Project A  ", technologies=["  Python  "])]
        )
    )
    engine = ProjectIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["project_names"] == ["Project A"]
    assert output["technologies"] == ["Python"]


# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------


def test_result_is_intelligence_result_with_correct_engine_name():
    context = make_context(
        candidate_profile=make_candidate(projects=[Project(name="Project A")])
    )
    engine = ProjectIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.engine_name == "project_intelligence"
    assert result.status == ExecutionStatus.SUCCESS


def test_output_is_json_serializable():
    context = make_context(
        candidate_profile=make_candidate(
            projects=[Project(name="Project A", technologies=["Python"])]
        )
    )
    engine = ProjectIntelligenceEngine()

    result = run_async(engine.run(context))

    serialized = json.dumps(result.output)
    assert isinstance(serialized, str)


def test_output_can_be_reconstructed_as_project_intelligence():
    context = make_context(
        candidate_profile=make_candidate(
            projects=[Project(name="Project A", technologies=["Python"])]
        )
    )
    engine = ProjectIntelligenceEngine()

    result = run_async(engine.run(context))
    reconstructed = ProjectIntelligence.model_validate(result.output)

    assert reconstructed.project_names == ["Project A"]
    assert reconstructed.technologies == ["Python"]


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------


def test_confidence_is_between_0_and_1():
    context = make_context(
        candidate_profile=make_candidate(
            projects=[
                Project(
                    name="Project A",
                    description="A project.",
                    technologies=["Python"],
                )
            ]
        )
    )
    engine = ProjectIntelligenceEngine()

    result = run_async(engine.run(context))

    assert 0.0 <= result.confidence <= 1.0


def test_empty_project_data_produces_zero_confidence():
    context = make_context(candidate_profile=make_candidate(projects=[]))
    engine = ProjectIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.confidence == 0.0


def test_complete_project_data_produces_full_confidence():
    context = make_context(
        candidate_profile=make_candidate(
            projects=[
                Project(
                    name="Project A",
                    description="A complete project record.",
                    technologies=["Python"],
                )
            ]
        )
    )
    engine = ProjectIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.confidence == 1.0


def test_confidence_reflects_extraction_completeness_not_project_count():
    """A single fully-described project and a large but sparse project
    list should not be judged by volume — confidence measures field
    completeness, not how many/impressive the projects are."""
    single_complete = make_context(
        candidate_profile=make_candidate(
            projects=[
                Project(
                    name="Project A",
                    description="Complete.",
                    technologies=["Python"],
                )
            ]
        )
    )
    many_sparse = make_context(
        candidate_profile=make_candidate(
            projects=[Project(name=f"Project {i}") for i in range(10)]
        )
    )
    engine = ProjectIntelligenceEngine()

    complete_result = run_async(engine.run(single_complete))
    sparse_result = run_async(engine.run(many_sparse))

    assert complete_result.confidence == 1.0
    assert sparse_result.confidence < complete_result.confidence


# ---------------------------------------------------------------------------
# Framework integration
# ---------------------------------------------------------------------------


def test_engine_integrates_with_registry():
    registry = EngineRegistry()
    registry.register(ProjectIntelligenceEngine())

    assert registry.is_registered("project_intelligence") is True
    assert registry.get("project_intelligence").name == "project_intelligence"


def test_engine_integrates_with_orchestrator():
    registry = EngineRegistry()
    registry.register(ProjectIntelligenceEngine())
    orchestrator = AIOrchestrator(registry)
    context = make_context(
        candidate_profile=make_candidate(projects=[Project(name="Project A")])
    )

    workflow_result = run_async(orchestrator.run(context, ["project_intelligence"]))

    assert len(workflow_result.results) == 1
    assert workflow_result.results[0].engine_name == "project_intelligence"


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


def test_performance_1000_executions_under_100ms():
    """1000 sequential engine executions against an already-constructed
    CandidateProfile stay comfortably under 100ms, matching the
    performance convention established in
    test_education_intelligence.py."""
    context = make_context(
        candidate_profile=make_candidate(
            projects=[
                Project(
                    name="Project A",
                    description="A project.",
                    technologies=["Python", "FastAPI"],
                )
            ]
        )
    )
    engine = ProjectIntelligenceEngine()

    async def run_many() -> float:
        start = time.perf_counter()
        for _ in range(1000):
            await engine.run(context)
        return time.perf_counter() - start

    elapsed_seconds = run_async(run_many())

    assert elapsed_seconds < 0.1