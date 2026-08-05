"""
Skill Intelligence data models for H.I.R.E.

These models represent the structured skill intelligence produced by
the Skill Intelligence engine (HIRE-AI-103) from a candidate's
CandidateProfile.skills. They are pure data contracts: no AI-framework
dependencies, no processing logic.
"""

from typing import List

from pydantic import BaseModel, Field


class SkillCategory(BaseModel):
    """A single skill category and the candidate's skills within it."""

    name: str = Field(..., description="Category name, e.g. 'Programming Languages'.")
    skills: List[str] = Field(
        default_factory=list,
        description="Normalized skills belonging to this category.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Coverage of this category: the fraction of this category's "
            "known reference skills the candidate possesses, 0.0-1.0."
        ),
    )


class SkillMetrics(BaseModel):
    """Aggregate counts describing a candidate's skill set."""

    technical_skill_count: int = Field(
        ..., ge=0, description="Count of technical skills as reported by the CandidateProfile."
    )
    soft_skill_count: int = Field(
        ..., ge=0, description="Count of soft skills as reported by the CandidateProfile."
    )
    total_skills: int = Field(
        ..., ge=0, description="Total unique normalized skills (technical + soft, deduplicated)."
    )
    categorized_skills: int = Field(
        ..., ge=0, description="Count of normalized skills successfully assigned to a known category."
    )
    uncategorized_skills: int = Field(
        ..., ge=0, description="Count of normalized skills that did not match any known category."
    )


class SkillGap(BaseModel):
    """Generic, non-job-specific skill gap analysis."""

    missing_categories: List[str] = Field(
        default_factory=list, description="Known skill categories with zero skills present."
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Generic recommendations, one per missing category."
    )


class SkillIntelligence(BaseModel):
    """
    Complete skill intelligence output for a candidate, produced by the
    Skill Intelligence engine (HIRE-AI-103).
    """

    categories: List[SkillCategory] = Field(default_factory=list)
    metrics: SkillMetrics
    gaps: SkillGap
    normalized_skills: List[str] = Field(
        default_factory=list, description="Deduplicated, alias-normalized skill list."
    )
    duplicate_skills: List[str] = Field(
        default_factory=list,
        description="Original-form skill strings identified as duplicates of an already-normalized skill.",
    )