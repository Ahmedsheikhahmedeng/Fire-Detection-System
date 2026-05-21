from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time_utils import utc_now_naive
from app.models.fire_cluster import FireCluster

CLUSTER_STATUS_ACTIVE = "active"
CLUSTER_STATUS_MONITORING = "monitoring"
CLUSTER_STATUS_RESOLVED = "resolved"
CLUSTER_STATUSES = {
    CLUSTER_STATUS_ACTIVE,
    CLUSTER_STATUS_MONITORING,
    CLUSTER_STATUS_RESOLVED,
}


def get_cluster_status_for_last_seen(
    last_seen_at: Optional[datetime],
    *,
    reference_time: Optional[datetime] = None,
    active_hours: Optional[int] = None,
    monitoring_hours: Optional[int] = None,
) -> str:
    if last_seen_at is None:
        return CLUSTER_STATUS_RESOLVED

    now = reference_time or utc_now_naive()
    active_window = active_hours if active_hours is not None else settings.CLUSTER_ACTIVE_HOURS
    monitoring_window = (
        monitoring_hours
        if monitoring_hours is not None
        else settings.CLUSTER_MONITORING_HOURS
    )

    if last_seen_at >= now - timedelta(hours=active_window):
        return CLUSTER_STATUS_ACTIVE
    if last_seen_at >= now - timedelta(hours=monitoring_window):
        return CLUSTER_STATUS_MONITORING
    return CLUSTER_STATUS_RESOLVED


def update_cluster_statuses(
    db: Session,
    *,
    reference_time: Optional[datetime] = None,
    commit: bool = True,
) -> Dict[str, Any]:
    now = reference_time or utc_now_naive()
    clusters = db.query(FireCluster).order_by(FireCluster.id.asc()).all()
    report = {
        "processed_clusters": 0,
        CLUSTER_STATUS_ACTIVE: 0,
        CLUSTER_STATUS_MONITORING: 0,
        CLUSTER_STATUS_RESOLVED: 0,
        "changed_clusters": 0,
        "errors": 0,
    }

    try:
        for cluster in clusters:
            try:
                next_status = get_cluster_status_for_last_seen(
                    cluster.last_seen_at,
                    reference_time=now,
                )
                report["processed_clusters"] += 1
                report[next_status] += 1
                if cluster.status != next_status:
                    cluster.status = next_status
                    cluster.updated_at = now
                    report["changed_clusters"] += 1
            except Exception:
                report["errors"] += 1

        if commit:
            db.commit()
        else:
            db.flush()
        return report
    except Exception:
        db.rollback()
        raise
