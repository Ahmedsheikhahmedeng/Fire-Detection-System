import logging
from datetime import datetime, timezone

from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.services.scheduler_state import read_scheduler_state

logger = logging.getLogger("fire_detection.health")


def check_database_health() -> str:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "connected"
    except Exception as exc:
        logger.warning("Health database check failed: %s", exc)
        return "disconnected"


def get_ml_model_status() -> str:
    try:
        from app.services.ml_service import v3_fire_model_service

        if getattr(v3_fire_model_service, "is_loaded", False):
            return "loaded"
        if getattr(v3_fire_model_service, "models", None):
            return "loaded"
        return "not_loaded"
    except Exception:
        return "unknown"


def get_scheduler_health_status() -> str:
    try:
        db = SessionLocal()
        try:
            persisted_status = read_scheduler_state(db)
        finally:
            db.close()

        worker_last_seen = persisted_status.get("worker_last_seen_at")
        worker_status = persisted_status.get("worker_status")
        worker_alive = False
        if worker_status == "running" and worker_last_seen:
            heartbeat = datetime.fromisoformat(str(worker_last_seen).replace("Z", "+00:00"))
            if heartbeat.tzinfo is None:
                heartbeat = heartbeat.replace(tzinfo=timezone.utc)
            worker_alive = (datetime.now(timezone.utc) - heartbeat).total_seconds() <= 180

        if worker_alive:
            return "worker_active"

        if not settings.ENABLE_SCHEDULER:
            return "disabled"

        from app.services.scheduler import get_scheduler_status

        status = get_scheduler_status()
        return "running" if status.get("is_running") else "enabled"
    except Exception:
        return "unknown"


def get_security_status() -> str:
    return "enabled" if settings.API_KEY else "not_configured"


def build_health_response() -> dict:
    database_status = check_database_health()
    ml_model_status = get_ml_model_status()
    scheduler_status = get_scheduler_health_status()
    security_status = get_security_status()

    overall_status = "ok"
    if database_status != "connected":
        overall_status = "degraded"

    return {
        "status": overall_status,
        "app": settings.APP_NAME or "Fire Detection Backend",
        "environment": settings.APP_ENV,
        "version": settings.APP_VERSION,
        "database": database_status,
        "ml_model": ml_model_status,
        "scheduler": scheduler_status,
        "security": security_status,
    }
