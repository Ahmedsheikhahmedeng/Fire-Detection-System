from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.system_health_service import get_system_health

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/health")
def system_health(db: Session = Depends(get_db)):
    return get_system_health(db)
