"""
API-level tests for POST /api/v1/resume/analyze (HIRE-AI-106).

Exercises the route through FastAPI's TestClient against the real
app.main.app instance (no mocking of the AI framework), so these tests
verify the actual request/response contract, not just the workflow
function in isolation (see test_resume_analysis_workflow.py for that).

Note: this sandbox does not include the real app/core/exceptions.py
global exception handler referenced by app/ai/exceptions.py (it exists
in the actual repository from HIRE-BE-004 but was not part of my
uploaded context — see the final report). Because no handler is
registered here, an unhandled AIException surfaces as an unhandled
exception through Starlette rather than a translated HTTP response.
Tests that exercise engine-failure propagation are therefore covered
at the workflow layer (test_resume_analysis_workflow.py), which is
the layer this ticket actually delivers; this file covers request
validation and the successful-response contract, which do not depend
on that handler.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ENDPOINT = "/api/v1/resume/analyze"


def _valid_payload(resume_text: str, job_requirement_payload: dict) -> dict:
    return {
        "resume_text": resume_text,
        "job_requirement": job_requirement_payload,
    }


# ---------------------------------------------------------------------------
# Successful resume analysis
# ---------------------------------------------------------------------------


def test_successful_resume_analysis_returns_200(
    sample_resume_text, sample_job_requirement_payload
):
    payload = _valid_payload(sample_resume_text, sample_job_requirement_payload)
    response = client.post(ENDPOINT, json=payload)

    assert response.status_code == 200


def test_successful_response_structure(
    sample_resume_text, sample_job_requirement_payload
):
    payload = _valid_payload(sample_resume_text, sample_job_requirement_payload)
    response = client.post(ENDPOINT, json=payload)
    body = response.json()

    # SuccessResponse envelope
    assert body["success"] is True
    assert "message" in body
    assert "data" in body

    # Aggregated ResumeAnalysisData payload
    data = body["data"]
    assert "candidate_profile" in data
    assert "skill_intelligence" in data
    assert "experience_intelligence" in data
    assert "candidate_matching" in data

    assert data["candidate_profile"]["personal_info"]["email"] == "john.doe@example.com"
    assert "categories" in data["skill_intelligence"]
    assert "metrics" in data["skill_intelligence"]
    assert "timeline" in data["experience_intelligence"]
    assert "seniority_level" in data["experience_intelligence"]
    assert "recommendation" in data["candidate_matching"]
    assert "overall_score" in data["candidate_matching"]


# ---------------------------------------------------------------------------
# Invalid request
# ---------------------------------------------------------------------------


def test_missing_job_requirement_field_returns_422(sample_resume_text):
    response = client.post(ENDPOINT, json={"resume_text": sample_resume_text})
    assert response.status_code == 422


def test_malformed_job_requirement_returns_422(sample_resume_text):
    payload = {
        "resume_text": sample_resume_text,
        # job_requirement.title is required; omit it to trigger validation failure
        "job_requirement": {"required_skills": []},
    }
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


def test_wrong_type_for_resume_text_returns_422(sample_job_requirement_payload):
    payload = {"resume_text": 12345, "job_requirement": sample_job_requirement_payload}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Missing resume
# ---------------------------------------------------------------------------


def test_missing_resume_text_field_returns_422(sample_job_requirement_payload):
    payload = {"job_requirement": sample_job_requirement_payload}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


def test_blank_resume_text_returns_422(sample_job_requirement_payload):
    payload = {"resume_text": "   ", "job_requirement": sample_job_requirement_payload}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422


def test_empty_string_resume_text_returns_422(sample_job_requirement_payload):
    payload = {"resume_text": "", "job_requirement": sample_job_requirement_payload}
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 422