from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def root():
    return {
        "project": "H.I.R.E.",
        "message": "Backend is running successfully."
    }


@router.get("/health")
def health():
    return {
        "status": "healthy"
    }


@router.get("/version")
def version():
    return {
        "version": "1.0.0"
    }