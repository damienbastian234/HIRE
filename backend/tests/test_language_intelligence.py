"""
Unit tests for the Language Intelligence engine (HIRE-AI-110).

Follows the same testing style as the other intelligence-engine tests:
plain `def test_...()` functions with `asyncio.run()` internally, rather
than adding a pytest-asyncio dependency (see test_candidate_matching.py,
test_education_intelligence.py, test_project_intelligence.py,
test_certification_intelligence.py — tests/test_skill_intelligence.py
does not exist in this repository, so those four are the relevant
conventions followed here).
"""

import asyncio
import json
import time

import pytest

from app.ai.context import AIContext
from app.ai.engines.language_intelligence import LanguageIntelligenceEngine
from app.ai.exceptions import ContextValidationException
from app.ai.orchestrator import AIOrchestrator
from app.ai.registry import EngineRegistry
from app.ai.result import ExecutionStatus
from app.models.candidate import CandidateProfile
from app.models.language_intelligence import LanguageIntelligence


def run_async(coro):
    """Run an async coroutine from a synchronous pytest test function."""
    return asyncio.run(coro)


def make_candidate(*, languages: list[str] | None = None) -> CandidateProfile:
    return CandidateProfile(
        personal_info={"full_name": "Jane Doe"},
        languages=languages or [],
    )


def make_context(*, candidate_profile=None) -> AIContext:
    return AIContext(data={"candidate_profile": candidate_profile})


# ---------------------------------------------------------------------------
# Context validation
# ---------------------------------------------------------------------------


def test_missing_candidate_profile_key_raises_context_validation_exception():
    engine = LanguageIntelligenceEngine()
    context = AIContext(data={})

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_none_candidate_profile_raises_context_validation_exception():
    engine = LanguageIntelligenceEngine()
    context = make_context(candidate_profile=None)

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_wrong_candidate_profile_type_raises_context_validation_exception():
    engine = LanguageIntelligenceEngine()
    context = make_context(candidate_profile={"languages": ["English"]})

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_valid_candidate_profile_passes_context_validation():
    engine = LanguageIntelligenceEngine()
    context = make_context(candidate_profile=make_candidate(languages=["English"]))

    result = run_async(engine.run(context))

    assert result.status == ExecutionStatus.SUCCESS


# ---------------------------------------------------------------------------
# Language data
# ---------------------------------------------------------------------------


def test_empty_language_list():
    context = make_context(candidate_profile=make_candidate(languages=[]))
    engine = LanguageIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["language_count"] == 0
    assert output["languages"] == []


def test_one_language():
    context = make_context(candidate_profile=make_candidate(languages=["English"]))
    engine = LanguageIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["language_count"] == 1
    assert output["languages"] == ["English"]


def test_multiple_languages():
    context = make_context(
        candidate_profile=make_candidate(languages=["English", "Spanish", "French"])
    )
    engine = LanguageIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["language_count"] == 3
    assert output["languages"] == ["English", "Spanish", "French"]


def test_duplicate_language_names_are_deduplicated():
    context = make_context(
        candidate_profile=make_candidate(languages=["English", "English"])
    )
    engine = LanguageIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["language_count"] == 1
    assert output["languages"] == ["English"]


def test_case_insensitive_duplicates_preserve_first_seen_casing():
    context = make_context(
        candidate_profile=make_candidate(languages=["Python", "python", "PYTHON"])
    )
    engine = LanguageIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["language_count"] == 1
    assert output["languages"] == ["Python"]


def test_whitespace_around_values_is_trimmed():
    context = make_context(
        candidate_profile=make_candidate(languages=["  English  ", " Spanish"])
    )
    engine = LanguageIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["languages"] == ["English", "Spanish"]


def test_whitespace_only_values_are_treated_as_absent():
    context = make_context(candidate_profile=make_candidate(languages=["   ", ""]))
    engine = LanguageIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["language_count"] == 0
    assert output["languages"] == []


def test_incomplete_language_records_are_handled_gracefully():
    """A mix of valid and blank entries must not crash the engine."""
    context = make_context(
        candidate_profile=make_candidate(languages=["English", "", "  ", "Spanish"])
    )
    engine = LanguageIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["language_count"] == 2
    assert output["languages"] == ["English", "Spanish"]


def test_no_semantic_normalization_is_applied():
    """Per the ticket, no alias mapping (e.g. names to ISO codes) is
    applied — distinct spellings remain distinct entries."""
    context = make_context(
        candidate_profile=make_candidate(languages=["English", "British English"])
    )
    engine = LanguageIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.output["languages"] == ["English", "British English"]


# ---------------------------------------------------------------------------
# No invented proficiency / primary-language fields
# ---------------------------------------------------------------------------


def test_output_does_not_contain_a_proficiency_field():
    """CandidateProfile.languages is a plain list[str] with no
    proficiency/level information anywhere in the schema; the output
    must not invent one."""
    context = make_context(candidate_profile=make_candidate(languages=["English"]))
    engine = LanguageIntelligenceEngine()

    result = run_async(engine.run(context))

    assert "proficiency" not in result.output
    assert "level" not in result.output
    assert "fluency" not in result.output


def test_output_does_not_contain_a_primary_language_field():
    """No deterministic ordering signal exists (no date, no
    proficiency), so no primary/most-relevant language field is
    produced."""
    context = make_context(
        candidate_profile=make_candidate(languages=["English", "Spanish"])
    )
    engine = LanguageIntelligenceEngine()

    result = run_async(engine.run(context))

    assert "primary_language" not in result.output
    assert "most_relevant_language" not in result.output


# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------


def test_result_is_intelligence_result_with_correct_engine_name():
    context = make_context(candidate_profile=make_candidate(languages=["English"]))
    engine = LanguageIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.engine_name == "language_intelligence"
    assert result.status == ExecutionStatus.SUCCESS


def test_output_is_json_serializable():
    context = make_context(
        candidate_profile=make_candidate(languages=["English", "Spanish"])
    )
    engine = LanguageIntelligenceEngine()

    result = run_async(engine.run(context))

    serialized = json.dumps(result.output)
    assert isinstance(serialized, str)


def test_output_can_be_reconstructed_as_language_intelligence():
    context = make_context(
        candidate_profile=make_candidate(languages=["English", "Spanish"])
    )
    engine = LanguageIntelligenceEngine()

    result = run_async(engine.run(context))
    reconstructed = LanguageIntelligence.model_validate(result.output)

    assert reconstructed.languages == ["English", "Spanish"]
    assert reconstructed.language_count == 2


def test_output_contains_expected_required_fields():
    context = make_context(candidate_profile=make_candidate(languages=["English"]))
    engine = LanguageIntelligenceEngine()

    result = run_async(engine.run(context))

    for field in ("language_count", "languages"):
        assert field in result.output


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------


def test_confidence_is_between_0_and_1():
    context = make_context(candidate_profile=make_candidate(languages=["English"]))
    engine = LanguageIntelligenceEngine()

    result = run_async(engine.run(context))

    assert 0.0 <= result.confidence <= 1.0


def test_empty_language_data_produces_zero_confidence():
    context = make_context(candidate_profile=make_candidate(languages=[]))
    engine = LanguageIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.confidence == 0.0


def test_complete_language_data_produces_full_confidence():
    context = make_context(
        candidate_profile=make_candidate(languages=["English", "Spanish"])
    )
    engine = LanguageIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.confidence == 1.0


def test_partially_blank_entries_produce_proportional_confidence():
    context = make_context(
        candidate_profile=make_candidate(languages=["English", "", "Spanish", "   "])
    )
    engine = LanguageIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.confidence == 0.5


def test_confidence_does_not_increase_merely_from_more_languages():
    """Confidence measures extraction completeness, not how many
    languages the candidate speaks."""
    one_language = make_context(candidate_profile=make_candidate(languages=["English"]))
    five_languages = make_context(
        candidate_profile=make_candidate(
            languages=["English", "Spanish", "French", "German", "Italian"]
        )
    )
    engine = LanguageIntelligenceEngine()

    one_result = run_async(engine.run(one_language))
    five_result = run_async(engine.run(five_languages))

    assert one_result.confidence == five_result.confidence == 1.0


# ---------------------------------------------------------------------------
# Framework integration
# ---------------------------------------------------------------------------


def test_engine_integrates_with_registry():
    registry = EngineRegistry()
    registry.register(LanguageIntelligenceEngine())

    assert registry.is_registered("language_intelligence") is True
    engine_name = registry.get("language_intelligence").name
    assert engine_name == "language_intelligence"


def test_engine_integrates_with_orchestrator():
    registry = EngineRegistry()
    registry.register(LanguageIntelligenceEngine())
    orchestrator = AIOrchestrator(registry)
    context = make_context(candidate_profile=make_candidate(languages=["English"]))

    workflow_result = run_async(orchestrator.run(context, ["language_intelligence"]))

    assert len(workflow_result.results) == 1
    assert workflow_result.results[0].engine_name == "language_intelligence"


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


def test_performance_1000_executions_under_100ms():
    """1000 sequential engine executions against an already-constructed
    CandidateProfile stay comfortably under 100ms, matching the
    performance convention established in
    test_education_intelligence.py / test_project_intelligence.py /
    test_certification_intelligence.py. No network, external APIs, or
    timing-sensitive external systems are involved."""
    context = make_context(
        candidate_profile=make_candidate(languages=["English", "Spanish"])
    )
    engine = LanguageIntelligenceEngine()

    async def run_many() -> float:
        start = time.perf_counter()
        for _ in range(1000):
            await engine.run(context)
        return time.perf_counter() - start

    elapsed_seconds = run_async(run_many())

    assert elapsed_seconds < 0.1