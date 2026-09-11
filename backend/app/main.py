from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger
from app.database.base import create_tables

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting H.I.R.E Backend (env=%s, debug=%s)...", settings.ENVIRONMENT, settings.DEBUG)
    # Create database tables on startup (idempotent — safe to call on every start).
    create_tables()
    logger.info("H.I.R.E Backend Ready")
    yield
    logger.info("Shutting down H.I.R.E Backend...")


# Gate OpenAPI docs: only expose in DEBUG mode so /docs is never live in production.
_docs_url  = "/docs"   if settings.DEBUG else None
_redoc_url = "/redoc"  if settings.DEBUG else None

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
allowed_origins = [
    origin.strip()
    for origin in settings.ALLOWED_ORIGINS.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    # Restrict to the methods and headers the frontend actually needs.
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


# ── Security headers middleware ────────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ── Exception handlers + routes ───────────────────────────────────────────────
register_exception_handlers(app)
app.include_router(router, prefix=settings.API_PREFIX)