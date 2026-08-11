"""
Candidate Matching data models for H.I.R.E.

These models represent the final output of the Candidate Matching
Intelligence Engine: a structured comparison between a CandidateProfile
(see app/models/candidate.py) and a JobRequirement (see
app/models/job_requirement.py). They are pure data contracts — no
scoring logic, no recommendation logic, no confidence calculation, no
comparison logic. All of that belongs to the engine and its helper
modules, implemented in later steps of HIRE-AI-105.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RecommendationLevel(StrEnum):
    """Overall hiring recommendation tier produced by the matching engine."""

    STRONG_MATCH = "Strong Match"
    GOOD_MATCH = "Good Match"
    POSSIBLE_MATCH = "Possible Match"
    WEAK_MATCH = "Weak Match"
    NOT_RECOMMENDED = "Not Recommended"


class SkillMatch(BaseModel):
    """
    Result of comparing a candidate's skills against a job's required
    and preferred skills.
    """

    model_config = ConfigDict(extra="forbid")

    matched_required_skills: list[str] = Field(
        default_factory=list,
        description="Required skills the candidate possesses.",
    )
    missing_required_skills: list[str] = Field(
        default_factory=list,
        description="Required skills the candidate does not possess.",
    )
    matched_preferred_skills: list[str] = Field(
        default_factory=list,
        description="Preferred (non-mandatory) skills the candidate possesses.",
    )
    required_match_percentage: float = Field(
        ...,
        ge=0,
        le=100,
        description="Percentage of required skills matched, 0-100.",
    )
    preferred_match_percentage: float = Field(
        ...,
        ge=0,
        le=100,
        description="Percentage of preferred skills matched, 0-100.",
    )


class ExperienceMatch(BaseModel):
    """Result of comparing a candidate's total experience against a job's requirement."""

    model_config = ConfigDict(extra="forbid")

    required_years: float = Field(
        ..., ge=0, description="Years of experience required by the job. Must be >= 0."
    )
    candidate_years: float = Field(
        ..., ge=0, description="Years of experience the candidate has. Must be >= 0."
    )
    meets_requirement: bool = Field(
        ...,
        description="Whether the candidate's experience meets the job's requirement.",
    )
    experience_match_percentage: float = Field(
        ...,
        ge=0,
        le=100,
        description="Percentage representing how closely candidate experience matches the requirement, 0-100.",
    )


class EducationMatch(BaseModel):
    """
    Result of comparing a candidate's education against a job's
    education requirement.

    Holds only the two degree values being compared and the outcome;
    it performs no comparison itself — that logic belongs to the
    engine that populates this model.
    """

    model_config = ConfigDict(extra="forbid")

    required_degree: str | None = Field(
        default=None, description="Degree required by the job, if any."
    )
    candidate_degree: str | None = Field(
        default=None, description="Degree held by the candidate, if any."
    )
    meets_requirement: bool = Field(
        ...,
        description="Whether the candidate's education meets the job's requirement.",
    )


class OverallScore(BaseModel):
    """Aggregate scoring breakdown for a single candidate-job comparison."""

    model_config = ConfigDict(extra="forbid")

    skill_score: float = Field(..., ge=0, le=100, description="Skill-match component score, 0-100.")
    experience_score: float = Field(
        ..., ge=0, le=100, description="Experience-match component score, 0-100."
    )
    education_score: float = Field(
        ..., ge=0, le=100, description="Education-match component score, 0-100."
    )
    overall_score: float = Field(
        ..., ge=0, le=100, description="Combined overall match score, 0-100."
    )


class CandidateMatching(BaseModel):
    """
    Complete candidate-job matching result produced by the Candidate
    Matching Intelligence Engine.

    This is a pure data contract: it holds the outcome of matching a
    CandidateProfile against a JobRequirement, but contains no logic
    for how that outcome is computed. Scoring, recommendation
    derivation, and confidence calculation are implemented by the
    engine (a later step of HIRE-AI-105), not by this model.
    """

    model_config = ConfigDict(extra="forbid")

    skill_match: SkillMatch = Field(..., description="Detailed skill comparison result.")
    experience_match: ExperienceMatch = Field(
        ..., description="Detailed experience comparison result."
    )
    education_match: EducationMatch = Field(
        ..., description="Detailed education comparison result."
    )
    overall_score: OverallScore = Field(..., description="Aggregate scoring breakdown.")
    recommendation: RecommendationLevel = Field(
        ..., description="Overall hiring recommendation tier."
    )
    confidence: float = Field(
        ...,
        ge=0,
        le=100,
        description="Confidence in this matching result, 0-100.",
    )
