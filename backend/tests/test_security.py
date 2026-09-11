"""
Unit tests for the security module — password hashing and verification.
"""

import pytest
from app.core.security import hash_password, verify_password


class TestHashPassword:
    def test_returns_string(self):
        h = hash_password("password123")
        assert isinstance(h, str)

    def test_not_plaintext(self):
        plain = "password123"
        h = hash_password(plain)
        assert h != plain

    def test_different_hashes_for_same_input(self):
        # bcrypt uses a random salt — two hashes of the same input must differ.
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2

    def test_bcrypt_prefix(self):
        h = hash_password("whatever")
        assert h.startswith("$2b$") or h.startswith("$2a$")  # bcrypt format


class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        plain = "MyS3cur3Pass!"
        h = hash_password(plain)
        assert verify_password(plain, h) is True

    def test_wrong_password_returns_false(self):
        h = hash_password("correct_password")
        assert verify_password("wrong_password", h) is False

    def test_empty_password_returns_false(self):
        h = hash_password("notempty")
        assert verify_password("", h) is False

    def test_similar_password_returns_false(self):
        h = hash_password("password123")
        assert verify_password("password1234", h) is False


class TestRequireRole:
    """Integration-level tests for the require_role dependency."""

    def test_require_role_returns_callable(self):
        from app.core.auth import require_role
        dep = require_role("candidate")
        assert callable(dep)

    def test_different_roles_are_different_dependencies(self):
        from app.core.auth import require_role
        dep_c = require_role("candidate")
        dep_r = require_role("recruiter")
        assert dep_c is not dep_r


class TestJWT:
    """Tests for JWT creation and validation."""

    def test_create_and_decode_token(self):
        from app.core.auth import create_access_token, decode_token
        token = create_access_token(
            user_id="abc-123",
            email="test@example.com",
            name="Test User",
            role="candidate",
        )
        payload = decode_token(token)
        assert payload["sub"] == "abc-123"
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "candidate"

    def test_invalid_signature_raises_401(self):
        from fastapi import HTTPException
        from app.core.auth import decode_token
        with pytest.raises(HTTPException) as exc_info:
            decode_token("not.a.valid.token")
        assert exc_info.value.status_code == 401

    def test_tampered_token_raises_401(self):
        from fastapi import HTTPException
        from app.core.auth import create_access_token, decode_token
        token = create_access_token("id", "a@b.com", "Name", "candidate")
        # Flip a character in the signature portion
        parts = token.split(".")
        parts[2] = parts[2][:-2] + "XX"
        tampered = ".".join(parts)
        with pytest.raises(HTTPException) as exc_info:
            decode_token(tampered)
        assert exc_info.value.status_code == 401

    def test_expired_token_raises_401(self):
        from datetime import datetime, timedelta, timezone
        from fastapi import HTTPException
        from jose import jwt
        from app.core.auth import decode_token
        from app.core.config import settings

        # Create a token that expired 1 minute ago.
        payload = {
            "sub": "user-id",
            "email": "x@x.com",
            "name": "X",
            "role": "candidate",
            "exp": datetime.now(tz=timezone.utc) - timedelta(minutes=1),
        }
        expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        with pytest.raises(HTTPException) as exc_info:
            decode_token(expired_token)
        assert exc_info.value.status_code == 401
