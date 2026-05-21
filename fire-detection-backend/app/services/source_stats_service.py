from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.hotspot import Hotspot
from app.services.nasa_service import FIRMS_SOURCES

TRT = ZoneInfo("Europe/Istanbul")


def _parse_observation_utc(acq_date, acq_time):
    if not acq_date or acq_time is None:
        return None

    time_value = str(acq_time).replace(".0", "").zfill(4)
    try:
        return datetime(
            year=acq_date.year,
            month=acq_date.month,
            day=acq_date.day,
            hour=int(time_value[:2]),
            minute=int(time_value[2:4]),
            tzinfo=timezone.utc,
        )
    except (TypeError, ValueError):
        return None


def get_hotspot_source_stats(db: Session):
    now_utc = datetime.now(timezone.utc)
    server_time_trt = now_utc.astimezone(TRT)

    source_filter = Hotspot.firms_source.in_(FIRMS_SOURCES)
    total_hotspot_count = db.query(func.count(Hotspot.id)).filter(source_filter).scalar() or 0
    groups = (
        db.query(
            Hotspot.firms_source,
            Hotspot.satellite,
            Hotspot.instrument,
            func.count(Hotspot.id).label("total_hotspots"),
        )
        .filter(Hotspot.firms_source.isnot(None))
        .filter(source_filter)
        .group_by(Hotspot.firms_source, Hotspot.satellite, Hotspot.instrument)
        .order_by(Hotspot.firms_source.asc(), Hotspot.satellite.asc())
        .all()
    )

    sources = []
    for firms_source, satellite, instrument, total_hotspots in groups:
        latest = (
            db.query(Hotspot)
            .filter(
                Hotspot.firms_source == firms_source,
                Hotspot.satellite == satellite,
                Hotspot.instrument == instrument,
            )
            .order_by(Hotspot.acq_date.desc().nullslast(), Hotspot.acq_time.desc().nullslast())
            .first()
        )

        latest_observation_utc = _parse_observation_utc(
            getattr(latest, "acq_date", None),
            getattr(latest, "acq_time", None),
        )
        latest_observation_trt = (
            latest_observation_utc.astimezone(TRT) if latest_observation_utc else None
        )
        hours_since_latest_observation = (
            round((now_utc - latest_observation_utc).total_seconds() / 3600, 2)
            if latest_observation_utc
            else None
        )

        sources.append({
            "firms_source": firms_source,
            "satellite": satellite,
            "instrument": instrument,
            "total_hotspots": int(total_hotspots or 0),
            "latest_acq_date": latest.acq_date.isoformat() if latest and latest.acq_date else None,
            "latest_acq_time": str(latest.acq_time).replace(".0", "").zfill(4)
            if latest and latest.acq_time is not None
            else None,
            "latest_observation_utc": latest_observation_utc.isoformat().replace("+00:00", "Z")
            if latest_observation_utc
            else None,
            "latest_observation_trt": latest_observation_trt.isoformat()
            if latest_observation_trt
            else None,
            "hours_since_latest_observation": hours_since_latest_observation,
        })

    return {
        "status": "success",
        "server_time_utc": now_utc.isoformat().replace("+00:00", "Z"),
        "server_time_trt": server_time_trt.isoformat(),
        "total_hotspot_count": int(total_hotspot_count),
        "source_count": len(sources),
        "prediction_limit_per_fetch": settings.V3_MAX_PREDICTIONS_PER_NASA_FETCH,
        "prediction_limit_note": (
            f"Prediction processing limited to "
            f"{settings.V3_MAX_PREDICTIONS_PER_NASA_FETCH} records per fetch cycle"
        ),
        "sources": sources,
    }
