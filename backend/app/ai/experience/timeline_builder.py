"""
Timeline builder for Experience Intelligence (HIRE-AI-104).

Deterministic date parsing only — no AI, no NLP, no fuzzy matching.
A pure input/output component: given a candidate's raw experience
entries, resolves their start/end dates where possible and produces a
chronologically ordered CareerTimeline. Tolerates missing dates,
"Present"/ongoing employment, a single job, and empty experience.
"""

import re
from datetime import datetime, timezone

from app.models.candidate import Experience
from app.models.experience_intelligence_model import CareerTimeline, TimelineEntry

_MONTH_NAMES = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

_MONTH_YEAR_PATTERN = re.compile(r"^([A-Za-z]{3,9})\.?\s+(\d{4})$")
_YEAR_ONLY_PATTERN = re.compile(r"^(\d{4})$")
_PRESENT_TERMS = {"present", "current", "ongoing", "now"}


def build_timeline(experience: list[Experience]) -> CareerTimeline:
    """
    Build a chronologically ordered CareerTimeline from raw Experience
    entries.

    Dated entries (those with a resolvable start date) are sorted
    oldest-first. Entries with no resolvable start date are appended
    afterward, in their original order, since there is no reliable way
    to place them chronologically.

    Args:
        experience: Raw experience entries from CandidateProfile.
            May be empty.

    Returns:
        A CareerTimeline. Always returns successfully, even for empty
        or entirely undated input.
    """
    entries = [_build_entry(exp) for exp in experience]

    dated = [e for e in entries if e.start_year is not None]
    undated = [e for e in entries if e.start_year is None]
    dated.sort(key=lambda e: (e.start_year, e.start_month if e.start_month is not None else 1))

    return CareerTimeline(entries=dated + undated)


def _build_entry(exp: Experience) -> TimelineEntry:
    start_year, start_month = _parse_date(exp.start_date)
    is_current = _is_present(exp.end_date)
    end_year, end_month = (None, None) if is_current else _parse_date(exp.end_date)

    duration_months = _compute_duration_months(
        start_year, start_month, end_year, end_month, is_current
    )

    return TimelineEntry(
        company=exp.company,
        position=exp.position,
        start_year=start_year,
        start_month=start_month,
        end_year=end_year,
        end_month=end_month,
        is_current=is_current,
        duration_months=duration_months,
        has_valid_dates=start_year is not None,
    )


def _parse_date(raw: str | None) -> tuple[int | None, int | None]:
    """Parse a free-text date string into (year, month). month is None if unresolvable."""
    if not raw or not raw.strip():
        return None, None

    text = raw.strip()

    month_year_match = _MONTH_YEAR_PATTERN.match(text)
    if month_year_match:
        month = _MONTH_NAMES.get(month_year_match.group(1).lower())
        year = int(month_year_match.group(2))
        return year, month

    year_only_match = _YEAR_ONLY_PATTERN.match(text)
    if year_only_match:
        return int(year_only_match.group(1)), None

    return None, None


def _is_present(raw: str | None) -> bool:
    """True if the raw end-date string indicates ongoing employment."""
    return bool(raw) and raw.strip().lower() in _PRESENT_TERMS


def _compute_duration_months(
    start_year: int | None,
    start_month: int | None,
    end_year: int | None,
    end_month: int | None,
    is_current: bool,
) -> int | None:
    """
    Compute tenure in months, inclusive of both the start and end
    month (e.g. Jan 2022 - Jan 2022 counts as 1 month, not 0).

    For ongoing roles (`is_current`), the end boundary is today's date.
    When only a year is known (no month), the earliest month (1) is
    assumed for a start date and the latest month (12) for an end
    date, to avoid understating tenure.

    Returns None if there isn't enough information to compute a
    duration (no start year, or a non-current role with no end date).
    """
    if start_year is None:
        return None

    resolved_start_month = start_month if start_month is not None else 1

    if is_current:
        now = datetime.now(timezone.utc)
        end_year_resolved, end_month_resolved = now.year, now.month
    elif end_year is not None:
        end_year_resolved = end_year
        end_month_resolved = end_month if end_month is not None else 12
    else:
        return None

    months = (end_year_resolved - start_year) * 12 + (end_month_resolved - resolved_start_month) + 1
    return max(months, 0)