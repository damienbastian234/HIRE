"""
Education section parser for Resume Intelligence (HIRE-AI-102).

Deterministic, pattern-based extraction only. See
personal_info_parser.py for the module-level design rationale shared
by every parser in this package.
"""

import re
from typing import List

from app.models.candidate import Education

_GPA_PATTERN = re.compile(r"(?:CGPA|GPA)\s*[:\-]?\s*([\d.]+)", re.IGNORECASE)
_YEAR_PATTERN = re.compile(r"(?:19|20)\d{2}")


def parse_education(section_text: str) -> List[Education]:
    """
    Extract education entries from the education section of a resume.

    Each non-empty line is treated as one education entry. Missing
    sub-fields within an entry are left as None rather than causing
    extraction to fail.

    Args:
        section_text: Raw text of the resume's education section. May
            be empty if the resume has no education section.

    Returns:
        A list of Education entries, empty if none could be found.
    """
    if not section_text or not section_text.strip():
        return []

    entries: List[Education] = []
    for line in section_text.splitlines():
        stripped = line.strip().lstrip("-•* ").strip()
        if not stripped:
            continue
        entries.append(_parse_education_line(stripped))
    return entries


def _parse_education_line(line: str) -> Education:
    gpa_match = _GPA_PATTERN.search(line)
    year_match = _YEAR_PATTERN.search(line)

    parts = [p.strip() for p in line.split(",") if p.strip()]
    degree = parts[0] if parts else None
    institution = parts[1] if len(parts) > 1 else None

    specialization = None
    if len(parts) > 2:
        candidate = parts[2]
        if not _GPA_PATTERN.search(candidate) and not _YEAR_PATTERN.search(candidate):
            specialization = candidate

    return Education(
        degree=degree,
        institution=institution,
        specialization=specialization,
        gpa=gpa_match.group(1) if gpa_match else None,
        graduation_year=year_match.group(0) if year_match else None,
    )