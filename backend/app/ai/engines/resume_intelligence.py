"""
Resume Intelligence engine (HIRE-AI-102).

The first production Intelligence System built on the HIRE-AI-101 AI
framework. Transforms raw resume text into a structured, validated
CandidateProfile using deterministic, rule-based parsing.

This engine performs information extraction only. It does not score,
rank, or recommend candidates, and it never mutates `context.state` —
that remains the AIOrchestrator's exclusive responsibility (see
app.ai.context.WorkflowState).
"""


from app.ai.base_engine import BaseEngine
from app.ai.context import AIContext
from app.ai.exceptions import ContextValidationException, EngineExecutionException
from app.ai.parsers.certifications_parser import parse_certifications
from app.ai.parsers.education_parser import parse_education
from app.ai.parsers.experience_parser import parse_experience
from app.ai.parsers.languages_parser import parse_languages
from app.ai.parsers.personal_info_parser import parse_personal_info
from app.ai.parsers.projects_parser import parse_projects
from app.ai.parsers.section_parser import parse_sections
from app.ai.parsers.skills_parser import parse_skills
from app.ai.result import ExecutionStatus, IntelligenceResult
from app.core.logging import get_logger
from app.models.candidate import CandidateProfile, PersonalInfo, Skills

logger = get_logger(__name__)

# Weights for the deterministic, extraction-completeness confidence
# score. Must sum to 1.0.
_CONFIDENCE_WEIGHTS: dict[str, float] = {
    "personal_info": 0.20,
    "education": 0.15,
    "experience": 0.25,
    "skills": 0.20,
    "projects": 0.10,
    "certifications": 0.05,
    "languages": 0.05,
}


class ResumeIntelligenceEngine(BaseEngine):
    """
    Transforms raw resume text (`context.data["resume_text"]`) into a
    structured `CandidateProfile`.

    Orchestrates a set of specialized, independent parser functions
    (one per resume section) rather than containing parsing logic
    itself, so any individual parser can be swapped for an NLP- or
    LLM-based implementation in a future ticket without this engine's
    interface changing.
    """

    def __init__(self) -> None:
        super().__init__(name="resume_intelligence")

    def validate_context(self, context: AIContext) -> None:
        """
        Ensure `context.data["resume_text"]` is present and is a string.

        An empty or whitespace-only string is valid input (an "empty
        resume") and is handled inside `execute`, not rejected here.
        Only a missing key or a non-string value is treated as invalid
        input.
        """
        if "resume_text" not in context.data:
            raise ContextValidationException(
                "ResumeIntelligenceEngine requires 'resume_text' in context.data."
            )
        if not isinstance(context.data["resume_text"], str):
            raise ContextValidationException(
                "'resume_text' in context.data must be a string."
            )

    async def execute(self, context: AIContext) -> IntelligenceResult:
        """
        Parse `context.data["resume_text"]` into a CandidateProfile and
        return an IntelligenceResult.

        Any failure during parsing is caught and re-raised as an
        EngineExecutionException; no raw exception escapes this engine.
        """
        resume_text = context.data["resume_text"]
        logger.info("Resume parsing started.")

        try:
            profile, warnings = self._build_profile(resume_text)
        except Exception as exc:
            logger.exception("Resume parsing failed unexpectedly.")
            raise EngineExecutionException(
                "Resume Intelligence failed to parse the provided resume."
            ) from exc

        confidence = self._calculate_confidence(profile)

        skill_count = len(profile.skills.technical_skills) + len(profile.skills.soft_skills)
        logger.info(
            "Resume parsing completed. skills_extracted=%d experiences_extracted=%d confidence=%.2f",
            skill_count,
            len(profile.experience),
            confidence,
        )
        for warning in warnings:
            logger.warning(warning)

        return IntelligenceResult(
            engine_name=self.name,
            status=ExecutionStatus.SUCCESS,
            confidence=confidence,
            output=profile.model_dump(),
            warnings=warnings,
        )

    def _build_profile(self, resume_text: str) -> tuple[CandidateProfile, list[str]]:
        """Run every specialized parser against the resume text and assemble a CandidateProfile."""
        warnings: list[str] = []
        sections = parse_sections(resume_text)

        personal_info = parse_personal_info(resume_text)
        education = parse_education(sections.get("education", ""))
        experience = parse_experience(sections.get("experience", ""))
        skills = parse_skills(sections.get("skills", ""))
        projects = parse_projects(sections.get("projects", ""))
        certifications = parse_certifications(sections.get("certifications", ""))
        languages = parse_languages(sections.get("languages", ""))

        if not resume_text.strip():
            warnings.append("Resume text was empty; no information could be extracted.")
        else:
            if not personal_info.email:
                warnings.append("No email address could be extracted.")
            if not education:
                warnings.append("No education section could be found or parsed.")
            if not experience:
                warnings.append("No experience section could be found or parsed.")
            if not skills.technical_skills and not skills.soft_skills:
                warnings.append("No skills section could be found or parsed.")

        profile = CandidateProfile(
            personal_info=personal_info,
            education=education,
            experience=experience,
            skills=skills,
            projects=projects,
            certifications=certifications,
            languages=languages,
        )
        return profile, warnings

    def _calculate_confidence(self, profile: CandidateProfile) -> float:
        """
        Compute a deterministic, weighted extraction-completeness score.

        Each section contributes a 0.0-1.0 completeness sub-score,
        combined using the weights in _CONFIDENCE_WEIGHTS (which sum
        to 1.0), producing an overall confidence in [0.0, 1.0].
        """
        scores = {
            "personal_info": self._personal_info_completeness(profile.personal_info),
            "education": self._list_completeness(
                profile.education,
                fields=["degree", "institution", "specialization", "gpa", "graduation_year"],
            ),
            "experience": self._list_completeness(
                profile.experience,
                fields=["company", "position", "start_date", "end_date"],
            ),
            "skills": self._skills_completeness(profile.skills),
            "projects": 1.0 if profile.projects else 0.0,
            "certifications": 1.0 if profile.certifications else 0.0,
            "languages": 1.0 if profile.languages else 0.0,
        }

        confidence = sum(scores[key] * weight for key, weight in _CONFIDENCE_WEIGHTS.items())
        return round(min(max(confidence, 0.0), 1.0), 4)

    @staticmethod
    def _personal_info_completeness(personal_info: PersonalInfo) -> float:
        fields = [
            personal_info.full_name,
            personal_info.email,
            personal_info.phone,
            personal_info.linkedin_url,
            personal_info.github_url,
            personal_info.portfolio_url,
            personal_info.location,
        ]
        filled = sum(1 for f in fields if f)
        return filled / len(fields)

    @staticmethod
    def _list_completeness(entries: list, fields: list[str]) -> float:
        if not entries:
            return 0.0
        per_entry_scores = []
        for entry in entries:
            values = [getattr(entry, f) for f in fields]
            filled = sum(1 for v in values if v)
            per_entry_scores.append(filled / len(fields))
        return sum(per_entry_scores) / len(per_entry_scores)

    @staticmethod
    def _skills_completeness(skills: Skills) -> float:
        has_technical = bool(skills.technical_skills)
        has_soft = bool(skills.soft_skills)
        if has_technical and has_soft:
            return 1.0
        if has_technical or has_soft:
            return 0.5
        return 0.0