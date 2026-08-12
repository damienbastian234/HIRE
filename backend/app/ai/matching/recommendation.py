"""
Deterministic recommendation helper for H.I.R.E.

Maps an overall score to a hiring recommendation.
"""

from app.models.candidate_matching_model import RecommendationLevel


def generate_recommendation(score: float) -> RecommendationLevel:
    """
    Convert an overall score into a recommendation level.
    """

    if score >= 90:
        return RecommendationLevel.STRONG_MATCH

    if score >= 75:
        return RecommendationLevel.GOOD_MATCH

    if score >= 60:
        return RecommendationLevel.POSSIBLE_MATCH

    if score >= 40:
        return RecommendationLevel.WEAK_MATCH

    return RecommendationLevel.NOT_RECOMMENDED