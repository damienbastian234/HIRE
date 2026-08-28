"""
Certification Intelligence data models for H.I.R.E.

These models represent the structured certification intelligence
produced by the Certification Intelligence engine (HIRE-AI-109) from a
candidate's CandidateProfile.certifications. They are pure data
contracts: no AI framework dependencies, no processing logic.

CandidateProfile.certifications is a list of `Certification` entries
(see app/models/candidate.py), each with only three fields: free-text
`name`, free-text `organization`, and `completion_date` (a free-text
field that, per the existing certifications_parser.py, is always
either None or a bare 4-digit year string extracted via the same
_YEAR_PATTERN regex used for Education.graduation_year). No credential
ID, URL, expiry date, or skill-tag field exists anywhere in the
schema. This model does not invent such structure; it only aggregates
and deduplicates what CandidateProfile already provides.
"""

from pydantic import BaseModel, Field


class CertificationIntelligence(BaseModel):
    """
    Complete certification intelligence output for a candidate,
    produced by the Certification Intelligence engine (HIRE-AI-109).

    Every field is derived directly from
    CandidateProfile.certifications, without inventing information
    (e.g. no prestige ranking, no validity/confidence judgment, no
    inferred skill proficiency) that the schema does not already
    capture.
    """

    certification_count: int = Field(
        ...,
        ge=0,
        description="Total number of certification records on the candidate's profile.",
    )
    certification_names: list[str] = Field(
        default_factory=list,
        description=(
            "Deduplicated, non-empty `name` values from the "
            "candidate's certification records, in first-seen order."
        ),
    )
    issuing_organizations: list[str] = Field(
        default_factory=list,
        description=(
            "Deduplicated, non-empty `organization` values from the "
            "candidate's certification records, in first-seen order."
        ),
    )
    most_recent_certification: str | None = Field(
        default=None,
        description=(
            "The `name` of the candidate's most recently completed "
            "certification, ordered by `completion_date` (a bare "
            "4-digit year, per certifications_parser.py). Falls back "
            "to the first certification record with a non-null `name` "
            "if no completion_date is resolvable. None if no "
            "certification record has a name at all. This is a "
            "recency signal only — Certification has no prestige, "
            "difficulty, or level field, so no ranking by importance "
            "is attempted or implied."
        ),
    )