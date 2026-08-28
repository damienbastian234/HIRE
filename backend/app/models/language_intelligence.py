"""
Language Intelligence data models for H.I.R.E.

These models represent the structured language intelligence produced
by the Language Intelligence engine (HIRE-AI-110) from a candidate's
CandidateProfile.languages.

IMPORTANT — schema finding from inspection: unlike Education, Project,
and Certification, there is no `Language` model anywhere in
app/models/candidate.py. `CandidateProfile.languages` is a plain
`list[str]` ("Spoken languages, deduplicated." per its own field
description), and app/ai/parsers/languages_parser.py confirms it is
already deduplicated case-insensitively, first-seen order, before it
ever reaches CandidateProfile. There is no proficiency/level field, no
date field, and no per-entry structure of any kind to derive further
intelligence from.

Consequently this model is deliberately thinner than
EducationIntelligence / ProjectIntelligence / CertificationIntelligence:
- No proficiency/level field is exposed, because none exists in the
  schema to faithfully represent.
- No `primary_language` / `most_relevant_language` field is provided,
  because the schema contains no deterministic ordering signal (no
  date, no proficiency, nothing) to select one by. Inventing a
  "primary" language from an unordered list of plain strings would be
  arbitrary, not derived.
"""

from pydantic import BaseModel, Field


class LanguageIntelligence(BaseModel):
    """
    Complete language intelligence output for a candidate, produced by
    the Language Intelligence engine (HIRE-AI-110).

    Both fields are derived directly from CandidateProfile.languages,
    without inventing information (proficiency, fluency, importance,
    or a "primary" language) that the schema does not capture.
    """

    language_count: int = Field(
        ...,
        ge=0,
        description=(
            "Count of distinct languages after deduplication. Language "
            "has no per-entry record structure separate from the "
            "value itself (unlike Education/Project/Certification), "
            "so this reflects the deduplicated `languages` list below, "
            "not a raw pre-dedup entry count."
        ),
    )
    languages: list[str] = Field(
        default_factory=list,
        description=(
            "Deduplicated, non-empty language names from the "
            "candidate's profile, in first-seen order, whitespace-"
            "trimmed. Deduplication is case-insensitive (e.g. "
            "'English' and 'english' collapse to one entry, preserving "
            "the first-seen casing) but never semantic — no alias "
            "mapping (e.g. 'English' -> 'en') is applied."
        ),
    )