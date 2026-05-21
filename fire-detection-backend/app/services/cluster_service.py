import math
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, Optional

from sqlalchemy.orm import Session

from app.core.time_utils import utc_now_naive
from app.models.fire_cluster import FireCluster
from app.models.hotspot import Hotspot
from app.services.cluster_status_service import (
    CLUSTER_STATUS_ACTIVE,
    CLUSTER_STATUS_MONITORING,
    get_cluster_status_for_last_seen,
)

CLUSTER_RADIUS_KM = 5
CLUSTER_TIME_WINDOW_HOURS = 6

RISK_ORDER = {
    None: 0,
    "UNKNOWN": 0,
    "LOW": 1,
    "WATCH": 2,
    "MEDIUM": 3,
    "HIGH": 4,
    "CRITICAL": 5,
}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _hotspot_observed_at(hotspot: Hotspot) -> datetime:
    if hotspot.acq_date is None:
        return utc_now_naive()

    acq_time = str(hotspot.acq_time or "0000").replace(".0", "").zfill(4)
    try:
        hour = int(acq_time[:2])
        minute = int(acq_time[2:4])
    except ValueError:
        hour = 0
        minute = 0

    return datetime.combine(hotspot.acq_date, datetime.min.time()).replace(hour=hour, minute=minute)


def _merge_unique(existing: Optional[Iterable[str]], value: Optional[str]) -> list[str]:
    items = [str(item) for item in (existing or []) if item]
    if value and str(value) not in items:
        items.append(str(value))
    return sorted(items)


def _risk_level_from_prediction(prediction: Dict[str, Any]) -> str:
    decision_level = int(prediction.get("decision", {}).get("decision_level", 0) or 0)
    if decision_level >= 4:
        return "CRITICAL"
    if decision_level == 3:
        return "HIGH"
    if decision_level == 2:
        return "MEDIUM"
    if decision_level == 1:
        return "WATCH"
    return "LOW"


class ClusterService:
    def assign_hotspot_to_cluster(self, db: Session, hotspot: Hotspot) -> FireCluster:
        observed_at = _hotspot_observed_at(hotspot)
        window_start = observed_at - timedelta(hours=CLUSTER_TIME_WINDOW_HOURS)
        window_end = observed_at + timedelta(hours=CLUSTER_TIME_WINDOW_HOURS)

        candidates = (
            db.query(FireCluster)
            .filter(FireCluster.status.in_([CLUSTER_STATUS_ACTIVE, CLUSTER_STATUS_MONITORING]))
            .filter(FireCluster.last_seen_at >= window_start)
            .filter(FireCluster.first_seen_at <= window_end)
            .all()
        )

        closest = None
        closest_distance = None
        for cluster in candidates:
            distance = _haversine_km(
                hotspot.latitude,
                hotspot.longitude,
                cluster.center_latitude,
                cluster.center_longitude,
            )
            if distance > CLUSTER_RADIUS_KM:
                continue
            if closest is None or distance < closest_distance:
                closest = cluster
                closest_distance = distance

        if closest is None:
            closest = FireCluster(
                center_latitude=hotspot.latitude,
                center_longitude=hotspot.longitude,
                first_seen_at=observed_at,
                last_seen_at=observed_at,
                hotspot_count=0,
                max_fire_probability=None,
                max_risk_level=None,
                sources=[],
                satellites=[],
                status="active",
            )
            db.add(closest)
            db.flush()

        self.add_hotspot_to_cluster(db, closest, hotspot, observed_at)
        return closest

    def add_hotspot_to_cluster(
        self,
        db: Session,
        cluster: FireCluster,
        hotspot: Hotspot,
        observed_at: Optional[datetime] = None,
    ) -> FireCluster:
        observed_at = observed_at or _hotspot_observed_at(hotspot)
        old_count = int(cluster.hotspot_count or 0)
        new_count = old_count + 1

        cluster.center_latitude = ((cluster.center_latitude * old_count) + hotspot.latitude) / new_count
        cluster.center_longitude = ((cluster.center_longitude * old_count) + hotspot.longitude) / new_count
        cluster.first_seen_at = min(cluster.first_seen_at, observed_at)
        cluster.last_seen_at = max(cluster.last_seen_at, observed_at)
        cluster.hotspot_count = new_count
        cluster.sources = _merge_unique(cluster.sources, hotspot.firms_source)
        cluster.satellites = _merge_unique(cluster.satellites, hotspot.satellite)
        cluster.status = get_cluster_status_for_last_seen(cluster.last_seen_at)
        cluster.updated_at = utc_now_naive()

        hotspot.cluster_id = cluster.id
        db.flush()
        return cluster

    def update_cluster_from_prediction(
        self,
        db: Session,
        hotspot_id: Optional[int],
        prediction: Dict[str, Any],
    ) -> Optional[FireCluster]:
        if hotspot_id is None:
            return None

        hotspot = db.query(Hotspot).filter(Hotspot.id == hotspot_id).first()
        if not hotspot or not hotspot.cluster_id:
            return None

        cluster = db.query(FireCluster).filter(FireCluster.id == hotspot.cluster_id).first()
        if not cluster:
            return None

        probability = prediction.get("probabilities", {}).get("ensemble_fire_probability")
        if probability is not None:
            probability = float(probability)
            if cluster.max_fire_probability is None or probability > cluster.max_fire_probability:
                cluster.max_fire_probability = probability

        risk_level = _risk_level_from_prediction(prediction)
        current_rank = RISK_ORDER.get(str(cluster.max_risk_level or "UNKNOWN").upper(), 0)
        next_rank = RISK_ORDER.get(risk_level, 0)
        if next_rank > current_rank:
            cluster.max_risk_level = risk_level

        cluster.updated_at = utc_now_naive()
        db.commit()
        db.refresh(cluster)
        return cluster


cluster_service = ClusterService()
