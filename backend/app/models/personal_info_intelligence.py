"""
Personal Info Intelligence data models for H.I.R.E.

These models represent the structured intelligence produced by the
Personal Info Intelligence engine (HIRE-AI-111) from a candidate's
CandidateProfile.personal_info.

IMPORTANT — schema finding from inspection: `PersonalInfo`
(app/models/candidate.py) is a *single object*, not a list, with
seven independent optional string fields (`full_name`, `email`,
`phone`, `linkedin_url`, `github_url`, `portfolio_url`, `location`).
This is structurally different from every domain covered by
HIRE-AI-107 through HIRE-AI-110, all of which aggregated across a
*list* of records (dedup, counts, first-seen order). With exactly one
record, there is nothing to deduplicate or aggregate across, and no
date/score/level/category field exists to derive an ordering,
ranking, or "primary contact method" signal from.

Consequently this model deliberately does NOT re-expose the raw field
values (full_name, email, etc.). Duplicating them here would just
mirror CandidateProfile.personal_info verbatim, not derive anything
from it. The only intelligence the schema actually supports is a
completeness/presence audit: which of PersonalInfo's fields are
populated versus missing.
"""

from pydantic import BaseModel, Field


class PersonalInfoIntelligence(BaseModel):
    """
    Complete personal-info intelligence output for a candidate,
    produced by the Personal Info Intelligence engine (HIRE-AI-111).

    Both list fields are derived directly from which of
    CandidateProfile.personal_info's seven fields are populated
    (non-blank) versus missing, in the field's declaration order in
    PersonalInfo. No raw contact values (email addresses, phone
    numbers, URLs, etc.) are reproduced here — only field names,
    since exposing the underlying values would be duplication, not
    intelligence.
    """

    provided_fields: list[str] = Field(
        default_factory=list,
        description=(
            "Names of PersonalInfo fields with a non-blank value, in "
            "PersonalInfo's declaration order (full_name, email, "
            "phone, linkedin_url, github_url, portfolio_url, "
            "location)."
        ),
    )
    missing_fields: list[str] = Field(
        default_factory=list,
        description=(
            "Names of PersonalInfo fields that are None or "
            "whitespace-only, in the same declaration order as "
            "`provided_fields`."
        ),
    )
    provided_field_count: int = Field(
        ...,
        ge=0,
        description="Count of populated PersonalInfo fields (len(provided_fields)).",
    )