"""
Projects section parser for Resume Intelligence (HIRE-AI-102).

Deterministic, pattern-based extraction only. See
personal_info_parser.py for the module-level design rationale shared
by every parser in this package.
"""


from app.models.candidate import Project

_TECH_LABELS = {"technologies", "tech stack", "tools", "stack"}


def parse_projects(section_text: str) -> list[Project]:
    """
    Extract project entries from the projects section of a resume.

    Entries are separated by blank lines. Within an entry, the first
    line is treated as "Name - Description", and a line labeled
    "Technologies:" (or similar) is treated as the technology list.

    Args:
        section_text: Raw text of the resume's projects section. May
            be empty if the resume has no projects section.

    Returns:
        A list of Project entries, empty if none could be found.
    """
    if not section_text or not section_text.strip():
        return []

    blocks = _split_into_blocks(section_text)
    return [_parse_project_block(block) for block in blocks if block]


def _split_into_blocks(section_text: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in section_text.splitlines():
        if line.strip():
            current.append(line.strip())
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def _parse_project_block(lines: list[str]) -> Project:
    header = lines[0].lstrip("-•* ").strip()
    name, description = _split_name_description(header)

    technologies: list[str] = []
    for line in lines[1:]:
        stripped = line.lstrip("-•* ").strip()
        label, sep, rest = stripped.partition(":")
        if sep and label.strip().lower() in _TECH_LABELS:
            technologies = [t.strip() for t in rest.split(",") if t.strip()]

    return Project(
        name=name,
        description=description,
        technologies=technologies,
    )


def _split_name_description(header: str) -> tuple[str | None, str | None]:
    if " - " in header:
        name, _, description = header.partition(" - ")
        return name.strip() or None, description.strip() or None
    return header.strip() or None, None