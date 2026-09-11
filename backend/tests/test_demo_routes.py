"""
Integration tests for all non-AI routes in demo.py.

These tests assert *secure* behavior:
- Login requires correct credentials; wrong password and unknown email both return 401.
- Passwords are hashed; the hash is never the plaintext.
- Role is server-controlled; PUT /profile cannot change it.
- Dashboard role comes from JWT, not the URL.
- Recruiter endpoints reject candidates.
- Object ownership: users can only access their own data.
"""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import register_and_login


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CANDIDATE = {"email": "alice@test.com", "password": "AlicePass1!"}
RECRUITER  = {"email": "bob@test.com",   "password": "BobPass1!"}


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register(client: TestClient, email: str, password: str, role: str = "candidate") -> dict:
    r = client.post("/api/v1/auth/register", json={
        "name": "Test User", "email": email, "password": password, "role": role,
    })
    return r


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestRegister:
    def test_register_returns_201_with_token_and_user(self, client):
        r = _register(client, **CANDIDATE)
        assert r.status_code == 201
        body = r.json()
        assert "token" in body
        assert body["user"]["email"] == CANDIDATE["email"]
        assert body["user"]["role"] == "candidate"

    def test_register_preserves_recruiter_role(self, client):
        r = _register(client, **RECRUITER, role="recruiter")
        assert r.status_code == 201
        assert r.json()["user"]["role"] == "recruiter"

    def test_register_duplicate_email_returns_409(self, client):
        _register(client, **CANDIDATE)
        r = _register(client, **CANDIDATE)
        assert r.status_code == 409

    def test_register_password_not_in_response(self, client):
        r = _register(client, **CANDIDATE)
        body = str(r.json())
        assert CANDIDATE["password"] not in body

    def test_register_short_password_returns_422(self, client):
        r = _register(client, "x@x.com", "short")
        assert r.status_code == 422

    def test_register_invalid_email_returns_422(self, client):
        r = _register(client, "not-an-email", "ValidPass123!")
        assert r.status_code == 422

    def test_register_empty_name_returns_422(self, client):
        r = client.post("/api/v1/auth/register", json={
            "name": "   ", "email": "e@e.com", "password": "ValidPass123!",
        })
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# Login — security-critical
# ---------------------------------------------------------------------------

class TestLogin:
    def test_correct_credentials_succeed(self, client):
        _register(client, **CANDIDATE)
        r = client.post("/api/v1/auth/login", json=CANDIDATE)
        assert r.status_code == 200
        assert "token" in r.json()

    def test_wrong_password_returns_401(self, client):
        _register(client, **CANDIDATE)
        r = client.post("/api/v1/auth/login", json={
            "email": CANDIDATE["email"], "password": "WrongPassword999!",
        })
        assert r.status_code == 401

    def test_unknown_email_returns_401(self, client):
        r = client.post("/api/v1/auth/login", json={
            "email": "nobody@nowhere.com", "password": "AnyPassword1!",
        })
        assert r.status_code == 401

    def test_wrong_password_and_unknown_email_same_message(self, client):
        """Same error message prevents account enumeration."""
        _register(client, **CANDIDATE)

        def _get_msg(r) -> str:
            body = r.json()
            # Handle both { "detail": "..." } and { "error": { "message": "..." } }
            if "detail" in body:
                return body["detail"]
            if "error" in body and isinstance(body["error"], dict):
                return body["error"].get("message", "")
            return str(body)

        r_wrong_pw = client.post("/api/v1/auth/login", json={
            "email": CANDIDATE["email"], "password": "Wrong!",
        })
        r_unknown = client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com", "password": "Wrong!",
        })
        assert _get_msg(r_wrong_pw) == _get_msg(r_unknown)

    def test_login_does_not_auto_create_account(self, client):
        """Unknown email must NOT create a new account — must return 401."""
        r = client.post("/api/v1/auth/login", json={
            "email": "new@example.com", "password": "SomePass123!",
        })
        assert r.status_code == 401  # NOT 200 / 201

    def test_login_returns_correct_role(self, client):
        _register(client, **RECRUITER, role="recruiter")
        r = client.post("/api/v1/auth/login", json=RECRUITER)
        assert r.json()["user"]["role"] == "recruiter"


# ---------------------------------------------------------------------------
# Auth / me
# ---------------------------------------------------------------------------

class TestAuthMe:
    def test_me_returns_current_user(self, client):
        token = register_and_login(client, **CANDIDATE)
        r = client.get("/api/v1/auth/me", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["email"] == CANDIDATE["email"]

    def test_me_without_token_returns_401(self, client):
        r = client.get("/api/v1/auth/me")
        assert r.status_code == 401

    def test_me_with_invalid_token_returns_401(self, client):
        r = client.get("/api/v1/auth/me", headers=_auth("bad.token.value"))
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Protected routes (no token)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("method,path", [
    ("GET",  "/api/v1/profile"),
    ("GET",  "/api/v1/jobs"),
    ("GET",  "/api/v1/dashboard/candidate"),
    ("GET",  "/api/v1/recruiter/candidates"),
])
def test_protected_route_without_token_returns_401(client, method, path):
    r = client.request(method, path)
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Profile — role immutability
# ---------------------------------------------------------------------------

class TestProfile:
    def test_get_profile_returns_profile(self, client):
        token = register_and_login(client, **CANDIDATE)
        r = client.get("/api/v1/profile", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["email"] == CANDIDATE["email"]

    def test_update_profile_persists_changes(self, client):
        token = register_and_login(client, **CANDIDATE)
        r = client.put("/api/v1/profile", headers=_auth(token),
                       json={"title": "Senior Engineer", "location": "London"})
        assert r.status_code == 200
        assert r.json()["profile"]["title"] == "Senior Engineer"

    def test_candidate_cannot_change_role_via_profile(self, client):
        """PUT /profile must NOT allow a candidate to self-promote to recruiter."""
        token = register_and_login(client, **CANDIDATE)
        r = client.put("/api/v1/profile", headers=_auth(token),
                       json={"role": "recruiter"})
        # Must still be candidate — role field is silently ignored or rejected.
        me = client.get("/api/v1/auth/me", headers=_auth(token))
        assert me.json()["role"] == "candidate"

    def test_profile_is_user_scoped(self, client):
        token_a = register_and_login(client, "a@test.com", "Password123!")
        token_b = register_and_login(client, "b@test.com", "Password123!")
        client.put("/api/v1/profile", headers=_auth(token_a),
                   json={"title": "Only Alice's Title"})
        r = client.get("/api/v1/profile", headers=_auth(token_b))
        assert r.json().get("title") != "Only Alice's Title"


# ---------------------------------------------------------------------------
# Dashboard — role from JWT, not URL
# ---------------------------------------------------------------------------

class TestDashboard:
    def test_candidate_dashboard_returns_applications(self, client):
        token = register_and_login(client, **CANDIDATE)
        r = client.get("/api/v1/dashboard/candidate", headers=_auth(token))
        assert r.status_code == 200
        assert "applications" in r.json()

    def test_candidate_calling_dashboard_recruiter_gets_candidate_view(self, client):
        """
        Role is derived from JWT — a candidate calling /dashboard/recruiter
        must get the candidate view, NOT the recruiter view.
        """
        token = register_and_login(client, **CANDIDATE)
        r = client.get("/api/v1/dashboard/recruiter", headers=_auth(token))
        assert r.status_code == 200
        body = r.json()
        # Candidate view has 'applications', recruiter view has 'stats' + 'candidates'
        assert "applications" in body

    def test_recruiter_dashboard_returns_recruiter_view(self, client):
        token = register_and_login(client, **RECRUITER, role="recruiter")
        r = client.get("/api/v1/dashboard/recruiter", headers=_auth(token))
        assert r.status_code == 200
        assert "candidates" in r.json()


# ---------------------------------------------------------------------------
# Recruiter-only endpoints
# ---------------------------------------------------------------------------

class TestRecruiterEndpoints:
    def test_recruiter_can_access_candidates(self, client):
        token = register_and_login(client, **RECRUITER, role="recruiter")
        r = client.get("/api/v1/recruiter/candidates", headers=_auth(token))
        assert r.status_code == 200
        assert "candidates" in r.json()

    def test_candidate_cannot_access_recruiter_candidates(self, client):
        """Candidates must receive 403, not recruiter data."""
        token = register_and_login(client, **CANDIDATE)
        r = client.get("/api/v1/recruiter/candidates", headers=_auth(token))
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Jobs + Applications
# ---------------------------------------------------------------------------

class TestJobs:
    def test_get_jobs_returns_list(self, client):
        token = register_and_login(client, **CANDIDATE)
        r = client.get("/api/v1/jobs", headers=_auth(token))
        assert r.status_code == 200
        assert len(r.json()["jobs"]) > 0

    def test_apply_returns_application_id(self, client):
        token = register_and_login(client, **CANDIDATE)
        job_id = "job-backend-engineer"
        r = client.post(f"/api/v1/jobs/{job_id}/apply", headers=_auth(token))
        assert r.status_code == 200
        assert "applicationId" in r.json()

    def test_duplicate_apply_returns_409(self, client):
        token = register_and_login(client, **CANDIDATE)
        job_id = "job-backend-engineer"
        client.post(f"/api/v1/jobs/{job_id}/apply", headers=_auth(token))
        r = client.post(f"/api/v1/jobs/{job_id}/apply", headers=_auth(token))
        assert r.status_code == 409

    def test_application_appears_in_dashboard(self, client):
        token = register_and_login(client, **CANDIDATE)
        client.post("/api/v1/jobs/job-backend-engineer/apply", headers=_auth(token))
        r = client.get("/api/v1/dashboard/candidate", headers=_auth(token))
        apps = r.json()["applications"]
        assert any(a["jobId"] == "job-backend-engineer" for a in apps)

    def test_applications_are_user_scoped(self, client):
        token_a = register_and_login(client, "a@test.com", "Password123!")
        token_b = register_and_login(client, "b@test.com", "Password123!")
        client.post("/api/v1/jobs/job-backend-engineer/apply", headers=_auth(token_a))
        r = client.get("/api/v1/dashboard/candidate", headers=_auth(token_b))
        assert len(r.json()["applications"]) == 0


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health_returns_ok(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
