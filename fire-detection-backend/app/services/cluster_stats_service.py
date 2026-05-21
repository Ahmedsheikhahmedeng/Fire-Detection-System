from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.fire_cluster import FireCluster
from app.services.cluster_status_service import (
    CLUSTER_STATUS_ACTIVE,
    CLUSTER_STATUS_MONITORING,
    CLUSTER_STATUS_RESOLVED,
    CLUSTER_STATUSES,
)


def _cluster_payload(cluster: FireCluster) -> dict:
    return {
        "id": cluster.id,
        "center_latitude": cluster.center_latitude,
        "center_longitude": cluster.center_longitude,
        "first_seen_at": cluster.first_seen_at.isoformat() if cluster.first_seen_at else None,
        "last_seen_at": cluster.last_seen_at.isoformat() if cluster.last_seen_at else None,
        "hotspot_count": cluster.hotspot_count or 0,
        "max_fire_probability": cluster.max_fire_probability,
        "max_risk_level": cluster.max_risk_level,
        "sources": cluster.sources or [],
        "satellites": cluster.satellites or [],
        "status": cluster.status,
        "created_at": cluster.created_at.isoformat() if cluster.created_at else None,
        "updated_at": cluster.updated_at.isoformat() if cluster.updated_at else None,
    }


def _normalize_status_filter(status: str | None) -> tuple[list[str] | None, str]:
    if status is None or status == "":
        statuses = [CLUSTER_STATUS_ACTIVE, CLUSTER_STATUS_MONITORING]
        return statuses, ",".join(statuses)

    raw = str(status).strip().lower()
    if raw == "all":
        return None, "all"

    statuses = [item.strip() for item in raw.split(",") if item.strip()]
    valid_statuses = [item for item in statuses if item in CLUSTER_STATUSES]
    if not valid_statuses:
        valid_statuses = [CLUSTER_STATUS_ACTIVE, CLUSTER_STATUS_MONITORING]

    return valid_statuses, ",".join(valid_statuses)


def _status_counts(db: Session) -> dict:
    rows = (
        db.query(FireCluster.status, func.count(FireCluster.id))
        .group_by(FireCluster.status)
        .all()
    )
    counts = {
        CLUSTER_STATUS_ACTIVE: 0,
        CLUSTER_STATUS_MONITORING: 0,
        CLUSTER_STATUS_RESOLVED: 0,
    }
    for status, count in rows:
        key = str(status or CLUSTER_STATUS_RESOLVED).lower()
        if key in counts:
            counts[key] = int(count)
    return counts


def get_fire_clusters(db: Session, status: str | None = None, limit: int = 50) -> dict:
    statuses, filter_label = _normalize_status_filter(status)
    query = db.query(FireCluster)
    if statuses is not None:
        query = query.filter(FireCluster.status.in_(statuses))

    counts = _status_counts(db)
    matching_count = query.with_entities(func.count(FireCluster.id)).scalar() or 0
    clusters = (
        query.order_by(FireCluster.last_seen_at.desc(), FireCluster.id.desc())
        .limit(limit)
        .all()
    )

    return {
        "status": "success",
        "cluster_count": int(sum(counts.values())),
        "matching_count": int(matching_count),
        "returned_count": len(clusters),
        "status_counts": counts,
        "filters": {
            "status": filter_label,
            "limit": limit,
        },
        "clusters": [_cluster_payload(cluster) for cluster in clusters],
    }
