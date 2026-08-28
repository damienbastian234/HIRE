"""
Certification Intelligence engine (HIRE-AI-109).

Consumes the CandidateProfile produced by HIRE-AI-102 (specifically
its `certifications` field) and produces deterministic certification
intelligence for downstream systems.

This engine does not parse resumes — that is exclusively HIRE-AI-102's
responsibility — and it does not invent certification prestige,
validity, or difficulty rankings that CandidateProfile's
`Certification` model does not already capture (see
app/models/candidate.py: Certification has only free-text `name`,
free-text `organization`, and `completion_date` — no credential ID,
URL, expiry date, or skill tag). It never mutates `context.state`;
that remains the AIOrchestrator's exclusive responsibility (see
app.ai.context.WorkflowState).
"""


from collections.abc import Iterable

from app.ai.base_engine import BaseEngine
from app.ai.context import AIContext
from app.ai.exceptions import ContextValidationException, EngineExecutionException
from app.ai.result import ExecutionStatus, IntelligenceResult
from app.core.logging import get_logger
from app.models.candidate import CandidateProfile, Certification
from app.models.certification_intelligence import CertificationIntelligence

logger = get_logger(__name__)

# Weights for the deterministic, extraction-completeness confidence
# score. Must sum to 1.0. Mirrors the stage-completeness pattern used
# by EducationIntelligenceEngine / ProjectIntelligenceEngine: these
# scores measure how much of the available certification data could
# be extracted, not how prestigious or valuable the candidate's
# certifications are.
_CONFIDENCE_WEIGHTS: dict[str, float] = {
    "most_recent_certification": 0.30,
    "name_extraction": 0.40,
    "organization_extraction": 0.30,
}


class CertificationIntelligenceEngine(BaseEngine):
    """
    Transforms `context.data["candidate_profile"]` (a CandidateProfile)
    into structured CertificationIntelligence, analyzing only its
    `certifications` field.

    Kept as a single self-contained engine (no per-stage helper
    package, following the precedent set by
    EducationIntelligenceEngine and ProjectIntelligenceEngine over
    Skill/Experience Intelligence's multi-module pipelines):
    Certification's schema is thin (name, organization,
    completion_date only), so there is no multi-stage pipeline to
    decompose into swappable components.
    """

    def __init__(self) -> None:
        super().__init__(name="certification_intelligence")

    def validate_context(self, context: AIContext) -> None:
        """
        Ensure `context.data["candidate_profile"]` is present and is a
        CandidateProfile instance.
        """
        if "candidate_profile" not in context.data:
            raise ContextValidationException(
                "CertificationIntelligenceEngine requires "
                "'candidate_profile' in context.data."
            )
        profile = context.data["candidate_profile"]
        if profile is None:
            raise ContextValidationException(
                "'candidate_profile' in context.data must not be None."
            )
        if not isinstance(profile, CandidateProfile):
            raise ContextValidationException(
                "'candidate_profile' in context.data must be a "
                "CandidateProfile instance."
            )

    async def execute(self, context: AIContext) -> IntelligenceResult:
        """
        Build CertificationIntelligence from the candidate's
        certification records and return an IntelligenceResult.

        Any failure during processing is caught and re-raised as an
        EngineExecutionException; no raw exception escapes this engine.
        """
        profile: CandidateProfile = context.data["candidate_profile"]

        try:
            intelligence, confidence = self._build_certification_intelligence(
                profile
            )
        except Exception as exc:
            logger.exception(
                "Certification intelligence processing failed unexpectedly."
            )
            raise EngineExecutionException(
                "Certification Intelligence failed to process the "
                "candidate's certifications."
            ) from exc

        logger.info(
            "Certification intelligence completed. certification_count=%d "
            "most_recent_certification=%s confidence=%.2f",
            intelligence.certification_count,
            intelligence.most_recent_certification,
            confidence,
        )

        return IntelligenceResult(
            engine_name=self.name,
            status=ExecutionStatus.SUCCESS,
            confidence=confidence,
            output=intelligence.model_dump(),
            warnings=[],
        )

    def _build_certification_intelligence(
        self, profile: CandidateProfile
    ) -> tuple[CertificationIntelligence, float]:
        """Aggregate the candidate's certification records into
        CertificationIntelligence."""
        certifications = profile.certifications

        certification_names = self._deduplicate(
            c.name for c in certifications if c.name
        )
        issuing_organizations = self._deduplicate(
            c.organization for c in certifications if c.organization
        )
        most_recent_certification = self._determine_most_recent_certification(
            certifications
        )

        intelligence = CertificationIntelligence(
            certification_count=len(certifications),
            certification_names=certification_names,
            issuing_organizations=issuing_organizations,
            most_recent_certification=most_recent_certification,
        )

        confidence = self._calculate_confidence(certifications, intelligence)
        return intelligence, confidence

    @staticmethod
    def _determine_most_recent_certification(
        certifications: list[Certification],
    ) -> str | None:
        """
        Determine the candidate's most recently completed certification.

        `Certification` has no prestige, difficulty, or level field
        (see app/models/candidate.py) — only free-text `name`,
        `organization`, and `completion_date`. `completion_date` is
        always either None or a bare 4-digit year string, exactly as
        produced by certifications_parser.py (the same _YEAR_PATTERN
        regex used for Education.graduation_year), so it is a genuine
        deterministic ordering signal — not an invented one.

        Certifications with an unresolvable completion_date are not
        considered as an "improvement" on an already-found dated
        entry; if no entry has a resolvable completion_date, the first
        certification record with a non-null `name` is used as a
        stable fallback, preserving the order the record already
        appears in. Returns None if no certification has a name.
        """
        dated_names = [
            (int(cert.completion_date), cert.name)
            for cert in certifications
            if cert.name and cert.completion_date and cert.completion_date.isdigit()
        ]
        if dated_names:
            _, name = max(dated_names, key=lambda item: item[0])
            return name

        for cert in certifications:
            if cert.name:
                return cert.name
        return None

    @staticmethod
    def _deduplicate(values: Iterable[str]) -> list[str]:
        """
        Deduplicate a sequence of strings case-insensitively, preserving
        first-seen order and original casing.

        Mirrors the existing `_deduplicate` helpers already used
        elsewhere in the AI pipeline (see
        app/ai/parsers/languages_parser.py,
        app/ai/engines/education_intelligence.py,
        app/ai/engines/project_intelligence.py) rather than
        introducing a new convention or a new shared utility module.
        Per the ticket, certification names/organizations are never
        semantically normalized (e.g. "AWS Certified Developer" is not
        treated as equivalent to "AWS Developer Certification") — only
        exact, case-insensitive, whitespace-trimmed duplicates collapse.
        """
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            key = value.strip().lower()
            if key and key not in seen:
                seen.add(key)
                result.append(value.strip())
        return result

    def _calculate_confidence(
        self,
        certifications: list[Certification],
        intelligence: CertificationIntelligence,
    ) -> float:
        """
        Compute a deterministic, weighted extraction-completeness score.

        Each stage contributes a 0.0-1.0 sub-score reflecting how much
        of the available certification data could be extracted,
        combined using the weights in _CONFIDENCE_WEIGHTS (which sum
        to 1.0). As with the other Intelligence engines, this measures
        processing completeness, not the prestige or value of the
        candidate's certifications, and does not increase merely
        because the candidate has more certifications.
        """
        scores = {
            "most_recent_certification": (
                1.0 if intelligence.most_recent_certification else 0.0
            ),
            "name_extraction": self._field_presence_score(certifications, "name"),
            "organization_extraction": self._field_presence_score(
                certifications, "organization"
            ),
        }
        confidence = sum(
            scores[key] * weight for key, weight in _CONFIDENCE_WEIGHTS.items()
        )
        return round(min(max(confidence, 0.0), 1.0), 4)

    @staticmethod
    def _field_presence_score(certifications: list[Certification], field: str) -> float:
        """Fraction of certification entries with a non-null value for `field`."""
        if not certifications:
            return 0.0
        filled = sum(1 for entry in certifications if getattr(entry, field))
        return filled / len(certifications)