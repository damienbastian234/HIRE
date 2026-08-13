"""
Shared pytest fixtures for HIRE-AI-106 tests.
"""

import pytest

from app.models.job_requirement import (
    EducationRequirement,
    ExperienceRequirement,
    JobRequirement,
    SkillRequirement,
)

SAMPLE_RESUME_TEXT = """John Doe
john.doe@example.com
+1 555-123-4567
linkedin.com/in/johndoe
github.com/johndoe

EDUCATION
B.Tech Computer Science, Example University, 2020, CGPA: 8.5

EXPERIENCE
Software Engineer at Example Corp (Jan 2021 - Present)
- Built backend services
- Led a team of 3 engineers

SKILLS
Technical Skills: Python, FastAPI, PostgreSQL, Docker
Soft Skills: Communication, Leadership

PROJECTS
Resume Analyzer - AI-powered resume parsing tool
Technologies: Python, FastAPI

CERTIFICATIONS
AWS Certified Developer - Amazon - 2022

LANGUAGES
English, Spanish
"""


@pytest.fixture
def sample_resume_text() -> str:
    return SAMPLE_RESUME_TEXT


@pytest.fixture
def sample_job_requirement() -> JobRequirement:
    return JobRequirement(
        title="Backend Engineer",
        required_skills=[
            SkillRequirement(name="Python"),
            SkillRequirement(name="FastAPI"),
        ],
        preferred_skills=[
            SkillRequirement(name="Docker", required=False),
        ],
        experience=ExperienceRequirement(minimum_years=1.0),
        education=EducationRequirement(degrees=["B.Tech"]),
    )


@pytest.fixture
def sample_job_requirement_payload(sample_job_requirement: JobRequirement) -> dict:
    """JSON-serializable form of sample_job_requirement for request bodies."""
    return sample_job_requirement.model_dump(mode="json")