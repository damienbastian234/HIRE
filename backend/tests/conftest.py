"""
Shared pytest fixtures for the H.I.R.E. test suite.

The SECRET_KEY environment variable is set here — before any app module
is imported — so that `app.core.config.Settings` can initialize without
requiring a real .env file during CI or local test runs.

Database: an in-memory SQLite instance is created per-test-session so
that tests are fully isolated from any local hire.db file.
"""

import os

# Must be set before any `app.*` import (pydantic-settings reads it at import time).
os.environ.setdefault("SECRET_KEY", "test-secret-key-only-for-pytest-minimum-32-chars!")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")
# Force in-memory SQLite for tests — never touch the real hire.db.
os.environ["DATABASE_URL"] = "sqlite://"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.database.base import Base  # noqa: E402
from app.database.deps import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.job_requirement import (  # noqa: E402
    EducationRequirement,
    ExperienceRequirement,
    JobRequirement,
    SkillRequirement,
)

# ─── In-memory test database ──────────────────────────────────────────────────
# Use a named shared in-memory SQLite DB so that all connections in the same
# process share the same tables (plain "sqlite://" creates a new DB per connection).
_TEST_DB_URL = "sqlite:///file:testdb?mode=memory&cache=shared&uri=true"
_TEST_ENGINE = create_engine(
    _TEST_DB_URL,
    connect_args={"check_same_thread": False},
)
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_TEST_ENGINE)


@pytest.fixture(autouse=True)
def _reset_db():
    """Create all tables on the test engine before each test; drop all after."""
    Base.metadata.create_all(bind=_TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=_TEST_ENGINE)


@pytest.fixture
def db_session():
    """Raw SQLAlchemy session pointing at the in-memory test DB."""
    session = _TestSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _override_get_db():
    db = _TestSession()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@pytest.fixture
def client():
    """TestClient wired to the in-memory test database."""
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ─── Sample data fixtures ─────────────────────────────────────────────────────

SAMPLE_RESUME_TEXT = """\
John Doe
john.doe@example.com
+1 555-123-4567
linkedin.com/in/johndoe
github.com/johndoe

EDUCATION
B.Tech Computer Science, Example University, 2020, CGPA: 8.5

EXPERIENCE
Software Engineer at Example Corp (Jan 2021 - Present)
- Built backend services
- Led a team of 3 engineers

SKILLS
Technical Skills: Python, FastAPI, PostgreSQL, Docker
Soft Skills: Communication, Leadership

PROJECTS
Resume Analyzer - AI-powered resume parsing tool
Technologies: Python, FastAPI

CERTIFICATIONS
AWS Certified Developer - Amazon - 2022

LANGUAGES
English, Spanish
"""


@pytest.fixture
def sample_resume_text() -> str:
    return SAMPLE_RESUME_TEXT


@pytest.fixture
def sample_job_requirement() -> JobRequirement:
    return JobRequirement(
        title="Backend Engineer",
        required_skills=[
            SkillRequirement(name="Python"),
            SkillRequirement(name="FastAPI"),
        ],
        preferred_skills=[
            SkillRequirement(name="Docker", required=False),
        ],
        experience=ExperienceRequirement(minimum_years=1.0),
        education=EducationRequirement(degrees=["B.Tech"]),
    )


@pytest.fixture
def sample_job_requirement_payload(sample_job_requirement: JobRequirement) -> dict:
    """JSON-serializable form of sample_job_requirement for request bodies."""
    return sample_job_requirement.model_dump(mode="json")


# ─── Auth helpers ─────────────────────────────────────────────────────────────

def register_and_login(client: TestClient, email: str, password: str, role: str = "candidate") -> str:
    """Register a user and return their Bearer token."""
    r = client.post("/api/v1/auth/register", json={
        "name": "Test User",
        "email": email,
        "password": password,
        "role": role,
    })
    assert r.status_code == 201, f"Registration failed: {r.json()}"
    return r.json()["token"]


@pytest.fixture
def candidate_token(client: TestClient) -> str:
    return register_and_login(client, "candidate@example.com", "Password123!")


@pytest.fixture
def recruiter_token(client: TestClient) -> str:
    return register_and_login(client, "recruiter@example.com", "Password123!", role="recruiter")