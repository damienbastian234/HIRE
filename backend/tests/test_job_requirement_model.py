"""Unit tests for the Job Requirement domain models."""

import json
import time

import pytest
from pydantic import ValidationError

from app.models.job_requirement import (
    EducationRequirement,
    EmploymentType,
    ExperienceRequirement,
    JobRequirement,
    SalaryRange,
    SkillRequirement,
    WorkMode,
)

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


def test_employment_type_enum_values():
    assert EmploymentType.FULL_TIME.value == "FULL_TIME"
    assert EmploymentType.PART_TIME.value == "PART_TIME"
    assert EmploymentType.CONTRACT.value == "CONTRACT"
    assert EmploymentType.INTERN.value == "INTERN"
    assert EmploymentType.FREELANCE.value == "FREELANCE"
    assert EmploymentType.TEMPORARY.value == "TEMPORARY"


def test_work_mode_enum_values():
    assert WorkMode.ONSITE.value == "ONSITE"
    assert WorkMode.REMOTE.value == "REMOTE"
    assert WorkMode.HYBRID.value == "HYBRID"


# ---------------------------------------------------------------------------
# ExperienceRequirement
# ---------------------------------------------------------------------------


def test_experience_requirement_valid():
    exp = ExperienceRequirement(minimum_years=2, preferred_years=5)
    assert exp.minimum_years == 2
    assert exp.preferred_years == 5


def test_experience_requirement_no_preferred_is_valid():
    exp = ExperienceRequirement(minimum_years=3)
    assert exp.preferred_years is None


def test_experience_requirement_negative_minimum_invalid():
    with pytest.raises(ValidationError):
        ExperienceRequirement(minimum_years=-1)


def test_experience_requirement_preferred_less_than_minimum_invalid():
    with pytest.raises(ValidationError):
        ExperienceRequirement(minimum_years=5, preferred_years=2)


def test_experience_requirement_preferred_equal_minimum_valid():
    exp = ExperienceRequirement(minimum_years=4, preferred_years=4)
    assert exp.preferred_years == exp.minimum_years


# ---------------------------------------------------------------------------
# SalaryRange
# ---------------------------------------------------------------------------


def test_salary_range_valid():
    salary = SalaryRange(minimum=50000, maximum=80000)
    assert salary.minimum == 50000
    assert salary.maximum == 80000


def test_salary_range_max_less_than_min_invalid():
    with pytest.raises(ValidationError):
        SalaryRange(minimum=80000, maximum=50000)


def test_salary_range_default_currency():
    salary = SalaryRange(minimum=10000, maximum=20000)
    assert salary.currency == "INR"


def test_salary_range_negative_minimum_invalid():
    with pytest.raises(ValidationError):
        SalaryRange(minimum=-100, maximum=50000)


def test_salary_range_only_minimum_is_valid():
    salary = SalaryRange(minimum=50000)
    assert salary.maximum is None


# ---------------------------------------------------------------------------
# EducationRequirement
# ---------------------------------------------------------------------------


def test_education_requirement_valid_cgpa():
    edu = EducationRequirement(minimum_cgpa=8.5)
    assert edu.minimum_cgpa == 8.5


def test_education_requirement_invalid_cgpa_too_high():
    with pytest.raises(ValidationError):
        EducationRequirement(minimum_cgpa=10.5)


def test_education_requirement_invalid_cgpa_negative():
    with pytest.raises(ValidationError):
        EducationRequirement(minimum_cgpa=-0.5)


def test_education_requirement_valid_percentage():
    edu = EducationRequirement(minimum_percentage=75)
    assert edu.minimum_percentage == 75


def test_education_requirement_invalid_percentage_too_high():
    with pytest.raises(ValidationError):
        EducationRequirement(minimum_percentage=101)


def test_education_requirement_invalid_percentage_negative():
    with pytest.raises(ValidationError):
        EducationRequirement(minimum_percentage=-1)


def test_education_requirement_degree_list_trimmed():
    edu = EducationRequirement(degrees=["  B.Tech  ", "", "M.Sc"])
    assert edu.degrees == ["B.Tech", "M.Sc"]


# ---------------------------------------------------------------------------
# SkillRequirement
# ---------------------------------------------------------------------------


def test_skill_requirement_required_true():
    skill = SkillRequirement(name="Python", required=True)
    assert skill.required is True


def test_skill_requirement_optional_false():
    skill = SkillRequirement(name="Docker", required=False)
    assert skill.required is False


def test_skill_requirement_invalid_negative_years():
    with pytest.raises(ValidationError):
        SkillRequirement(name="Python", minimum_years=-2)


def test_skill_requirement_empty_name_invalid():
    with pytest.raises(ValidationError):
        SkillRequirement(name="")


def test_skill_requirement_name_trimmed():
    skill = SkillRequirement(name="  Python  ")
    assert skill.name == "Python"


# ---------------------------------------------------------------------------
# JobRequirement
# ---------------------------------------------------------------------------


def test_job_requirement_minimal_object():
    job = JobRequirement(title="Backend Engineer")
    assert job.title == "Backend Engineer"
    assert job.department is None
    assert job.responsibilities == []
    assert job.required_skills == []


def test_job_requirement_full_object():
    job = JobRequirement(
        title="Senior Backend Engineer",
        department="Engineering",
        company="Acme Corp",
        location="Chennai, India",
        work_mode=WorkMode.HYBRID,
        employment_type=EmploymentType.FULL_TIME,
        description="Build and maintain APIs.",
        responsibilities=["Design APIs", "Mentor juniors"],
        required_skills=[SkillRequirement(name="Python", minimum_years=3)],
        preferred_skills=[SkillRequirement(name="Docker", required=False)],
        experience=ExperienceRequirement(minimum_years=5, preferred_years=8),
        education=EducationRequirement(degrees=["B.Tech"], minimum_cgpa=7.0),
        salary=SalaryRange(minimum=1500000, maximum=2500000),
        keywords=["backend", "python", "api"],
    )
    assert job.work_mode == WorkMode.HYBRID
    assert job.employment_type == EmploymentType.FULL_TIME
    assert len(job.required_skills) == 1
    assert len(job.preferred_skills) == 1
    assert job.salary.currency == "INR"


def test_job_requirement_empty_responsibilities():
    job = JobRequirement(title="X", responsibilities=[])
    assert job.responsibilities == []


def test_job_requirement_empty_preferred_skills():
    job = JobRequirement(title="X", preferred_skills=[])
    assert job.preferred_skills == []


def test_job_requirement_empty_keywords():
    job = JobRequirement(title="X", keywords=[])
    assert job.keywords == []


def test_job_requirement_empty_title_invalid():
    with pytest.raises(ValidationError):
        JobRequirement(title="   ")


def test_job_requirement_whitespace_trimmed():
    job = JobRequirement(title="  Backend Engineer  ", company="  Acme  ")
    assert job.title == "Backend Engineer"
    assert job.company == "Acme"


def test_job_requirement_empty_string_converted_to_none():
    job = JobRequirement(title="X", department="   ", location="")
    assert job.department is None
    assert job.location is None


def test_job_requirement_list_items_trimmed_and_blanks_dropped():
    job = JobRequirement(
        title="X",
        responsibilities=["  Write code  ", "", "   ", "Review PRs"],
        keywords=["python", "  ", "backend"],
    )
    assert job.responsibilities == ["Write code", "Review PRs"]
    assert job.keywords == ["python", "backend"]


def test_job_requirement_auto_generates_job_id():
    job1 = JobRequirement(title="X")
    job2 = JobRequirement(title="Y")
    assert job1.job_id != job2.job_id


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def test_job_requirement_model_dump():
    job = JobRequirement(title="Backend Engineer", employment_type=EmploymentType.FULL_TIME)
    dumped = job.model_dump()
    assert isinstance(dumped, dict)
    assert dumped["title"] == "Backend Engineer"
    assert dumped["employment_type"] == EmploymentType.FULL_TIME


def test_job_requirement_model_validate_round_trip():
    original = JobRequirement(
        title="Backend Engineer",
        required_skills=[SkillRequirement(name="Python", minimum_years=2)],
        salary=SalaryRange(minimum=50000, maximum=80000),
    )
    dumped = original.model_dump()
    reconstructed = JobRequirement.model_validate(dumped)
    assert reconstructed.title == original.title
    assert reconstructed.required_skills[0].name == "Python"
    assert reconstructed.salary.minimum == 50000


def test_job_requirement_json_serialization():
    job = JobRequirement(title="Backend Engineer", work_mode=WorkMode.REMOTE)
    json_str = job.model_dump_json()
    parsed = json.loads(json_str)
    assert parsed["title"] == "Backend Engineer"
    assert parsed["work_mode"] == "REMOTE"
    # Round-trip through JSON
    reconstructed = JobRequirement.model_validate_json(json_str)
    assert reconstructed.title == job.title
    assert reconstructed.work_mode == WorkMode.REMOTE


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


def test_construct_1000_job_requirements_under_100ms():
    start = time.perf_counter()
    jobs = [
        JobRequirement(
            title=f"Job {i}",
            required_skills=[SkillRequirement(name="Python", minimum_years=2)],
            experience=ExperienceRequirement(minimum_years=2, preferred_years=4),
            salary=SalaryRange(minimum=50000, maximum=80000),
        )
        for i in range(1000)
    ]
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert len(jobs) == 1000
    assert elapsed_ms < 100.0


def test_title_with_only_whitespace_is_invalid():
    with pytest.raises(ValidationError):
        JobRequirement(title="   ")


def test_title_is_trimmed_and_optional_fields_are_normalized():
    job = JobRequirement(
        title="  Backend Engineer  ",
        department="   ",
        company="  Acme  ",
        location="",
        description="  Build APIs  ",
    )

    assert job.title == "Backend Engineer"
    assert job.department is None
    assert job.company == "Acme"
    assert job.location is None
    assert job.description == "Build APIs"


def test_skill_name_is_trimmed_and_empty_name_is_invalid():
    skill = SkillRequirement(name="  Python  ")
    assert skill.name == "Python"

    with pytest.raises(ValidationError):
        SkillRequirement(name="   ")
