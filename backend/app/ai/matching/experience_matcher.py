"""
Deterministic experience matching helper for H.I.R.E.

Compares candidate experience against job requirements.

No AI.
No NLP.
No date parsing.
"""

from app.models.candidate import CandidateProfile
from app.models.candidate_matching_model import ExperienceMatch
from app.models.job_requirement import JobRequirement


def _total_years(candidate: CandidateProfile) -> float:
    """
    Calculate candidate experience.

    Uses the duration field only when it contains a numeric value.

    Future HIRE-AI-104 outputs may replace this implementation.
    """

    total = 0.0

    for experience in candidate.experience:
        duration = experience.duration

        if duration is None:
            continue

        try:
            total += float(duration)
        except ValueError:
            continue

    return total


def match_experience(
    candidate: CandidateProfile,
    job: JobRequirement,
) -> ExperienceMatch:
    """
    Compare candidate experience against the job requirement.
    """

    required = (
        job.experience.minimum_years
        if job.experience
        else 0.0
    )

    candidate_years = _total_years(candidate)

    meets = candidate_years >= required

    if required == 0:
        percentage = 100.0
    else:
        percentage = min(
            (candidate_years / required) * 100,
            100.0,
        )

    return ExperienceMatch(
        required_years=required,
        candidate_years=candidate_years,
        meets_requirement=meets,
        experience_match_percentage=percentage,
    )