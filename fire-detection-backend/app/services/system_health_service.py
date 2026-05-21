from __future__ import annotations

from datetime import timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.time_utils import utc_now, utc_now_naive
from app.models.alert import Alert
from app.models.fire_cluster import FireCluster
from app.models.hotspot import Hotspot
from app.models.nasa_fetch_run import NasaFetchRun
from app.services.nasa_fetch_run_service import EXPECTED_FIRMS_SOURCES

TRT = timezone(timedelta(hours=3))


def _iso_utc(value):
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _iso_trt(value):
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc).astimezone(TRT).isoformat()


def _status_counts(db: Session) -> Dict[str, int]:
    counts = {"active": 0, "monitoring": 0, "resolved": 0}
    rows = db.query(FireCluster.status, func.count(FireCluster.id)).group_by(FireCluster.status).all()
    for status, count in rows:
        key = str(status or "resolved").lower()
        if key in counts:
            counts[key] = int(count)
    return counts


def _database_counts(db: Session) -> Dict[str, int]:
    hotspots_total = db.query(func.count(Hotspot.id)).scalar() or 0
    hotspots_clustered = (
        db.query(func.count(Hotspot.id))
        .filter(Hotspot.cluster_id.isnot(None))
        .scalar()
        or 0
    )
    alerts_total = db.query(func.count(Alert.id)).scalar() or 0
    alerts_clustered = (
        db.query(func.count(Alert.id))
        .filter(Alert.cluster_id.isnot(None))
        .scalar()
        or 0
    )
    return {
        "hotspots_total": int(hotspots_total),
        "hotspots_clustered": int(hotspots_clustered),
        "hotspots_unclustered": int(hotspots_total - hotspots_clustered),
        "alerts_total": int(alerts_total),
        "alerts_clustered": int(alerts_clustered),
    }


def _sources_payload(run: Optional[NasaFetchRun]) -> Dict[str, Dict[str, Any]]:
    source_errors = {}
    if run:
        for item in run.source_errors or []:
            source = item.get("source")
            if source:
                source_errors[source] = item.get("error") or "source failed"

    payload = {}
    for source in EXPECTED_FIRMS_SOURCES:
        payload[source] = {
            "received": int((run.received_by_source or {}).get(source, 0)) if run else 0,
            "inserted": int((run.inserted_by_source or {}).get(source, 0)) if run else 0,
            "duplicates": int((run.duplicates_by_source or {}).get(source, 0)) if run else 0,
            "predictions": int((run.predictions_by_source or {}).get(source, 0)) if run else 0,
            "row_errors": int((run.row_errors_by_source or {}).get(source, 0)) if run else 0,
            "status": "error" if source in source_errors else "ok" if run else "unknown",
        }
        if source in source_errors:
            payload[source]["error"] = source_errors[source]
    return payload


def _last_fetch_payload(run: Optional[NasaFetchRun]) -> Optional[Dict[str, Any]]:
    if run is None:
        return None

    return {
        "id": run.id,
        "status": run.status,
        "started_at": _iso_utc(run.started_at),
        "started_at_trt": _iso_trt(run.started_at),
        "finished_at": _iso_utc(run.finished_at),
        "finished_at_trt": _iso_trt(run.finished_at),
        "duration_seconds": run.duration_seconds,
        "received_count": run.received_count or 0,
        "inserted_count": run.inserted_count or 0,
        "duplicate_count": run.duplicate_count or 0,
        "source_error_count": run.source_error_count or 0,
        "row_error_count": run.row_error_count or 0,
        "v3_prediction_count": run.v3_prediction_count or 0,
        "prediction_limit_per_fetch": run.prediction_limit_per_fetch,
        "prediction_limit_applied": bool(run.prediction_limit_applied),
        "prediction_limit_note": run.prediction_limit_note,
        "error_message": run.error_message,
    }


def _calculate_health(run: Optional[NasaFetchRun], db_ok: bool = True) -> str:
    if not db_ok:
        return "error"
    if run is None:
        return "degraded"
    if run.status == "failed":
        return "error"
    if run.status == "partial" or int(run.source_error_count or 0) > 0:
        return "degraded"
    if run.finished_at and run.finished_at < utc_now_naive() - timedelta(hours=3):
        return "degraded"
    if int(run.weather_fallback_count or 0) > 50:
        return "degraded"
    return "healthy"


def get_system_health(db: Session) -> Dict[str, Any]:
    run = db.query(NasaFetchRun).order_by(NasaFetchRun.finished_at.desc(), NasaFetchRun.id.desc()).first()
    clusters = _status_counts(db)
    database = _database_counts(db)
    health = _calculate_health(run)

    response = {
        "status": "success",
        "health": health,
        "server_time_utc": utc_now().isoformat().replace("+00:00", "Z"),
        "server_time_trt": utc_now().astimezone(TRT).isoformat(),
        "last_fetch": _last_fetch_payload(run),
        "sources": _sources_payload(run),
        "clusters": {
            "total": int(sum(clusters.values())),
            **clusters,
        },
        "weather": {
            "timeout_count": int(run.weather_timeout_count or 0) if run else 0,
            "fallback_count": int(run.weather_fallback_count or 0) if run else 0,
            "error_count": int(run.weather_error_count or 0) if run else 0,
        },
        "database": database,
    }

    if run is None:
        response["message"] = "No NASA fetch run recorded yet"

    return response
