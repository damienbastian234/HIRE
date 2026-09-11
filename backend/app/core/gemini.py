"""
Shared Gemini AI helper for H.I.R.E.

Provides:
- _gemini_client()         — builds a configured genai.Client
- call_gemini_text()       — text-only call with automatic model fallback
- call_gemini_vision()     — multimodal (image/PDF + text) call with fallback
- parse_quota_error()      — extracts human-readable quota message from 429 errors

Model fallback chain (free tier spreads quota across models):
  gemini-3.6-flash → gemini-2.5-flash → gemini-3.5-flash-lite → gemini-2.5-flash-lite
"""

import re
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Ordered fallback chain — if primary is quota-exhausted, try the next
_MODEL_CHAIN = [
    "gemini-3.6-flash",
    "gemini-2.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash-lite",
]


def _gemini_client():
    """Return a configured Gemini client, raising 503 if key is missing."""
    if not settings.GOOGLE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI features are not configured. Please add GOOGLE_API_KEY to .env.",
        )
    from google import genai
    return genai.Client(api_key=settings.GOOGLE_API_KEY)


def _parse_retry_seconds(exc) -> int | None:
    """Extract retry delay seconds from a Gemini 429 error, if present."""
    try:
        msg = str(exc)
        m = re.search(r"retry.*?(\d+)[s.]", msg, re.IGNORECASE)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return None


def _is_quota_error(exc) -> bool:
    return "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc)


def _is_model_not_found(exc) -> bool:
    return "404" in str(exc) or "not found" in str(exc).lower()


def _quota_http_error(exc) -> HTTPException:
    """Build a clean 429 HTTPException with retry guidance."""
    retry = _parse_retry_seconds(exc)
    msg = "API rate limit reached. You've used today's free quota for the AI service."
    if retry:
        msg += f" Please try again in about {retry} seconds."
    else:
        msg += " Please try again in a few minutes or tomorrow."
    return HTTPException(status_code=429, detail=msg)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def call_gemini_text(
    prompt: str,
    temperature: float = 0.7,
    max_output_tokens: int = 4096,
) -> str:
    """
    Call Gemini with a text-only prompt. Tries each model in _MODEL_CHAIN
    until one succeeds. Raises HTTPException on quota exhaustion or failure.
    """
    from google.genai import types

    client = _gemini_client()
    last_exc: Exception | None = None

    for model in _MODEL_CHAIN:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                ),
            )
            logger.debug("Gemini text call succeeded with model=%s", model)
            return response.text.strip()
        except Exception as exc:
            if _is_quota_error(exc):
                logger.warning("Quota exhausted for model=%s, trying next", model)
                last_exc = exc
                continue
            if _is_model_not_found(exc):
                logger.warning("Model not found: %s, trying next", model)
                last_exc = exc
                continue
            # Any other error — raise immediately
            raise

    # All models exhausted quota
    raise _quota_http_error(last_exc)


def call_gemini_vision(
    image_bytes: bytes,
    mime_type: str,
    prompt: str,
    temperature: float = 0.2,
    max_output_tokens: int = 4096,
) -> str:
    """
    Call Gemini with an image/PDF + text prompt. Tries each model in
    _MODEL_CHAIN until one succeeds. Raises HTTPException on failure.
    """
    from google.genai import types

    client = _gemini_client()
    last_exc: Exception | None = None

    for model in _MODEL_CHAIN:
        try:
            response = client.models.generate_content(
                model=model,
                contents=[
                    types.Content(parts=[
                        types.Part(inline_data=types.Blob(mime_type=mime_type, data=image_bytes)),
                        types.Part(text=prompt),
                    ])
                ],
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                ),
            )
            logger.debug("Gemini vision call succeeded with model=%s", model)
            return response.text.strip()
        except Exception as exc:
            if _is_quota_error(exc):
                logger.warning("Quota exhausted for model=%s, trying next", model)
                last_exc = exc
                continue
            if _is_model_not_found(exc):
                logger.warning("Model not found: %s, trying next", model)
                last_exc = exc
                continue
            raise

    raise _quota_http_error(last_exc)
