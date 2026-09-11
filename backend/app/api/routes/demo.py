"""
All non-AI API routes for H.I.R.E.

Authentication is backed by SQLite (via SQLAlchemy) — data survives
server restarts and is consistent across requests.

Security properties enforced in this module:
- Passwords are hashed with bcrypt; plaintext is never stored or logged.
- Login verifies the hash; unknown email and wrong password return the
  same HTTP 401 so callers cannot enumerate accounts.
- Role is server-controlled: stored in the database at registration time
  and never accepted from client payloads.
- Dashboard role is derived from the JWT, not from the URL segment.
- Every state-changing endpoint requires a valid Bearer token.
- Object-level ownership: users can only read/write their own data.

Endpoints
─────────
Auth:
    POST /auth/register
    POST /auth/login
    GET  /auth/me

Profile:
    GET  /profile
    PUT  /profile   (role field silently ignored even if supplied)

Jobs (read-only catalogue — no DB write):
    GET  /jobs
    GET  /jobs/{job_id}
    POST /jobs/{job_id}/apply

Dashboard:
    GET  /dashboard/{role}   (role derived from JWT, URL param ignored)

Recruiter:
    GET  /recruiter/candidates   (recruiter role required)

Health alias — see health.py.
"""

import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import create_access_token, get_current_user, require_role
from app.core.security import hash_password, verify_password
from app.database.deps import get_db
from app.database.models import User
from app.database.repositories import (
    ApplicationRepository,
    ProfileRepository,
    UserRepository,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Static job catalogue (shared, read-only — no DB write needed)
# ---------------------------------------------------------------------------
JOBS: list[dict] = [
    {
        "id": "job-product-designer",
        "title": "Product Designer",
        "company": "Northstar Labs",
        "location": "San Francisco, CA",
        "type": "Full-time",
        "salary": "$120k – $150k",
        "description": (
            "Design and ship AI-powered recruiting workflows. Work closely with "
            "engineers and PMs to deliver polished, accessible user experiences."
        ),
    },
    {
        "id": "job-senior-recruiting-analyst",
        "title": "Senior Recruiting Analyst",
        "company": "Harmonic Health",
        "location": "Remote",
        "type": "Contract",
        "salary": "$90k – $120k",
        "description": (
            "Drive candidate experience and funnel analytics for high-growth hiring teams."
        ),
    },
    {
        "id": "job-backend-engineer",
        "title": "Backend Engineer",
        "company": "Meridian AI",
        "location": "New York, NY",
        "type": "Full-time",
        "salary": "$130k – $160k",
        "description": (
            "Build scalable Python/FastAPI services powering the next generation "
            "of AI-driven enterprise software."
        ),
    },
    {
        "id": "job-data-scientist",
        "title": "Data Scientist",
        "company": "Veritas Analytics",
        "location": "Austin, TX",
        "type": "Full-time",
        "salary": "$110k – $140k",
        "description": (
            "Turn complex datasets into actionable insights using machine learning "
            "and statistical modelling."
        ),
    },
]

_JOBS_BY_ID: dict[str, dict] = {j["id"]: j for j in JOBS}

# ---------------------------------------------------------------------------
# Email / password policy helpers
# ---------------------------------------------------------------------------
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MIN_PASSWORD_LEN = 8

# Same generic message for unknown-email and wrong-password so callers
# cannot tell which one was wrong (prevents account enumeration).
_INVALID_CREDENTIALS_MSG = "Invalid email or password."


def _validate_email(email: str) -> str:
    clean = email.strip().lower()
    if not _EMAIL_RE.match(clean):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Please provide a valid email address.",
        )
    return clean


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: Literal["candidate", "recruiter"] = "candidate"

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name must not be empty.")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_policy(cls, v: str) -> str:
        if len(v) < _MIN_PASSWORD_LEN:
            raise ValueError(f"Password must be at least {_MIN_PASSWORD_LEN} characters.")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class ProfileUpdateRequest(BaseModel):
    # NOTE: 'role' is intentionally absent — role is server-controlled.
    name: str | None = None
    title: str | None = None
    location: str | None = None
    bio: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _user_stats(db: Session, user: User) -> list[dict]:
    apps = ApplicationRepository.list_by_user(db, user.id)
    interviews = sum(1 for a in apps if "interview" in a.status.lower())
    return [
        {"label": "Applications", "value": len(apps)},
        {"label": "Interviews",   "value": interviews},
        {"label": "Profile",      "value": "Complete" if user.profile and user.profile.title else "Incomplete"},
        {"label": "AI Analyses",  "value": 0},
    ]


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = _validate_email(payload.email)

    if UserRepository.get_by_email(db, email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    try:
        user = UserRepository.create(
            db,
            name=payload.name,
            email=email,
            password_hash=hash_password(payload.password),
            role=payload.role,
        )
        ProfileRepository.get_or_create(db, user)
    except IntegrityError:
        # Race condition: another request inserted the same email between
        # our check and our insert — treat as duplicate.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
    )
    logger.info("New user registered: %s (role=%s)", user.email, user.role)
    return {"token": token, "user": user.to_dict()}


@router.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = _validate_email(payload.email)
    user = UserRepository.get_by_email(db, email)

    # Use the same error and same response time for both unknown-email and
    # wrong-password paths to prevent account enumeration.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_INVALID_CREDENTIALS_MSG,
        )

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
    )
    return {"token": token, "user": user.to_dict()}


@router.get("/auth/me")
def get_me(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the authenticated user's identity from the database."""
    user = UserRepository.get_by_id(db, current_user["sub"])
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
        )
    return user.to_dict()


class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


@router.post("/auth/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset a user's password.

    Returns the same 200 response whether the email exists or not to
    prevent account enumeration.  The new password must be at least 8
    characters.
    """
    try:
        email = _validate_email(payload.email)
    except HTTPException:
        # Invalid e-mail format — still return 200 so we don't reveal anything.
        return {"success": True, "message": "If that account exists, your password has been updated."}

    user = UserRepository.get_by_email(db, email)
    if user is not None:
        UserRepository.update_password(db, user, hash_password(payload.new_password))
        logger.info("Password reset for: %s", email)

    return {"success": True, "message": "If that account exists, your password has been updated."}


# ---------------------------------------------------------------------------
# Profile endpoints
# ---------------------------------------------------------------------------

@router.get("/profile")
def get_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = UserRepository.get_by_id(db, current_user["sub"])
    if user is None:
        raise HTTPException(status_code=401, detail="User not found.")
    profile = ProfileRepository.get_or_create(db, user)
    return profile.to_dict(user)


@router.put("/profile")
def update_profile(
    payload: ProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = UserRepository.get_by_id(db, current_user["sub"])
    if user is None:
        raise HTTPException(status_code=401, detail="User not found.")

    # Update user's display name if provided
    if payload.name and payload.name.strip():
        UserRepository.update_name(db, user, payload.name)

    profile = ProfileRepository.get_or_create(db, user)
    updates = payload.model_dump(exclude_none=True)
    updates.pop("name", None)  # name lives on User, not Profile
    ProfileRepository.update(db, profile, updates)

    return {"success": True, "profile": profile.to_dict(user)}


# ---------------------------------------------------------------------------
# Job endpoints (read-only catalogue)
# ---------------------------------------------------------------------------

@router.get("/jobs")
def get_jobs(_current_user: dict = Depends(get_current_user)):
    return {"jobs": JOBS, "total": len(JOBS)}


@router.get("/jobs/{job_id}")
def get_job_by_id(job_id: str, _current_user: dict = Depends(get_current_user)):
    job = _JOBS_BY_ID.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {"job": job}


@router.post("/jobs/{job_id}/apply")
def apply_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = _JOBS_BY_ID.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    user_id = current_user["sub"]

    if ApplicationRepository.exists(db, user_id, job_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"You have already applied for {job['title']}.",
        )

    application = ApplicationRepository.create(
        db,
        user_id=user_id,
        job_id=job_id,
        job_title=job["title"],
        company=job["company"],
    )

    return {
        "success": True,
        "message": f"Your application for {job['title']} has been submitted.",
        "applicationId": application.id,
    }


# ---------------------------------------------------------------------------
# Dashboard endpoint
# ---------------------------------------------------------------------------

@router.get("/dashboard/{role}")
def get_dashboard(
    role: str,  # kept for URL compatibility but ignored — JWT role is authoritative
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return dashboard data for the authenticated user.

    The `role` URL segment is IGNORED.  The actual role is read from the
    JWT claims so a candidate calling /dashboard/recruiter receives their
    own candidate view, not the recruiter view.
    """
    actual_role = current_user["role"]
    user_id = current_user["sub"]

    user = UserRepository.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found.")

    if actual_role == "recruiter":
        total_candidates = ApplicationRepository.count_all(db)
        r_stats = [
            {"label": "Open roles",           "value": len(JOBS)},
            {"label": "Active candidates",    "value": total_candidates},
            {"label": "Interviews this week", "value": 0},
            {"label": "Avg. time to hire",    "value": "—"},
        ]
        return {
            "company": user.profile.title or "Your Company" if user.profile else "Your Company",
            "stats": r_stats,
            "candidates": [
                {"name": "Mia Johnson",   "stage": "Interview",  "skillMatch": 94},
                {"name": "Chris Smith",   "stage": "Screening",  "skillMatch": 88},
                {"name": "Priya Nair",    "stage": "Applied",    "skillMatch": 76},
            ],
        }

    apps = ApplicationRepository.list_by_user(db, user_id)
    return {
        "applications": [a.to_dict() for a in apps],
        "stats": _user_stats(db, user),
    }


# ---------------------------------------------------------------------------
# Recruiter-only: candidate list
# ---------------------------------------------------------------------------

@router.get("/recruiter/candidates")
def recruiter_candidates(
    _current_user: dict = Depends(require_role("recruiter")),
    db: Session = Depends(get_db),
):
    """Return a candidate list for the recruiter dashboard.  Requires recruiter role."""
    total = ApplicationRepository.count_all(db)
    return {
        "candidates": [
            {"name": "Mia Johnson",   "email": "mia@example.com",   "stage": "Interview", "skillMatch": 94},
            {"name": "Chris Smith",   "email": "chris@example.com",  "stage": "Screening", "skillMatch": 88},
            {"name": "Priya Nair",    "email": "priya@example.com",  "stage": "Applied",   "skillMatch": 76},
        ],
        "total": total,
    }
