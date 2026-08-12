"""
Experience section parser for Resume Intelligence (HIRE-AI-102).

Deterministic, pattern-based extraction only. See
personal_info_parser.py for the module-level design rationale shared
by every parser in this package.
"""

import re

from app.models.candidate import Experience

_DATE_RANGE_PATTERN = re.compile(
    r"([A-Za-z]{3,9}\.?\s*\d{4}|\d{4})\s*(?:-|to|–|—)\s*"
    r"(Present|present|[A-Za-z]{3,9}\.?\s*\d{4}|\d{4})"
)
_EMPLOYMENT_TYPES = ["full-time", "part-time", "internship", "contract", "freelance"]


def parse_experience(section_text: str) -> list[Experience]:
    """
    Extract work experience entries from the experience section.

    Entries are separated by blank lines. Within an entry, the first
    line is treated as a "Position at Company (dates)" header, and
    subsequent bullet lines are treated as responsibilities.

    Args:
        section_text: Raw text of the resume's experience section. May
            be empty if the resume has no experience section.

    Returns:
        A list of Experience entries, empty if none could be found.
    """
    if not section_text or not section_text.strip():
        return []

    blocks = _split_into_blocks(section_text)
    return [_parse_experience_block(block) for block in blocks if block]


def _split_into_blocks(section_text: str) -> list[list[str]]:
    """Split section text into blocks of lines, separated by blank lines."""
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in section_text.splitlines():
        if line.strip():
            current.append(line.strip())
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def _parse_experience_block(lines: list[str]) -> Experience:
    header = lines[0]
    responsibilities = [
        line.lstrip("-•* ").strip() for line in lines[1:] if line.strip()
    ]

    date_match = _DATE_RANGE_PATTERN.search(header)
    start_date = date_match.group(1) if date_match else None
    end_date = date_match.group(2) if date_match else None

    header_without_dates = header
    if date_match:
        header_without_dates = _DATE_RANGE_PATTERN.sub("", header).strip(" ()-")

    employment_type = next(
        (t for t in _EMPLOYMENT_TYPES if t in header_without_dates.lower()), None
    )

    position, company = _split_position_company(header_without_dates)

    return Experience(
        company=company,
        position=position,
        employment_type=employment_type,
        start_date=start_date,
        end_date=end_date,
        duration=None,
        responsibilities=responsibilities,
    )


def _split_position_company(header: str) -> tuple[str | None, str | None]:
    """Split a 'Position at Company' or 'Position, Company' header."""
    for separator in [" at ", " - ", ", "]:
        if separator in header:
            position, _, company = header.partition(separator)
            return position.strip() or None, company.strip() or None
    return header.strip() or None, None