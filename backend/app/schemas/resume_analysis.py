"""
Request and response data schemas for the Resume Analysis API
(HIRE-AI-106, POST /api/v1/resume/analyze).

These are pure data contracts only — no parsing, scoring, matching,
or orchestration logic lives here. They exist because no request
schema for this endpoint previously existed and the response payload
needs a typed shape to subscript the existing `SuccessResponse`
envelope (see app/schemas/responses.py).

Existing models are reused directly wherever possible:
    - JobRequirement    (app.models.job_requirement)
    - CandidateProfile  (app.models.candidate)
    - SkillIntelligence (app.models.skill_intelligence)
    - ExperienceIntelligence (app.models.experience_intelligence_model)
    - CandidateMatching (app.models.candidate_matching_model)

Nothing here duplicates or redefines those models.
"""

from pydantic import BaseModel, Field, field_validator

from app.models.candidate import CandidateProfile
from app.models.candidate_matching_model import CandidateMatching
from app.models.experience_intelligence_model import ExperienceIntelligence
from app.models.job_requirement import JobRequirement
from app.models.skill_intelligence import SkillIntelligence


class ResumeAnalysisRequest(BaseModel):
    """
    Request body for POST /api/v1/resume/analyze.

    Accepts plain resume text (no PDF/DOCX extraction — out of scope
    for this ticket) and a job requirement to match the candidate
    against, reusing the existing JobRequirement model directly.
    """

    resume_text: str = Field(
        ...,
        min_length=1,
        description="Raw resume text to analyze. Must not be empty or whitespace-only.",
    )
    job_requirement: JobRequirement = Field(
        ...,
        description="Job posting to match the parsed candidate against.",
    )

    @field_validator("resume_text")
    @classmethod
    def _reject_blank_resume_text(cls, value: str) -> str:
        """Reject whitespace-only resume text as a validation error (missing resume)."""
        if not value.strip():
            raise ValueError("resume_text must not be blank.")
        return value


class ResumeAnalysisData(BaseModel):
    """
    Aggregated result of a full resume analysis workflow, returned as
    the `data` payload of `SuccessResponse[ResumeAnalysisData]`.

    Bundles the outputs of all four Intelligence Systems the workflow
    coordinates, without altering any of their existing shapes.
    """

    candidate_profile: CandidateProfile = Field(
        ..., description="Structured candidate profile parsed from the resume text."
    )
    skill_intelligence: SkillIntelligence = Field(
        ..., description="Skill Intelligence output for the candidate."
    )
    experience_intelligence: ExperienceIntelligence = Field(
        ..., description="Experience Intelligence output for the candidate."
    )
    candidate_matching: CandidateMatching = Field(
        ...,
        description="Candidate-job matching result against the job requirement",
    )