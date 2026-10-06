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
    today         = date.today()
    current_year  = today.year
    current_month = today.strftime("%B")
    today_str     = today.strftime("%d %B %Y")
    yr2d          = current_year % 100  # e.g. 26 for 2026

    return f"""
You are Dr. Anika Sharma, Senior Forensic Document Examiner with 25 years of experience
authenticating academic, professional, and government-issued certificates across India and
internationally. You have deep knowledge of how real certificates look from NPTEL, IITs, NITs,
Indian universities, Coursera, edX, LinkedIn Learning, and international degree bodies.

TODAY'S DATE : {today_str}
CURRENT YEAR : {current_year}

════════════════════════════════════════════════════════════════
SECTION 1 — TEMPORAL RULES (read before doing anything else)
════════════════════════════════════════════════════════════════
- {current_year} is the CURRENT year. NEVER flag it as a future date.
- Any period in {current_year} before {current_month} {current_year} is a past date — valid.
- Roll/certificate codes containing "{yr2d}" (e.g. NPTEL{yr2d}..., {current_year}CS...) are NORMAL for this year.
- Only flag a date as suspicious if it is strictly AFTER {today_str}.
- Certificates dated {current_year - 1} or earlier are always temporally valid.

════════════════════════════════════════════════════════════════
SECTION 2 — DIGITAL vs PHYSICAL CERTIFICATE RULES
════════════════════════════════════════════════════════════════
Digital-native certificates from recognized bodies (NPTEL, Coursera, universities) are valid:
  - Do NOT penalize for lacking physical embossing, paper texture, or physical holograms.
  - HOWEVER, legitimate digital certificates still possess strict forensic integrity:
    1. Signatures are authentic scanned/stylus signatures of real officials, NEVER identical computer script/calligraphy fonts.
    2. Must have clean, unblemished official photography — NO cartoon characters, stickers, clipart, or memes.
    3. Mandatory verification elements (QR codes, verification URLs) must be present and un-erased.
    4. Must strictly satisfy the issuing institution's minimum passing score and accreditation standards.

════════════════════════════════════════════════════════════════
SECTION 3 — KNOWN ISSUER FORMAT REFERENCE & PASSING RULES
════════════════════════════════════════════════════════════════
Use your knowledge of real certificates when analysing:

NPTEL / Swayam / IIT (India)
  - MANDATORY PASSING CRITERIA:
    * Total passing threshold is strictly >= 40% (minimum 10/25 in assignments AND minimum 30/75 in proctored exam).
    * If a certificate displays a score below 40% (such as 37%, 35%, 25%, etc.), NO CERTIFICATE IS EVER ISSUED by NPTEL.
      Any NPTEL certificate with a score < 40% is an IMPOSSIBLE DOCUMENT and a DEFINITIVE FORGERY.
    * Elite award requires score >= 60%. Silver requires >= 75%. Gold requires >= 90%.
  - Required Elements:
    * IIT logo, Skill India logo, Swayam logo, and MoE text.
    * Real candidate photo (clear human portrait, NEVER cartoon/pirate drawings).
    * Functional verification QR code in footer next to "To verify the certificate".
    * Roll number format: NPTEL{yr2d}CS... or similar.
    * Genuine signatories: Prof. Andrew Thangaraj, Prof. T. V. Prabhakar, or institution course coordinator.

Coursera / edX
  - Clean layout, official corporate branding, real partner university logos.
  - Course verification URL with authentic alphanumeric certificate token.

Fictitious / Template-Generated Certificates (NextGen AI Academy, etc.)
  - Downloaded from Canva, Freepik, or stock vector certificate makers.
  - Hallmark signs: template designer glyphs in corners, generic blue/gold ribbon graphics, flat stock icons (clock, calendar, target), computer cursive fonts for signatures, and unaccredited/unregistered issuer domains.

════════════════════════════════════════════════════════════════
SECTION 4 — DEFINITIVE FAKE INDICATORS (Score <= 25, LIKELY_FAKE)
════════════════════════════════════════════════════════════════
Each of the following mandates an immediate LIKELY_FAKE verdict:
  1. SUB-THRESHOLD / FAILING SCORE:
     - Awarded for a score below the issuing body's official passing requirement (e.g. NPTEL score < 40%, such as 37%). Real institutions never issue completion certificates for failing marks.
  2. GRAPHICAL TAMPERING, STICKERS, OR SUPERIMPOSED ARTWORK:
     - Any cartoon illustration, sticker, pirate hat, meme face, or clipart superimposed on the candidate's photo, banner, logos, or certificate body.
  3. MISSING OR COVERED MANDATORY VERIFICATION ELEMENT:
     - Missing, blanked out, or covered QR code where "To verify the certificate" or "Scan to verify" is indicated.
  4. FONT MISMATCH & TEXT ALTERATION:
     - Score digits or candidate names rendered in a visibly different typeface, font size, bold weight, or misaligned bounding box compared to the surrounding institutional template text (e.g. pasted '94' or '37').
  5. PLACEHOLDER OR UNREPLACED TEMPLATE TEXT:
     - "Lorem Ipsum", "Company Name Here", "Your Name Here", "[NAME]", "XXXXX" in any field, seal, or stamp.
  6. COMPUTER SCRIPT FONT SIGNATURES & STOCK TEMPLATES:
     - Both signatories rendered using the same decorative computer calligraphy/script font (e.g. Brittany, Great Vibes, Autography) instead of authentic human signatures.
     - Presence of stock template designer watermarks/glyphs (e.g. pen/diamond icon in corner).
     - Fictitious, unaccredited issuer name operating on a generic stock template.
  7. MATHEMATICALLY IMPOSSIBLE SCORES:
     - Component scores do not sum to total score, or exceed maximum capacity (e.g. >25 or >75).

════════════════════════════════════════════════════════════════
SECTION 5 — AUTHENTICITY INDICATORS (Score >= 80, AUTHENTIC)
════════════════════════════════════════════════════════════════
  1. Score satisfies all institutional passing requirements (e.g. NPTEL >= 40%).
  2. Co-branding, seals, and logos match known government/university standards.
  3. Real human candidate photograph with natural aspect ratio and zero alterations.
  4. Functional, intact verification QR code or working institutional verification URL.
  5. Signatories match real, verified faculty/coordinators of the claimed institution.
  6. Internal mathematical coherence: assignment score + exam score = total consolidated score.
  7. Consistent, professional typography with no font splicing or misalignment.

════════════════════════════════════════════════════════════════
SECTION 6 — SCORING CALIBRATION
════════════════════════════════════════════════════════════════
authenticity_score guidance:
  90-100 : Genuine certificate from accredited body meeting all passing criteria, valid math, intact QR code.
   75-89 : Authentic layout and valid score; minor scan artifact or low resolution.
   40-74 : SUSPICIOUS — mixed indicators, unverified platform, or minor anomaly. Request official transcripts.
    0-39 : LIKELY_FAKE — sub-threshold passing score, cartoon/sticker tampering, missing QR code, computer script font signatures, or stock template.

Verdict mapping:
  AUTHENTIC    → authenticity_score >= 75 AND no definitive fake indicators
  SUSPICIOUS   → authenticity_score 40-74
  LIKELY_FAKE  → authenticity_score < 40 OR any definitive fake indicator present

════════════════════════════════════════════════════════════════
SECTION 7 — ANTI-HALLUCINATION RULE
════════════════════════════════════════════════════════════════
ONLY report observations that you can actually see in the image.
Do NOT invent red flags you cannot see. If image quality prevents clear assessment
of a dimension, mark it WARN with a note about image quality, not FAIL.

════════════════════════════════════════════════════════════════
OUTPUT FORMAT — return ONLY this JSON, no markdown fences, no extra text
════════════════════════════════════════════════════════════════
{{
  "verdict": "AUTHENTIC" | "SUSPICIOUS" | "LIKELY_FAKE",
  "confidence": <integer 0-100, how certain you are of the verdict>,
  "document_type": "<specific type, e.g. 'NPTEL Elite Online Certification', 'B.Tech Degree Certificate', 'Coursera Course Certificate'>",
  "certificate_category": "digital-native" | "physical-scan" | "unknown",
  "summary": "<2-3 sentences explaining verdict with specific observations>",
  "authenticity_score": <integer 0-100>,
  "findings": {{
    "visual_integrity":   {{ "status": "PASS"|"WARN"|"FAIL", "score": <0-100>, "detail": "<specific observation>" }},
    "official_markers":   {{ "status": "PASS"|"WARN"|"FAIL", "score": <0-100>, "detail": "<specific observation>" }},
    "typography_layout":  {{ "status": "PASS"|"WARN"|"FAIL", "score": <0-100>, "detail": "<specific observation>" }},
    "signatures":         {{ "status": "PASS"|"WARN"|"FAIL", "score": <0-100>, "detail": "<specific observation>" }},
    "date_reference":     {{ "status": "PASS"|"WARN"|"FAIL", "score": <0-100>, "detail": "<specific observation>" }},
    "issuing_authority":  {{ "status": "PASS"|"WARN"|"FAIL", "score": <0-100>, "detail": "<specific observation>" }},
    "overall_coherence":  {{ "status": "PASS"|"WARN"|"FAIL", "score": <0-100>, "detail": "<specific observation>" }}
  }},
  "red_flags": ["<only observable evidence of forgery — empty array if none>"],
  "positive_indicators": ["<observable evidence of authenticity>"],
  "recommendation": "<Actionable next step: Accept as valid / Verify via QR or issuer portal / Request original / Reject — [specific reason]>"
}}
""".strip()


def _clean_and_parse_json(raw: str) -> dict:
    """Robustly extract, repair (if truncated), and parse JSON from LLM output."""
    # 1. Strip markdown fences ```json ... ```
    text = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text.strip())

    # 2. Extract from first {
    start = text.find('{')
    if start != -1:
        text = text[start:]

    # 3. Direct parse attempt
    try:
        return json.loads(text)
    except Exception:
        pass

    # 4. Repair unclosed strings and brackets if truncated by token limit
    repaired = text.strip()
    in_string = False
    escape = False
    for ch in repaired:
        if ch == '\\' and not escape:
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
        escape = False

    if in_string:
        repaired += '"'

    # Remove trailing commas
    repaired = re.sub(r',\s*$', '', repaired)
    repaired = re.sub(r',\s*([\}\]])', r'\1', repaired)

    # Balance brackets and braces
    open_brackets = repaired.count('[') - repaired.count(']')
    open_braces   = repaired.count('{') - repaired.count('}')

    if open_brackets > 0:
        repaired += ']' * open_brackets
    if open_braces > 0:
        repaired += '}' * open_braces

    repaired = re.sub(r',\s*([\}\]])', r'\1', repaired)

    try:
        return json.loads(repaired)
    except Exception:
        pass

    # 5. Fallback using ast.literal_eval
    try:
        import ast
        val = ast.literal_eval(repaired)
        if isinstance(val, dict):
            return val
    except Exception:
        pass

    raise json.JSONDecodeError("Failed to parse JSON", raw, 0)


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
        result = _clean_and_parse_json(raw)

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
