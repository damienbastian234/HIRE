"""
Certifications section parser for Resume Intelligence (HIRE-AI-102).

Deterministic, pattern-based extraction only. See
personal_info_parser.py for the module-level design rationale shared
by every parser in this package.
"""

import re
from typing import List, Optional

from app.models.candidate import Certification

_YEAR_PATTERN = re.compile(r"(?:19|20)\d{2}")


def parse_certifications(section_text: str) -> List[Certification]:
    """
    Extract certification entries from the certifications section.

    Each non-empty line is treated as one certification, in the form
    "Name - Organization - Year" (trailing parts are optional).

    Args:
        section_text: Raw text of the resume's certifications section.
            May be empty if the resume has no certifications section.

    Returns:
        A list of Certification entries, empty if none could be found.
    """
    if not section_text or not section_text.strip():
        return []

    entries: List[Certification] = []
    for line in section_text.splitlines():
        stripped = line.strip().lstrip("-•* ").strip()
        if not stripped:
            continue
        entries.append(_parse_certification_line(stripped))
    return entries


def _parse_certification_line(line: str) -> Certification:
    year_match = _YEAR_PATTERN.search(line)
    without_year = _YEAR_PATTERN.sub("", line).strip(" ,-")

    parts = [p.strip() for p in without_year.split("-") if p.strip()]
    if len(parts) == 1:
        parts = [p.strip() for p in without_year.split(",") if p.strip()]

    name = parts[0] if parts else None
    organization = parts[1] if len(parts) > 1 else None

    return Certification(
        name=name,
        organization=organization,
        completion_date=year_match.group(0) if year_match else None,
    )