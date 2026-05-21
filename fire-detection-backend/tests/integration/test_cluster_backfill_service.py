from datetime import date, datetime

from app.models.alert import Alert
from app.models.fire_cluster import FireCluster
from app.models.hotspot import Hotspot
from app.models.prediction import Prediction
from app.services.cluster_backfill_service import (
    backfill_alert_clusters,
    backfill_fire_clusters,
    recalculate_fire_clusters,
)
from app.services.cluster_service import cluster_service


def _hotspot(lat, lon, acq_time, *, source="VIIRS_SNPP_NRT", satellite="N"):
    return Hotspot(
        latitude=lat,
        longitude=lon,
        brightness=330,
        bright_ti5=295,
        frp=45,
        scan=0.5,
        track=0.5,
        confidence="h",
        daynight="D",
        satellite=satellite,
        instrument="VIIRS",
        firms_source=source,
        type=0,
        version=2,
        acq_date=date(2026, 5, 19),
        acq_time=acq_time,
        city=None,
    )


def test_backfill_links_legacy_hotspots_into_clusters(db_session):
    first = _hotspot(38.4, 27.1, "1200", source="VIIRS_SNPP_NRT", satellite="N")
    second = _hotspot(38.401, 27.101, "1210", source="VIIRS_NOAA21_NRT", satellite="N21")
    far = _hotspot(39.4, 28.1, "1220")
    db_session.add_all([first, second, far])
    db_session.commit()

    report = backfill_fire_clusters(db_session)

    assert report["processed_hotspots"] == 3
    assert report["linked_hotspots"] == 3
    assert report["created_clusters"] == 2
    db_session.refresh(first)
    db_session.refresh(second)
    db_session.refresh(far)
    assert first.cluster_id == second.cluster_id
    assert far.cluster_id != first.cluster_id


def test_backfill_dry_run_does_not_write(db_session):
    hotspot = _hotspot(38.4, 27.1, "1200")
    db_session.add(hotspot)
    db_session.commit()

    report = backfill_fire_clusters(db_session, dry_run=True)

    assert report["processed_hotspots"] == 1
    assert db_session.query(FireCluster).count() == 0
    db_session.refresh(hotspot)
    assert hotspot.cluster_id is None


def test_backfill_limit_parameter(db_session):
    db_session.add_all([
        _hotspot(38.4, 27.1, "1200"),
        _hotspot(39.4, 28.1, "1210"),
        _hotspot(40.4, 29.1, "1220"),
    ])
    db_session.commit()

    report = backfill_fire_clusters(db_session, limit=2)

    assert report["processed_hotspots"] == 2
    assert db_session.query(Hotspot).filter(Hotspot.cluster_id.isnot(None)).count() == 2
    assert db_session.query(Hotspot).filter(Hotspot.cluster_id.is_(None)).count() == 1


def test_alert_cluster_backfill_links_existing_alert(db_session):
    hotspot = _hotspot(38.4, 27.1, "1200")
    db_session.add(hotspot)
    db_session.flush()
    cluster_service.assign_hotspot_to_cluster(db_session, hotspot)
    alert = Alert(
        hotspot_id=hotspot.id,
        risk_level="HIGH",
        message="legacy alert",
        status="ACTIVE",
    )
    db_session.add(alert)
    db_session.commit()

    report = backfill_alert_clusters(db_session)

    db_session.refresh(alert)
    assert report["linked_alerts"] == 1
    assert alert.cluster_id == hotspot.cluster_id


def test_recalculate_fire_clusters_repairs_cluster_values(db_session):
    first = _hotspot(38.4, 27.1, "1200", source="VIIRS_SNPP_NRT", satellite="N")
    second = _hotspot(38.42, 27.12, "1210", source="VIIRS_NOAA20_NRT", satellite="N20")
    cluster = FireCluster(
        center_latitude=0,
        center_longitude=0,
        first_seen_at=datetime(2026, 1, 1),
        last_seen_at=datetime(2026, 1, 1),
        hotspot_count=0,
        max_fire_probability=None,
        max_risk_level=None,
        sources=[],
        satellites=[],
        status="active",
    )
    db_session.add(cluster)
    db_session.flush()
    first.cluster_id = cluster.id
    second.cluster_id = cluster.id
    db_session.add_all([first, second])
    db_session.flush()
    db_session.add_all([
        Prediction(hotspot_id=first.id, fire_probability=0.7, risk_level="HIGH", decision_level=3),
        Prediction(hotspot_id=second.id, fire_probability=0.9, risk_level="CRITICAL", decision_level=4),
    ])
    db_session.commit()

    report = recalculate_fire_clusters(db_session)

    db_session.refresh(cluster)
    assert report["recalculated_clusters"] == 1
    assert cluster.hotspot_count == 2
    assert cluster.sources == ["VIIRS_NOAA20_NRT", "VIIRS_SNPP_NRT"]
    assert cluster.satellites == ["N", "N20"]
    assert cluster.max_fire_probability == 0.9
    assert cluster.max_risk_level == "CRITICAL"
