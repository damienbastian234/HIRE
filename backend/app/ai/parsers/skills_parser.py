"""
Skills section parser for Resume Intelligence (HIRE-AI-102).

Deterministic, pattern-based extraction only. See
personal_info_parser.py for the module-level design rationale shared
by every parser in this package.
"""

import re
from typing import List

from app.models.candidate import Skills

_TECHNICAL_LABELS = {"technical skills", "technical", "programming languages", "tech skills"}
_SOFT_LABELS = {"soft skills", "soft"}


def parse_skills(section_text: str) -> Skills:
    """
    Extract and categorize skills from the skills section of a resume.

    If the section explicitly labels "Technical Skills:" and
    "Soft Skills:" sub-lines, those labels are honored. Otherwise, all
    comma/semicolon-separated items in the section are treated as
    technical skills, since that's the far more common unlabeled
    convention. Duplicate skills (case-insensitive) are removed while
    preserving first-seen order and original casing.

    Args:
        section_text: Raw text of the resume's skills section. May be
            empty if the resume has no skills section.

    Returns:
        A Skills instance with deduplicated technical_skills and
        soft_skills lists.
    """
    if not section_text or not section_text.strip():
        return Skills()

    technical: List[str] = []
    soft: List[str] = []
    unlabeled: List[str] = []

    for line in section_text.splitlines():
        stripped = line.strip().lstrip("-•* ").strip()
        if not stripped:
            continue

        label, sep, rest = stripped.partition(":")
        label_normalized = label.strip().lower()

        if sep and label_normalized in _TECHNICAL_LABELS:
            technical.extend(_split_items(rest))
        elif sep and label_normalized in _SOFT_LABELS:
            soft.extend(_split_items(rest))
        else:
            unlabeled.extend(_split_items(stripped))

    if not technical and not soft:
        technical = unlabeled

    return Skills(
        technical_skills=_deduplicate(technical),
        soft_skills=_deduplicate(soft),
    )


def _split_items(text: str) -> List[str]:
    return [item.strip() for item in re.split(r"[,;]", text) if item.strip()]


def _deduplicate(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result