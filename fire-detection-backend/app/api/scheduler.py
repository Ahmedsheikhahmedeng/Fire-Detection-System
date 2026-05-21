import logging
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.database import SessionLocal, get_db
from app.core.config import settings
from app.core.security import verify_api_key
from app.services import scheduler as scheduler_service
from app.services.nasa_service import resolve_missing_cities
from app.services.scheduler_state import normalize_scheduler_state, read_scheduler_state
from sqlalchemy.orm import Session

logger = logging.getLogger("fire_detection.scheduler_api")

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


def build_scheduler_status_response(db: Session | None = None) -> dict:
    persisted_status = read_scheduler_state(db) if db is not None else {}
    api_scheduler_enabled = bool(settings.ENABLE_SCHEDULER)
    status = normalize_scheduler_state(
        {**scheduler_service.get_scheduler_status(), **persisted_status},
        api_scheduler_enabled,
    )
    worker_alive = bool(status.get("worker_alive", False))
    enabled = bool(status.get("enabled", api_scheduler_enabled or worker_alive))
    is_running = bool(status.get("is_running", False))
    last_error = status.get("last_error") or status.get("last_cycle_error")

    if is_running:
        scheduler_state = "running"
    elif worker_alive:
        scheduler_state = "worker_active"
    elif api_scheduler_enabled:
        scheduler_state = "enabled"
    else:
        scheduler_state = "disabled"

    return {
        "status": "ok",
        "scheduler": scheduler_state,
        "enabled": enabled,
        "api_scheduler_enabled": api_scheduler_enabled,
        "worker_alive": worker_alive,
        "worker_status": status.get("worker_status"),
        "worker_started_at": status.get("worker_started_at"),
        "worker_last_seen_at": status.get("worker_last_seen_at"),
        "is_running": is_running,
        "last_run_at": status.get("last_cycle_started_at"),
        "last_success_at": (
            status.get("last_cycle_finished_at")
            or status.get("last_ml_scan")
            or status.get("last_nasa_fetch")
        ) if not last_error else None,
        "last_nasa_fetch": status.get("last_nasa_fetch"),
        "last_weather_refresh": status.get("last_weather_refresh"),
        "last_ml_scan": status.get("last_ml_scan"),
        "last_city_resolve_at": status.get("last_city_resolve_at"),
        "last_city_resolved_count": status.get("last_city_resolved_count", 0),
        "last_error": last_error,
        "message": "Scheduler status retrieved successfully",
    }


@router.get("/status")
def get_scheduler_status(db: Session = Depends(get_db)):
    return build_scheduler_status_response(db)


@router.post("/run-once")
async def run_scheduler_once(_: bool = Depends(verify_api_key)):
    current_status = scheduler_service.get_scheduler_status()
    if current_status.get("is_running"):
        raise HTTPException(
            status_code=409,
            detail="Scheduler cycle is already running",
        )

    try:
        result = await scheduler_service.run_full_cycle()
    except Exception:
        logger.exception("Scheduler full cycle failed")
        raise HTTPException(
            status_code=500,
            detail="Scheduler full cycle failed",
        )

    if isinstance(result, dict) and result.get("skipped") and result.get("reason") == "scheduler_cycle_already_running":
        raise HTTPException(
            status_code=409,
            detail="Scheduler cycle is already running",
        )

    if isinstance(result, dict) and result.get("error"):
        raise HTTPException(
            status_code=500,
            detail="Scheduler full cycle failed",
        )

    return {
        "status": "success",
        "message": "Scheduler full cycle completed successfully",
        "result": result,
    }


def _resolve_cities_once_sync(batch_size: int) -> int:
    db = SessionLocal()
    try:
        return resolve_missing_cities(db, batch_size=batch_size)
    finally:
        db.close()


@router.post("/resolve-cities-once")
async def resolve_cities_once(
    batch_size: int = Query(default=20, ge=1, le=100),
    _: bool = Depends(verify_api_key),
):
    resolved = await asyncio.to_thread(_resolve_cities_once_sync, batch_size)

    scheduler_service.scheduler_status["last_city_resolve_at"] = scheduler_service.utc_now().isoformat()
    scheduler_service.scheduler_status["last_city_resolved_count"] = resolved

    return {
        "status": "success",
        "resolved": resolved,
        "batch_size": batch_size,
        "message": "City resolve completed",
    }
