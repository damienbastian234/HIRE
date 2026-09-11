"""
JWT authentication helpers for H.I.R.E.

Provides:
- create_access_token  – signs a JWT with the app SECRET_KEY
- decode_token         – validates and decodes a JWT, raises 401 on failure
- get_current_user     – FastAPI dependency: extracts caller from Authorization header
- require_role         – factory returning a FastAPI dependency that enforces a role
"""

from datetime import datetime, timedelta, timezone
from functools import lru_cache

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt

from app.core.config import settings

_ALGORITHM = settings.ALGORITHM
_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# Generic 401 detail — same message for unknown email AND wrong password
# so callers cannot distinguish the two (prevents user enumeration).
_UNAUTHORIZED_MSG = "Invalid credentials."


def create_access_token(
    user_id: str,
    email: str,
    name: str,
    role: str,
) -> str:
    """Return a signed JWT containing the user's identity claims."""
    expire = datetime.now(tz=timezone.utc) + timedelta(minutes=_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT.

    Returns the decoded payload dict on success.
    Raises HTTP 401 on any failure (expired, invalid signature, etc.).
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[_ALGORITHM])
        if not payload.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject.",
            )
        return payload
    except JWTError:
        # Do NOT include the internal JWTError message in the response —
        # it can leak library internals or token structure.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )


def get_current_user(request: Request) -> dict:
    """
    FastAPI dependency — extract and validate the Bearer token.

    Usage:
        @router.get("/protected")
        def protected(user: dict = Depends(get_current_user)):
            ...
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or malformed.",
        )
    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token is empty.",
        )
    return decode_token(token)


@lru_cache(maxsize=8)
def require_role(role: str):
    """
    FastAPI dependency factory that enforces a specific role.

    Usage:
        @router.get("/recruiter/only")
        def recruiter_only(user: dict = Depends(require_role("recruiter"))):
            ...

    Returns HTTP 403 if the authenticated user's role doesn't match.
    The role is read from the JWT claims (server-issued) — never from
    client-supplied data.
    """
    def _check(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires the '{role}' role.",
            )
        return current_user

    # Give each closure a unique __name__ so FastAPI's dependency graph
    # treats different roles as distinct dependencies.
    _check.__name__ = f"require_role_{role}"
    return _check
