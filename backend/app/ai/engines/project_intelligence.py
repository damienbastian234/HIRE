"""
Project Intelligence engine (HIRE-AI-108).

Consumes the CandidateProfile produced by HIRE-AI-102 (specifically
its `projects` field) and produces deterministic project intelligence
for downstream systems.

This engine does not parse resumes — that is exclusively HIRE-AI-102's
responsibility — and it does not invent project-complexity rankings,
technology-prestige rankings, or outcomes that CandidateProfile's
`Project` model does not already capture (see app/models/candidate.py:
Project has only free-text `name`, free-text `description`, and a
`technologies` list — no dates, roles, links, or outcomes). It never
mutates `context.state`; that remains the AIOrchestrator's exclusive
responsibility (see app.ai.context.WorkflowState).
"""


from collections.abc import Iterable

from app.ai.base_engine import BaseEngine
from app.ai.context import AIContext
from app.ai.exceptions import ContextValidationException, EngineExecutionException
from app.ai.result import ExecutionStatus, IntelligenceResult
from app.core.logging import get_logger
from app.models.candidate import CandidateProfile, Project
from app.models.project_intelligence import ProjectIntelligence

logger = get_logger(__name__)

# Weights for the deterministic, extraction-completeness confidence
# score. Must sum to 1.0. Mirrors the stage-completeness pattern used
# by ResumeIntelligenceEngine / SkillIntelligenceEngine /
# ExperienceIntelligenceEngine / EducationIntelligenceEngine: these
# scores measure how much of the available project data could be
# extracted, not how "good" the candidate's projects are.
_CONFIDENCE_WEIGHTS: dict[str, float] = {
    "name_extraction": 0.35,
    "technology_extraction": 0.35,
    "description_presence": 0.30,
}


class ProjectIntelligenceEngine(BaseEngine):
    """
    Transforms `context.data["candidate_profile"]` (a CandidateProfile)
    into structured ProjectIntelligence, analyzing only its `projects`
    field.

    Kept as a single self-contained engine (no per-stage helper
    package, following the precedent set by
    EducationIntelligenceEngine over Skill/Experience Intelligence's
    multi-module pipelines): Project's schema is thin (name,
    description, technologies only), so there is no multi-stage
    pipeline to decompose into swappable components.
    """

    def __init__(self) -> None:
        super().__init__(name="project_intelligence")

    def validate_context(self, context: AIContext) -> None:
        """
        Ensure `context.data["candidate_profile"]` is present and is a
        CandidateProfile instance.
        """
        if "candidate_profile" not in context.data:
            raise ContextValidationException(
                "ProjectIntelligenceEngine requires 'candidate_profile' "
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
        Build ProjectIntelligence from the candidate's project records
        and return an IntelligenceResult.

        Any failure during processing is caught and re-raised as an
        EngineExecutionException; no raw exception escapes this engine.
        """
        profile: CandidateProfile = context.data["candidate_profile"]

        try:
            intelligence, confidence = self._build_project_intelligence(profile)
        except Exception as exc:
            logger.exception("Project intelligence processing failed unexpectedly.")
            raise EngineExecutionException(
                "Project Intelligence failed to process the candidate's projects."
            ) from exc

        logger.info(
            "Project intelligence completed. project_count=%d "
            "technology_count=%d confidence=%.2f",
            intelligence.project_count,
            len(intelligence.technologies),
            confidence,
        )

        return IntelligenceResult(
            engine_name=self.name,
            status=ExecutionStatus.SUCCESS,
            confidence=confidence,
            output=intelligence.model_dump(),
            warnings=[],
        )

    def _build_project_intelligence(
        self, profile: CandidateProfile
    ) -> tuple[ProjectIntelligence, float]:
        """Aggregate the candidate's project records into ProjectIntelligence."""
        projects = profile.projects

        project_names = self._deduplicate(p.name for p in projects if p.name)
        technologies = self._deduplicate(
            tech for p in projects for tech in p.technologies if tech
        )

        intelligence = ProjectIntelligence(
            project_count=len(projects),
            project_names=project_names,
            technologies=technologies,
        )

        confidence = self._calculate_confidence(projects)
        return intelligence, confidence

    @staticmethod
    def _deduplicate(values: Iterable[str]) -> list[str]:
        """
        Deduplicate a sequence of strings case-insensitively, preserving
        first-seen order and original casing.

        Mirrors the existing `_deduplicate` helpers already used
        elsewhere in the AI pipeline (see
        app/ai/parsers/languages_parser.py,
        app/ai/parsers/skills_parser.py,
        app/ai/engines/education_intelligence.py) rather than
        introducing a new convention or a new shared utility module.
        """
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            key = value.strip().lower()
            if key and key not in seen:
                seen.add(key)
                result.append(value.strip())
        return result

    def _calculate_confidence(self, projects: list[Project]) -> float:
        """
        Compute a deterministic, weighted extraction-completeness score.

        Each stage contributes a 0.0-1.0 sub-score reflecting how much
        of the available project data could be extracted, combined
        using the weights in _CONFIDENCE_WEIGHTS (which sum to 1.0).
        As with the other Intelligence engines, this measures
        processing completeness, not the quality or complexity of the
        candidate's projects.
        """
        scores = {
            "name_extraction": self._field_presence_score(projects, "name"),
            "technology_extraction": self._technology_presence_score(projects),
            "description_presence": self._field_presence_score(projects, "description"),
        }
        confidence = sum(
            scores[key] * weight for key, weight in _CONFIDENCE_WEIGHTS.items()
        )
        return round(min(max(confidence, 0.0), 1.0), 4)

    @staticmethod
    def _field_presence_score(projects: list[Project], field: str) -> float:
        """Fraction of project entries with a non-null value for `field`."""
        if not projects:
            return 0.0
        filled = sum(1 for entry in projects if getattr(entry, field))
        return filled / len(projects)

    @staticmethod
    def _technology_presence_score(projects: list[Project]) -> float:
        """Fraction of project entries with at least one technology listed."""
        if not projects:
            return 0.0
        filled = sum(1 for entry in projects if entry.technologies)
        return filled / len(projects)