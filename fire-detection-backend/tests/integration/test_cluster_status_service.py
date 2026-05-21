from datetime import timedelta

from app.core.time_utils import utc_now_naive
from app.models.fire_cluster import FireCluster
from app.services.cluster_status_service import (
    get_cluster_status_for_last_seen,
    update_cluster_statuses,
)


def _cluster(last_seen_at, status="active"):
    return FireCluster(
        center_latitude=38.4,
        center_longitude=27.1,
        first_seen_at=last_seen_at,
        last_seen_at=last_seen_at,
        hotspot_count=1,
        max_fire_probability=0.8,
        max_risk_level="HIGH",
        sources=["VIIRS_SNPP_NRT"],
        satellites=["N"],
        status=status,
    )


def test_cluster_status_rules():
    now = utc_now_naive()

    assert get_cluster_status_for_last_seen(now - timedelta(hours=2), reference_time=now) == "active"
    assert get_cluster_status_for_last_seen(now - timedelta(hours=36), reference_time=now) == "monitoring"
    assert get_cluster_status_for_last_seen(now - timedelta(hours=90), reference_time=now) == "resolved"


def test_update_cluster_statuses_counts_active_monitoring_resolved(db_session):
    now = utc_now_naive()
    active = _cluster(now - timedelta(hours=2), status="resolved")
    monitoring = _cluster(now - timedelta(hours=36), status="active")
    resolved = _cluster(now - timedelta(hours=90), status="active")
    db_session.add_all([active, monitoring, resolved])
    db_session.commit()

    report = update_cluster_statuses(db_session, reference_time=now)
    db_session.refresh(active)
    db_session.refresh(monitoring)
    db_session.refresh(resolved)

    assert report["processed_clusters"] == 3
    assert report["active"] == 1
    assert report["monitoring"] == 1
    assert report["resolved"] == 1
    assert active.status == "active"
    assert monitoring.status == "monitoring"
    assert resolved.status == "resolved"
