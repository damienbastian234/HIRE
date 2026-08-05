"""
Seniority analysis for Experience Intelligence (HIRE-AI-104).

Deterministic threshold lookup only — no AI, no fuzzy logic. A pure
input/output component: given total years of experience, returns a
SeniorityLevel.
"""

from app.models.experience_intelligence_model import SeniorityLevel

# Lower-bound-inclusive thresholds, in years. Example ranges from the
# ticket ("0-1 Entry", "2-4 Junior", "5-8 Mid", "9-14 Senior", "15+
# Principal") map directly onto these boundaries.
_THRESHOLDS: list[tuple[float, SeniorityLevel]] = [
    (15.0, SeniorityLevel.PRINCIPAL),
    (9.0, SeniorityLevel.SENIOR),
    (5.0, SeniorityLevel.MID),
    (2.0, SeniorityLevel.JUNIOR),
    (0.0, SeniorityLevel.ENTRY),
]


def determine_seniority(total_experience_years: float) -> SeniorityLevel:
    """
    Determine a candidate's seniority level from total years of
    experience, using fixed, deterministic thresholds.

    Args:
        total_experience_years: Total years of experience (may be 0.0).

    Returns:
        The matching SeniorityLevel. Always returns successfully.
    """
    for threshold, level in _THRESHOLDS:
        if total_experience_years >= threshold:
            return level
    return SeniorityLevel.ENTRY