"""
Skill gap analysis for Skill Intelligence (HIRE-AI-103).

A pure input/output component: given a candidate's categorized
skills, identifies known categories with zero representation and
produces generic, non-job-specific recommendations. No AI, no
external dependencies beyond the data models and the categorizer's
known-category list.
"""


from app.ai.skills.skill_categorizer import KNOWN_CATEGORIES
from app.models.skill_intelligence import SkillCategory, SkillGap

# Generic, non-job-specific recommendation phrasing per category.
_RECOMMENDATION_PHRASES: dict[str, str] = {
    "Programming Languages": "Consider adding programming language experience.",
    "Frameworks": "Consider adding framework experience.",
    "Databases": "Consider adding database experience.",
    "Cloud & DevOps": "Consider adding cloud and DevOps experience.",
    "Tools": "Consider adding tooling experience.",
    "Soft Skills": "Consider highlighting soft skills such as communication or leadership.",
}


def analyze_gaps(categories: list[SkillCategory]) -> SkillGap:
    """
    Identify known skill categories with zero representation and
    produce a generic recommendation for each.

    Args:
        categories: Categorized skill groups, as produced by
            skill_categorizer.categorize_skills. Only categories with
            at least one skill are expected to appear here.

    Returns:
        A SkillGap with the missing category names and one generic
        recommendation per missing category, in KNOWN_CATEGORIES order.
    """
    present = {category.name for category in categories}
    missing = [name for name in KNOWN_CATEGORIES if name not in present]
    recommendations = [_RECOMMENDATION_PHRASES[name] for name in missing]

    return SkillGap(missing_categories=missing, recommendations=recommendations)