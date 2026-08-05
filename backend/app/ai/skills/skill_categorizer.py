"""
Skill categorization for Skill Intelligence (HIRE-AI-103).

Deterministic lookup-based categorization only — no AI, no fuzzy
matching. A pure input/output component: given a list of normalized
skill names, returns them grouped into known categories plus a list
of skills that matched no known category.
"""

from typing import Dict, List, Tuple

from app.models.skill_intelligence import SkillCategory

# Category name -> that category's known reference skills. Skill names
# here must match the canonical forms produced by
# skill_normalizer.normalize_skills.
_CATEGORY_SKILLS: Dict[str, List[str]] = {
    "Programming Languages": ["Python", "Java", "JavaScript", "Go", "Rust", "C++", "C#", "TypeScript"],
    "Frameworks": ["FastAPI", "Flask", "Django", "Spring", "React", "Angular", "Vue", "Node.js"],
    "Databases": ["MySQL", "PostgreSQL", "MongoDB", "SQLite", "Redis"],
    "Cloud & DevOps": ["AWS", "Azure", "GCP", "Docker", "Kubernetes"],
    "Tools": ["Git", "GitHub", "Linux", "Postman", "Jira"],
    "Soft Skills": ["Leadership", "Communication", "Problem Solving", "Teamwork", "Critical Thinking"],
}

# Reverse lookup for O(1) categorization: canonical skill name -> category.
_SKILL_TO_CATEGORY: Dict[str, str] = {
    skill: category
    for category, skills in _CATEGORY_SKILLS.items()
    for skill in skills
}

# The full universe of known categories, exposed for gap analysis.
KNOWN_CATEGORIES: List[str] = list(_CATEGORY_SKILLS.keys())


def categorize_skills(normalized_skills: List[str]) -> Tuple[List[SkillCategory], List[str]]:
    """
    Group normalized skills into known categories.

    Args:
        normalized_skills: Deduplicated, alias-resolved skill names
            (the output of skill_normalizer.normalize_skills).

    Returns:
        A tuple of (categories, uncategorized):
        - categories: one SkillCategory per known category that has at
          least one matching skill. Each category's `confidence` is a
          coverage score: how many of that category's known reference
          skills the candidate has, divided by that category's total
          reference skill count.
        - uncategorized: skills that did not match any known category.
    """
    grouped: Dict[str, List[str]] = {name: [] for name in KNOWN_CATEGORIES}
    uncategorized: List[str] = []

    for skill in normalized_skills:
        category = _SKILL_TO_CATEGORY.get(skill)
        if category:
            grouped[category].append(skill)
        else:
            uncategorized.append(skill)

    categories = [
        SkillCategory(
            name=category_name,
            skills=skills,
            confidence=min(1.0, len(skills) / len(_CATEGORY_SKILLS[category_name])),
        )
        for category_name, skills in grouped.items()
        if skills
    ]

    return categories, uncategorized