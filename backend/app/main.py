from fastapi import FastAPI

from app.api.router import router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Human-Interactive Intelligent Recruitment Engine API"
)

app.include_router(router)