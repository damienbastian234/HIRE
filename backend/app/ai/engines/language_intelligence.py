"""
Language Intelligence engine (HIRE-AI-110).

Consumes the CandidateProfile produced by HIRE-AI-102 (specifically
its `languages` field) and produces deterministic language
intelligence for downstream systems.

This engine does not parse resumes — that is exclusively HIRE-AI-102's
responsibility (see app/ai/parsers/languages_parser.py) — and it does
not invent proficiency, fluency, or a "primary language" ranking that
CandidateProfile's schema does not already capture. Unlike Education,
Project, and Certification, there is no `Language` model at all:
`CandidateProfile.languages` is a plain `list[str]`, already
deduplicated by the parser before it ever reaches CandidateProfile
(see app/models/candidate.py and languages_parser.py). This engine
still deduplicates defensively rather than assuming its input always
came from that parser — CandidateProfile is this engine's contract,
not the parser specifically. It never mutates `context.state`; that
remains the AIOrchestrator's exclusive responsibility (see
app.ai.context.WorkflowState).
"""


from collections.abc import Iterable

from app.ai.base_engine import BaseEngine
from app.ai.context import AIContext
from app.ai.exceptions import ContextValidationException, EngineExecutionException
from app.ai.result import ExecutionStatus, IntelligenceResult
from app.core.logging import get_logger
from app.models.candidate import CandidateProfile
from app.models.language_intelligence import LanguageIntelligence

logger = get_logger(__name__)

# Confidence weighting for extraction completeness. Must sum to 1.0.
# Unlike Education/Project/Certification (each with 2-4 independently
# extractable sub-fields per record, e.g. degree/institution/gpa),
# Language has no per-entry structure at all: a language name is
# atomic, either a usable non-blank string or not. There is genuinely
# only one extractable dimension here, so a single weight is used
# rather than inventing additional stages to weight against nothing.
_CONFIDENCE_WEIGHTS: dict[str, float] = {
    "language_extraction": 1.0,
}


class LanguageIntelligenceEngine(BaseEngine):
    """
    Transforms `context.data["candidate_profile"]` (a CandidateProfile)
    into structured LanguageIntelligence, analyzing only its
    `languages` field.

    Kept as a single self-contained engine (no helper package),
    following the precedent set by EducationIntelligenceEngine,
    ProjectIntelligenceEngine, and CertificationIntelligenceEngine:
    Language's schema (a flat list[str]) is thinner than any of those,
    so there is even less here to decompose into pipeline stages.
    """

    def __init__(self) -> None:
        super().__init__(name="language_intelligence")

    def validate_context(self, context: AIContext) -> None:
        """
        Ensure `context.data["candidate_profile"]` is present and is a
        CandidateProfile instance.
        """
        if "candidate_profile" not in context.data:
            raise ContextValidationException(
                "LanguageIntelligenceEngine requires 'candidate_profile' "
                "in context.data."
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
        Build LanguageIntelligence from the candidate's languages and
        return an IntelligenceResult.

        Any failure during processing is caught and re-raised as an
        EngineExecutionException; no raw exception escapes this engine.
        """
        profile: CandidateProfile = context.data["candidate_profile"]

        try:
            intelligence, confidence = self._build_language_intelligence(profile)
        except Exception as exc:
            logger.exception("Language intelligence processing failed unexpectedly.")
            raise EngineExecutionException(
                "Language Intelligence failed to process the candidate's languages."
            ) from exc

        logger.info(
            "Language intelligence completed. language_count=%d confidence=%.2f",
            intelligence.language_count,
            confidence,
        )

        return IntelligenceResult(
            engine_name=self.name,
            status=ExecutionStatus.SUCCESS,
            confidence=confidence,
            output=intelligence.model_dump(),
            warnings=[],
        )

    def _build_language_intelligence(
        self, profile: CandidateProfile
    ) -> tuple[LanguageIntelligence, float]:
        """Aggregate the candidate's languages into LanguageIntelligence."""
        raw_languages = profile.languages

        languages = self._deduplicate(
            lang for lang in raw_languages if lang and lang.strip()
        )

        intelligence = LanguageIntelligence(
            language_count=len(languages),
            languages=languages,
        )

        confidence = self._calculate_confidence(raw_languages)
        return intelligence, confidence

    @staticmethod
    def _deduplicate(values: Iterable[str]) -> list[str]:
        """
        Deduplicate a sequence of strings case-insensitively, preserving
        first-seen order and original casing.

        Mirrors the existing `_deduplicate` helpers already used
        elsewhere in the AI pipeline (see
        app/ai/parsers/languages_parser.py,
        app/ai/engines/education_intelligence.py,
        app/ai/engines/project_intelligence.py,
        app/ai/engines/certification_intelligence.py) rather than
        introducing a new convention or a new shared utility module.
        No semantic alias mapping (e.g. "English" -> "en") is applied.
        """
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            key = value.strip().lower()
            if key and key not in seen:
                seen.add(key)
                result.append(value.strip())
        return result

    def _calculate_confidence(self, raw_languages: list[str]) -> float:
        """
        Compute a deterministic extraction-completeness score.

        Language has no per-entry sub-fields, so completeness here
        means: what fraction of the raw `CandidateProfile.languages`
        entries were usable (non-blank) values, rather than a
        multi-stage weighted score over several fields as in the other
        Intelligence engines. An empty list produces 0.0. This never
        depends on how many languages the candidate knows, and never
        represents fluency, importance, or employability.
        """
        if not raw_languages:
            return 0.0

        usable = sum(1 for lang in raw_languages if lang and lang.strip())
        extraction_score = usable / len(raw_languages)

        confidence = extraction_score * _CONFIDENCE_WEIGHTS["language_extraction"]
        return round(min(max(confidence, 0.0), 1.0), 4)