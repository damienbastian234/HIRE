from fastapi import APIRouter

router = APIRouter(tags=["demo"])
profile_store = {
    "name": "Demo Candidate",
    "title": "Product Designer",
    "email": "candidate@example.com",
    "location": "San Francisco, CA",
}


@router.post("/auth/login")
def login(payload: dict):
    return {
        "token": "demo-token",
        "user": {
            "id": "demo-user",
            "name": "Demo Candidate",
            "email": payload.get("email", "candidate@example.com"),
            "role": "candidate",
        },
    }


@router.post("/auth/register")
def register(payload: dict):
    return {
        "token": "demo-token",
        "user": {
            "id": "demo-user",
            "name": payload.get("name", "Demo User"),
            "email": payload.get("email", "candidate@example.com"),
            "role": payload.get("role", "candidate"),
        },
    }


@router.get("/jobs")
def get_jobs(search: str | None = None, location: str | None = None, type: str | None = None, page: int = 1):
    jobs = [
        {
            "id": "job-1",
            "title": "Senior Product Designer",
            "company": "Northstar Labs",
            "location": "Remote",
            "type": "Full-time",
            "postedDaysAgo": 3,
            "matchScore": 92,
            "salaryRange": "$140k - $180k",
            "description": "Shape the end-to-end product experience for a fast-moving SaaS team.",
            "responsibilities": ["Lead design strategy", "Collaborate with product and engineering"],
            "requirements": ["6+ years in product design", "Figma and prototyping"],
            "tags": ["Design", "Remote", "Leadership"],
        },
        {
            "id": "job-2",
            "title": "Frontend Engineer",
            "company": "Brightly",
            "location": "New York, NY",
            "type": "Contract",
            "postedDaysAgo": 7,
            "matchScore": 87,
            "salaryRange": "$110k - $130k",
            "description": "Build polished user experiences for a modern analytics platform.",
            "responsibilities": ["Implement React interfaces", "Improve performance"],
            "requirements": ["React and TypeScript", "3+ years experience"],
            "tags": ["React", "TypeScript", "Product"],
        },
    ]

    filtered = jobs
    if search:
        term = search.lower()
        filtered = [job for job in filtered if term in job["title"].lower() or term in job["company"].lower()]
    if location:
        filtered = [job for job in filtered if location.lower() in job["location"].lower()]
    if type and type.lower() != "all":
        filtered = [job for job in filtered if job["type"].lower() == type.lower()]

    return {"jobs": filtered, "total": len(filtered)}


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    jobs = get_jobs().__getitem__("jobs")
    job = next((item for item in jobs if item["id"] == job_id), None)
    if not job:
        return {"detail": "Not found"}
    return {"job": job}


@router.post("/jobs/{job_id}/apply")
def apply_to_job(job_id: str, payload: dict):
    return {
        "success": True,
        "message": "Application submitted.",
        "applicationId": f"app-{job_id}",
        "payload": payload,
    }


@router.get("/dashboard/{role}")
def get_dashboard(role: str):
    if role == "recruiter":
        return {
            "company": "Northstar Labs",
            "stats": [
                {"label": "Open roles", "value": "8"},
                {"label": "Active candidates", "value": "24"},
                {"label": "Interviews this week", "value": "6"},
                {"label": "Avg. time to hire", "value": "14d"},
            ],
            "candidates": [
                {"id": "cand-1", "name": "Ava Patel", "role": "Product Designer", "stage": "Screening", "matchScore": 91},
                {"id": "cand-2", "name": "Miles Chen", "role": "Frontend Engineer", "stage": "Interview", "matchScore": 88},
            ],
        }

    return {
        "applications": [
            {"id": "app-1", "jobTitle": "Senior Product Designer", "company": "Northstar Labs", "stage": "Applied", "rejected": False},
            {"id": "app-2", "jobTitle": "Frontend Engineer", "company": "Brightly", "stage": "Interview", "rejected": False},
        ],
        "stats": [
            {"label": "Applications", "value": "2"},
            {"label": "Interviews", "value": "1"},
            {"label": "Offers", "value": "0"},
            {"label": "Profile match", "value": "92%"},
        ],
    }


@router.get("/applications/{application_id}")
def get_application(application_id: str):
    return {
        "id": application_id,
        "status": "In review",
        "updatedAt": "Today",
    }


@router.get("/profile")
def get_profile():
    return profile_store


@router.put("/profile")
def update_profile(payload: dict):
    profile_store.update(payload)
    return {"success": True, "profile": profile_store}


@router.post("/resume/upload")
def upload_resume():
    return {
        "success": True,
        "resumeId": "resume-001",
        "message": "Resume uploaded and parsed.",
    }


@router.post("/interview/start")
def start_interview(payload: dict):
    return {
        "sessionId": "interview-demo",
        "questions": [
            {"id": "q1", "prompt": "Tell me about yourself."},
            {"id": "q2", "prompt": "Describe a challenge you overcame."},
        ],
        "payload": payload,
    }


@router.post("/interview/{session_id}/answer")
def submit_answer(session_id: str, payload: dict):
    return {"success": True, "sessionId": session_id, "payload": payload}


@router.get("/interview/{session_id}/result")
def get_result(session_id: str):
    return {
        "sessionId": session_id,
        "status": "complete",
        "score": 88,
        "feedback": "Strong communication and clear examples.",
    }
