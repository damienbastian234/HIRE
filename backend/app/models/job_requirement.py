"""Job requirement domain models for H.I.R.E.

These models represent a structured job posting — the employer-side
counterpart to CandidateProfile (see app/models/candidate.py). They
are pure data contracts: no AI-framework dependencies, no database
dependencies, no business logic. Future engines (HIRE-AI-105+) will
compare a CandidateProfile against a JobRequirement to produce
candidate-job matching intelligence.
"""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class EmploymentType(StrEnum):
    """The employment arrangement offered for a job posting."""

    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    INTERN = "INTERN"
    FREELANCE = "FREELANCE"
    TEMPORARY = "TEMPORARY"


class WorkMode(StrEnum):
    """Where the role is performed."""

    ONSITE = "ONSITE"
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"


def _trim_or_none(value: str | None) -> str | None:
    """Strip whitespace from a string field; convert an empty result to None."""
    if value is None or not isinstance(value, str):
        return value

    stripped = value.strip()
    return stripped or None


def _trim_list_items(values: list[str] | None) -> list[str] | None:
    """Strip whitespace from each string in a list, dropping any that become empty."""
    if values is None:
        return values

    return [item.strip() for item in values if isinstance(item, str) and item.strip()]


class ExperienceRequirement(BaseModel):
    """
    Years-of-experience requirement for a job posting.
    """

    minimum_years: float = Field(
        ..., ge=0, description="Minimum years of experience required. Must be >= 0."
    )
    preferred_years: float | None = Field(
        default=None,
        ge=0,
        description="Preferred (ideal) years of experience, if any. Must be >= minimum_years when set.",
    )

    @model_validator(mode="after")
    def _validate_preferred_not_below_minimum(self) -> "ExperienceRequirement":
        """Ensure preferred_years, when set, is not lower than minimum_years."""
        if self.preferred_years is not None and self.preferred_years < self.minimum_years:
            raise ValueError("preferred_years must be greater than or equal to minimum_years.")
        return self


class SalaryRange(BaseModel):
    """
    Compensation range for a job posting.
    """

    minimum: float | None = Field(
        default=None, ge=0, description="Minimum salary offered, if disclosed. Must be >= 0."
    )
    maximum: float | None = Field(
        default=None, ge=0, description="Maximum salary offered, if disclosed. Must be >= 0."
    )
    currency: str = Field(
        default="INR", description="Currency code or symbol for this range. Defaults to INR."
    )

    @model_validator(mode="after")
    def _validate_maximum_not_below_minimum(self) -> "SalaryRange":
        """Ensure maximum, when both bounds are set, is not lower than minimum."""
        if self.minimum is not None and self.maximum is not None and self.maximum < self.minimum:
            raise ValueError("maximum must be greater than or equal to minimum.")
        return self

    @field_validator("currency", mode="before")
    @classmethod
    def _trim_currency(cls, value: str | None) -> str | None:
        """Trim whitespace from the currency field."""
        if isinstance(value, str):
            return value.strip()
        return value


class EducationRequirement(BaseModel):
    """
    Educational qualifications required or preferred for a job posting.
    """

    degrees: list[str] = Field(
        default_factory=list, description="Acceptable degree names, e.g. 'B.Tech', 'M.Sc'."
    )
    fields_of_study: list[str] = Field(
        default_factory=list, description="Acceptable fields of study, e.g. 'Computer Science'."
    )
    minimum_percentage: float | None = Field(
        default=None, ge=0, le=100, description="Minimum academic percentage required, 0-100."
    )
    minimum_cgpa: float | None = Field(
        default=None, ge=0, le=10, description="Minimum CGPA required, 0-10."
    )

    @field_validator("degrees", "fields_of_study", mode="before")
    @classmethod
    def _trim_list_fields(cls, value: list[str] | None) -> list[str] | None:
        """Trim whitespace from list items and drop blank values."""
        return _trim_list_items(value)


class SkillRequirement(BaseModel):
    """
    A single skill requirement for a job posting.

    Used for both `JobRequirement.required_skills` and
    `JobRequirement.preferred_skills`. The `required` flag describes
    this individual skill entry's own mandatory/optional status and is
    intentionally not cross-validated against which list it appears
    in — that association is left entirely to the caller, consistent
    with this ticket's "do not infer values" constraint.
    """

    name: str = Field(
        ...,
        min_length=1,
        description="Skill name, exactly as specified by the employer. No normalization or fuzzy matching is applied.",
    )
    required: bool = Field(
        default=True,
        description="Whether this specific skill is mandatory (True) or merely desirable (False).",
    )
    minimum_proficiency: str | None = Field(
        default=None,
        description=(
            "Free-text minimum proficiency descriptor (e.g. 'Intermediate'), "
            "if specified. No normalization or fuzzy matching is applied."
        ),
    )
    minimum_years: float | None = Field(
        default=None,
        ge=0,
        description="Minimum years of experience with this specific skill, if specified. Must be >= 0.",
    )

    @field_validator("name", mode="before")
    @classmethod
    def _trim_name(cls, value: str | None) -> str | None:
        """Trim whitespace from the skill name."""
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        """Ensure the trimmed skill name is not empty."""
        if not value:
            raise ValueError("name must not be empty")
        return value

    @field_validator("minimum_proficiency", mode="before")
    @classmethod
    def _trim_proficiency(cls, value: str | None) -> str | None:
        """Trim whitespace from proficiency text and convert empty values to None."""
        return _trim_or_none(value)


class JobRequirement(BaseModel):
    """
    The canonical structured representation of a job posting.

    This is the employer-side counterpart to CandidateProfile:
    downstream matching engines (HIRE-AI-105+) will compare a
    CandidateProfile against a JobRequirement to produce candidate-job
    fit intelligence.
    """

    job_id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for this job posting."
    )
    title: str = Field(..., min_length=1, description="Job title. Required, non-empty.")
    department: str | None = Field(default=None, description="Hiring department, if specified.")
    company: str | None = Field(default=None, description="Hiring company name, if specified.")
    location: str | None = Field(
        default=None, description="Job location, if specified (may be omitted for remote roles)."
    )
    work_mode: WorkMode | None = Field(
        default=None, description="Where the role is performed, if specified."
    )
    employment_type: EmploymentType | None = Field(
        default=None, description="Employment arrangement, if specified."
    )
    description: str | None = Field(default=None, description="Free-text job description, if provided.")
    responsibilities: list[str] = Field(
        default_factory=list, description="Job responsibilities, as a list of statements."
    )
    required_skills: list[SkillRequirement] = Field(
        default_factory=list, description="Skills mandatory for this role."
    )
    preferred_skills: list[SkillRequirement] = Field(
        default_factory=list, description="Skills that are a bonus but not mandatory for this role."
    )
    experience: ExperienceRequirement | None = Field(
        default=None, description="Years-of-experience requirement, if specified."
    )
    education: EducationRequirement | None = Field(
        default=None, description="Educational requirement, if specified."
    )
    salary: SalaryRange | None = Field(default=None, description="Compensation range, if disclosed.")
    keywords: list[str] = Field(
        default_factory=list, description="Free-form search/matching keywords for this posting."
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp this job requirement record was created, in UTC.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp this job requirement record was last updated, in UTC.",
    )

    @field_validator("title", mode="before")
    @classmethod
    def _trim_title(cls, value: str | None) -> str | None:
        """Trim whitespace from the title before validation."""
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("title")
    @classmethod
    def _validate_title(cls, value: str) -> str:
        """Ensure the trimmed title is not empty."""
        if not value:
            raise ValueError("title must not be empty")
        return value

    @field_validator("department", "company", "location", "description", mode="before")
    @classmethod
    def _trim_optional_text_fields(cls, value: str | None) -> str | None:
        """Trim optional text fields and convert empty values to None."""
        return _trim_or_none(value)

    @field_validator("responsibilities", "keywords", mode="before")
    @classmethod
    def _trim_list_fields(cls, value: list[str] | None) -> list[str] | None:
        """Trim whitespace from list items and drop blank values."""
        return _trim_list_items(value)
