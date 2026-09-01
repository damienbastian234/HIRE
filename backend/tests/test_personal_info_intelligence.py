"""
Unit tests for the Personal Info Intelligence engine (HIRE-AI-111).

Follows the same testing style as the other intelligence-engine tests:
plain `def test_...()` functions with `asyncio.run()` internally, rather
than adding a pytest-asyncio dependency (see test_candidate_matching.py,
test_education_intelligence.py, test_project_intelligence.py,
test_certification_intelligence.py, test_language_intelligence.py —
tests/test_resume_intelligence.py and tests/test_experience_intelligence.py
do not exist in this repository, confirmed during inspection).

PersonalInfo is a single object, not a list (unlike every prior
domain), so deduplication/first-seen-order/multi-record tests are not
applicable here and are replaced with field-presence tests instead.
"""

import asyncio
import json
import time

import pytest

from app.ai.context import AIContext
from app.ai.engines.personal_info_intelligence import PersonalInfoIntelligenceEngine
from app.ai.exceptions import ContextValidationException
from app.ai.orchestrator import AIOrchestrator
from app.ai.registry import EngineRegistry
from app.ai.result import ExecutionStatus
from app.models.candidate import CandidateProfile, PersonalInfo
from app.models.personal_info_intelligence import PersonalInfoIntelligence


def run_async(coro):
    """Run an async coroutine from a synchronous pytest test function."""
    return asyncio.run(coro)


def make_candidate(*, personal_info: PersonalInfo | None = None) -> CandidateProfile:
    return CandidateProfile(personal_info=personal_info or PersonalInfo())


def make_context(*, candidate_profile=None) -> AIContext:
    return AIContext(data={"candidate_profile": candidate_profile})


# ---------------------------------------------------------------------------
# Context validation
# ---------------------------------------------------------------------------


def test_missing_candidate_profile_key_raises_context_validation_exception():
    engine = PersonalInfoIntelligenceEngine()
    context = AIContext(data={})

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_none_candidate_profile_raises_context_validation_exception():
    engine = PersonalInfoIntelligenceEngine()
    context = make_context(candidate_profile=None)

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_wrong_candidate_profile_type_raises_context_validation_exception():
    engine = PersonalInfoIntelligenceEngine()
    context = make_context(candidate_profile={"personal_info": {}})

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_valid_candidate_profile_passes_context_validation():
    engine = PersonalInfoIntelligenceEngine()
    context = make_context(
        candidate_profile=make_candidate(
            personal_info=PersonalInfo(full_name="Jane Doe")
        )
    )

    result = run_async(engine.run(context))

    assert result.status == ExecutionStatus.SUCCESS


# ---------------------------------------------------------------------------
# Empty / basic data
# ---------------------------------------------------------------------------


def test_empty_personal_info():
    context = make_context(
        candidate_profile=make_candidate(personal_info=PersonalInfo())
    )
    engine = PersonalInfoIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["provided_fields"] == []
    assert output["provided_field_count"] == 0
    assert output["missing_fields"] == [
        "full_name",
        "email",
        "phone",
        "linkedin_url",
        "github_url",
        "portfolio_url",
        "location",
    ]


def test_one_field_populated():
    context = make_context(
        candidate_profile=make_candidate(personal_info=PersonalInfo(email="jane@example.com"))
    )
    engine = PersonalInfoIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["provided_fields"] == ["email"]
    assert output["provided_field_count"] == 1
    assert "email" not in output["missing_fields"]


def test_multiple_fields_populated():
    context = make_context(
        candidate_profile=make_candidate(
            personal_info=PersonalInfo(
                full_name="Jane Doe", email="jane@example.com", location="Bengaluru"
            )
        )
    )
    engine = PersonalInfoIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["provided_fields"] == ["full_name", "email", "location"]
    assert output["provided_field_count"] == 3


def test_all_fields_populated():
    context = make_context(
        candidate_profile=make_candidate(
            personal_info=PersonalInfo(
                full_name="Jane Doe",
                email="jane@example.com",
                phone="+1 555-123-4567",
                linkedin_url="linkedin.com/in/janedoe",
                github_url="github.com/janedoe",
                portfolio_url="janedoe.dev",
                location="Bengaluru",
            )
        )
    )
    engine = PersonalInfoIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["provided_field_count"] == 7
    assert output["missing_fields"] == []


# ---------------------------------------------------------------------------
# Incomplete / whitespace data
# ---------------------------------------------------------------------------


def test_whitespace_only_value_treated_as_missing():
    context = make_context(
        candidate_profile=make_candidate(personal_info=PersonalInfo(full_name="   "))
    )
    engine = PersonalInfoIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert "full_name" not in output["provided_fields"]
    assert "full_name" in output["missing_fields"]


def test_provided_and_missing_fields_preserve_declaration_order():
    context = make_context(
        candidate_profile=make_candidate(
            personal_info=PersonalInfo(
                email="jane@example.com", github_url="github.com/jane"
            )
        )
    )
    engine = PersonalInfoIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["provided_fields"] == ["email", "github_url"]
    assert output["missing_fields"] == [
        "full_name",
        "phone",
        "linkedin_url",
        "portfolio_url",
        "location",
    ]


def test_provided_field_count_matches_provided_fields_length():
    context = make_context(
        candidate_profile=make_candidate(
            personal_info=PersonalInfo(full_name="Jane Doe", phone="555-1234")
        )
    )
    engine = PersonalInfoIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["provided_field_count"] == len(output["provided_fields"])


# ---------------------------------------------------------------------------
# No invented intelligence
# ---------------------------------------------------------------------------


def test_raw_contact_values_are_not_reproduced_in_output():
    """The engine reports field presence only — it must never re-expose
    the underlying email/phone/URL values, since that would be
    duplication, not derived intelligence."""
    context = make_context(
        candidate_profile=make_candidate(
            personal_info=PersonalInfo(
                email="jane@example.com", phone="555-1234", location="Bengaluru"
            )
        )
    )
    engine = PersonalInfoIntelligenceEngine()

    result = run_async(engine.run(context))

    serialized = json.dumps(result.output)
    assert "jane@example.com" not in serialized
    assert "555-1234" not in serialized
    assert "Bengaluru" not in serialized


def test_no_primary_contact_method_field_is_invented():
    """PersonalInfo has no ordering/importance signal, so no 'primary
    contact method' or similar ranking field should be produced."""
    context = make_context(
        candidate_profile=make_candidate(
            personal_info=PersonalInfo(email="jane@example.com", phone="555-1234")
        )
    )
    engine = PersonalInfoIntelligenceEngine()

    result = run_async(engine.run(context))

    assert "primary_contact" not in result.output
    assert "primary_contact_method" not in result.output
    assert "preferred_contact" not in result.output


def test_no_professional_link_grouping_is_invented():
    """The schema does not group linkedin_url/github_url/portfolio_url
    into a category; no such grouping should appear in the output."""
    context = make_context(
        candidate_profile=make_candidate(
            personal_info=PersonalInfo(linkedin_url="linkedin.com/in/jane")
        )
    )
    engine = PersonalInfoIntelligenceEngine()

    result = run_async(engine.run(context))

    assert "has_professional_links" not in result.output
    assert "professional_links" not in result.output


# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------


def test_result_is_intelligence_result_with_correct_engine_name():
    context = make_context(
        candidate_profile=make_candidate(
            personal_info=PersonalInfo(full_name="Jane Doe")
        )
    )
    engine = PersonalInfoIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.engine_name == "personal_info_intelligence"
    assert result.status == ExecutionStatus.SUCCESS


def test_output_is_json_serializable():
    context = make_context(
        candidate_profile=make_candidate(
            personal_info=PersonalInfo(full_name="Jane Doe")
        )
    )
    engine = PersonalInfoIntelligenceEngine()

    result = run_async(engine.run(context))

    serialized = json.dumps(result.output)
    assert isinstance(serialized, str)


def test_output_can_be_reconstructed_as_personal_info_intelligence():
    context = make_context(
        candidate_profile=make_candidate(
            personal_info=PersonalInfo(full_name="Jane Doe")
        )
    )
    engine = PersonalInfoIntelligenceEngine()

    result = run_async(engine.run(context))
    reconstructed = PersonalInfoIntelligence.model_validate(result.output)

    assert reconstructed.provided_fields == ["full_name"]
    assert reconstructed.provided_field_count == 1


def test_output_contains_expected_required_fields():
    context = make_context(
        candidate_profile=make_candidate(
            personal_info=PersonalInfo(full_name="Jane Doe")
        )
    )
    engine = PersonalInfoIntelligenceEngine()

    result = run_async(engine.run(context))

    for field in ("provided_fields", "missing_fields", "provided_field_count"):
        assert field in result.output


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------


def test_confidence_is_between_0_and_1():
    context = make_context(
        candidate_profile=make_candidate(
            personal_info=PersonalInfo(full_name="Jane Doe")
        )
    )
    engine = PersonalInfoIntelligenceEngine()

    result = run_async(engine.run(context))

    assert 0.0 <= result.confidence <= 1.0


def test_empty_personal_info_produces_zero_confidence():
    context = make_context(
        candidate_profile=make_candidate(personal_info=PersonalInfo())
    )
    engine = PersonalInfoIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.confidence == 0.0


def test_complete_personal_info_produces_full_confidence():
    context = make_context(
        candidate_profile=make_candidate(
            personal_info=PersonalInfo(
                full_name="Jane Doe",
                email="jane@example.com",
                phone="555-1234",
                linkedin_url="linkedin.com/in/jane",
                github_url="github.com/jane",
                portfolio_url="jane.dev",
                location="Bengaluru",
            )
        )
    )
    engine = PersonalInfoIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.confidence == 1.0


def test_incomplete_personal_info_produces_proportional_confidence():
    context = make_context(
        candidate_profile=make_candidate(
            personal_info=PersonalInfo(full_name="Jane Doe", email="jane@example.com")
        )
    )
    engine = PersonalInfoIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.confidence == round(2 / 7, 4)


def test_confidence_does_not_depend_on_which_fields_are_present():
    """Every field is weighted equally — two different but
    equal-sized sets of populated fields must produce identical
    confidence."""
    context_a = make_context(
        candidate_profile=make_candidate(
            personal_info=PersonalInfo(full_name="Jane Doe", email="jane@example.com")
        )
    )
    context_b = make_context(
        candidate_profile=make_candidate(
            personal_info=PersonalInfo(portfolio_url="jane.dev", location="Bengaluru")
        )
    )
    engine = PersonalInfoIntelligenceEngine()

    result_a = run_async(engine.run(context_a))
    result_b = run_async(engine.run(context_b))

    assert result_a.confidence == result_b.confidence


# ---------------------------------------------------------------------------
# Framework integration
# ---------------------------------------------------------------------------


def test_engine_integrates_with_registry():
    registry = EngineRegistry()
    registry.register(PersonalInfoIntelligenceEngine())

    assert registry.is_registered("personal_info_intelligence") is True
    engine_name = registry.get("personal_info_intelligence").name
    assert engine_name == "personal_info_intelligence"


def test_engine_integrates_with_orchestrator():
    registry = EngineRegistry()
    registry.register(PersonalInfoIntelligenceEngine())
    orchestrator = AIOrchestrator(registry)
    context = make_context(
        candidate_profile=make_candidate(
            personal_info=PersonalInfo(full_name="Jane Doe")
        )
    )

    workflow_result = run_async(
        orchestrator.run(context, ["personal_info_intelligence"])
    )

    assert len(workflow_result.results) == 1
    assert workflow_result.results[0].engine_name == "personal_info_intelligence"


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


def test_performance_1000_executions_under_100ms():
    """1000 sequential engine executions against an already-constructed
    CandidateProfile stay comfortably under 100ms, matching the
    performance convention established in prior intelligence-engine
    tests. This engine's processing is a fixed 7-field presence check,
    so the same <100ms target legitimately applies with no adjustment."""
    context = make_context(
        candidate_profile=make_candidate(
            personal_info=PersonalInfo(full_name="Jane Doe", email="jane@example.com")
        )
    )
    engine = PersonalInfoIntelligenceEngine()

    async def run_many() -> float:
        start = time.perf_counter()
        for _ in range(1000):
            await engine.run(context)
        return time.perf_counter() - start

    elapsed_seconds = run_async(run_many())

    assert elapsed_seconds < 0.1