from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

DEMO_PROFILE = {
    "name": "Demo Candidate",
    "title": "Product Designer",
    "email": "candidate@example.com",
    "location": "San Francisco, CA",
    "role": "candidate",
}

JOBS = [
    {
        "id": "job-product-designer",
        "title": "Product Designer",
        "company": "Northstar Labs",
        "location": "San Francisco, CA",
        "type": "Full-time",
        "salary": "$120k - $150k",
        "description": "Design and ship AI-powered recruiting workflows.",
    },
    {
        "id": "job-senior-recruiting-analyst",
        "title": "Senior Recruiting Analyst",
        "company": "Harmonic Health",
        "location": "Remote",
        "type": "Contract",
        "salary": "$90k - $120k",
        "description": "Drive candidate experience and funnel analytics.",
    },
]

CANDIDATE_STATS = [
    {"label": "Applications", "value": 3},
    {"label": "Interviews", "value": 1},
    {"label": "Offers", "value": 1},
    {"label": "Profile match", "value": "92%"},
]

RECRUITER_STATS = [
    {"label": "Open roles", "value": 12},
    {"label": "Active candidates", "value": 42},
    {"label": "Interviews this week", "value": 26},
    {"label": "Avg. time to hire", "value": "19 days"},
]

APPLICATIONS = [
    {"id": "app-001", "jobId": "job-product-designer", "status": "In review", "updatedAt": "Today"},
    {"id": "app-002", "jobId": "job-senior-recruiting-analyst", "status": "Interview scheduled", "updatedAt": "2d ago"},
]


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: Literal["candidate", "recruiter"] | None = "candidate"


class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    title: str | None = None
    email: str | None = None
    location: str | None = None
    role: Literal["candidate", "recruiter"] | None = None


@router.post("/auth/login")
def login(payload: LoginRequest):
    user = {
        "id": "demo-user",
        "name": DEMO_PROFILE["name"],
        "email": payload.email or DEMO_PROFILE["email"],
        "role": "candidate",
    }
    return {
        "token": "demo-token",
        "user": user,
    }


@router.post("/auth/register")
def register(payload: RegisterRequest):
    user = {
        "id": "demo-user",
        "name": payload.name or "Demo Candidate",
        "email": payload.email or DEMO_PROFILE["email"],
        "role": payload.role or "candidate",
    }
    return {
        "token": "demo-token",
        "user": user,
    }


@router.get("/profile")
def get_profile():
    return DEMO_PROFILE.copy()


@router.put("/profile")
def update_profile(payload: ProfileUpdateRequest):
    merged = DEMO_PROFILE.copy()
    for key, value in payload.model_dump(exclude_none=True).items():
        merged[key] = value
    DEMO_PROFILE.clear()
    DEMO_PROFILE.update(merged)
    return {"success": True, "profile": DEMO_PROFILE.copy()}


@router.get("/jobs")
def get_jobs():
    return {"jobs": JOBS, "total": len(JOBS)}


@router.get("/jobs/{job_id}")
def get_job_by_id(job_id: str):
    job = next((item for item in JOBS if item["id"] == job_id), None)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job": job}


@router.post("/jobs/{job_id}/apply")
def apply_job(job_id: str):
    return {
        "success": True,
        "message": "Application submitted.",
        "applicationId": f"app-{job_id}",
    }


@router.get("/dashboard/{role}")
def get_dashboard(role: str):
    if role == "recruiter":
        return {
            "company": "Northstar Labs",
            "stats": RECRUITER_STATS,
            "candidates": [
                {"name": "Mia Johnson", "stage": "Interview", "skillMatch": 94},
                {"name": "Chris Smith", "stage": "Screening", "skillMatch": 88},
            ],
        }

    return {
        "applications": APPLICATIONS,
        "stats": CANDIDATE_STATS,
    }


@router.get("/applications/{application_id}")
def get_application_status(application_id: str):
    result = next((item for item in APPLICATIONS if item["id"] == application_id), None)
    if not result:
        return {"id": application_id, "status": "In review", "updatedAt": "Today"}
    return result
