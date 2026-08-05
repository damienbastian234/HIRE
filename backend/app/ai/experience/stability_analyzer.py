"""
Stability analysis for Experience Intelligence (HIRE-AI-104).

Deterministic tenure-based scoring only — no AI, no fuzzy logic. A
pure input/output component: given a CareerTimeline and its computed
ExperienceMetrics, produces a StabilityAnalysis.
"""

from app.models.experience_intelligence_model import (
    CareerTimeline,
    ExperienceMetrics,
    StabilityAnalysis,
)

# Average tenure, in months, treated as the benchmark for "fully
# stable" (stability_score == 1.0). Chosen as a round, defensible
# baseline (2 years) rather than derived from any external dataset.
_STABLE_TENURE_BENCHMARK_MONTHS = 24


def analyze_stability(timeline: CareerTimeline, metrics: ExperienceMetrics) -> StabilityAnalysis:
    """
    Compute a deterministic stability score and related metrics.

    stability_score is `average_tenure_months / 24`, capped at 1.0, so
    a candidate whose average tenure is 2+ years scores as fully
    stable, and shorter average tenures scale down proportionally. If
    there is no role with a resolvable duration, the score is 0.0
    (there is no data to support any other value).

    Args:
        timeline: The candidate's CareerTimeline.
        metrics: The candidate's ExperienceMetrics, as produced by
            experience_calculator.calculate_metrics.

    Returns:
        A populated StabilityAnalysis. Always returns successfully.
    """
    if metrics.average_tenure_months is None:
        stability_score = 0.0
    else:
        stability_score = min(1.0, metrics.average_tenure_months / _STABLE_TENURE_BENCHMARK_MONTHS)

    dated_entry_count = sum(1 for e in timeline.entries if e.has_valid_dates)
    job_change_count = max(dated_entry_count - 1, 0)

    return StabilityAnalysis(
        stability_score=round(stability_score, 4),
        average_tenure_months=metrics.average_tenure_months,
        job_change_count=job_change_count,
        longest_tenure_months=metrics.longest_tenure_months,
    )