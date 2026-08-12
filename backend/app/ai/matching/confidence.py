"""
Deterministic confidence helper for H.I.R.E.

Confidence measures how complete the comparison was,
not how good the candidate is.
"""

from app.models.candidate_matching_model import (
    EducationMatch,
    ExperienceMatch,
    SkillMatch,
)


def calculate_confidence(
    skill: SkillMatch,
    experience: ExperienceMatch,
    education: EducationMatch,
) -> float:
    """
    Calculate comparison completeness.
    """

    confidence = 100.0

    if (
        not skill.matched_required_skills
        and not skill.missing_required_skills
    ):
        confidence -= 40

    if experience.required_years == 0:
        confidence -= 20

    if education.required_degree is None:
        confidence -= 20

    return max(confidence, 0.0)