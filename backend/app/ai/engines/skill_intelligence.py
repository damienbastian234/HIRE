"""
Skill Intelligence engine (HIRE-AI-103).

The second production Intelligence System built on the HIRE-AI-101
framework. Consumes the CandidateProfile produced by HIRE-AI-102
(specifically its `skills` field) and produces comprehensive,
deterministic skill intelligence for downstream systems such as
Candidate Matching, Resume Scoring, and Job Recommendation.

This engine does not parse resumes — that is exclusively HIRE-AI-102's
responsibility. It never mutates `context.state`; that remains the
AIOrchestrator's exclusive responsibility (see app.ai.context.WorkflowState).
"""


from app.ai.base_engine import BaseEngine
from app.ai.context import AIContext
from app.ai.exceptions import ContextValidationException, EngineExecutionException
from app.ai.result import ExecutionStatus, IntelligenceResult
from app.ai.skills.skill_categorizer import KNOWN_CATEGORIES, categorize_skills
from app.ai.skills.skill_gap_analyzer import analyze_gaps
from app.ai.skills.skill_metrics import compute_metrics
from app.ai.skills.skill_normalizer import normalize_skills
from app.core.logging import get_logger
from app.models.candidate import CandidateProfile
from app.models.skill_intelligence import SkillGap, SkillIntelligence

logger = get_logger(__name__)

# Weights for the deterministic, stage-completeness confidence score.
# Must sum to 1.0.
_CONFIDENCE_WEIGHTS: dict[str, float] = {
    "normalization": 0.20,
    "categorization": 0.35,
    "metrics": 0.20,
    "gap_analysis": 0.15,
    "duplicate_detection": 0.10,
}


class SkillIntelligenceEngine(BaseEngine):
    """
    Transforms `context.data["candidate_profile"]` (a CandidateProfile)
    into structured SkillIntelligence.

    Orchestrates four specialized, independent components — one per
    pipeline stage (normalize, categorize, compute metrics, analyze
    gaps) — rather than containing that logic itself, so any stage can
    be swapped for a more sophisticated implementation (e.g. fuzzy
    matching, ML-based categorization) in a future ticket without this
    engine's interface changing.
    """

    def __init__(self) -> None:
        super().__init__(name="skill_intelligence")

    def validate_context(self, context: AIContext) -> None:
        """
        Ensure `context.data["candidate_profile"]` is present and is a
        CandidateProfile instance.
        """
        if "candidate_profile" not in context.data:
            raise ContextValidationException(
                "SkillIntelligenceEngine requires 'candidate_profile' in context.data."
            )
        profile = context.data["candidate_profile"]
        if profile is None:
            raise ContextValidationException(
                "'candidate_profile' in context.data must not be None."
            )
        if not isinstance(profile, CandidateProfile):
            raise ContextValidationException(
                "'candidate_profile' in context.data must be a CandidateProfile instance."
            )

    async def execute(self, context: AIContext) -> IntelligenceResult:
        """
        Build SkillIntelligence from the candidate's skills and return
        an IntelligenceResult.

        Any failure during processing is caught and re-raised as an
        EngineExecutionException; no raw exception escapes this engine.
        """
        profile: CandidateProfile = context.data["candidate_profile"]

        try:
            intelligence, confidence = self._build_skill_intelligence(profile)
        except Exception as exc:
            logger.exception("Skill intelligence processing failed unexpectedly.")
            raise EngineExecutionException(
                "Skill Intelligence failed to process the candidate's skills."
            ) from exc

        logger.info(
            "Skill intelligence completed. technical_skill_count=%d "
            "soft_skill_count=%d category_count=%d confidence=%.2f",
            intelligence.metrics.technical_skill_count,
            intelligence.metrics.soft_skill_count,
            len(intelligence.categories),
            confidence,
        )

        return IntelligenceResult(
            engine_name=self.name,
            status=ExecutionStatus.SUCCESS,
            confidence=confidence,
            output=intelligence.model_dump(),
            warnings=[],
        )

    def _build_skill_intelligence(
        self, profile: CandidateProfile
    ) -> tuple[SkillIntelligence, float]:
        """Run the full normalize -> categorize -> metrics -> gap-analysis pipeline."""
        raw_skills = list(profile.skills.technical_skills) + list(profile.skills.soft_skills)

        normalized_unique, duplicates = normalize_skills(raw_skills)
        categories, uncategorized = categorize_skills(normalized_unique)
        metrics = compute_metrics(normalized_unique, categories, uncategorized)
        gaps = analyze_gaps(categories)

        intelligence = SkillIntelligence(
            categories=categories,
            metrics=metrics,
            gaps=gaps,
            normalized_skills=normalized_unique,
            duplicate_skills=duplicates,
        )

        confidence = self._calculate_confidence(
            raw_skills=raw_skills,
            normalized_unique=normalized_unique,
            uncategorized=uncategorized,
            total_skills=metrics.total_skills,
            gaps=gaps,
        )
        return intelligence, confidence

    def _calculate_confidence(
        self,
        raw_skills: list[str],
        normalized_unique: list[str],
        uncategorized: list[str],
        total_skills: int,
        gaps: SkillGap,
    ) -> float:
        """
        Compute a deterministic, weighted stage-completeness score.

        Each pipeline stage contributes a 0.0-1.0 sub-score, combined
        using the weights in _CONFIDENCE_WEIGHTS (which sum to 1.0):

        - normalization: whether normalization had valid input to
          process and completed successfully — not whether individual
          skills matched a known alias. See _normalization_score for
          why this is deliberately independent of alias-dictionary
          coverage.
        - categorization: fraction of normalized skills successfully
          assigned to a known category.
        - metrics: 1.0 if there was any skill data to measure, else 0.0.
        - gap_analysis: fraction of known categories that have at
          least one matching skill (i.e. category coverage).
        - duplicate_detection: 1.0 if duplicate detection had any
          input to run against, else 0.0.
        """
        scores = {
            "normalization": self._normalization_score(raw_skills),
            "categorization": self._categorization_score(normalized_unique, uncategorized),
            "metrics": 1.0 if total_skills > 0 else 0.0,
            "gap_analysis": self._gap_analysis_score(gaps),
            "duplicate_detection": 1.0 if raw_skills else 0.0,
        }
        confidence = sum(scores[key] * weight for key, weight in _CONFIDENCE_WEIGHTS.items())
        return round(min(max(confidence, 0.0), 1.0), 4)

    @staticmethod
    def _normalization_score(raw_skills: list[str]) -> float:
        """
        Score whether normalization had valid data to process and
        completed successfully — deliberately independent of whether
        any individual skill matched a known alias.

        normalize_skills() deterministically resolves every non-blank
        input string to either a new normalized entry or a recorded
        duplicate; it never silently drops valid input. So "did
        normalization succeed" reduces to "was there any valid,
        non-blank skill string to process" — not "did our dictionary
        already recognize this technology." A resume listing skills we
        have no alias for (e.g. "Blockchain") is normalized just as
        successfully as one listing "Python", and should not be
        penalized here for that.
        """
        valid_input_count = sum(1 for s in raw_skills if s and s.strip())
        return 1.0 if valid_input_count > 0 else 0.0

    @staticmethod
    def _categorization_score(normalized_unique: list[str], uncategorized: list[str]) -> float:
        if not normalized_unique:
            return 0.0
        categorized_count = len(normalized_unique) - len(uncategorized)
        return categorized_count / len(normalized_unique)

    @staticmethod
    def _gap_analysis_score(gaps: SkillGap) -> float:
        total_categories = len(KNOWN_CATEGORIES)
        present = total_categories - len(gaps.missing_categories)
        return present / total_categories