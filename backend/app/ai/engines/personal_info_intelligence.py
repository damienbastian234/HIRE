"""
Personal Info Intelligence engine (HIRE-AI-111).

Consumes the CandidateProfile produced by HIRE-AI-102 (specifically
its `personal_info` field) and produces a deterministic completeness
audit for downstream systems.

This engine does not parse resumes — that is exclusively HIRE-AI-102's
responsibility (see app/ai/parsers/personal_info_parser.py) — and it
does not invent a "primary contact method," a professional-link
grouping, or any validity/quality judgment about the candidate's
contact information that CandidateProfile's `PersonalInfo` model does
not already capture. Unlike Education, Project, Certification, and
Language, `PersonalInfo` is a single object, not a list: there is
nothing to deduplicate or aggregate across, so this engine's shape
necessarily differs from its predecessors. It never mutates
`context.state`; that remains the AIOrchestrator's exclusive
responsibility (see app.ai.context.WorkflowState).
"""


from app.ai.base_engine import BaseEngine
from app.ai.context import AIContext
from app.ai.exceptions import ContextValidationException, EngineExecutionException
from app.ai.result import ExecutionStatus, IntelligenceResult
from app.core.logging import get_logger
from app.models.candidate import CandidateProfile
from app.models.personal_info_intelligence import PersonalInfoIntelligence

logger = get_logger(__name__)

# PersonalInfo's fields, in declaration order (see app/models/candidate.py).
# Hardcoded rather than introspected via PersonalInfo.model_fields for the
# same reason field names are hardcoded in every prior engine (explicit,
# readable, and PersonalInfo is out of scope to modify for this ticket).
_PERSONAL_INFO_FIELDS: tuple[str, ...] = (
    "full_name",
    "email",
    "phone",
    "linkedin_url",
    "github_url",
    "portfolio_url",
    "location",
)


class PersonalInfoIntelligenceEngine(BaseEngine):
    """
    Transforms `context.data["candidate_profile"]` (a CandidateProfile)
    into structured PersonalInfoIntelligence, analyzing only its
    `personal_info` field.

    Kept as a single self-contained engine (no helper package),
    consistent with EducationIntelligenceEngine,
    ProjectIntelligenceEngine, CertificationIntelligenceEngine, and
    LanguageIntelligenceEngine: the underlying schema here is a single
    flat object, so there is nothing to decompose into pipeline
    stages.
    """

    def __init__(self) -> None:
        super().__init__(name="personal_info_intelligence")

    def validate_context(self, context: AIContext) -> None:
        """
        Ensure `context.data["candidate_profile"]` is present and is a
        CandidateProfile instance.
        """
        if "candidate_profile" not in context.data:
            raise ContextValidationException(
                "PersonalInfoIntelligenceEngine requires "
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
        Build PersonalInfoIntelligence from the candidate's personal
        info and return an IntelligenceResult.

        Any failure during processing is caught and re-raised as an
        EngineExecutionException; no raw exception escapes this engine.
        """
        profile: CandidateProfile = context.data["candidate_profile"]

        try:
            intelligence, confidence = self._build_personal_info_intelligence(
                profile
            )
        except Exception as exc:
            logger.exception(
                "Personal info intelligence processing failed unexpectedly."
            )
            raise EngineExecutionException(
                "Personal Info Intelligence failed to process the "
                "candidate's personal info."
            ) from exc

        logger.info(
            "Personal info intelligence completed. "
            "provided_field_count=%d confidence=%.2f",
            intelligence.provided_field_count,
            confidence,
        )

        return IntelligenceResult(
            engine_name=self.name,
            status=ExecutionStatus.SUCCESS,
            confidence=confidence,
            output=intelligence.model_dump(),
            warnings=[],
        )

    def _build_personal_info_intelligence(
        self, profile: CandidateProfile
    ) -> tuple[PersonalInfoIntelligence, float]:
        """Audit which of the candidate's personal-info fields are populated."""
        personal_info = profile.personal_info

        provided_fields: list[str] = []
        missing_fields: list[str] = []
        for field_name in _PERSONAL_INFO_FIELDS:
            value = getattr(personal_info, field_name)
            if value and value.strip():
                provided_fields.append(field_name)
            else:
                missing_fields.append(field_name)

        intelligence = PersonalInfoIntelligence(
            provided_fields=provided_fields,
            missing_fields=missing_fields,
            provided_field_count=len(provided_fields),
        )

        confidence = self._calculate_confidence(intelligence)
        return intelligence, confidence

    @staticmethod
    def _calculate_confidence(intelligence: PersonalInfoIntelligence) -> float:
        """
        Compute a deterministic extraction-completeness score.

        `PersonalInfo` has seven independently extractable fields and
        no basis in the schema for treating any one of them as more
        diagnostic of completeness than another (e.g. weighting
        `email` above `portfolio_url` would be an invented value
        judgment, not something the schema supports) — so every field
        contributes equally. This reduces to the fraction of
        PersonalInfo's fields that are populated:
        provided_field_count / total field count. An entirely empty
        PersonalInfo therefore produces 0.0, and a fully populated one
        produces 1.0. This never depends on which fields specifically
        are present, and never represents contact-information quality
        or validity (e.g. no email-format checking).
        """
        total_fields = len(_PERSONAL_INFO_FIELDS)
        if total_fields == 0:
            return 0.0
        confidence = intelligence.provided_field_count / total_fields
        return round(min(max(confidence, 0.0), 1.0), 4)