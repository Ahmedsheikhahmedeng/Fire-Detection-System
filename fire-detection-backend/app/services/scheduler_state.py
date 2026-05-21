from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.time_utils import utc_now_naive


def write_scheduler_state(db: Session, values: dict) -> None:
    """Persist scheduler state so the API can read it from a separate process."""
    now = utc_now_naive()
    for key, value in values.items():
        if value is None:
            continue

        db.execute(
            text(
                """
                INSERT INTO scheduler_state (key, value, updated_at)
                VALUES (:key, :value, :updated_at)
                ON CONFLICT (key)
                DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = EXCLUDED.updated_at
                """
            ),
            {
                "key": key,
                "value": str(value),
                "updated_at": now,
            },
        )
    db.commit()


def read_scheduler_state(db: Session) -> dict:
    rows = db.execute(text("SELECT key, value FROM scheduler_state")).all()
    return {row.key: row.value for row in rows}


def _parse_datetime(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def is_recent_worker_heartbeat(value, max_age_seconds: int = 180) -> bool:
    heartbeat = _parse_datetime(value)
    if heartbeat is None:
        return False

    if heartbeat.tzinfo is None:
        heartbeat = heartbeat.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    return (now - heartbeat).total_seconds() <= max_age_seconds


def optional_int(value, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_scheduler_state(status: dict, api_scheduler_enabled: bool) -> dict:
    """Normalize persisted scheduler state before exposing it through API responses."""
    normalized = {**status}
    persisted_worker_status = normalized.get("worker_status")
    worker_alive = (
        persisted_worker_status == "running"
        and is_recent_worker_heartbeat(normalized.get("worker_last_seen_at"))
    )

    if persisted_worker_status == "running" and not worker_alive:
        normalized["worker_status"] = "stopped"

    normalized["worker_alive"] = worker_alive
    normalized["enabled"] = bool(api_scheduler_enabled or worker_alive)
    normalized["last_city_resolved_count"] = optional_int(
        normalized.get("last_city_resolved_count"),
        0,
    )

    for key in (
        "nasa_hotspots_inserted",
        "v3_prediction_count",
        "v3_alert_count",
        "ml_processed",
        "ml_high_risk",
    ):
        if key in normalized:
            normalized[key] = optional_int(normalized.get(key), 0)

    return normalized
