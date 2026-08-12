"""
Personal / contact information parser for Resume Intelligence (HIRE-AI-102).

Deterministic, regex/pattern-based extraction only. This module has no
AI framework dependencies — it is a pure text-in, model-out component
so it can be swapped for an NLP- or LLM-based implementation in a
future ticket without the engine's interface changing.
"""

import re

from app.models.candidate import PersonalInfo

_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_PATTERN = re.compile(
    r"(?:\+?\d{1,3}[\s.-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}"
)
_LINKEDIN_PATTERN = re.compile(r"(https?://)?(www\.)?linkedin\.com/\S+", re.IGNORECASE)
_GITHUB_PATTERN = re.compile(r"(https?://)?(www\.)?github\.com/\S+", re.IGNORECASE)
_LABELED_LINE_PATTERN = re.compile(r"^\s*([A-Za-z ]+):\s*(.+)$")

_LABEL_TO_FIELD = {
    "portfolio": "portfolio_url",
    "website": "portfolio_url",
    "location": "location",
    "address": "location",
    "based in": "location",
}


def parse_personal_info(text: str) -> PersonalInfo:
    """
    Extract personal/contact information from raw resume text.

    Searches the full text (not a single section) for email, phone,
    and profile-URL patterns, since contact details can appear
    anywhere in a resume.

    Args:
        text: Raw resume text. May be empty.

    Returns:
        A PersonalInfo instance with any fields that could be found
        populated, and the rest left as None.
    """
    if not text or not text.strip():
        return PersonalInfo()

    email_match = _EMAIL_PATTERN.search(text)
    phone_match = _PHONE_PATTERN.search(text)
    linkedin_match = _LINKEDIN_PATTERN.search(text)
    github_match = _GITHUB_PATTERN.search(text)

    labeled_values = _extract_labeled_values(text)

    return PersonalInfo(
        full_name=_extract_full_name(text),
        email=email_match.group(0) if email_match else None,
        phone=phone_match.group(0).strip() if phone_match else None,
        linkedin_url=linkedin_match.group(0) if linkedin_match else None,
        github_url=github_match.group(0) if github_match else None,
        portfolio_url=labeled_values.get("portfolio_url"),
        location=labeled_values.get("location"),
    )


def _extract_labeled_values(text: str) -> dict:
    """Scan for 'Label: value' lines matching known personal-info labels."""
    found: dict = {}
    for line in text.splitlines():
        match = _LABELED_LINE_PATTERN.match(line)
        if not match:
            continue
        label = match.group(1).strip().lower()
        field = _LABEL_TO_FIELD.get(label)
        if field and field not in found:
            found[field] = match.group(2).strip()
    return found


def _extract_full_name(text: str) -> str | None:
    """
    Heuristically treat the first non-empty line as the candidate's
    name, provided it doesn't look like an email, phone number, or a
    labeled contact field.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _EMAIL_PATTERN.search(stripped):
            return None
        digit_count = len(re.sub(r"\D", "", stripped))
        if _PHONE_PATTERN.search(stripped) and digit_count >= 7:
            return None
        if _LABELED_LINE_PATTERN.match(stripped):
            return None
        return stripped
    return None