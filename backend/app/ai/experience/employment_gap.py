"""
Employment gap analysis for Experience Intelligence (HIRE-AI-104).

Deterministic date-arithmetic only — no AI, no fuzzy logic. A pure
input/output component: given a CareerTimeline, detects gaps between
consecutive dated roles. Degrades gracefully whenever dates are
unavailable, simply skipping pairs that can't be evaluated rather than
raising or guessing.
"""

from app.models.experience_intelligence_model import CareerTimeline, EmploymentGap, EmploymentGapAnalysis

# A gap shorter than this (in months) is treated as a normal
# transition between roles, not a reportable employment gap.
_GAP_THRESHOLD_MONTHS = 1


def analyze_gaps(
    timeline: CareerTimeline, gap_threshold_months: int = _GAP_THRESHOLD_MONTHS
) -> EmploymentGapAnalysis:
    """
    Detect employment gaps between consecutive dated roles.

    Only entries with a resolvable start date are considered, and a
    gap is only reported between a pair where the earlier role's end
    date AND the later role's start date are both resolvable. Pairs
    where either date is missing are skipped entirely (graceful
    degradation) rather than guessed at.

    Args:
        timeline: The candidate's CareerTimeline, as produced by
            timeline_builder.build_timeline (assumed already sorted
            with dated entries first, oldest to newest).
        gap_threshold_months: Minimum gap length, in months, to be
            reported. Defaults to 1.

    Returns:
        A populated EmploymentGapAnalysis. Always returns
        successfully, including for empty, single-entry, or entirely
        undated timelines (zero gaps).
    """
    dated_entries = [e for e in timeline.entries if e.has_valid_dates]

    gaps: list[EmploymentGap] = []
    for i in range(len(dated_entries) - 1):
        earlier = dated_entries[i]
        later = dated_entries[i + 1]

        if earlier.is_current:
            # An ongoing role can't be followed by a later role in a
            # correctly-ordered timeline; nothing to evaluate.
            continue

        gap_months = _months_between_end_and_start(earlier, later)
        if gap_months is None:
            continue
        if gap_months >= gap_threshold_months:
            gaps.append(
                EmploymentGap(
                    after_company=earlier.company,
                    before_company=later.company,
                    gap_months=gap_months,
                )
            )

    return EmploymentGapAnalysis(
        gaps=gaps,
        gap_count=len(gaps),
        total_gap_months=sum(g.gap_months for g in gaps),
    )


def _months_between_end_and_start(earlier, later) -> int | None:
    """Months between `earlier`'s end date and `later`'s start date, or None if not resolvable."""
    if earlier.end_year is None or later.start_year is None:
        return None

    earlier_end_month = earlier.end_month if earlier.end_month is not None else 12
    later_start_month = later.start_month if later.start_month is not None else 1

    total_months = (later.start_year - earlier.end_year) * 12 + (later_start_month - earlier_end_month)
    # Subtract 1 since consecutive months (e.g. end=Jan, start=Feb) are
    # a seamless transition, not a 1-month gap.
    return max(total_months - 1, 0)