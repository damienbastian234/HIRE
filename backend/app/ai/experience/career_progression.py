"""
Career progression analysis for Experience Intelligence (HIRE-AI-104).

Deterministic title-keyword ranking only — no AI, no NLP, no fuzzy
matching. A pure input/output component: given a CareerTimeline,
classifies each transition between consecutive dated roles as a
promotion, lateral move, or step down, and summarizes the overall
career trend.
"""

from app.models.experience_intelligence_model import CareerMove, CareerProgression, CareerTimeline

# Deterministic seniority ladder, evaluated in order from most to
# least specific so that e.g. "senior manager" matches "manager" (a
# higher rank) rather than "senior" alone. Keys are lowercase keyword
# fragments checked via substring match against the position title.
_SENIORITY_LADDER: list[tuple[int, list[str]]] = [
    (7, ["chief", "cto", "ceo", "cfo", "coo", "executive"]),
    (6, ["vice president", "vp "]),
    (5, ["director", "head of"]),
    (4, ["principal", "manager"]),
    (3, ["lead", "staff"]),
    (2, ["senior", "sr."]),
    (1, ["junior", "jr.", "associate", "entry"]),
    (0, ["intern", "trainee"]),
]


def analyze_progression(timeline: CareerTimeline) -> CareerProgression:
    """
    Analyze career progression across a CareerTimeline's dated entries.

    Only entries with a resolvable start date are considered, since
    progression is inherently about chronological transitions.
    Consecutive dated entries are compared pairwise, in chronological
    order, to classify each transition.

    Args:
        timeline: The candidate's CareerTimeline, as produced by
            timeline_builder.build_timeline (assumed already sorted
            with dated entries first, oldest to newest).

    Returns:
        A populated CareerProgression. Always returns successfully,
        including for empty or single-entry timelines (zero moves,
        overall_trend of "unknown" or "stable" respectively).
    """
    dated_entries = [e for e in timeline.entries if e.has_valid_dates]

    if len(dated_entries) == 0:
        return CareerProgression(moves=[], overall_trend="unknown")
    if len(dated_entries) == 1:
        return CareerProgression(moves=[], overall_trend="stable")

    moves = [
        _classify_move(dated_entries[i], dated_entries[i + 1])
        for i in range(len(dated_entries) - 1)
    ]

    overall_trend = _determine_overall_trend(moves)
    return CareerProgression(moves=moves, overall_trend=overall_trend)


def _rank_position(position: str | None) -> int | None:
    """Return a deterministic seniority rank for a position title, or None if unrecognized."""
    if not position:
        return None
    normalized = position.strip().lower()
    for rank, keywords in _SENIORITY_LADDER:
        if any(keyword in normalized for keyword in keywords):
            return rank
    return None


def _classify_move(from_entry, to_entry) -> CareerMove:
    from_rank = _rank_position(from_entry.position)
    to_rank = _rank_position(to_entry.position)

    if from_rank is None or to_rank is None:
        move_type = "unknown"
    elif to_rank > from_rank:
        move_type = "promotion"
    elif to_rank < from_rank:
        move_type = "step_down"
    else:
        move_type = "lateral_move"

    return CareerMove(
        from_company=from_entry.company,
        from_position=from_entry.position,
        to_company=to_entry.company,
        to_position=to_entry.position,
        move_type=move_type,
    )


def _determine_overall_trend(moves: list[CareerMove]) -> str:
    """
    Summarize the whole career as 'growth', 'stable', or 'unknown'.

    - 'growth': more promotions than step-downs, and at least one
      promotion occurred.
    - 'stable': no promotions and no step-downs (only lateral moves,
      or all moves unranked... see note below).
    - 'unknown': mixed/ambiguous signal (e.g. promotions and
      step-downs both occurred and roughly offset each other), or
      every move was unrankable.
    """
    promotions = sum(1 for m in moves if m.move_type == "promotion")
    step_downs = sum(1 for m in moves if m.move_type == "step_down")
    unknowns = sum(1 for m in moves if m.move_type == "unknown")

    if unknowns == len(moves):
        return "unknown"
    if promotions > step_downs and promotions > 0:
        return "growth"
    if promotions == 0 and step_downs == 0:
        return "stable"
    return "unknown"