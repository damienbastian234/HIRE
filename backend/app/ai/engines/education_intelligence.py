"""
Education Intelligence engine (HIRE-AI-107).

Consumes the CandidateProfile produced by HIRE-AI-102 (specifically
its `education` field) and produces deterministic education
intelligence for downstream systems such as Candidate Matching and
Career Report generation.

This engine does not parse resumes — that is exclusively HIRE-AI-102's
responsibility — and it does not invent qualification rankings,
grading scales, or institution rankings that CandidateProfile's
`Education` model does not already capture (see
app/models/candidate.py: Education has only free-text `degree`,
`institution`, `specialization`, `gpa`, and `graduation_year`). It
never mutates `context.state`; that remains the AIOrchestrator's
exclusive responsibility (see app.ai.context.WorkflowState).
"""


from collections.abc import Iterable

from app.ai.base_engine import BaseEngine
from app.ai.context import AIContext
from app.ai.exceptions import ContextValidationException, EngineExecutionException
from app.ai.result import ExecutionStatus, IntelligenceResult
from app.core.logging import get_logger
from app.models.candidate import CandidateProfile, Education
from app.models.education_intelligence import EducationIntelligence

logger = get_logger(__name__)

# Weights for the deterministic, extraction-completeness confidence
# score. Must sum to 1.0. Mirrors the stage-completeness pattern used
# by ResumeIntelligenceEngine / SkillIntelligenceEngine /
# ExperienceIntelligenceEngine: these scores measure how much of the
# available education data could be extracted, not how "good" the
# candidate's education is.
_CONFIDENCE_WEIGHTS: dict[str, float] = {
    "highest_qualification": 0.25,
    "degree_extraction": 0.30,
    "institution_extraction": 0.20,
    "academic_performance": 0.25,
}


class EducationIntelligenceEngine(BaseEngine):
    """
    Transforms `context.data["candidate_profile"]` (a CandidateProfile)
    into structured EducationIntelligence, analyzing only its
    `education` field.

    Kept as a single self-contained engine (no per-stage helper
    package, unlike Skill/Experience Intelligence) because education
    analysis here is a small, non-branching aggregation over an
    already-structured list — there is no multi-stage pipeline to
    decompose into swappable components.
    """

    def __init__(self) -> None:
        super().__init__(name="education_intelligence")

    def validate_context(self, context: AIContext) -> None:
        """
        Ensure `context.data["candidate_profile"]` is present and is a
        CandidateProfile instance.
        """
        if "candidate_profile" not in context.data:
            raise ContextValidationException(
                "EducationIntelligenceEngine requires 'candidate_profile' "
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
        Build EducationIntelligence from the candidate's education
        records and return an IntelligenceResult.

        Any failure during processing is caught and re-raised as an
        EngineExecutionException; no raw exception escapes this engine.
        """
        profile: CandidateProfile = context.data["candidate_profile"]

        try:
            intelligence, confidence = self._build_education_intelligence(profile)
        except Exception as exc:
            logger.exception("Education intelligence processing failed unexpectedly.")
            raise EngineExecutionException(
                "Education Intelligence failed to process the candidate's education."
            ) from exc

        logger.info(
            "Education intelligence completed. education_count=%d "
            "highest_qualification=%s confidence=%.2f",
            intelligence.education_count,
            intelligence.highest_qualification,
            confidence,
        )

        return IntelligenceResult(
            engine_name=self.name,
            status=ExecutionStatus.SUCCESS,
            confidence=confidence,
            output=intelligence.model_dump(),
            warnings=[],
        )

    def _build_education_intelligence(
        self, profile: CandidateProfile
    ) -> tuple[EducationIntelligence, float]:
        """Aggregate the candidate's education records into EducationIntelligence."""
        education = profile.education

        highest_qualification = self._determine_highest_qualification(education)
        degrees = self._deduplicate(e.degree for e in education if e.degree)
        fields_of_study = self._deduplicate(
            e.specialization for e in education if e.specialization
        )
        institutions = self._deduplicate(
            e.institution for e in education if e.institution
        )
        academic_performance = self._deduplicate(e.gpa for e in education if e.gpa)

        intelligence = EducationIntelligence(
            highest_qualification=highest_qualification,
            degrees=degrees,
            fields_of_study=fields_of_study,
            institutions=institutions,
            academic_performance=academic_performance,
            education_count=len(education),
        )

        confidence = self._calculate_confidence(education, intelligence)
        return intelligence, confidence

    @staticmethod
    def _determine_highest_qualification(education: list[Education]) -> str | None:
        """
        Determine the candidate's highest qualification.

        `Education` has no structured qualification-level field (see
        app/models/candidate.py) — only free-text `degree`,
        `institution`, `specialization`, `gpa`, and `graduation_year`
        strings, exactly as produced by education_parser.py. Ranking
        degree names by academic level (e.g. treating "PhD" as higher
        than "Bachelor's") would require an external classification
        dictionary that exists nowhere in the current schema or
        codebase, so this engine does not invent one.

        Instead, "highest qualification" is resolved deterministically
        from data the schema already provides: the degree of the most
        recently completed education record, ordered by
        `graduation_year`. If no entry has a resolvable
        `graduation_year`, the first education record with a non-null
        `degree` is used as a stable, order-preserving fallback. If no
        entry has a `degree` at all, returns None.
        """
        dated_degrees = [
            (int(entry.graduation_year), entry.degree)
            for entry in education
            if entry.degree
            and entry.graduation_year
            and entry.graduation_year.isdigit()
        ]
        if dated_degrees:
            _, degree = max(dated_degrees, key=lambda item: item[0])
            return degree

        for entry in education:
            if entry.degree:
                return entry.degree
        return None

    @staticmethod
    def _deduplicate(values: Iterable[str]) -> list[str]:
        """
        Deduplicate a sequence of strings case-insensitively, preserving
        first-seen order and original casing.

        Mirrors the existing `_deduplicate` helpers already used
        elsewhere in the AI parsing pipeline (see
        app/ai/parsers/languages_parser.py,
        app/ai/parsers/skills_parser.py) rather than introducing a new
        convention.
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
        self, education: list[Education], intelligence: EducationIntelligence
    ) -> float:
        """
        Compute a deterministic, weighted extraction-completeness score.

        Each stage contributes a 0.0-1.0 sub-score reflecting how much
        of the available education data could be extracted, combined
        using the weights in _CONFIDENCE_WEIGHTS (which sum to 1.0).
        As with the other Intelligence engines, this measures
        processing completeness, not the quality or prestige of the
        candidate's education.
        """
        scores = {
            "highest_qualification": (
                1.0 if intelligence.highest_qualification else 0.0
            ),
            "degree_extraction": self._field_extraction_score(education, "degree"),
            "institution_extraction": self._field_extraction_score(
                education, "institution"
            ),
            "academic_performance": self._field_extraction_score(education, "gpa"),
        }
        confidence = sum(
            scores[key] * weight for key, weight in _CONFIDENCE_WEIGHTS.items()
        )
        return round(min(max(confidence, 0.0), 1.0), 4)

    @staticmethod
    def _field_extraction_score(education: list[Education], field: str) -> float:
        """Fraction of education entries with a non-null value for `field`."""
        if not education:
            return 0.0
        filled = sum(1 for entry in education if getattr(entry, field))
        return filled / len(education)