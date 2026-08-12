"""
Deterministic education matching helper for H.I.R.E.

Performs a simple case-insensitive comparison between the candidate's
highest education and the job's required degree.

No AI.
No NLP.
"""

from app.models.candidate import CandidateProfile
from app.models.candidate_matching_model import EducationMatch
from app.models.job_requirement import JobRequirement


def match_education(
    candidate: CandidateProfile,
    job: JobRequirement,
) -> EducationMatch:
    """
    Compare candidate education against job requirements.
    """

    required_degree = None
    candidate_degree = None

    if job.education and job.education.degrees:
        required_degree = job.education.degrees[0]

    if candidate.education:
        candidate_degree = candidate.education[0].degree

    if required_degree is None:
        meets = True
    elif candidate_degree is None:
        meets = False
    else:
        meets = (
            candidate_degree.strip().casefold()
            == required_degree.strip().casefold()
        )

    return EducationMatch(
        required_degree=required_degree,
        candidate_degree=candidate_degree,
        meets_requirement=meets,
    )