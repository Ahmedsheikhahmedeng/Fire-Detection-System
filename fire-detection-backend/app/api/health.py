from fastapi import APIRouter

from app.services.health_service import build_health_response


router = APIRouter()


@router.get("/health")
def health_check():
    return build_health_response()
