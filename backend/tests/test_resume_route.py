"""
API-level tests for POST /api/v1/resume/analyze (HIRE-AI-106).

Exercises the route through FastAPI's TestClient against the real
app.main.app instance. These tests verify the actual request/response
contract including the authentication requirement added in the
production-hardening pass.

Note: tests that require the full AI pipeline (successful_resume_analysis,
successful_response_structure) require valid AI credentials. They are marked
with the comment # LIVE_AI so CI environments can skip them with:
    pytest -m "not live_ai"
"""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import register_and_login

ENDPOINT = "/api/v1/resume/analyze"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _valid_payload(resume_text: str, job_requirement_payload: dict) -> dict:
    return {
        "resume_text": resume_text,
        "job_requirement": job_requirement_payload,
    }


# ---------------------------------------------------------------------------
# Authentication (these don't need the AI pipeline)
# ---------------------------------------------------------------------------

def test_analyze_without_token_returns_401(client, sample_resume_text, sample_job_requirement_payload):
    payload = _valid_payload(sample_resume_text, sample_job_requirement_payload)
    response = client.post(ENDPOINT, json=payload)
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Request validation — these fail at Pydantic level before any AI call.
# Auth is required, so we need a token; but the 422 is returned before
# the AI engine runs, so no live AI credentials are needed.
# ---------------------------------------------------------------------------

def test_missing_job_requirement_field_returns_422(client, candidate_token, sample_resume_text):
    response = client.post(
        ENDPOINT,
        json={"resume_text": sample_resume_text},
        headers=_auth(candidate_token),
    )
    assert response.status_code == 422


def test_malformed_job_requirement_returns_422(client, candidate_token, sample_resume_text):
    payload = {
        "resume_text": sample_resume_text,
        # job_requirement.title is required; omit it to trigger validation failure.
        "job_requirement": {"required_skills": []},
    }
    response = client.post(ENDPOINT, json=payload, headers=_auth(candidate_token))
    assert response.status_code == 422


def test_wrong_type_for_resume_text_returns_422(client, candidate_token, sample_job_requirement_payload):
    payload = {"resume_text": 12345, "job_requirement": sample_job_requirement_payload}
    response = client.post(ENDPOINT, json=payload, headers=_auth(candidate_token))
    assert response.status_code == 422


def test_missing_resume_text_field_returns_422(client, candidate_token, sample_job_requirement_payload):
    payload = {"job_requirement": sample_job_requirement_payload}
    response = client.post(ENDPOINT, json=payload, headers=_auth(candidate_token))
    assert response.status_code == 422


def test_blank_resume_text_returns_422(client, candidate_token, sample_job_requirement_payload):
    payload = {"resume_text": "   ", "job_requirement": sample_job_requirement_payload}
    response = client.post(ENDPOINT, json=payload, headers=_auth(candidate_token))
    assert response.status_code == 422


def test_empty_string_resume_text_returns_422(client, candidate_token, sample_job_requirement_payload):
    payload = {"resume_text": "", "job_requirement": sample_job_requirement_payload}
    response = client.post(ENDPOINT, json=payload, headers=_auth(candidate_token))
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Successful resume analysis — requires live AI credentials.
# Marked with live_ai so they can be skipped in CI.
# ---------------------------------------------------------------------------

@pytest.mark.live_ai
def test_successful_resume_analysis_returns_200(
    client, candidate_token, sample_resume_text, sample_job_requirement_payload,
):
    payload = _valid_payload(sample_resume_text, sample_job_requirement_payload)
    response = client.post(ENDPOINT, json=payload, headers=_auth(candidate_token))
    assert response.status_code == 200


@pytest.mark.live_ai
def test_successful_response_structure(
    client, candidate_token, sample_resume_text, sample_job_requirement_payload,
):
    payload = _valid_payload(sample_resume_text, sample_job_requirement_payload)
    response = client.post(ENDPOINT, json=payload, headers=_auth(candidate_token))
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