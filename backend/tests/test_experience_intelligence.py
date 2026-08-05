"""
Unit tests for the Experience Intelligence engine (HIRE-AI-104).

Follows the same testing style as HIRE-AI-102/103: plain
`def test_...()` functions with `asyncio.run()` internally, rather
than adding a pytest-asyncio dependency.
"""

import asyncio

import pytest

from app.ai.context import AIContext, WorkflowStatus
from app.ai.engines.experience_intelligence import ExperienceIntelligenceEngine
from app.ai.exceptions import ContextValidationException
from app.ai.orchestrator import AIOrchestrator
from app.ai.registry import EngineRegistry
from app.ai.result import ExecutionStatus
from app.models.candidate import CandidateProfile, Experience


def run_async(coro):
    """Run an async coroutine from a synchronous pytest test function."""
    return asyncio.run(coro)


def make_context(experience=None) -> AIContext:
    profile = CandidateProfile(experience=experience or [])
    return AIContext(data={"candidate_profile": profile})


# ---------------------------------------------------------------------------
# Complete experience
# ---------------------------------------------------------------------------


def test_complete_experience_produces_full_intelligence():
    experience = [
        Experience(company="Acme", position="Junior Developer", start_date="Jan 2015", end_date="Dec 2017"),
        Experience(company="Acme", position="Senior Developer", start_date="Jan 2018", end_date="Jun 2021"),
        Experience(company="BetaSoft", position="Engineering Manager", start_date="Jul 2021", end_date="Present"),
    ]
    context = make_context(experience)
    engine = ExperienceIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.engine_name == "experience_intelligence"
    assert result.status == ExecutionStatus.SUCCESS
    assert 0.0 <= result.confidence <= 1.0
    output = result.output
    assert output["metrics"]["company_count"] == 2
    assert output["metrics"]["is_currently_employed"] is True
    assert output["seniority_level"] in {"Entry", "Junior", "Mid", "Senior", "Principal"}
    assert result.warnings == []


# ---------------------------------------------------------------------------
# Empty experience
# ---------------------------------------------------------------------------


def test_empty_experience_does_not_crash():
    context = make_context([])
    engine = ExperienceIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.status == ExecutionStatus.SUCCESS
    output = result.output
    assert output["timeline"]["entries"] == []
    assert output["metrics"]["total_experience_months"] == 0
    assert output["metrics"]["company_count"] == 0
    assert output["seniority_level"] == "Entry"
    assert output["progression"]["overall_trend"] == "unknown"
    assert output["gap_analysis"]["gap_count"] == 0


# ---------------------------------------------------------------------------
# One job
# ---------------------------------------------------------------------------


def test_one_job():
    experience = [Experience(company="Solo Co", position="Developer", start_date="Jan 2022", end_date="Present")]
    context = make_context(experience)
    engine = ExperienceIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["metrics"]["company_count"] == 1
    assert output["progression"]["moves"] == []
    assert output["progression"]["overall_trend"] == "stable"
    assert output["gap_analysis"]["gap_count"] == 0


# ---------------------------------------------------------------------------
# Multiple jobs
# ---------------------------------------------------------------------------


def test_multiple_jobs():
    experience = [
        Experience(company="A", position="Developer", start_date="Jan 2018", end_date="Dec 2019"),
        Experience(company="B", position="Developer", start_date="Jan 2020", end_date="Dec 2021"),
        Experience(company="C", position="Developer", start_date="Jan 2022", end_date="Present"),
    ]
    context = make_context(experience)
    engine = ExperienceIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert len(output["timeline"]["entries"]) == 3
    assert output["metrics"]["company_count"] == 3
    # chronological order: A, B, C
    companies_in_order = [e["company"] for e in output["timeline"]["entries"]]
    assert companies_in_order == ["A", "B", "C"]


# ---------------------------------------------------------------------------
# Promotions
# ---------------------------------------------------------------------------


def test_promotions_detected_as_growth():
    experience = [
        Experience(company="Acme", position="Junior Developer", start_date="Jan 2015", end_date="Dec 2017"),
        Experience(company="Acme", position="Senior Developer", start_date="Jan 2018", end_date="Present"),
    ]
    context = make_context(experience)
    engine = ExperienceIntelligenceEngine()

    result = run_async(engine.run(context))

    progression = result.output["progression"]
    assert progression["moves"][0]["move_type"] == "promotion"
    assert progression["overall_trend"] == "growth"


# ---------------------------------------------------------------------------
# Lateral moves
# ---------------------------------------------------------------------------


def test_lateral_moves_detected():
    experience = [
        Experience(company="A", position="Senior Engineer", start_date="Jan 2018", end_date="Dec 2019"),
        Experience(company="B", position="Senior Developer", start_date="Jan 2020", end_date="Present"),
    ]
    context = make_context(experience)
    engine = ExperienceIntelligenceEngine()

    result = run_async(engine.run(context))

    progression = result.output["progression"]
    assert progression["moves"][0]["move_type"] == "lateral_move"


# ---------------------------------------------------------------------------
# Employment gaps
# ---------------------------------------------------------------------------


def test_employment_gap_detected():
    experience = [
        Experience(company="A", position="Developer", start_date="Jan 2018", end_date="Dec 2019"),
        Experience(company="B", position="Developer", start_date="Jan 2021", end_date="Present"),
    ]
    context = make_context(experience)
    engine = ExperienceIntelligenceEngine()

    result = run_async(engine.run(context))

    gap_analysis = result.output["gap_analysis"]
    assert gap_analysis["gap_count"] == 1
    assert gap_analysis["gaps"][0]["gap_months"] == 12


# ---------------------------------------------------------------------------
# No gaps
# ---------------------------------------------------------------------------


def test_no_gaps_for_seamless_transitions():
    experience = [
        Experience(company="A", position="Developer", start_date="Jan 2018", end_date="Dec 2019"),
        Experience(company="B", position="Developer", start_date="Jan 2020", end_date="Present"),
    ]
    context = make_context(experience)
    engine = ExperienceIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.output["gap_analysis"]["gap_count"] == 0


# ---------------------------------------------------------------------------
# Current employment
# ---------------------------------------------------------------------------


def test_current_employment_flagged():
    experience = [Experience(company="A", position="Developer", start_date="Jan 2022", end_date="Present")]
    context = make_context(experience)
    engine = ExperienceIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.output["metrics"]["is_currently_employed"] is True
    assert result.output["timeline"]["entries"][0]["is_current"] is True


def test_no_current_employment_when_all_roles_ended():
    experience = [Experience(company="A", position="Developer", start_date="Jan 2018", end_date="Dec 2019")]
    context = make_context(experience)
    engine = ExperienceIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.output["metrics"]["is_currently_employed"] is False


# ---------------------------------------------------------------------------
# Seniority thresholds
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "years_of_experience,expected_level",
    [
        (0, "Entry"),
        (1, "Entry"),
        (3, "Junior"),
        (7, "Mid"),
        (12, "Senior"),
        (20, "Principal"),
    ],
)
def test_seniority_thresholds(years_of_experience, expected_level):
    # One long, cleanly-dated role spanning exactly N years.
    start_year = 2024 - years_of_experience
    experience = (
        [Experience(company="A", position="Developer", start_date=f"Jan {start_year}", end_date="Dec 2023")]
        if years_of_experience > 0
        else []
    )
    context = make_context(experience)
    engine = ExperienceIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.output["seniority_level"] == expected_level


# ---------------------------------------------------------------------------
# Stability analysis
# ---------------------------------------------------------------------------


def test_stability_high_for_long_tenures():
    experience = [Experience(company="A", position="Developer", start_date="Jan 2015", end_date="Dec 2023")]
    context = make_context(experience)
    engine = ExperienceIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.output["stability"]["stability_score"] == 1.0


def test_stability_low_for_short_tenures():
    experience = [
        Experience(company="A", position="Developer", start_date="Jan 2020", end_date="Apr 2020"),
        Experience(company="B", position="Developer", start_date="May 2020", end_date="Aug 2020"),
        Experience(company="C", position="Developer", start_date="Sep 2020", end_date="Dec 2020"),
    ]
    context = make_context(experience)
    engine = ExperienceIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.output["stability"]["stability_score"] < 0.5


# ---------------------------------------------------------------------------
# Missing candidate_profile
# ---------------------------------------------------------------------------


def test_missing_candidate_profile_key_raises_context_validation_exception():
    engine = ExperienceIntelligenceEngine()
    context = AIContext(data={})

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


# ---------------------------------------------------------------------------
# None candidate_profile
# ---------------------------------------------------------------------------


def test_none_candidate_profile_raises_context_validation_exception():
    engine = ExperienceIntelligenceEngine()
    context = AIContext(data={"candidate_profile": None})

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


# ---------------------------------------------------------------------------
# Wrong type
# ---------------------------------------------------------------------------


def test_wrong_type_candidate_profile_raises_context_validation_exception():
    engine = ExperienceIntelligenceEngine()
    context = AIContext(data={"candidate_profile": {"experience": []}})

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


# ---------------------------------------------------------------------------
# Registry integration
# ---------------------------------------------------------------------------


def test_registry_integration():
    registry = EngineRegistry()
    registry.register(ExperienceIntelligenceEngine())

    assert registry.is_registered("experience_intelligence")
    engine = registry.get("experience_intelligence")
    assert engine.name == "experience_intelligence"


# ---------------------------------------------------------------------------
# Orchestrator integration
# ---------------------------------------------------------------------------


def test_orchestrator_integration():
    registry = EngineRegistry()
    registry.register(ExperienceIntelligenceEngine())
    orchestrator = AIOrchestrator(registry)
    context = make_context([Experience(company="A", position="Developer", start_date="Jan 2020", end_date="Present")])

    workflow_result = run_async(orchestrator.run(context, ["experience_intelligence"]))

    assert workflow_result.workflow_id == context.workflow_id
    assert len(workflow_result.results) == 1
    assert workflow_result.results[0].engine_name == "experience_intelligence"


# ---------------------------------------------------------------------------
# Engine never mutates context.state
# ---------------------------------------------------------------------------


def test_engine_never_mutates_context_state_directly():
    context = make_context([Experience(company="A", position="Developer", start_date="Jan 2020", end_date="Present")])
    engine = ExperienceIntelligenceEngine()

    run_async(engine.run(context))

    assert context.state.workflow_status == WorkflowStatus.PENDING
    assert context.state.current_engine is None
    assert context.state.completed_engines == []
    assert context.state.progress == 0.0


def test_state_is_updated_when_run_through_orchestrator():
    registry = EngineRegistry()
    registry.register(ExperienceIntelligenceEngine())
    orchestrator = AIOrchestrator(registry)
    context = make_context([Experience(company="A", position="Developer", start_date="Jan 2020", end_date="Present")])

    run_async(orchestrator.run(context, ["experience_intelligence"]))

    assert context.state.workflow_status == WorkflowStatus.COMPLETED
    assert context.state.completed_engines == ["experience_intelligence"]


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


def test_performance_under_100ms():
    experience = [
        Experience(company="A", position="Junior Developer", start_date="Jan 2015", end_date="Dec 2016"),
        Experience(company="A", position="Developer", start_date="Jan 2017", end_date="Dec 2018"),
        Experience(company="B", position="Senior Developer", start_date="Jan 2019", end_date="Dec 2021"),
        Experience(company="C", position="Engineering Manager", start_date="Jan 2022", end_date="Present"),
    ]
    context = make_context(experience)
    engine = ExperienceIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.execution_time_ms is not None
    assert result.execution_time_ms < 100.0