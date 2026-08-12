"""
Skill metrics computation for Skill Intelligence (HIRE-AI-103).

A pure input/output component: given the normalized/deduplicated skill
set and categorization results, produces a SkillMetrics summary. No
AI, no fuzzy matching, no dependency beyond the skill_intelligence
data models.
"""


from app.models.skill_intelligence import SkillCategory, SkillMetrics

_SOFT_SKILLS_CATEGORY = "Soft Skills"


def compute_metrics(
    normalized_skills: list[str],
    categories: list[SkillCategory],
    uncategorized: list[str],
) -> SkillMetrics:
    """
    Compute aggregate skill metrics from the normalized pipeline output.

    All counts are derived from `normalized_skills` (the deduplicated,
    alias-resolved skill set already used by categorization and gap
    analysis), not from the candidate's raw, pre-deduplication skill
    lists — keeping every reported metric internally consistent with
    the rest of the pipeline.

    `technical_skill_count` and `soft_skill_count` are derived from
    the categorization result: `soft_skill_count` is the size of the
    "Soft Skills" category, and `technical_skill_count` is everything
    else in the normalized set (the 5 technical categories plus any
    uncategorized skills). This keeps the two counts an exact
    partition of `total_skills` by construction.

    Args:
        normalized_skills: The deduplicated, alias-resolved skill list
            (the output of skill_normalizer.normalize_skills).
        categories: Categorized skill groups, as produced by
            skill_categorizer.categorize_skills.
        uncategorized: Skills that matched no known category, as
            produced by skill_categorizer.categorize_skills.

    Returns:
        A populated SkillMetrics instance.
    """
    total_skills = len(normalized_skills)
    categorized_count = sum(len(category.skills) for category in categories)
    soft_skill_count = next(
        (len(category.skills) for category in categories if category.name == _SOFT_SKILLS_CATEGORY),
        0,
    )
    technical_skill_count = total_skills - soft_skill_count

    return SkillMetrics(
        technical_skill_count=technical_skill_count,
        soft_skill_count=soft_skill_count,
        total_skills=total_skills,
        categorized_skills=categorized_count,
        uncategorized_skills=len(uncategorized),
    )