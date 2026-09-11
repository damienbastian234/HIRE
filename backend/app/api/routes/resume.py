"""
Resume API routes.

Security properties enforced here:
- Both /extract and /analyze require a valid Bearer token.
- Upload size is checked before the full file is read — files exceeding
  MAX_UPLOAD_SIZE_MB are rejected with HTTP 413.
- .doc is not accepted (legacy binary format; UTF-8 decode is unreliable).
  Users must convert to .docx or PDF.
- Exception detail is logged server-side only; only a stable safe string
  is returned to the client.
- The filename is sanitised (directory components stripped) before use.
"""

from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.ai.workflows.resume_analysis_workflow import run_resume_analysis
from app.core.auth import get_current_user
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.responses import SuccessResponse
from app.schemas.resume_analysis import ResumeAnalysisData, ResumeAnalysisRequest

logger = get_logger(__name__)

router = APIRouter(prefix="/resume", tags=["Resume"])

SUPPORTED_EXTENSIONS = {".pdf", ".docx"}
_MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@router.post("/extract")
async def extract_resume(
    file: UploadFile,
    _current_user: dict = Depends(get_current_user),
):
    """Extract plain text from a PDF or DOCX resume.  Requires authentication."""
    # Sanitise filename — strip any directory components from attacker input.
    safe_filename = Path(file.filename or "").name
    extension = Path(safe_filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "Only PDF and DOCX resumes are supported. "
                "If you have a .doc file, please save it as .docx or PDF and try again."
            ),
        )

    # ── Enforce upload size before expensive parsing ──────────────────────────
    # Read exactly one byte beyond the limit. If we get it, the file is too large.
    content = await file.read(_MAX_BYTES + 1)
    if len(content) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB.",
        )

    if not content:
        raise HTTPException(status_code=400, detail="The uploaded resume is empty.")


    try:
        if extension == ".pdf":
            from pypdf import PdfReader
            text = "\n".join(
                page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages
            )
        else:  # .docx
            from docx import Document
            document = Document(BytesIO(content))
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)

    except HTTPException:
        raise
    except Exception:
        # Log the real exception server-side only — do not expose library
        # internals, file paths, or stack traces to the client.
        logger.exception("Resume extraction failed for file: %s", safe_filename)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not read this resume. Please ensure the file is a valid, non-corrupted PDF or DOCX.",
        )

    text = text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No readable text was found in this resume.",
        )

    return {"filename": safe_filename, "text": text}


@router.post(
    "/analyze",
    response_model=SuccessResponse[ResumeAnalysisData],
    status_code=status.HTTP_200_OK,
    summary="Analyze a resume against a job requirement",
)
async def analyze_resume(
    payload: ResumeAnalysisRequest,
    _current_user: dict = Depends(get_current_user),
) -> SuccessResponse[ResumeAnalysisData]:
    """
    Analyze resume text against a job requirement.  Requires authentication.

    Runs the full Resume → Skill → Experience → Candidate Matching pipeline
    and returns the aggregated result.
    """
    result = await run_resume_analysis(
        resume_text=payload.resume_text,
        job_requirement=payload.job_requirement,
    )
    return SuccessResponse(
        message="Resume analyzed successfully.",
        data=result,
    )