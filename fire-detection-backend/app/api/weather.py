from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.security import verify_api_key
from app.core.database import SessionLocal
from app.services.weather_service import enrich_weather_for_hotspot

router = APIRouter(prefix="/weather", tags=["Weather"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/enrich/{hotspot_id}")
def enrich_weather(
    hotspot_id: int,
    _: bool = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    try:
        result = enrich_weather_for_hotspot(hotspot_id, db)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Weather enrichment failed")

    if not result:
        raise HTTPException(status_code=404, detail="Hotspot not found")

    return {
        "hotspot_id": result.hotspot_id,
        "temperature": result.temperature,
        "humidity": result.humidity,
        "wind_speed": result.wind_speed,
        "pressure": result.pressure,
        "rain_1h": result.rain_1h
    }
