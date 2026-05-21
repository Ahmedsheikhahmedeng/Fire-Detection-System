from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.time_utils import utc_now_naive
from app.models.alert import Alert
from app.models.fire_cluster import FireCluster
from app.models.hotspot import Hotspot
from app.models.prediction import Prediction
from app.services.cluster_service import RISK_ORDER, _hotspot_observed_at, cluster_service
from app.services.cluster_status_service import get_cluster_status_for_last_seen


def _ordered_unclustered_hotspots(db: Session, limit: Optional[int] = None):
    query = (
        db.query(Hotspot)
        .filter(Hotspot.cluster_id.is_(None))
        .order_by(Hotspot.acq_date.asc().nullslast(), Hotspot.acq_time.asc().nullslast(), Hotspot.id.asc())
    )
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def backfill_fire_clusters(
    db: Session,
    *,
    dry_run: bool = False,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    total_unclustered = db.query(func.count(Hotspot.id)).filter(Hotspot.cluster_id.is_(None)).scalar() or 0
    hotspots = _ordered_unclustered_hotspots(db, limit)
    existing_cluster_ids = {row[0] for row in db.query(FireCluster.id).all()}

    report = {
        "dry_run": dry_run,
        "total_unclustered_hotspots": int(total_unclustered),
        "limit": limit,
        "processed_hotspots": 0,
        "created_clusters": 0,
        "updated_clusters": 0,
        "linked_hotspots": 0,
        "skipped_hotspots": 0,
        "errors": 0,
    }
    created_cluster_ids = set()
    updated_cluster_ids = set()

    try:
        for hotspot in hotspots:
            try:
                cluster = cluster_service.assign_hotspot_to_cluster(db, hotspot)
                report["processed_hotspots"] += 1
                report["linked_hotspots"] += 1

                if cluster.id not in existing_cluster_ids and cluster.id not in created_cluster_ids:
                    created_cluster_ids.add(cluster.id)
                    report["created_clusters"] += 1
                elif cluster.id in existing_cluster_ids:
                    updated_cluster_ids.add(cluster.id)
            except Exception:
                report["errors"] += 1
                report["skipped_hotspots"] += 1

        report["updated_clusters"] = len(updated_cluster_ids)
        alert_report = backfill_alert_clusters(db, dry_run=False)
        report["linked_alerts"] = alert_report["linked_alerts"]

        if dry_run:
            db.rollback()
        else:
            db.commit()

        return report
    except Exception:
        db.rollback()
        raise


def backfill_alert_clusters(db: Session, *, dry_run: bool = False) -> Dict[str, Any]:
    alerts = (
        db.query(Alert)
        .join(Hotspot, Alert.hotspot_id == Hotspot.id)
        .filter(Alert.cluster_id.is_(None), Hotspot.cluster_id.isnot(None))
        .all()
    )
    report = {
        "dry_run": dry_run,
        "processed_alerts": len(alerts),
        "linked_alerts": 0,
        "skipped_alerts": 0,
    }

    try:
        for alert in alerts:
            hotspot = db.query(Hotspot).filter(Hotspot.id == alert.hotspot_id).first()
            if not hotspot or hotspot.cluster_id is None:
                report["skipped_alerts"] += 1
                continue
            alert.cluster_id = hotspot.cluster_id
            alert.updated_at = utc_now_naive()
            report["linked_alerts"] += 1

        if dry_run:
            db.rollback()
        else:
            db.flush()
        return report
    except Exception:
        db.rollback()
        raise


def recalculate_fire_clusters(db: Session, *, dry_run: bool = False) -> Dict[str, Any]:
    clusters = db.query(FireCluster).order_by(FireCluster.id.asc()).all()
    predictions = (
        db.query(Prediction, Hotspot.cluster_id)
        .join(Hotspot, Prediction.hotspot_id == Hotspot.id)
        .filter(Hotspot.cluster_id.isnot(None))
        .all()
    )
    prediction_by_cluster = defaultdict(list)
    for prediction, cluster_id in predictions:
        prediction_by_cluster[cluster_id].append(prediction)

    report = {
        "dry_run": dry_run,
        "processed_clusters": 0,
        "recalculated_clusters": 0,
        "empty_clusters": 0,
        "errors": 0,
    }

    try:
        for cluster in clusters:
            try:
                hotspots = (
                    db.query(Hotspot)
                    .filter(Hotspot.cluster_id == cluster.id)
                    .order_by(Hotspot.acq_date.asc().nullslast(), Hotspot.acq_time.asc().nullslast())
                    .all()
                )
                report["processed_clusters"] += 1
                if not hotspots:
                    cluster.hotspot_count = 0
                    cluster.status = "resolved"
                    cluster.updated_at = utc_now_naive()
                    report["empty_clusters"] += 1
                    continue

                times = [_hotspot_observed_at(hotspot) for hotspot in hotspots]
                cluster.center_latitude = sum(h.latitude for h in hotspots) / len(hotspots)
                cluster.center_longitude = sum(h.longitude for h in hotspots) / len(hotspots)
                cluster.first_seen_at = min(times)
                cluster.last_seen_at = max(times)
                cluster.hotspot_count = len(hotspots)
                cluster.sources = sorted({h.firms_source for h in hotspots if h.firms_source})
                cluster.satellites = sorted({h.satellite for h in hotspots if h.satellite})

                max_probability = None
                max_risk_level = None
                max_risk_rank = 0
                for prediction in prediction_by_cluster.get(cluster.id, []):
                    if prediction.fire_probability is not None:
                        probability = float(prediction.fire_probability)
                        if max_probability is None or probability > max_probability:
                            max_probability = probability
                    risk_level = str(prediction.risk_level or "UNKNOWN").upper()
                    risk_rank = RISK_ORDER.get(risk_level, 0)
                    if risk_rank > max_risk_rank:
                        max_risk_rank = risk_rank
                        max_risk_level = risk_level

                cluster.max_fire_probability = max_probability
                cluster.max_risk_level = max_risk_level
                cluster.status = get_cluster_status_for_last_seen(cluster.last_seen_at)
                cluster.updated_at = utc_now_naive()
                report["recalculated_clusters"] += 1
            except Exception:
                report["errors"] += 1

        if dry_run:
            db.rollback()
        else:
            db.commit()
        return report
    except Exception:
        db.rollback()
        raise
