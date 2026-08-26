"""
Education Intelligence data models for H.I.R.E.

These models represent the structured education intelligence produced
by the Education Intelligence engine (HIRE-AI-107) from a candidate's
CandidateProfile.education. They are pure data contracts: no AI
framework dependencies, no processing logic.

CandidateProfile.education is a list of `Education` entries (see
app/models/candidate.py), each with free-text `degree`, `institution`,
`specialization`, `gpa`, and `graduation_year` fields — no structured
qualification-level, GPA scale, or institution-ranking field exists
anywhere in the schema. This model does not invent such structure; it
only aggregates and deduplicates what CandidateProfile already
provides, in the same shape it already exists in (plain strings).
"""

from pydantic import BaseModel, Field


class EducationIntelligence(BaseModel):
    """
    Complete education intelligence output for a candidate, produced by
    the Education Intelligence engine (HIRE-AI-107).

    Every field is derived directly from CandidateProfile.education,
    without inventing information (e.g. no qualification-level ranking
    system, no inferred grading scale) that the schema does not
    already capture.
    """

    highest_qualification: str | None = Field(
        default=None,
        description=(
            "The `degree` text of the candidate's most recently "
            "completed education record (by graduation_year), or the "
            "first education record's degree if no graduation_year is "
            "resolvable. None if no education records have a degree. "
            "Education has no structured qualification-level field, so "
            "recency is the only deterministic ordering signal the "
            "existing schema provides — this is not an academic-level "
            "ranking."
        ),
    )
    degrees: list[str] = Field(
        default_factory=list,
        description=(
            "Deduplicated, non-empty `degree` values from the "
            "candidate's education records, in first-seen order."
        ),
    )
    fields_of_study: list[str] = Field(
        default_factory=list,
        description=(
            "Deduplicated, non-empty `specialization` values from the "
            "candidate's education records, in first-seen order."
        ),
    )
    institutions: list[str] = Field(
        default_factory=list,
        description=(
            "Deduplicated, non-empty `institution` values from the "
            "candidate's education records, in first-seen order."
        ),
    )
    academic_performance: list[str] = Field(
        default_factory=list,
        description=(
            "Deduplicated, non-empty `gpa` values from the candidate's "
            "education records, in first-seen order, preserved exactly "
            "as extracted (CGPA, percentage, letter grade, etc.) — see "
            "Education.gpa. Never inferred when absent."
        ),
    )
    education_count: int = Field(
        ...,
        ge=0,
        description="Total number of education records on the candidate's profile.",
    )