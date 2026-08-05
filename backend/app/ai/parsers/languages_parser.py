"""
Languages section parser for Resume Intelligence (HIRE-AI-102).

Deterministic, pattern-based extraction only. See
personal_info_parser.py for the module-level design rationale shared
by every parser in this package.
"""

import re
from typing import List

_LABEL_PATTERN = re.compile(r"^[A-Za-z ]+:\s*")


def parse_languages(section_text: str) -> List[str]:
    """
    Extract known spoken languages from the languages section.

    Args:
        section_text: Raw text of the resume's languages section. May
            be empty if the resume has no languages section.

    Returns:
        A deduplicated list of language names, empty if none found.
    """
    if not section_text or not section_text.strip():
        return []

    items: List[str] = []
    for line in section_text.splitlines():
        stripped = line.strip().lstrip("-•* ").strip()
        if not stripped:
            continue
        stripped = _LABEL_PATTERN.sub("", stripped)
        items.extend(part.strip() for part in re.split(r"[,;]", stripped) if part.strip())

    return _deduplicate(items)


def _deduplicate(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result