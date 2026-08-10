"""
Experience Intelligence data models for H.I.R.E.

These models represent the structured experience analysis produced by
the Experience Intelligence engine (HIRE-AI-104) from a candidate's
CandidateProfile.experience. They are pure data contracts: no AI
framework dependencies, no processing logic.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SeniorityLevel(str, Enum):
    """Deterministic seniority band based on total years of experience."""

    ENTRY = "Entry"
    JUNIOR = "Junior"
    MID = "Mid"
    SENIOR = "Senior"
    PRINCIPAL = "Principal"


class TimelineEntry(BaseModel):
    """A single work experience entry, resolved onto a chronological timeline."""

    company: Optional[str] = Field(default=None, description="Employer name, as reported by CandidateProfile.")
    position: Optional[str] = Field(default=None, description="Job title, as reported by CandidateProfile.")
    start_year: Optional[int] = Field(default=None, description="Parsed start year, if resolvable.")
    start_month: Optional[int] = Field(default=None, description="Parsed start month (1-12), if resolvable.")
    end_year: Optional[int] = Field(default=None, description="Parsed end year, if resolvable and not ongoing.")
    end_month: Optional[int] = Field(default=None, description="Parsed end month (1-12), if resolvable and not ongoing.")
    is_current: bool = Field(default=False, description="True if this role's end date indicated ongoing employment (e.g. 'Present').")
    duration_months: Optional[int] = Field(default=None, ge=0, description="Computed tenure in months, if resolvable.")
    has_valid_dates: bool = Field(default=False, description="True if at least a start date could be parsed.")


class CareerTimeline(BaseModel):
    """Chronologically ordered employment history."""

    entries: List[TimelineEntry] = Field(
        default_factory=list,
        description="Timeline entries. Dated entries appear first in chronological (oldest-first) order; entries with no resolvable start date are appended afterward in their original order.",
    )


class ExperienceMetrics(BaseModel):
    """Aggregate metrics describing a candidate's work experience."""

    total_experience_months: int = Field(..., ge=0, description="Sum of resolvable tenure across all roles, in months.")
    total_experience_years: float = Field(..., ge=0.0, description="total_experience_months converted to years, rounded to 1 decimal place.")
    company_count: int = Field(..., ge=0, description="Count of distinct, named companies.")
    average_tenure_months: Optional[float] = Field(default=None, ge=0.0, description="Average tenure across roles with resolvable duration; None if no role has a resolvable duration.")
    longest_tenure_months: Optional[int] = Field(default=None, ge=0, description="Longest single-role tenure in months, among roles with resolvable duration.")
    shortest_tenure_months: Optional[int] = Field(default=None, ge=0, description="Shortest single-role tenure in months, among roles with resolvable duration.")
    is_currently_employed: bool = Field(default=False, description="True if any role is marked as current/ongoing.")


class CareerMove(BaseModel):
    """A single transition between two consecutive roles in the timeline."""

    from_company: Optional[str] = None
    from_position: Optional[str] = None
    to_company: Optional[str] = None
    to_position: Optional[str] = None
    move_type: str = Field(
        ...,
        description="One of: 'promotion', 'lateral_move', 'step_down', 'unknown' (title seniority not determinable).",
    )


class CareerProgression(BaseModel):
    """Career progression analysis across the candidate's full timeline."""

    moves: List[CareerMove] = Field(default_factory=list, description="One entry per transition between consecutive dated roles.")
    overall_trend: str = Field(
        ...,
        description="One of: 'growth', 'stable', 'unknown'.",
    )


class EmploymentGap(BaseModel):
    """A single detected gap between two consecutive roles."""

    after_company: Optional[str] = Field(default=None, description="Company held immediately before the gap.")
    before_company: Optional[str] = Field(default=None, description="Company held immediately after the gap.")
    gap_months: int = Field(..., ge=0, description="Length of the gap in months.")


class EmploymentGapAnalysis(BaseModel):
    """Aggregate employment gap analysis."""

    gaps: List[EmploymentGap] = Field(default_factory=list)
    gap_count: int = Field(..., ge=0)
    total_gap_months: int = Field(..., ge=0)


class StabilityAnalysis(BaseModel):
    """Deterministic job-stability metrics."""

    stability_score: float = Field(..., ge=0.0, le=1.0, description="Deterministic stability score, 0.0-1.0.")
    average_tenure_months: Optional[float] = Field(default=None, ge=0.0)
    job_change_count: int = Field(..., ge=0, description="Number of transitions between recorded roles.")
    longest_tenure_months: Optional[int] = Field(default=None, ge=0)


class ExperienceIntelligence(BaseModel):
    """
    Complete experience intelligence output for a candidate, produced
    by the Experience Intelligence engine (HIRE-AI-104).
    """

    timeline: CareerTimeline
    metrics: ExperienceMetrics
    progression: CareerProgression
    gap_analysis: EmploymentGapAnalysis
    stability: StabilityAnalysis
    seniority_level: SeniorityLevel