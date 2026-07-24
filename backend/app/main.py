from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import router
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting H.I.R.E Backend...")
    logger.info("H.I.R.E Backend Ready")
    yield
    logger.info("Shutting down H.I.R.E Backend...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan,
)

app.include_router(router)