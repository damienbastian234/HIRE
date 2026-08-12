"""
Experience Intelligence engine (HIRE-AI-104).

The third production Intelligence System built on the HIRE-AI-101
framework. Consumes the CandidateProfile produced by HIRE-AI-102
(specifically its `experience` field) and produces comprehensive,
deterministic experience intelligence for downstream systems such as
Candidate Matching, Resume Scoring, Hiring Recommendation, and Career
Intelligence.

This engine does not parse resumes and does not analyze skills — both
are exclusively the responsibility of HIRE-AI-102 and HIRE-AI-103
respectively. It never mutates `context.state`; that remains the
AIOrchestrator's exclusive responsibility (see app.ai.context.WorkflowState).
"""


from app.ai.base_engine import BaseEngine
from app.ai.context import AIContext
from app.ai.exceptions import ContextValidationException, EngineExecutionException
from app.ai.experience.career_progression import analyze_progression
from app.ai.experience.employment_gap import analyze_gaps
from app.ai.experience.experience_calculator import calculate_metrics
from app.ai.experience.seniority_analyzer import determine_seniority
from app.ai.experience.stability_analyzer import analyze_stability
from app.ai.experience.timeline_builder import build_timeline
from app.ai.result import ExecutionStatus, IntelligenceResult
from app.core.logging import get_logger
from app.models.candidate import CandidateProfile
from app.models.experience_intelligence_model import (
    CareerProgression,
    CareerTimeline,
    EmploymentGapAnalysis,
    ExperienceIntelligence,
    ExperienceMetrics,
    StabilityAnalysis,
)

logger = get_logger(__name__)

# Weights for the deterministic, stage-completeness confidence score.
# Must sum to 1.0.
_CONFIDENCE_WEIGHTS: dict[str, float] = {
    "timeline": 0.20,
    "experience": 0.25,
    "progression": 0.20,
    "gap_analysis": 0.15,
    "stability": 0.10,
    "seniority": 0.10,
}


class ExperienceIntelligenceEngine(BaseEngine):
    """
    Transforms `context.data["candidate_profile"]` (a CandidateProfile)
    into structured ExperienceIntelligence, analyzing only its
    `experience` field.

    Orchestrates six specialized, independent components — one per
    pipeline stage (timeline, metrics, progression, gaps, stability,
    seniority) — rather than containing that logic itself, so any
    stage can be swapped for a more sophisticated implementation in a
    future ticket without this engine's interface changing.
    """

    def __init__(self) -> None:
        super().__init__(name="experience_intelligence")

    def validate_context(self, context: AIContext) -> None:
        """
        Ensure `context.data["candidate_profile"]` is present and is a
        CandidateProfile instance.
        """
        if "candidate_profile" not in context.data:
            raise ContextValidationException(
                "ExperienceIntelligenceEngine requires 'candidate_profile' in context.data."
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
        Build ExperienceIntelligence from the candidate's experience
        and return an IntelligenceResult.

        Any failure during processing is caught and re-raised as an
        EngineExecutionException; no raw exception escapes this engine.
        """
        profile: CandidateProfile = context.data["candidate_profile"]

        try:
            intelligence, confidence = self._build_experience_intelligence(profile)
        except Exception as exc:
            logger.exception("Experience intelligence processing failed unexpectedly.")
            raise EngineExecutionException(
                "Experience Intelligence failed to process the candidate's experience."
            ) from exc

        logger.info(
            "Experience intelligence completed. experience_count=%d company_count=%d "
            "stability_score=%.2f seniority=%s confidence=%.2f",
            len(profile.experience),
            intelligence.metrics.company_count,
            intelligence.stability.stability_score,
            intelligence.seniority_level.value,
            confidence,
        )

        return IntelligenceResult(
            engine_name=self.name,
            status=ExecutionStatus.SUCCESS,
            confidence=confidence,
            output=intelligence.model_dump(),
            warnings=[],
        )

    def _build_experience_intelligence(
        self, profile: CandidateProfile
    ) -> tuple[ExperienceIntelligence, float]:
        """Run the full timeline -> metrics -> progression -> gaps -> stability -> seniority pipeline."""
        timeline = build_timeline(profile.experience)
        metrics = calculate_metrics(timeline)
        progression = analyze_progression(timeline)
        gap_analysis = analyze_gaps(timeline)
        stability = analyze_stability(timeline, metrics)
        seniority_level = determine_seniority(metrics.total_experience_years)

        intelligence = ExperienceIntelligence(
            timeline=timeline,
            metrics=metrics,
            progression=progression,
            gap_analysis=gap_analysis,
            stability=stability,
            seniority_level=seniority_level,
        )

        confidence = self._calculate_confidence(
            timeline=timeline,
            metrics=metrics,
            progression=progression,
            gap_analysis=gap_analysis,
            stability=stability,
        )
        return intelligence, confidence

    def _calculate_confidence(
        self,
        timeline: CareerTimeline,
        metrics: ExperienceMetrics,
        progression: CareerProgression,
        gap_analysis: EmploymentGapAnalysis,
        stability: StabilityAnalysis,
    ) -> float:
        """
        Compute a deterministic, weighted stage-completeness score.

        Each pipeline stage contributes a 0.0-1.0 sub-score reflecting
        how much usable data that stage had to work with, combined
        using the weights in _CONFIDENCE_WEIGHTS (which sum to 1.0).
        As with HIRE-AI-103, these scores measure processing
        completeness (did the stage have data to work with), not
        whether individual values matched some external reference —
        e.g. an unrecognized job title does not by itself reduce
        confidence.
        """
        scores = {
            "timeline": self._timeline_score(timeline),
            "experience": self._experience_score(timeline),
            "progression": self._progression_score(progression),
            "gap_analysis": self._gap_analysis_score(timeline),
            "stability": 1.0 if metrics.average_tenure_months is not None else 0.0,
            "seniority": 1.0 if metrics.total_experience_months > 0 else 0.0,
        }
        confidence = sum(scores[key] * weight for key, weight in _CONFIDENCE_WEIGHTS.items())
        return round(min(max(confidence, 0.0), 1.0), 4)

    @staticmethod
    def _timeline_score(timeline: CareerTimeline) -> float:
        """Fraction of experience entries with a resolvable start date."""
        if not timeline.entries:
            return 0.0
        dated = sum(1 for e in timeline.entries if e.has_valid_dates)
        return dated / len(timeline.entries)

    @staticmethod
    def _experience_score(timeline: CareerTimeline) -> float:
        """Fraction of experience entries with a resolvable duration."""
        if not timeline.entries:
            return 0.0
        with_duration = sum(1 for e in timeline.entries if e.duration_months is not None)
        return with_duration / len(timeline.entries)

    @staticmethod
    def _progression_score(progression: CareerProgression) -> float:
        """Fraction of career moves that were classifiable (not 'unknown')."""
        if not progression.moves:
            return 0.0
        classifiable = sum(1 for m in progression.moves if m.move_type != "unknown")
        return classifiable / len(progression.moves)

    @staticmethod
    def _gap_analysis_score(timeline: CareerTimeline) -> float:
        """Fraction of consecutive dated-entry pairs where a gap determination was possible."""
        dated_entries: list = [e for e in timeline.entries if e.has_valid_dates]
        if len(dated_entries) < 2:
            return 0.0
        total_pairs = len(dated_entries) - 1
        determinable = sum(
            1
            for i in range(total_pairs)
            if not dated_entries[i].is_current
            and dated_entries[i].end_year is not None
            and dated_entries[i + 1].start_year is not None
        )
        return determinable / total_pairs