"""
Integration tests for /resume/extract and /resume/analyze.

Security assertions:
- Both endpoints require authentication.
- Upload size is enforced; files over MAX_UPLOAD_SIZE_MB get HTTP 413.
- .doc files return 415 (not silently parsed as garbage text).
- Unsupported extensions return 400.
- Parser errors return a safe client message, not stack traces.
"""

import io

import pytest
from fastapi.testclient import TestClient

from tests.conftest import register_and_login


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

class TestResumeAuth:
    def test_extract_without_token_returns_401(self, client):
        data = {"file": ("resume.pdf", b"%PDF-1.4 fake", "application/pdf")}
        r = client.post("/api/v1/resume/extract", files=data)
        assert r.status_code == 401

    def test_analyze_without_token_returns_401(self, client):
        r = client.post("/api/v1/resume/analyze", json={
            "resume_text": "some text",
            "job_requirement": {"title": "Dev", "required_skills": []},
        })
        assert r.status_code == 401

    def test_extract_with_invalid_token_returns_401(self, client):
        data = {"file": ("resume.pdf", b"%PDF-1.4 fake", "application/pdf")}
        r = client.post(
            "/api/v1/resume/extract",
            files=data,
            headers={"Authorization": "Bearer bad.token"},
        )
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Unsupported formats
# ---------------------------------------------------------------------------

class TestResumeFormats:
    def test_doc_file_returns_415(self, client):
        token = register_and_login(client, "u@test.com", "Password123!")
        data = {"file": ("resume.doc", b"binary doc content", "application/msword")}
        r = client.post("/api/v1/resume/extract", files=data, headers=_auth(token))
        assert r.status_code == 415

    def test_txt_file_returns_415(self, client):
        token = register_and_login(client, "u@test.com", "Password123!")
        data = {"file": ("resume.txt", b"plain text", "text/plain")}
        r = client.post("/api/v1/resume/extract", files=data, headers=_auth(token))
        assert r.status_code == 415

    def test_exe_file_returns_415(self, client):
        token = register_and_login(client, "u@test.com", "Password123!")
        data = {"file": ("resume.exe", b"\x4d\x5a payload", "application/octet-stream")}
        r = client.post("/api/v1/resume/extract", files=data, headers=_auth(token))
        assert r.status_code == 415

    def test_empty_file_returns_400(self, client):
        token = register_and_login(client, "u@test.com", "Password123!")
        data = {"file": ("resume.pdf", b"", "application/pdf")}
        r = client.post("/api/v1/resume/extract", files=data, headers=_auth(token))
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Upload size enforcement
# ---------------------------------------------------------------------------

class TestUploadSize:
    def test_oversized_file_returns_413(self, client):
        """File over MAX_UPLOAD_SIZE_MB (10 MB) must return 413."""
        token = register_and_login(client, "u@test.com", "Password123!")
        # 11 MB of zeros — larger than the 10 MB limit
        big_content = b"\x00" * (11 * 1024 * 1024)
        data = {"file": ("big.pdf", big_content, "application/pdf")}
        r = client.post("/api/v1/resume/extract", files=data, headers=_auth(token))
        assert r.status_code == 413

    def test_file_at_limit_is_processed(self, client):
        """A file exactly at the limit should attempt processing (not be rejected for size)."""
        token = register_and_login(client, "u@test.com", "Password123!")
        # Exactly 10 MB — should pass size check (may fail at parse, that's fine)
        at_limit = b"\x00" * (10 * 1024 * 1024)
        data = {"file": ("limit.pdf", at_limit, "application/pdf")}
        r = client.post("/api/v1/resume/extract", files=data, headers=_auth(token))
        # Should NOT be 413 — size is accepted (content may still fail to parse)
        assert r.status_code != 413


# ---------------------------------------------------------------------------
# Error message safety
# ---------------------------------------------------------------------------

class TestResumeErrorSafety:
    def test_malformed_pdf_returns_safe_message(self, client):
        """Parser exceptions must not leak stack traces or internal details."""
        token = register_and_login(client, "u@test.com", "Password123!")
        # A file named .pdf but containing garbage binary data.
        data = {"file": ("corrupt.pdf", b"this is not a pdf \x89\xff\xfe", "application/pdf")}
        r = client.post("/api/v1/resume/extract", files=data, headers=_auth(token))
        # Must be a client error
        assert r.status_code in (400, 422)
        detail = r.json().get("detail", "")
        # Must NOT contain Python traceback indicators or library internals.
        for forbidden in ["Traceback", "raise ", "File \"", "pypdf", "Exception", "\n  "]:
            assert forbidden not in detail, f"Error response leaks internal detail: {detail!r}"

    def test_malformed_docx_returns_safe_message(self, client):
        token = register_and_login(client, "u@test.com", "Password123!")
        data = {"file": ("corrupt.docx", b"not a real docx \x00\xff", "application/vnd.openxmlformats-officedocument")}
        r = client.post("/api/v1/resume/extract", files=data, headers=_auth(token))
        assert r.status_code in (400, 422)
        detail = r.json().get("detail", "")
        for forbidden in ["Traceback", "raise ", "File \""]:
            assert forbidden not in detail


# ---------------------------------------------------------------------------
# Filename sanitisation
# ---------------------------------------------------------------------------

class TestFilenameSafety:
    def test_path_traversal_filename_is_sanitised(self, client):
        """../../etc/passwd.pdf must NOT be reflected back as a path."""
        token = register_and_login(client, "u@test.com", "Password123!")
        data = {"file": ("../../etc/passwd.pdf", b"not a pdf", "application/pdf")}
        r = client.post("/api/v1/resume/extract", files=data, headers=_auth(token))
        if r.status_code == 200:
            # If extraction somehow succeeded, filename must be safe.
            assert "../../" not in r.json().get("filename", "")
            assert "/" not in r.json().get("filename", "")
