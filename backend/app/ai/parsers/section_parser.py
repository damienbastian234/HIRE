"""
Section detection parser for Resume Intelligence (HIRE-AI-102).

Deterministic, pattern-based extraction only. See
personal_info_parser.py for the module-level design rationale shared
by every parser in this package.

Splitting raw resume text into named sections (education, experience,
skills, etc.) is itself a parsing responsibility, so it lives here as
its own component rather than inside the engine. This allows future
NLP-, OCR-, or LLM-based section detection to be introduced later
without any change to ResumeIntelligenceEngine, which only ever calls
`parse_sections(text)`.
"""

from typing import Dict, List

# Recognized section header text (case-insensitive) mapped to the
# canonical section key used by the rest of the parsing pipeline.
_SECTION_HEADER_ALIASES: Dict[str, str] = {
    alias: key
    for key, aliases in {
        "education": ["education", "academic background", "academics"],
        "experience": [
            "experience",
            "work experience",
            "employment history",
            "professional experience",
        ],
        "skills": ["skills", "technical skills", "skill set"],
        "projects": ["projects", "personal projects", "academic projects"],
        "certifications": [
            "certifications",
            "certificates",
            "licenses & certifications",
        ],
        "languages": ["languages", "language proficiency"],
    }.items()
    for alias in aliases
}


def parse_sections(text: str) -> Dict[str, str]:
    """
    Split raw resume text into named sections based on recognized
    header lines (e.g. "EDUCATION", "Work Experience:").

    Text before the first recognized header is not attributed to any
    section here — personal info is parsed from the full text
    separately by personal_info_parser, since contact details can
    appear anywhere in a resume.

    Args:
        text: Raw resume text. May be empty.

    Returns:
        A dict mapping canonical section keys (e.g. "education",
        "experience") to the raw text belonging to that section. Only
        keys for sections actually found in the text are present.
    """
    if not text:
        return {}

    sections: Dict[str, List[str]] = {}
    current_key = None

    for line in text.splitlines():
        normalized = line.strip().rstrip(":").strip().lower()
        if normalized in _SECTION_HEADER_ALIASES:
            current_key = _SECTION_HEADER_ALIASES[normalized]
            sections.setdefault(current_key, [])
            continue
        if current_key:
            sections[current_key].append(line)

    return {key: "\n".join(lines) for key, lines in sections.items()}