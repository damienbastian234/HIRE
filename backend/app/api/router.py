from fastapi import APIRouter

from app.api.routes.certificate import router as certificate_router
from app.api.routes.chat import router as chat_router
from app.api.routes.demo import router as demo_router
from app.api.routes.health import router as health_router
from app.api.routes.interview import router as interview_router
from app.api.routes.resume import router as resume_router
from app.api.routes.root import router as root_router
from app.api.routes.version import router as version_router

router = APIRouter()

router.include_router(root_router)
router.include_router(health_router)
router.include_router(version_router)
router.include_router(demo_router)
router.include_router(resume_router)
router.include_router(chat_router)
router.include_router(interview_router)
router.include_router(certificate_router)