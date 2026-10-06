"""
AI Mock Interview route for H.I.R.E.

Endpoints:
  POST /interview/generate   — generate a set of interview questions for a job role
  POST /interview/evaluate   — evaluate a candidate's answer to one question

Authentication: requires a valid Bearer token.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/interview")

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
_GENERATE_PROMPT = """
You are an expert technical recruiter and interview coach.

Generate exactly {count} interview questions for a **{role}** position at {difficulty} level.

Mix the following types proportionally:
- Behavioural (STAR-format) — "Tell me about a time when…"
- Situational — "How would you handle…"
- Technical / role-specific — specific skills, tools, or concepts for the role
- Motivation / culture fit — why this role, how you work, etc.

Return ONLY a JSON array of objects. Each object must have:
  "id": integer (1-based),
  "type": one of "behavioural" | "situational" | "technical" | "motivation",
  "question": the full question text,
  "hint": a one-sentence tip on what a strong answer should cover (shown to the candidate after answering).

Return valid JSON only — no markdown fences, no extra commentary.
""".strip()

_EVALUATE_PROMPT = """
You are a senior interviewer evaluating a candidate's response to an interview question for a **{role}** position.

**Question ({type}):** {question}

**Candidate's Answer:** {answer}

Evaluate thoroughly and return ONLY a JSON object with these fields:
  "score": integer 1–10 (10 = outstanding, 7 = good, 5 = acceptable, below 5 = needs work),
  "verdict": one short sentence verdict (e.g. "Strong answer with good structure."),
  "strengths": array of 2–4 strings — what the candidate did well,
  "improvements": array of 2–4 strings — specific, actionable improvements,
  "model_answer": a 3–5 sentence example of an excellent answer to this question,
  "tip": one practical coaching tip for the candidate.

Return valid JSON only — no markdown fences, no extra commentary.
""".strip()

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class GenerateRequest(BaseModel):
    job_role: str
    difficulty: str = "intermediate"
    num_questions: int = 5

    @field_validator("num_questions")
    @classmethod
    def clamp_questions(cls, v: int) -> int:
        return max(3, min(15, v))

    @field_validator("difficulty")
    @classmethod
    def normalise_difficulty(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in ("beginner", "intermediate", "advanced"):
            return "intermediate"
        return v


class EvaluateRequest(BaseModel):
    job_role: str
    question_id: int
    question_text: str
    question_type: str
    answer: str


# ---------------------------------------------------------------------------
# Helper — get Gemini client
# ---------------------------------------------------------------------------
def _gemini_client():
    if not settings.GOOGLE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI features are not configured. Please add GOOGLE_API_KEY to the server .env file.",
        )
    from google import genai
    return genai.Client(api_key=settings.GOOGLE_API_KEY)


def _call_gemini(client, prompt: str) -> str:
    """Call Gemini with automatic model fallback on quota exhaustion."""
    from google.genai import types
    from app.core.gemini import _MODEL_CHAIN, _is_quota_error, _is_model_not_found, _quota_http_error

    last_exc = None
    for model in _MODEL_CHAIN:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=4096,
                ),
            )
            return response.text.strip()
        except Exception as exc:
            if _is_quota_error(exc):
                logger.warning("Interview: quota exhausted for model=%s, trying next", model)
                last_exc = exc; continue
            if _is_model_not_found(exc):
                logger.warning("Interview: model not found %s, trying next", model)
                last_exc = exc; continue
            raise

    raise _quota_http_error(last_exc)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/generate")
async def generate_questions(
    payload: GenerateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Generate a set of interview questions for a given job role."""
    import json, re

    client = _gemini_client()
    prompt = _GENERATE_PROMPT.format(
        count=payload.num_questions,
        role=payload.job_role,
        difficulty=payload.difficulty,
    )

    try:
        raw = _call_gemini(client, prompt)
        # Strip any accidental markdown fences
        raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()
        questions = json.loads(raw)
        logger.info(
            "Generated %d questions for role='%s' user=%s",
            len(questions), payload.job_role, current_user.get("email", "?")
        )
        return {"questions": questions, "job_role": payload.job_role, "difficulty": payload.difficulty}
    except Exception as exc:
        logger.exception("Question generation failed for user %s", current_user.get("email"))
        raise HTTPException(
            status_code=500,
            detail="Failed to generate interview questions. Please try again.",
        ) from exc


@router.post("/evaluate")
async def evaluate_answer(
    payload: EvaluateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Evaluate a candidate's answer to an interview question."""
    import json, re

    if not payload.answer.strip():
        raise HTTPException(status_code=400, detail="Answer cannot be empty.")

    client = _gemini_client()
    prompt = _EVALUATE_PROMPT.format(
        role=payload.job_role,
        type=payload.question_type,
        question=payload.question_text,
        answer=payload.answer,
    )

    try:
        raw = _call_gemini(client, prompt)
        raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()
        evaluation = json.loads(raw)
        logger.info(
            "Evaluated Q%d for role='%s' score=%s user=%s",
            payload.question_id, payload.job_role,
            evaluation.get("score", "?"), current_user.get("email", "?")
        )
        return {"evaluation": evaluation, "question_id": payload.question_id}
    except Exception as exc:
        logger.exception("Evaluation failed for user %s", current_user.get("email"))
        raise HTTPException(
            status_code=500,
            detail="Failed to evaluate your answer. Please try again.",
        ) from exc
