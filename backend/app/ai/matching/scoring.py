"""
Deterministic scoring helper for H.I.R.E.

Computes the weighted overall candidate match score.

Weights:
- Skills: 50%
- Experience: 35%
- Education: 15%
"""

from app.models.candidate_matching_model import (
    EducationMatch,
    ExperienceMatch,
    OverallScore,
    SkillMatch,
)

SKILL_WEIGHT = 0.50
EXPERIENCE_WEIGHT = 0.35
EDUCATION_WEIGHT = 0.15


def calculate_score(
    skill: SkillMatch,
    experience: ExperienceMatch,
    education: EducationMatch,
) -> OverallScore:
    """
    Calculate the weighted overall candidate score.
    """

    skill_score = skill.required_match_percentage

    experience_score = experience.experience_match_percentage

    education_score = 100.0 if education.meets_requirement else 0.0

    overall_score = (
        skill_score * SKILL_WEIGHT
        + experience_score * EXPERIENCE_WEIGHT
        + education_score * EDUCATION_WEIGHT
    )

    return OverallScore(
        skill_score=skill_score,
        experience_score=experience_score,
        education_score=education_score,
        overall_score=round(overall_score, 2),
    )