"""
Resume API routes.

HIRE-AI-106 adds the first production AI endpoint, POST
/api/v1/resume/analyze. Per the project's layered architecture
(routers -> services/workflows -> engines -> database), this route
contains no AI logic itself: it validates the request via
ResumeAnalysisRequest, delegates orchestration entirely to
`run_resume_analysis`, and wraps the result in the project's existing
SuccessResponse envelope.
"""

from fastapi import APIRouter, status

from app.ai.workflows.resume_analysis_workflow import run_resume_analysis
from app.schemas.responses import SuccessResponse
from app.schemas.resume_analysis import ResumeAnalysisData, ResumeAnalysisRequest

router = APIRouter(prefix="/resume", tags=["Resume"])


@router.post(
    "/analyze",
    response_model=SuccessResponse[ResumeAnalysisData],
    status_code=status.HTTP_200_OK,
    summary="Analyze a resume against a job requirement",
)
async def analyze_resume(
    payload: ResumeAnalysisRequest,
) -> SuccessResponse[ResumeAnalysisData]:
    """
    Analyze resume text against a job requirement.

    Runs the full Resume -> Skill -> Experience -> Candidate Matching
    Intelligence pipeline (via `run_resume_analysis`) and returns the
    aggregated result. Request validation failures are handled by
    FastAPI/Pydantic automatically; AI-layer failures propagate as the
    existing `AIException` hierarchy to H.I.R.E.'s global exception
    handler. No AI logic or exception translation happens in this
    route.
    """
    result = await run_resume_analysis(
        resume_text=payload.resume_text,
        job_requirement=payload.job_requirement,
    )
    return SuccessResponse(
        message="Resume analyzed successfully.",
        data=result,
    )