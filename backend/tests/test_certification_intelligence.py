"""
Unit tests for the Certification Intelligence engine (HIRE-AI-109).

Follows the same testing style as the other intelligence-engine tests:
plain `def test_...()` functions with `asyncio.run()` internally, rather
than adding a pytest-asyncio dependency (see test_candidate_matching.py,
test_education_intelligence.py, test_project_intelligence.py).
"""

import asyncio
import json
import time

import pytest

from app.ai.context import AIContext
from app.ai.engines.certification_intelligence import CertificationIntelligenceEngine
from app.ai.exceptions import ContextValidationException
from app.ai.orchestrator import AIOrchestrator
from app.ai.registry import EngineRegistry
from app.ai.result import ExecutionStatus
from app.models.candidate import CandidateProfile, Certification
from app.models.certification_intelligence import CertificationIntelligence


def run_async(coro):
    """Run an async coroutine from a synchronous pytest test function."""
    return asyncio.run(coro)


def make_candidate(
    *, certifications: list[Certification] | None = None
) -> CandidateProfile:
    return CandidateProfile(
        personal_info={"full_name": "Jane Doe"},
        certifications=certifications or [],
    )


def make_context(*, candidate_profile=None) -> AIContext:
    return AIContext(data={"candidate_profile": candidate_profile})


# ---------------------------------------------------------------------------
# Context validation
# ---------------------------------------------------------------------------


def test_missing_candidate_profile_key_raises_context_validation_exception():
    engine = CertificationIntelligenceEngine()
    context = AIContext(data={})

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_none_candidate_profile_raises_context_validation_exception():
    engine = CertificationIntelligenceEngine()
    context = make_context(candidate_profile=None)

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_wrong_candidate_profile_type_raises_context_validation_exception():
    engine = CertificationIntelligenceEngine()
    context = make_context(candidate_profile={"certifications": []})

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_valid_candidate_profile_passes_context_validation():
    engine = CertificationIntelligenceEngine()
    context = make_context(
        candidate_profile=make_candidate(
            certifications=[Certification(name="AWS Certified Developer")]
        )
    )

    result = run_async(engine.run(context))

    assert result.status == ExecutionStatus.SUCCESS


# ---------------------------------------------------------------------------
# Certification data — counts, single/multiple, dedup
# ---------------------------------------------------------------------------


def test_empty_certification_list():
    context = make_context(candidate_profile=make_candidate(certifications=[]))
    engine = CertificationIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["certification_count"] == 0
    assert output["certification_names"] == []
    assert output["issuing_organizations"] == []
    assert output["most_recent_certification"] is None


def test_single_certification():
    context = make_context(
        candidate_profile=make_candidate(
            certifications=[
                Certification(
                    name="AWS Certified Developer",
                    organization="Amazon",
                    completion_date="2022",
                )
            ]
        )
    )
    engine = CertificationIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["certification_count"] == 1
    assert output["certification_names"] == ["AWS Certified Developer"]
    assert output["issuing_organizations"] == ["Amazon"]
    assert output["most_recent_certification"] == "AWS Certified Developer"


def test_multiple_certifications():
    context = make_context(
        candidate_profile=make_candidate(
            certifications=[
                Certification(name="Cert A", organization="Org A"),
                Certification(name="Cert B", organization="Org B"),
            ]
        )
    )
    engine = CertificationIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["certification_count"] == 2
    assert output["certification_names"] == ["Cert A", "Cert B"]
    assert output["issuing_organizations"] == ["Org A", "Org B"]


# ---------------------------------------------------------------------------
# Most recent certification (deterministic, recency-based)
# ---------------------------------------------------------------------------


def test_most_recent_certification_picks_latest_completion_date():
    context = make_context(
        candidate_profile=make_candidate(
            certifications=[
                Certification(name="Cert A", completion_date="2018"),
                Certification(name="Cert B", completion_date="2022"),
                Certification(name="Cert C", completion_date="2015"),
            ]
        )
    )
    engine = CertificationIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.output["most_recent_certification"] == "Cert B"


def test_most_recent_certification_falls_back_to_first_entry_without_dates():
    context = make_context(
        candidate_profile=make_candidate(
            certifications=[
                Certification(name="Cert A"),
                Certification(name="Cert B"),
            ]
        )
    )
    engine = CertificationIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.output["most_recent_certification"] == "Cert A"


def test_most_recent_certification_is_none_when_no_name_present():
    context = make_context(
        candidate_profile=make_candidate(
            certifications=[
                Certification(organization="Amazon", completion_date="2020")
            ]
        )
    )
    engine = CertificationIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.output["most_recent_certification"] is None


def test_most_recent_certification_does_not_privilege_recognized_names():
    """No hardcoded certification-name ranking exists; an unusual/unknown
    certification name must be treated identically to a well-known one —
    recency is the only signal used."""
    context = make_context(
        candidate_profile=make_candidate(
            certifications=[
                Certification(
                    name="AWS Certified Solutions Architect",
                    completion_date="2015",
                ),
                Certification(
                    name="Basic First Aid Certificate", completion_date="2021"
                ),
            ]
        )
    )
    engine = CertificationIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.output["most_recent_certification"] == "Basic First Aid Certificate"


def test_unresolvable_completion_date_is_ignored_for_ranking():
    context = make_context(
        candidate_profile=make_candidate(
            certifications=[
                Certification(name="Cert A", completion_date="not-a-year"),
                Certification(name="Cert B", completion_date="2020"),
            ]
        )
    )
    engine = CertificationIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.output["most_recent_certification"] == "Cert B"


# ---------------------------------------------------------------------------
# Incomplete / missing / whitespace / duplicate edge cases
# ---------------------------------------------------------------------------


def test_certification_with_all_optional_fields_missing():
    context = make_context(
        candidate_profile=make_candidate(certifications=[Certification()])
    )
    engine = CertificationIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["certification_count"] == 1
    assert output["certification_names"] == []
    assert output["issuing_organizations"] == []
    assert output["most_recent_certification"] is None


def test_incomplete_certification_records_are_handled_gracefully():
    context = make_context(
        candidate_profile=make_candidate(
            certifications=[
                Certification(name="Cert A"),
                Certification(organization="Org Only"),
                Certification(completion_date="2019"),
            ]
        )
    )
    engine = CertificationIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["certification_count"] == 3
    assert output["certification_names"] == ["Cert A"]
    assert output["issuing_organizations"] == ["Org Only"]


def test_duplicate_certification_names_are_deduplicated_case_insensitively():
    context = make_context(
        candidate_profile=make_candidate(
            certifications=[
                Certification(name="AWS Certified Developer", organization="Amazon"),
                Certification(name="aws certified developer", organization="Amazon"),
            ]
        )
    )
    engine = CertificationIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["certification_count"] == 2
    assert output["certification_names"] == ["AWS Certified Developer"]
    assert output["issuing_organizations"] == ["Amazon"]


def test_semantically_similar_names_are_not_normalized():
    """Per the ticket, certification names/organizations are never
    semantically reinterpreted — only exact (case-insensitive,
    whitespace-trimmed) duplicates collapse."""
    context = make_context(
        candidate_profile=make_candidate(
            certifications=[
                Certification(name="AWS Certified Developer"),
                Certification(name="AWS Developer Certification"),
            ]
        )
    )
    engine = CertificationIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.output["certification_names"] == [
        "AWS Certified Developer",
        "AWS Developer Certification",
    ]


def test_whitespace_is_trimmed_from_names_and_organizations():
    context = make_context(
        candidate_profile=make_candidate(
            certifications=[Certification(name="  Cert A  ", organization="  Org A  ")]
        )
    )
    engine = CertificationIntelligenceEngine()

    result = run_async(engine.run(context))

    output = result.output
    assert output["certification_names"] == ["Cert A"]
    assert output["issuing_organizations"] == ["Org A"]


def test_whitespace_only_name_is_treated_as_absent():
    context = make_context(
        candidate_profile=make_candidate(certifications=[Certification(name="   ")])
    )
    engine = CertificationIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.output["certification_names"] == []


# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------


def test_result_is_intelligence_result_with_correct_engine_name():
    context = make_context(
        candidate_profile=make_candidate(certifications=[Certification(name="Cert A")])
    )
    engine = CertificationIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.engine_name == "certification_intelligence"
    assert result.status == ExecutionStatus.SUCCESS


def test_output_is_json_serializable():
    context = make_context(
        candidate_profile=make_candidate(
            certifications=[Certification(name="Cert A", organization="Org A")]
        )
    )
    engine = CertificationIntelligenceEngine()

    result = run_async(engine.run(context))

    serialized = json.dumps(result.output)
    assert isinstance(serialized, str)


def test_output_can_be_reconstructed_as_certification_intelligence():
    context = make_context(
        candidate_profile=make_candidate(
            certifications=[Certification(name="Cert A", organization="Org A")]
        )
    )
    engine = CertificationIntelligenceEngine()

    result = run_async(engine.run(context))
    reconstructed = CertificationIntelligence.model_validate(result.output)

    assert reconstructed.certification_names == ["Cert A"]
    assert reconstructed.issuing_organizations == ["Org A"]


def test_output_contains_expected_required_fields():
    context = make_context(
        candidate_profile=make_candidate(certifications=[Certification(name="Cert A")])
    )
    engine = CertificationIntelligenceEngine()

    result = run_async(engine.run(context))

    for field in (
        "certification_count",
        "certification_names",
        "issuing_organizations",
        "most_recent_certification",
    ):
        assert field in result.output


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------


def test_confidence_is_between_0_and_1():
    context = make_context(
        candidate_profile=make_candidate(
            certifications=[
                Certification(
                    name="Cert A", organization="Org A", completion_date="2020"
                )
            ]
        )
    )
    engine = CertificationIntelligenceEngine()

    result = run_async(engine.run(context))

    assert 0.0 <= result.confidence <= 1.0


def test_empty_certification_data_produces_zero_confidence():
    context = make_context(candidate_profile=make_candidate(certifications=[]))
    engine = CertificationIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.confidence == 0.0


def test_complete_certification_data_produces_full_confidence():
    context = make_context(
        candidate_profile=make_candidate(
            certifications=[
                Certification(
                    name="Cert A", organization="Org A", completion_date="2020"
                )
            ]
        )
    )
    engine = CertificationIntelligenceEngine()

    result = run_async(engine.run(context))

    assert result.confidence == 1.0


def test_incomplete_records_produce_proportionally_lower_confidence():
    context = make_context(
        candidate_profile=make_candidate(certifications=[Certification(name="Cert A")])
    )
    engine = CertificationIntelligenceEngine()

    result = run_async(engine.run(context))

    assert 0.0 < result.confidence < 1.0


def test_confidence_does_not_increase_merely_from_more_certifications():
    """Confidence measures extraction completeness, not certification
    count or prestige — a single complete record and a large but sparse
    list must not be judged by volume."""
    single_complete = make_context(
        candidate_profile=make_candidate(
            certifications=[
                Certification(
                    name="Cert A", organization="Org A", completion_date="2020"
                )
            ]
        )
    )
    many_sparse = make_context(
        candidate_profile=make_candidate(
            certifications=[Certification(name=f"Cert {i}") for i in range(10)]
        )
    )
    engine = CertificationIntelligenceEngine()

    complete_result = run_async(engine.run(single_complete))
    sparse_result = run_async(engine.run(many_sparse))

    assert complete_result.confidence == 1.0
    assert sparse_result.confidence < complete_result.confidence


# ---------------------------------------------------------------------------
# Framework integration
# ---------------------------------------------------------------------------


def test_engine_integrates_with_registry():
    registry = EngineRegistry()
    registry.register(CertificationIntelligenceEngine())

    assert registry.is_registered("certification_intelligence") is True
    engine_name = registry.get("certification_intelligence").name
    assert engine_name == "certification_intelligence"


def test_engine_integrates_with_orchestrator():
    registry = EngineRegistry()
    registry.register(CertificationIntelligenceEngine())
    orchestrator = AIOrchestrator(registry)
    context = make_context(
        candidate_profile=make_candidate(certifications=[Certification(name="Cert A")])
    )

    workflow_result = run_async(
        orchestrator.run(context, ["certification_intelligence"])
    )

    assert len(workflow_result.results) == 1
    assert workflow_result.results[0].engine_name == "certification_intelligence"


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


def test_performance_1000_executions_under_100ms():
    """1000 sequential engine executions against an already-constructed
    CandidateProfile stay comfortably under 100ms, matching the
    performance convention established in
    test_education_intelligence.py / test_project_intelligence.py."""
    context = make_context(
        candidate_profile=make_candidate(
            certifications=[
                Certification(
                    name="Cert A", organization="Org A", completion_date="2020"
                )
            ]
        )
    )
    engine = CertificationIntelligenceEngine()

    async def run_many() -> float:
        start = time.perf_counter()
        for _ in range(1000):
            await engine.run(context)
        return time.perf_counter() - start

    elapsed_seconds = run_async(run_many())

    assert elapsed_seconds < 0.1