from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.nasa_fetch_run import NasaFetchRun

logger = logging.getLogger("fire_detection.system_health")

EXPECTED_FIRMS_SOURCES = [
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
]


def determine_fetch_run_status(result: Dict[str, Any]) -> str:
    source_error_count = int(result.get("source_error_count", 0) or 0)
    received_count = int(result.get("received_count", 0) or 0)

    if source_error_count >= len(EXPECTED_FIRMS_SOURCES) and received_count == 0:
        return "failed"
    if source_error_count > 0:
        return "partial"
    return "success"


def save_nasa_fetch_run(
    db: Session,
    *,
    result: Dict[str, Any],
    started_at: datetime,
    finished_at: Optional[datetime] = None,
    error_message: Optional[str] = None,
) -> Optional[NasaFetchRun]:
    finished_at = finished_at or datetime.utcnow()
    duration_seconds = max(0.0, (finished_at - started_at).total_seconds())
    status = "failed" if error_message else determine_fetch_run_status(result)

    run = NasaFetchRun(
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=round(duration_seconds, 3),
        status=status,
        received_count=int(result.get("received_count", 0) or 0),
        inserted_count=int(result.get("inserted_count", 0) or 0),
        duplicate_count=int(result.get("duplicate_count", 0) or 0),
        source_error_count=int(result.get("source_error_count", 0) or 0),
        row_error_count=int(result.get("row_error_count", 0) or 0),
        v3_prediction_count=int(result.get("v3_prediction_count", 0) or 0),
        prediction_limit_per_fetch=result.get("prediction_limit_per_fetch"),
        prediction_limit_applied=bool(result.get("prediction_limit_applied", False)),
        prediction_limit_note=result.get("prediction_limit_note"),
        received_by_source=result.get("received_by_source") or {},
        inserted_by_source=result.get("inserted_by_source") or {},
        duplicates_by_source=result.get("duplicates_by_source") or {},
        row_errors_by_source=result.get("row_errors_by_source") or {},
        predictions_by_source=result.get("predictions_by_source") or {},
        source_errors=result.get("source_errors") or [],
        weather_timeout_count=int(result.get("weather_timeout_count", 0) or 0),
        weather_fallback_count=int(result.get("weather_fallback_count", 0) or 0),
        weather_error_count=int(result.get("weather_error_count", 0) or 0),
        error_message=error_message or result.get("error_message"),
    )

    db.add(run)
    db.commit()
    db.refresh(run)
    logger.info(
        "[SYSTEM HEALTH] NASA fetch run saved: status=%s received=%s inserted=%s predictions=%s",
        run.status,
        run.received_count,
        run.inserted_count,
        run.v3_prediction_count,
    )
    return run


def safe_save_nasa_fetch_run(
    db: Session,
    *,
    result: Dict[str, Any],
    started_at: datetime,
    finished_at: Optional[datetime] = None,
    error_message: Optional[str] = None,
) -> Optional[NasaFetchRun]:
    try:
        return save_nasa_fetch_run(
            db,
            result=result,
            started_at=started_at,
            finished_at=finished_at,
            error_message=error_message,
        )
    except Exception:
        db.rollback()
        logger.exception("[SYSTEM HEALTH] NASA fetch run could not be saved")
        return None
