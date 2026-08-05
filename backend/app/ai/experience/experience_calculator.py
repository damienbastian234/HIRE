"""
Experience metrics calculator for Experience Intelligence (HIRE-AI-104).

A pure input/output component: given a CareerTimeline, computes
aggregate experience metrics. No AI, no fuzzy logic.
"""

from app.models.experience_intelligence_model import CareerTimeline, ExperienceMetrics


def calculate_metrics(timeline: CareerTimeline) -> ExperienceMetrics:
    """
    Compute aggregate experience metrics from a CareerTimeline.

    Total experience is the sum of each entry's resolvable
    `duration_months` (entries with no resolvable duration are simply
    excluded from the sum, not treated as zero). Tenure statistics
    (average/longest/shortest) are likewise computed only over entries
    with a resolvable duration.

    Args:
        timeline: The candidate's CareerTimeline, as produced by
            timeline_builder.build_timeline.

    Returns:
        A populated ExperienceMetrics. Always returns successfully,
        even for an empty timeline (zero counts, None for statistics
        that require at least one data point).
    """
    durations = [e.duration_months for e in timeline.entries if e.duration_months is not None]

    total_months = sum(durations)
    company_count = len({e.company for e in timeline.entries if e.company})
    is_currently_employed = any(e.is_current for e in timeline.entries)

    average_tenure = (total_months / len(durations)) if durations else None
    longest_tenure = max(durations) if durations else None
    shortest_tenure = min(durations) if durations else None

    return ExperienceMetrics(
        total_experience_months=total_months,
        total_experience_years=round(total_months / 12, 1),
        company_count=company_count,
        average_tenure_months=average_tenure,
        longest_tenure_months=longest_tenure,
        shortest_tenure_months=shortest_tenure,
        is_currently_employed=is_currently_employed,
    )