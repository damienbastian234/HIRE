"""
Legal Certificate Analyzer route for H.I.R.E.

Endpoint: POST /certificate/analyze

Accepts an uploaded image (JPG, PNG, WEBP) or PDF document and uses
Gemini's multimodal vision to assess whether it appears authentic or
shows signs of tampering/forgery.

Returns a structured JSON verdict with confidence, findings, and red flags.

Authentication: requires a valid Bearer token.
"""

import re
import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/certificate")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MAX_BYTES = 15 * 1024 * 1024   # 15 MB
_SUPPORTED_MIME = {
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".webp": "image/webp",
    ".pdf":  "application/pdf",
}

# ---------------------------------------------------------------------------
# Analysis prompt — generated dynamically so today's date is always accurate
# ---------------------------------------------------------------------------
def _build_prompt() -> str:
    from datetime import date
    today = date.today()
    current_year  = today.year
    current_month = today.strftime("%B")
    today_str     = today.strftime("%d %B %Y")

    return f"""
You are a certified forensic document examiner and legal authentication specialist with 20+ years of experience.

TODAY'S DATE: {today_str}
CURRENT YEAR: {current_year}

*** CRITICAL TEMPORAL RULE — READ CAREFULLY ***
Any date, year, or time period visible on the document must be evaluated against TODAY'S DATE ({today_str}).
- A date of {current_year} is the CURRENT year — do NOT flag it as a future date.
- Any month/semester of {current_year} that has already passed (before {current_month} {current_year}) is a valid past date — do NOT treat it as suspicious.
- Only flag a date as suspicious if it is genuinely AFTER today ({today_str}).
- Certificate series codes or roll numbers containing "{current_year}" (e.g., NPTEL{current_year % 100:02d}...) are entirely consistent with a certificate issued in {current_year} — do NOT flag these.
- Certificates from {current_year - 1} or earlier are always valid temporally.

Carefully examine the uploaded document/certificate image and perform a comprehensive authenticity analysis.

Assess the following dimensions:

1. **Visual Integrity** — Look for signs of digital editing, cloning, blurring, inconsistent lighting, pixel artifacts, mismatched fonts or font sizes. Also check for placeholder/filler text such as "Lorem Ipsum", "Company Name Here", "Your Name", "[NAME]", or other template placeholders that were not replaced — these are definitive signs of a fake.
2. **Official Markers** — Check for presence/absence of official seals, stamps, watermarks, embossing, holograms, serial numbers, QR codes, barcodes. Verify logos match the claimed institution's known branding.
3. **Typography & Layout** — Assess font consistency, alignment, spacing, margins. Authentic documents follow strict formatting standards specific to that institution.
4. **Signatures** — Evaluate signature authenticity, ink consistency, and whether signatures appear digitally inserted or are from a known legitimate signatory of the claimed institution.
5. **Date & Reference Integrity** — Check if dates are consistent with today's date ({today_str}). Only flag future dates (after {today_str}) as suspicious. Past dates including earlier in {current_year} are valid. Verify roll numbers / reference codes match the institution's known format.
6. **Issuing Authority Markers** — Verify logos, letterhead, issuing body details, registration numbers match the publicly known institution. For well-known bodies (NPTEL, IIT, University of London, etc.) cross-reference branding with your knowledge of that institution.
7. **Paper/Background Texture** — Identify security paper patterns, guilloche patterns, background microprinting if visible.
8. **Overall Coherence** — Does everything fit together as a genuine document from that specific institution would, or are there incongruencies?

Return ONLY a valid JSON object with this exact structure:
{{
  "verdict": "AUTHENTIC" | "SUSPICIOUS" | "LIKELY_FAKE",
  "confidence": integer 0-100 (how confident you are in your verdict),
  "summary": "A 2-3 sentence plain-English summary of your finding.",
  "authenticity_score": integer 0-100 (overall authenticity score, 100=definitely real),
  "findings": {{
    "visual_integrity":   {{ "status": "PASS"|"WARN"|"FAIL", "detail": "..." }},
    "official_markers":   {{ "status": "PASS"|"WARN"|"FAIL", "detail": "..." }},
    "typography_layout":  {{ "status": "PASS"|"WARN"|"FAIL", "detail": "..." }},
    "signatures":         {{ "status": "PASS"|"WARN"|"FAIL", "detail": "..." }},
    "date_reference":     {{ "status": "PASS"|"WARN"|"FAIL", "detail": "..." }},
    "issuing_authority":  {{ "status": "PASS"|"WARN"|"FAIL", "detail": "..." }},
    "overall_coherence":  {{ "status": "PASS"|"WARN"|"FAIL", "detail": "..." }}
  }},
  "red_flags": ["list of specific suspicious observations, empty array if none"],
  "positive_indicators": ["list of authenticity markers found, empty array if none"],
  "recommendation": "What action should be taken (e.g. 'Accept as valid', 'Request original for physical verification', 'Verify via institution portal', 'Reject — clear signs of tampering')",
  "document_type": "Best guess of what type of document this is (e.g. 'NPTEL Online Certification', 'Academic Degree Certificate', 'Employment Certificate', 'ID Card')"
}}

Be thorough, objective, and specific. Return valid JSON only — no markdown fences, no extra text.
""".strip()


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------
@router.post("/analyze")
async def analyze_certificate(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Analyze an uploaded certificate/document for authenticity."""

    if not settings.GOOGLE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI features are not configured. Please add GOOGLE_API_KEY to .env.",
        )

    # ── Validate extension ─────────────────────────────────────────────────
    safe_name = Path(file.filename or "").name
    ext = Path(safe_name).suffix.lower()
    if ext not in _SUPPORTED_MIME:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{ext}'. Accepted: JPG, PNG, WEBP, PDF.",
        )
    mime_type = _SUPPORTED_MIME[ext]

    # ── Read & size-check ──────────────────────────────────────────────────
    content = await file.read(_MAX_BYTES + 1)
    if len(content) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 15 MB limit.",
        )
    if len(content) < 100:
        raise HTTPException(status_code=400, detail="File appears to be empty or corrupt.")

    logger.info(
        "Certificate analysis requested by %s — file=%s size=%d",
        current_user.get("email", "?"), safe_name, len(content)
    )

    # ── Call Gemini Vision ─────────────────────────────────────────────────
    try:
        from app.core.gemini import call_gemini_vision

        raw = call_gemini_vision(
            image_bytes=content,
            mime_type=mime_type,
            prompt=_build_prompt(),
            temperature=0.2,
            max_output_tokens=4096,
        )
        raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()
        result = json.loads(raw)

        logger.info(
            "Certificate analysis complete for %s — verdict=%s confidence=%s",
            current_user.get("email", "?"),
            result.get("verdict", "?"),
            result.get("confidence", "?"),
        )
        return {"filename": safe_name, "analysis": result}

    except HTTPException:
        raise
    except json.JSONDecodeError as exc:
        logger.exception("Gemini returned non-JSON for certificate analysis")
        raise HTTPException(
            status_code=500,
            detail="Analysis produced an unexpected response format. Please try again.",
        ) from exc
    except Exception as exc:
        logger.exception("Certificate analysis failed for %s", current_user.get("email"))
        raise HTTPException(
            status_code=500,
            detail="Certificate analysis is temporarily unavailable. Please try again shortly.",
        ) from exc
