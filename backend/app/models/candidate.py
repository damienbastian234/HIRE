"""
Candidate data models for H.I.R.E.

These models represent the structured, validated candidate profile
produced by the Resume Intelligence engine (HIRE-AI-102) from raw
resume text. They are pure data contracts: no AI-framework
dependencies, no parsing logic. Downstream Intelligence Systems
(Skill Intelligence, Experience Intelligence, Candidate Matching,
etc.) consume `CandidateProfile` as their canonical input.
"""


from pydantic import BaseModel, Field


class PersonalInfo(BaseModel):
    """Extracted personal / contact information from a resume."""

    full_name: str | None = Field(default=None, description="Candidate's full name, if found.")
    email: str | None = Field(default=None, description="Candidate's email address, if found.")
    phone: str | None = Field(default=None, description="Candidate's phone number, if found.")
    linkedin_url: str | None = Field(default=None, description="LinkedIn profile URL, if found.")
    github_url: str | None = Field(default=None, description="GitHub profile URL, if found.")
    portfolio_url: str | None = Field(default=None, description="Portfolio/personal website URL, if found.")
    location: str | None = Field(default=None, description="Candidate's location, if found.")


class Education(BaseModel):
    """A single education entry."""

    degree: str | None = Field(default=None, description="Degree name, e.g. 'B.Tech in Computer Science'.")
    institution: str | None = Field(default=None, description="Name of the educational institution.")
    specialization: str | None = Field(default=None, description="Field of study or specialization, if distinct from degree.")
    gpa: str | None = Field(default=None, description="CGPA/GPA as extracted, kept as text to preserve original scale/format.")
    graduation_year: str | None = Field(default=None, description="Graduation year, if found.")


class Experience(BaseModel):
    """A single work experience entry."""

    company: str | None = Field(default=None, description="Employer name.")
    position: str | None = Field(default=None, description="Job title / role.")
    employment_type: str | None = Field(default=None, description="e.g. full-time, internship, contract, if stated.")
    start_date: str | None = Field(default=None, description="Start date as extracted from the resume text.")
    end_date: str | None = Field(default=None, description="End date as extracted, or 'Present' if ongoing.")
    duration: str | None = Field(default=None, description="Computed duration, where determinable.")
    responsibilities: list[str] = Field(default_factory=list, description="Bullet-point responsibilities/achievements for this role.")


class Project(BaseModel):
    """A single project entry."""

    name: str | None = Field(default=None, description="Project name/title.")
    description: str | None = Field(default=None, description="Short project description, if found.")
    technologies: list[str] = Field(default_factory=list, description="Technologies used in the project.")


class Certification(BaseModel):
    """A single certification entry."""

    name: str | None = Field(default=None, description="Certification name.")
    organization: str | None = Field(default=None, description="Issuing organization, if found.")
    completion_date: str | None = Field(default=None, description="Completion date/year, if found.")


class Skills(BaseModel):
    """Categorized skills extracted from a resume."""

    technical_skills: list[str] = Field(default_factory=list, description="Technical/hard skills, deduplicated.")
    soft_skills: list[str] = Field(default_factory=list, description="Soft skills, deduplicated.")


class CandidateProfile(BaseModel):
    """
    The complete structured representation of a candidate, assembled
    by the Resume Intelligence engine from raw resume text.

    This is the canonical candidate representation consumed by every
    downstream Intelligence System.
    """

    personal_info: PersonalInfo = Field(default_factory=PersonalInfo)
    education: list[Education] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    skills: Skills = Field(default_factory=Skills)
    projects: list[Project] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list, description="Spoken languages, deduplicated.")