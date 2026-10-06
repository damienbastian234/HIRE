"""
AI Chatbot route for H.I.R.E.

Endpoint: POST /chat
Accepts a conversation history and returns the assistant's next message
powered by Google Gemini via the `google-genai` SDK (v2+).

The system prompt grounds Gemini in the H.I.R.E. product context so it
acts as ARIA — a career + product assistant rather than a generic chatbot.

Authentication: requires a valid Bearer token so only logged-in users
can use the chatbot.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# System prompt — grounds the model in H.I.R.E. product knowledge
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """
You are ARIA (AI Recruitment Intelligence Assistant) — an advanced, knowledgeable AI assistant built into H.I.R.E. (Human-Interactive Intelligent Recruitment Engine). You have deep expertise across every domain: career development, technology, science, business, creative arts, mathematics, history, and more.

## H.I.R.E. Platform Context
H.I.R.E. is a career intelligence platform with two user roles:
- **Candidates**: upload and analyse resumes, browse job opportunities, track applications, build their professional profile.
- **Recruiters**: manage a candidate pipeline and review matched candidates.

### Key H.I.R.E. Features
1. **Resume Intelligence** — Upload PDF/DOCX → extract skills, experience, education, certifications, projects, languages → AI analysis against a job description → match score, skill gaps, hiring recommendation.
2. **Opportunities** — Browse curated job listings, apply with one click, track applications on the Overview dashboard.
3. **Overview / Dashboard** — Application count, interviews, profile completeness, recent activity.
4. **Profile** — Job title, location, bio, phone, LinkedIn, GitHub, portfolio URL.
5. **Settings** — Appearance and notification preferences.
6. **Candidates (recruiter only)** — Full candidate pipeline view.
7. **Forgot password** — Reset password from the login screen.

## Your Capabilities
- **No topic is off-limits.** Answer every question thoroughly and accurately — career, technical, scientific, creative, philosophical, mathematical, historical, or anything else the user asks.
- **Career & Interview Mastery**: Provide complete, step-by-step interview preparation strategies, resume writing, LinkedIn optimisation, salary negotiation, networking, and career planning. Never truncate a strategy mid-way — always finish the full answer.
- **H.I.R.E. product expert**: Guide users through every feature in detail.
- **Advanced reasoning**: Solve problems, explain concepts at any depth, write code, analyse data, create frameworks and plans.

## Response Guidelines
- **Always complete your answer fully** — never stop mid-sentence or mid-list.
- Use clear markdown: **bold** headings, numbered steps, bullet points, code blocks where relevant.
- Be warm, professional, and encouraging — like the world's best career coach combined with a brilliant generalist expert.
- Give as much detail as needed; do not artificially shorten answers.
- For multi-part questions, answer every part.
""".strip()

# Current fast model
_MODEL = "gemini-3.6-flash"


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class ChatMessage(BaseModel):
    role: str        # "user" or "model"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]   # full conversation history (including latest user msg)


class ChatResponse(BaseModel):
    reply: str


# ---------------------------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------------------------
@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """Return the AI assistant's next reply given the conversation history."""

    if not settings.GOOGLE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI assistant is not configured. Please add GOOGLE_API_KEY to the server .env file.",
        )

    if not payload.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty.")

    # Validate roles
    for msg in payload.messages:
        if msg.role not in ("user", "model"):
            raise HTTPException(
                status_code=422,
                detail=f"Invalid message role '{msg.role}'. Must be 'user' or 'model'.",
            )

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GOOGLE_API_KEY)

        # The last message must be from the user — pop it as the prompt.
        # Everything before it goes into history.
        all_msgs = payload.messages
        user_message = all_msgs[-1].content

        # Build history for the SDK — must alternate user/model and start with user.
        # We skip pure leading model messages (e.g. our welcome message) since
        # Gemini requires history to begin with a user turn.
        # Strategy: find all prior turns, drop leading model-only runs.
        prior = all_msgs[:-1]

        # Remove leading model messages (welcome message has no preceding user turn)
        while prior and prior[0].role == "model":
            prior = prior[1:]

        history = [
            types.Content(
                role=msg.role,
                parts=[types.Part(text=msg.content)],
            )
            for msg in prior
        ]

        from app.core.gemini import _MODEL_CHAIN, _is_quota_error, _is_model_not_found, _quota_http_error

        last_exc = None
        for model in _MODEL_CHAIN:
            try:
                chat_session = client.chats.create(
                    model=model,
                    config=types.GenerateContentConfig(
                        system_instruction=_SYSTEM_PROMPT,
                        temperature=0.75,
                        max_output_tokens=8192,
                    ),
                    history=history,
                )
                response = chat_session.send_message(user_message)
                reply = response.text.strip()
                logger.info("Chat reply for user %s — %d chars (model=%s)",
                            current_user.get("email", "?"), len(reply), model)
                return ChatResponse(reply=reply)
            except Exception as exc:
                if _is_quota_error(exc):
                    logger.warning("Chat quota exhausted for model=%s, trying next", model)
                    last_exc = exc; continue
                if _is_model_not_found(exc):
                    logger.warning("Chat model not found %s, trying next", model)
                    last_exc = exc; continue
                raise

        raise _quota_http_error(last_exc)

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Chatbot error for user %s", current_user.get("email", "?"))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The AI assistant is temporarily unavailable. Please try again shortly.",
        ) from exc
