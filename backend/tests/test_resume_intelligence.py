"""
Unit tests for the Resume Intelligence engine (HIRE-AI-102).

Tests use synchronous `def test_...()` functions with `asyncio.run()`
internally, rather than `pytest-asyncio`, to stay within the project's
established testing dependencies (pytest + FastAPI TestClient only —
see 09_CODING_STANDARDS.md / prior ticket conventions). No new test
dependency is introduced.
"""

import asyncio

import pytest

from app.ai.context import AIContext, WorkflowStatus
from app.ai.engines.resume_intelligence import ResumeIntelligenceEngine
from app.ai.exceptions import ContextValidationException
from app.ai.orchestrator import AIOrchestrator
from app.ai.registry import EngineRegistry
from app.ai.result import ExecutionStatus


def run_async(coro):
    """Run an async coroutine from a synchronous pytest test function."""
    return asyncio.run(coro)


COMPLETE_RESUME = """John Doe
Email: john.doe@example.com
Phone: +1-555-123-4567
LinkedIn: linkedin.com/in/johndoe
GitHub: github.com/johndoe
Location: Chennai, India

EDUCATION
B.Tech in Computer Science, XYZ University, CGPA: 8.5, 2022

EXPERIENCE
Software Engineer at Acme Corp (Jan 2022 - Present)
- Built scalable APIs
- Led a team of 5

SKILLS
Technical Skills: Python, FastAPI, SQL, Docker
Soft Skills: Leadership, Communication

PROJECTS
Resume Parser - A tool to parse resumes
Technologies: Python, Regex

CERTIFICATIONS
AWS Certified Developer - Amazon - 2023

LANGUAGES
English, Tamil, Hindi
"""


# ---------------------------------------------------------------------------
# Complete resume
# ---------------------------------------------------------------------------


def test_complete_resume_extracts_all_sections():
    engine = ResumeIntelligenceEngine()
    context = AIContext(data={"resume_text": COMPLETE_RESUME})

    result = run_async(engine.run(context))

    assert result.engine_name == "resume_intelligence"
    assert result.status == ExecutionStatus.SUCCESS
    assert 0.0 <= result.confidence <= 1.0
    assert result.confidence > 0.8  # a fully-populated resume should score highly

    profile = result.output
    assert profile["personal_info"]["full_name"] == "John Doe"
    assert profile["personal_info"]["email"] == "john.doe@example.com"
    assert len(profile["education"]) == 1
    assert len(profile["experience"]) == 1
    assert profile["skills"]["technical_skills"] == ["Python", "FastAPI", "SQL", "Docker"]
    assert profile["skills"]["soft_skills"] == ["Leadership", "Communication"]
    assert len(profile["projects"]) == 1
    assert len(profile["certifications"]) == 1
    assert profile["languages"] == ["English", "Tamil", "Hindi"]
    assert result.warnings == []


def test_complete_resume_performance_under_250ms():
    engine = ResumeIntelligenceEngine()
    context = AIContext(data={"resume_text": COMPLETE_RESUME})

    result = run_async(engine.run(context))

    assert result.execution_time_ms is not None
    assert result.execution_time_ms < 250.0


# ---------------------------------------------------------------------------
# Resume with missing sections
# ---------------------------------------------------------------------------


def test_resume_with_missing_sections_does_not_crash():
    resume = """Jane Smith
Email: jane.smith@example.com

EDUCATION
B.Sc in Physics, State University, 2021
"""
    engine = ResumeIntelligenceEngine()
    context = AIContext(data={"resume_text": resume})

    result = run_async(engine.run(context))

    assert result.status == ExecutionStatus.SUCCESS
    profile = result.output
    assert profile["personal_info"]["full_name"] == "Jane Smith"
    assert len(profile["education"]) == 1
    assert profile["experience"] == []
    assert profile["skills"]["technical_skills"] == []
    assert profile["projects"] == []
    assert profile["certifications"] == []
    assert profile["languages"] == []
    # Missing sections should be surfaced as warnings, not failures.
    assert any("experience" in w.lower() for w in result.warnings)
    assert any("skills" in w.lower() for w in result.warnings)


def test_missing_sections_yield_lower_confidence_than_complete_resume():
    sparse_resume = "Jane Smith\nEmail: jane@example.com\n"
    engine = ResumeIntelligenceEngine()

    complete_result = run_async(engine.run(AIContext(data={"resume_text": COMPLETE_RESUME})))
    sparse_result = run_async(engine.run(AIContext(data={"resume_text": sparse_resume})))

    assert sparse_result.confidence < complete_result.confidence


# ---------------------------------------------------------------------------
# Empty resume
# ---------------------------------------------------------------------------


def test_empty_resume_string_does_not_raise():
    engine = ResumeIntelligenceEngine()
    context = AIContext(data={"resume_text": ""})

    result = run_async(engine.run(context))

    assert result.status == ExecutionStatus.SUCCESS
    assert result.confidence == 0.0
    profile = result.output
    assert profile["personal_info"]["full_name"] is None
    assert profile["education"] == []
    assert profile["experience"] == []
    assert "empty" in result.warnings[0].lower()


def test_whitespace_only_resume_treated_as_empty():
    engine = ResumeIntelligenceEngine()
    context = AIContext(data={"resume_text": "   \n\n   "})

    result = run_async(engine.run(context))

    assert result.status == ExecutionStatus.SUCCESS
    assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# Invalid input
# ---------------------------------------------------------------------------


def test_missing_resume_text_key_raises_context_validation_exception():
    engine = ResumeIntelligenceEngine()
    context = AIContext(data={})  # no 'resume_text' key at all

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_non_string_resume_text_raises_context_validation_exception():
    engine = ResumeIntelligenceEngine()
    context = AIContext(data={"resume_text": 12345})  # wrong type

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


def test_none_resume_text_raises_context_validation_exception():
    engine = ResumeIntelligenceEngine()
    context = AIContext(data={"resume_text": None})

    with pytest.raises(ContextValidationException):
        run_async(engine.run(context))


# ---------------------------------------------------------------------------
# Duplicate skills
# ---------------------------------------------------------------------------


def test_duplicate_skills_are_deduplicated():
    resume = """SKILLS
Technical Skills: Python, SQL, Python, python, SQL
Soft Skills: Leadership, Leadership
"""
    engine = ResumeIntelligenceEngine()
    context = AIContext(data={"resume_text": resume})

    result = run_async(engine.run(context))

    technical = result.output["skills"]["technical_skills"]
    soft = result.output["skills"]["soft_skills"]
    assert technical == ["Python", "SQL"]  # case-insensitive dedup, first-seen casing kept
    assert soft == ["Leadership"]


# ---------------------------------------------------------------------------
# Multiple education entries
# ---------------------------------------------------------------------------


def test_multiple_education_entries_are_all_extracted():
    resume = """EDUCATION
B.Tech in Computer Science, XYZ University, CGPA: 8.5, 2022
M.S. in Data Science, ABC University, GPA: 3.8, 2024
Ph.D. in AI, DEF Institute, 2027
"""
    engine = ResumeIntelligenceEngine()
    context = AIContext(data={"resume_text": resume})

    result = run_async(engine.run(context))

    education = result.output["education"]
    assert len(education) == 3
    assert education[0]["institution"] == "XYZ University"
    assert education[1]["institution"] == "ABC University"
    assert education[2]["institution"] == "DEF Institute"


# ---------------------------------------------------------------------------
# Multiple work experiences
# ---------------------------------------------------------------------------


def test_multiple_experience_entries_are_all_extracted():
    resume = """EXPERIENCE
Software Engineer at Acme Corp (Jan 2022 - Present)
- Built scalable APIs

Intern at StartupXYZ (Jun 2021 - Aug 2021)
- Assisted with data pipelines

Junior Developer at BetaSoft (Jan 2020 - May 2021)
- Fixed bugs
- Wrote tests
"""
    engine = ResumeIntelligenceEngine()
    context = AIContext(data={"resume_text": resume})

    result = run_async(engine.run(context))

    experience = result.output["experience"]
    assert len(experience) == 3
    assert experience[0]["company"] == "Acme Corp"
    assert experience[1]["company"] == "StartupXYZ"
    assert experience[2]["company"] == "BetaSoft"
    assert experience[2]["responsibilities"] == ["Fixed bugs", "Wrote tests"]


# ---------------------------------------------------------------------------
# AI Framework integration (engine never mutates context.state)
# ---------------------------------------------------------------------------


def test_engine_never_mutates_context_state_directly():
    engine = ResumeIntelligenceEngine()
    context = AIContext(data={"resume_text": COMPLETE_RESUME})

    run_async(engine.run(context))

    # WorkflowState is owned exclusively by the AIOrchestrator; running
    # the engine standalone (bypassing the orchestrator) must leave
    # context.state untouched.
    assert context.state.workflow_status == WorkflowStatus.PENDING
    assert context.state.current_engine is None
    assert context.state.completed_engines == []
    assert context.state.progress == 0.0


def test_engine_integrates_with_registry_and_orchestrator():
    registry = EngineRegistry()
    registry.register(ResumeIntelligenceEngine())
    orchestrator = AIOrchestrator(registry)
    context = AIContext(data={"resume_text": COMPLETE_RESUME})

    workflow_result = run_async(orchestrator.run(context, ["resume_intelligence"]))

    assert workflow_result.workflow_id == context.workflow_id
    assert len(workflow_result.results) == 1
    assert workflow_result.results[0].engine_name == "resume_intelligence"
    # Going through the orchestrator, state IS updated (by the
    # orchestrator, not the engine) — confirming the two are talking
    # correctly through the approved framework contract.
    assert context.state.workflow_status == WorkflowStatus.COMPLETED
    assert context.state.completed_engines == ["resume_intelligence"]