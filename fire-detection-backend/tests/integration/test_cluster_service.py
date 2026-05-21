from datetime import date, timedelta

from app.core.time_utils import utc_now_naive
from app.models.alert import Alert
from app.models.fire_cluster import FireCluster
from app.models.hotspot import Hotspot
from app.services.alert_service import alert_service
from app.services.cluster_service import cluster_service


def _hotspot(lat, lon, *, acq_date, acq_time, source="VIIRS_SNPP_NRT", satellite="N"):
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
        acq_date=acq_date,
        acq_time=acq_time,
        city=None,
    )


def _prediction(decision_level=3, probability=0.82):
    return {
        "model_version": "v3-test",
        "probabilities": {"ensemble_fire_probability": probability},
        "decision": {
            "decision_level": decision_level,
            "decision_name": "cluster_test",
        },
    }


def test_nearby_hotspots_share_cluster_and_sources_update(db_session):
    first = _hotspot(
        38.4000,
        27.1000,
        acq_date=date(2026, 5, 19),
        acq_time="1200",
        source="VIIRS_SNPP_NRT",
        satellite="N",
    )
    second = _hotspot(
        38.4100,
        27.1100,
        acq_date=date(2026, 5, 19),
        acq_time="1300",
        source="VIIRS_NOAA21_NRT",
        satellite="N21",
    )
    db_session.add_all([first, second])
    db_session.flush()

    cluster_one = cluster_service.assign_hotspot_to_cluster(db_session, first)
    cluster_two = cluster_service.assign_hotspot_to_cluster(db_session, second)
    db_session.commit()

    assert cluster_one.id == cluster_two.id
    assert first.cluster_id == cluster_one.id
    assert second.cluster_id == cluster_one.id
    assert cluster_two.hotspot_count == 2
    assert cluster_two.sources == ["VIIRS_NOAA21_NRT", "VIIRS_SNPP_NRT"]
    assert cluster_two.satellites == ["N", "N21"]


def test_far_hotspot_creates_new_cluster(db_session):
    first = _hotspot(38.4, 27.1, acq_date=date(2026, 5, 19), acq_time="1200")
    far = _hotspot(39.4, 28.1, acq_date=date(2026, 5, 19), acq_time="1300")
    db_session.add_all([first, far])
    db_session.flush()

    cluster_one = cluster_service.assign_hotspot_to_cluster(db_session, first)
    cluster_two = cluster_service.assign_hotspot_to_cluster(db_session, far)
    db_session.commit()

    assert cluster_one.id != cluster_two.id
    assert db_session.query(FireCluster).count() == 2


def test_old_hotspot_creates_new_cluster(db_session):
    first = _hotspot(38.4, 27.1, acq_date=date(2026, 5, 19), acq_time="1200")
    old = _hotspot(38.401, 27.101, acq_date=date(2026, 5, 19), acq_time="1901")
    db_session.add_all([first, old])
    db_session.flush()

    cluster_one = cluster_service.assign_hotspot_to_cluster(db_session, first)
    cluster_two = cluster_service.assign_hotspot_to_cluster(db_session, old)
    db_session.commit()

    assert cluster_one.id != cluster_two.id


def test_cluster_max_risk_updates_from_prediction(db_session):
    hotspot = _hotspot(38.4, 27.1, acq_date=date(2026, 5, 19), acq_time="1200")
    db_session.add(hotspot)
    db_session.flush()
    cluster = cluster_service.assign_hotspot_to_cluster(db_session, hotspot)
    db_session.commit()

    cluster_service.update_cluster_from_prediction(db_session, hotspot.id, _prediction(3, 0.82))
    cluster_service.update_cluster_from_prediction(db_session, hotspot.id, _prediction(4, 0.91))

    db_session.refresh(cluster)
    assert cluster.max_risk_level == "CRITICAL"
    assert cluster.max_fire_probability == 0.91


def test_same_cluster_does_not_create_duplicate_alert_and_escalates(db_session, monkeypatch):
    monkeypatch.setattr(
        "app.services.alert_service.notification_manager.send_alert",
        lambda alert, prediction: {"disabled": True},
    )
    monkeypatch.setattr(
        "app.services.alert_service.manager.broadcast_threadsafe",
        lambda payload: None,
    )

    first = _hotspot(38.4, 27.1, acq_date=date(2026, 5, 19), acq_time="1200")
    second = _hotspot(38.401, 27.101, acq_date=date(2026, 5, 19), acq_time="1210")
    db_session.add_all([first, second])
    db_session.flush()
    cluster_service.assign_hotspot_to_cluster(db_session, first)
    cluster_service.assign_hotspot_to_cluster(db_session, second)
    db_session.commit()

    first_alert = alert_service.create_alert_from_prediction(
        db_session,
        _prediction(3, 0.82),
        hotspot_id=first.id,
        broadcast=False,
    )
    duplicate = alert_service.create_alert_from_prediction(
        db_session,
        _prediction(3, 0.84),
        hotspot_id=second.id,
        broadcast=False,
    )
    escalated = alert_service.create_alert_from_prediction(
        db_session,
        _prediction(4, 0.94),
        hotspot_id=second.id,
        broadcast=False,
    )

    assert first_alert.id == duplicate.id == escalated.id
    assert db_session.query(Alert).count() == 1
    assert escalated.risk_level == "CRITICAL"
    assert escalated.hotspot_id == second.id
