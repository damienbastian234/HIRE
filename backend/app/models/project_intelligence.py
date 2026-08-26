"""
Project Intelligence data models for H.I.R.E.

These models represent the structured project intelligence produced
by the Project Intelligence engine (HIRE-AI-108) from a candidate's
CandidateProfile.projects. They are pure data contracts: no AI
framework dependencies, no processing logic.

CandidateProfile.projects is a list of `Project` entries (see
app/models/candidate.py), each with only three fields: free-text
`name`, free-text `description`, and a `technologies` list — no
dates, roles, links, or outcomes exist anywhere in the schema. This
model does not invent such structure; it only aggregates and
deduplicates what CandidateProfile already provides.

`description` is intentionally not surfaced here as a raw list. Unlike
`degree`/`institution`/`gpa` on Education (short, structured-ish
tokens), a project description is free-form prose; reproducing it
verbatim in an aggregate list would just duplicate
CandidateProfile.projects without adding derived intelligence, and
risks inviting downstream code to read outcomes or judgments into text
that was never structured for that purpose. Description presence is
used only as a completeness signal inside the engine's confidence
calculation (see project_intelligence.py), not exposed as a field.
"""

from pydantic import BaseModel, Field


class ProjectIntelligence(BaseModel):
    """
    Complete project intelligence output for a candidate, produced by
    the Project Intelligence engine (HIRE-AI-108).

    Every field is derived directly from CandidateProfile.projects,
    without inventing information (e.g. no project-complexity ranking,
    no technology-prestige ranking, no inferred outcomes) that the
    schema does not already capture. Project has no date field, so —
    unlike Education's `highest_qualification` (ordered by
    graduation_year) — there is no data-driven signal here to single
    out a "primary" or "most recent" project; none is attempted.
    """

    project_count: int = Field(
        ...,
        ge=0,
        description="Total number of project records on the candidate's profile.",
    )
    project_names: list[str] = Field(
        default_factory=list,
        description=(
            "Deduplicated, non-empty `name` values from the "
            "candidate's project records, in first-seen order."
        ),
    )
    technologies: list[str] = Field(
        default_factory=list,
        description=(
            "Deduplicated, non-empty technology values across every "
            "one of the candidate's project records, in first-seen "
            "order."
        ),
    )