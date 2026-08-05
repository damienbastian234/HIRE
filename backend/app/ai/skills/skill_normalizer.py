"""
Skill normalization for Skill Intelligence (HIRE-AI-103).

Deterministic alias-based normalization only — no AI, no fuzzy
matching. A pure input/output component: given a list of raw skill
strings, returns the normalized, deduplicated list plus the original-
form strings identified as duplicates.
"""

from typing import Dict, List, Set, Tuple

# Lowercased alias -> canonical skill name. Only variants explicitly
# listed here are normalized; anything not present is passed through
# unchanged (preserving its original casing).
_SKILL_ALIASES: Dict[str, str] = {
    # Programming Languages
    "python": "Python", "python3": "Python", "py": "Python",
    "javascript": "JavaScript", "js": "JavaScript", "java script": "JavaScript",
    "java": "Java",
    "go": "Go", "golang": "Go",
    "rust": "Rust",
    "c++": "C++", "cpp": "C++",
    "c#": "C#", "csharp": "C#",
    "typescript": "TypeScript", "ts": "TypeScript",

    # Frameworks
    "fastapi": "FastAPI", "fast api": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "spring": "Spring", "spring boot": "Spring",
    "react": "React", "reactjs": "React", "react.js": "React",
    "angular": "Angular",
    "vue": "Vue", "vuejs": "Vue", "vue.js": "Vue",
    "node": "Node.js", "nodejs": "Node.js", "node.js": "Node.js",

    # Databases
    "mysql": "MySQL",
    "postgresql": "PostgreSQL", "postgres": "PostgreSQL", "psql": "PostgreSQL",
    "mongodb": "MongoDB", "mongo": "MongoDB",
    "sqlite": "SQLite",
    "redis": "Redis",

    # Cloud & DevOps
    "aws": "AWS", "amazon web services": "AWS",
    "azure": "Azure",
    "gcp": "GCP", "google cloud": "GCP", "google cloud platform": "GCP",
    "docker": "Docker",
    "kubernetes": "Kubernetes", "k8s": "Kubernetes",

    # Tools
    "git": "Git",
    "github": "GitHub",
    "linux": "Linux",
    "postman": "Postman",
    "jira": "Jira",

    # Soft Skills
    "leadership": "Leadership",
    "communication": "Communication",
    "problem solving": "Problem Solving", "problem-solving": "Problem Solving",
    "teamwork": "Teamwork",
    "critical thinking": "Critical Thinking",
}


def normalize_skills(raw_skills: List[str]) -> Tuple[List[str], List[str]]:
    """
    Normalize a list of raw skill strings using deterministic aliases,
    deduplicate the result, and report which original strings were
    duplicates.

    Example:
        ["Python", "python", "Python3"] ->
            normalized_unique=["Python"], duplicates=["python", "Python3"]

    Args:
        raw_skills: Raw skill strings, e.g. from
            CandidateProfile.skills.technical_skills + .soft_skills.

    Returns:
        A tuple of (normalized_unique_skills, duplicate_skills):
        - normalized_unique_skills: deduplicated, alias-resolved
          skills, in first-seen order.
        - duplicate_skills: the *original* (pre-normalization) strings
          that were found to be duplicates of an already-seen skill,
          in the order encountered.
    """
    seen_canonical: Set[str] = set()
    normalized_unique: List[str] = []
    duplicates: List[str] = []

    for raw in raw_skills:
        if not raw or not raw.strip():
            continue
        canonical = _normalize_one(raw)
        key = canonical.lower()
        if key in seen_canonical:
            duplicates.append(raw)
        else:
            seen_canonical.add(key)
            normalized_unique.append(canonical)

    return normalized_unique, duplicates


def _normalize_one(raw_skill: str) -> str:
    """Resolve a single raw skill string to its canonical form, if known."""
    stripped = raw_skill.strip()
    return _SKILL_ALIASES.get(stripped.lower(), stripped)


def is_known_alias(skill: str) -> bool:
    """True if `skill` (any casing/variant) has a known deterministic alias entry."""
    return bool(skill) and skill.strip().lower() in _SKILL_ALIASES