from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def root():
    return {
        "project": "H.I.R.E.",
        "message": "Backend is running successfully."
    }