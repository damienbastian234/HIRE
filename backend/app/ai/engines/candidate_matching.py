"""
Candidate Matching Intelligence Engine for H.I.R.E.

This engine compares a structured CandidateProfile against a structured
JobRequirement and produces deterministic candidate matching
intelligence.

Responsibilities:
- Context validation
- Engine orchestration
- Result construction

This engine does NOT implement business logic itself.
All matching logic is delegated to helper modules under app.ai.matching.
"""

from app.ai.base_engine import BaseEngine
from app.ai.context import AIContext
from app.ai.exceptions import (
    ContextValidationException,
    EngineExecutionException,
)
from app.ai.matching.confidence import calculate_confidence
from app.ai.matching.education_matcher import match_education
from app.ai.matching.experience_matcher import match_experience
from app.ai.matching.recommendation import generate_recommendation
from app.ai.matching.scoring import calculate_score
from app.ai.matching.skill_matcher import match_skills
from app.ai.result import (
    ExecutionStatus,
    IntelligenceResult,
)
from app.core.logging import get_logger
from app.models.candidate import CandidateProfile
from app.models.candidate_matching_model import CandidateMatching
from app.models.job_requirement import JobRequirement

logger = get_logger(__name__)


class CandidateMatchingEngine(BaseEngine):
    """
    Compare a CandidateProfile against a JobRequirement and produce
    deterministic candidate matching intelligence.
    """

    def __init__(self) -> None:
        super().__init__(name="candidate_matching")

    async def execute(self, context: AIContext) -> IntelligenceResult:
        """Execute the Candidate Matching Intelligence Engine."""
        try:
            self.validate_context(context)

            candidate = context.data["candidate_profile"]
            job = context.data["job_requirement"]

            matching, confidence = self._build_candidate_matching(
                candidate,
                job,
            )

            logger.info(
                "Candidate matching completed "
                "(overall_score=%.2f, confidence=%.2f)",
                matching.overall_score.overall_score,
                confidence,
            )

            return IntelligenceResult(
                engine_name=self.name,
                status=ExecutionStatus.SUCCESS,
                confidence=round(confidence / 100.0, 4),
                output={
                    "candidate_matching": matching,
                },
                warnings=[],
            )

        except ContextValidationException:
            raise

        except Exception as exc:
            logger.exception("Candidate Matching Engine execution failed.")

            raise EngineExecutionException(
                "Candidate Matching Engine failed."
            ) from exc

    def _build_candidate_matching(
        self,
        profile: CandidateProfile,
        job: JobRequirement,
    ) -> tuple[CandidateMatching, float]:
        """Run the complete matching pipeline."""
        skill_match = match_skills(profile, job)
        experience_match = match_experience(profile, job)
        education_match = match_education(profile, job)

        overall_score = calculate_score(
            skill_match,
            experience_match,
            education_match,
        )
        recommendation = generate_recommendation(
            overall_score.overall_score,
        )
        confidence = calculate_confidence(
            skill_match,
            experience_match,
            education_match,
        )

        matching = CandidateMatching(
            skill_match=skill_match,
            experience_match=experience_match,
            education_match=education_match,
            overall_score=overall_score,
            recommendation=recommendation,
            confidence=confidence,
        )

        return matching, confidence

    def validate_context(self, context: AIContext) -> None:
        """Validate engine input."""

        if "candidate_profile" not in context.data:
            raise ContextValidationException(
                "Missing required context key: candidate_profile"
            )

        if "job_requirement" not in context.data:
            raise ContextValidationException(
                "Missing required context key: job_requirement"
            )

        candidate = context.data["candidate_profile"]
        job = context.data["job_requirement"]

        if candidate is None:
            raise ContextValidationException(
                "candidate_profile cannot be None."
            )

        if job is None:
            raise ContextValidationException(
                "job_requirement cannot be None."
            )

        if not isinstance(candidate, CandidateProfile):
            raise ContextValidationException(
                "candidate_profile must be an instance of CandidateProfile."
            )

        if not isinstance(job, JobRequirement):
            raise ContextValidationException(
                "job_requirement must be an instance of JobRequirement."
            )