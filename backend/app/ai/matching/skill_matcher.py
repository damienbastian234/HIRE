"""
Deterministic skill matching helper for H.I.R.E.

This module compares a CandidateProfile against a JobRequirement and
produces a SkillMatch result.

No AI.
No fuzzy matching.
No NLP.
"""

from app.models.candidate import CandidateProfile
from app.models.candidate_matching_model import SkillMatch
from app.models.job_requirement import JobRequirement


def _normalize(values: list[str]) -> set[str]:
    """
    Normalize strings for deterministic comparison.

    - strip whitespace
    - lowercase
    - remove blanks
    """

    return {
        value.strip().lower()
        for value in values
        if isinstance(value, str) and value.strip()
    }


def match_skills(
    candidate: CandidateProfile,
    job: JobRequirement,
) -> SkillMatch:
    """
    Compare candidate skills against job requirements.

    Comparison is:

    - deterministic
    - exact
    - case-insensitive

    No fuzzy matching.
    """

    candidate_skills = _normalize(candidate.skills.technical_skills)

    required = {
        skill.name.strip().lower()
        for skill in job.required_skills
    }

    preferred = {
        skill.name.strip().lower()
        for skill in job.preferred_skills
    }

    matched_required = sorted(
        skill
        for skill in required
        if skill in candidate_skills
    )

    missing_required = sorted(
        skill
        for skill in required
        if skill not in candidate_skills
    )

    matched_preferred = sorted(
        skill
        for skill in preferred
        if skill in candidate_skills
    )

    if required:
        required_percentage = (
            len(matched_required) / len(required)
        ) * 100
    else:
        required_percentage = 100.0

    if preferred:
        preferred_percentage = (
            len(matched_preferred) / len(preferred)
        ) * 100
    else:
        preferred_percentage = 100.0

    return SkillMatch(
        matched_required_skills=matched_required,
        missing_required_skills=missing_required,
        matched_preferred_skills=matched_preferred,
        required_match_percentage=required_percentage,
        preferred_match_percentage=preferred_percentage,
    )