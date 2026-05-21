from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List
from app.core.database import SessionLocal
from app.models.hotspot import Hotspot
from app.schemas.hotspot_schema import HotspotResponse
from app.services.cluster_stats_service import get_fire_clusters
from app.services.source_stats_service import get_hotspot_source_stats
from datetime import date


router = APIRouter(prefix="/hotspots", tags=["Hotspots"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("", response_model=List[HotspotResponse])
def list_hotspots(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    confidence: Optional[str] = None,
    min_lat: Optional[float] = Query(None),
    max_lat: Optional[float] = Query(None),
    min_lon: Optional[float] = Query(None),
    max_lon: Optional[float] = Query(None),
    limit: int = 500,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    query = db.query(Hotspot)

    if start_date:
        query = query.filter(Hotspot.acq_date >= start_date)

    if end_date:
        query = query.filter(Hotspot.acq_date <= end_date)

    if confidence:
        query = query.filter(Hotspot.confidence == confidence)

    # bbox filter
    if None not in [min_lat, max_lat, min_lon, max_lon]:
        query = query.filter(
            Hotspot.latitude >= min_lat,
            Hotspot.latitude <= max_lat,
            Hotspot.longitude >= min_lon,
            Hotspot.longitude <= max_lon
        )

    return query.offset(offset).limit(limit).all()


@router.get("/source-stats")
def source_stats(db: Session = Depends(get_db)):
    return get_hotspot_source_stats(db)


@router.get("/clusters")
def clusters(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return get_fire_clusters(db=db, status=status_filter, limit=limit)


@router.get("/{hotspot_id}", response_model=HotspotResponse)
def get_hotspot(hotspot_id: int, db: Session = Depends(get_db)):
    hotspot = db.query(Hotspot).filter(Hotspot.id == hotspot_id).first()

    if not hotspot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hotspot not found",
        )

    return hotspot
