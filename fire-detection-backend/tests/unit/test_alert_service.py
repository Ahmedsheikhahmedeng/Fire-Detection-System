import pytest

from app.models.alert import Alert
from app.services.alert_service import alert_service


def _get_alert_level(alert):
    """
    Alert modelinde risk seviyesi farkli kolon isimlerinde olabilir.
    Production kodun esnek oldugu icin test de esnek kontrol eder.
    """
    if hasattr(alert, "risk_level"):
        return alert.risk_level
    if hasattr(alert, "alert_level"):
        return alert.alert_level
    if hasattr(alert, "level"):
        return alert.level
    return None


def test_should_not_create_alert_for_level_0(low_risk_prediction_payload):
    result = alert_service.should_create_alert(low_risk_prediction_payload)

    assert result is False


def test_should_not_create_alert_for_level_1(watch_prediction_payload):
    result = alert_service.should_create_alert(watch_prediction_payload)

    assert result is False


def test_should_create_alert_for_level_2(medium_risk_prediction_payload):
    result = alert_service.should_create_alert(medium_risk_prediction_payload)

    assert result is True


def test_alert_level_mapping():
    assert alert_service.map_decision_to_alert_level(0) == "LOW"
    assert alert_service.map_decision_to_alert_level(1) == "LOW"
    assert alert_service.map_decision_to_alert_level(2) == "MEDIUM"
    assert alert_service.map_decision_to_alert_level(3) == "HIGH"
    assert alert_service.map_decision_to_alert_level(4) == "CRITICAL"
    assert alert_service.map_decision_to_alert_level(99) == "CRITICAL"


def test_build_alert_message_contains_decision_and_probability(high_risk_prediction_payload):
    message = alert_service.build_alert_message(high_risk_prediction_payload)

    assert "high_risk_fire" in message
    assert "0.880" in message
    assert "V3 fire alert" in message


def test_create_alert_from_medium_prediction(
    db_session,
    sample_hotspot_row,
    medium_risk_prediction_payload,
):
    alert = alert_service.create_alert_from_prediction(
        db=db_session,
        prediction=medium_risk_prediction_payload,
        hotspot_id=sample_hotspot_row.id,
        saved_prediction_id=None,
    )

    assert alert is not None
    assert alert.id is not None
    assert alert.hotspot_id == sample_hotspot_row.id
    assert alert.status == "ACTIVE"
    assert _get_alert_level(alert) == "MEDIUM"


def test_create_alert_from_high_prediction(
    db_session,
    sample_hotspot_row,
    high_risk_prediction_payload,
):
    alert = alert_service.create_alert_from_prediction(
        db=db_session,
        prediction=high_risk_prediction_payload,
        hotspot_id=sample_hotspot_row.id,
        saved_prediction_id=None,
    )

    assert alert is not None
    assert alert.hotspot_id == sample_hotspot_row.id
    assert alert.status == "ACTIVE"
    assert _get_alert_level(alert) == "HIGH"


def test_create_alert_from_critical_prediction(
    db_session,
    sample_hotspot_row,
    critical_risk_prediction_payload,
):
    alert = alert_service.create_alert_from_prediction(
        db=db_session,
        prediction=critical_risk_prediction_payload,
        hotspot_id=sample_hotspot_row.id,
        saved_prediction_id=None,
    )

    assert alert is not None
    assert alert.hotspot_id == sample_hotspot_row.id
    assert alert.status == "ACTIVE"
    assert _get_alert_level(alert) == "CRITICAL"


def test_no_alert_created_for_low_risk_prediction(
    db_session,
    sample_hotspot_row,
    low_risk_prediction_payload,
):
    alert = alert_service.create_alert_from_prediction(
        db=db_session,
        prediction=low_risk_prediction_payload,
        hotspot_id=sample_hotspot_row.id,
        saved_prediction_id=None,
    )

    assert alert is None

    count = db_session.query(Alert).count()
    assert count == 0


def test_no_alert_created_for_watch_prediction(
    db_session,
    sample_hotspot_row,
    watch_prediction_payload,
):
    alert = alert_service.create_alert_from_prediction(
        db=db_session,
        prediction=watch_prediction_payload,
        hotspot_id=sample_hotspot_row.id,
        saved_prediction_id=None,
    )

    assert alert is None

    count = db_session.query(Alert).count()
    assert count == 0


def test_no_alert_created_without_hotspot_id(
    db_session,
    high_risk_prediction_payload,
):
    alert = alert_service.create_alert_from_prediction(
        db=db_session,
        prediction=high_risk_prediction_payload,
        hotspot_id=None,
        saved_prediction_id=None,
    )

    assert alert is None

    count = db_session.query(Alert).count()
    assert count == 0


def test_duplicate_active_alert_is_not_created(
    db_session,
    sample_hotspot_row,
    high_risk_prediction_payload,
):
    first_alert = alert_service.create_alert_from_prediction(
        db=db_session,
        prediction=high_risk_prediction_payload,
        hotspot_id=sample_hotspot_row.id,
        saved_prediction_id=None,
    )

    second_alert = alert_service.create_alert_from_prediction(
        db=db_session,
        prediction=high_risk_prediction_payload,
        hotspot_id=sample_hotspot_row.id,
        saved_prediction_id=None,
    )

    assert first_alert is not None
    assert second_alert is not None
    assert first_alert.id == second_alert.id

    active_count = (
        db_session.query(Alert)
        .filter(Alert.hotspot_id == sample_hotspot_row.id, Alert.status == "ACTIVE")
        .count()
    )

    assert active_count == 1


def test_get_active_alert_for_hotspot_returns_existing_alert(
    db_session,
    sample_hotspot_row,
    high_risk_prediction_payload,
):
    created_alert = alert_service.create_alert_from_prediction(
        db=db_session,
        prediction=high_risk_prediction_payload,
        hotspot_id=sample_hotspot_row.id,
        saved_prediction_id=None,
    )

    active_alert = alert_service.get_active_alert_for_hotspot(
        db=db_session,
        hotspot_id=sample_hotspot_row.id,
    )

    assert active_alert is not None
    assert active_alert.id == created_alert.id
    assert active_alert.status == "ACTIVE"


def test_update_alert_status_to_acknowledged(
    db_session,
    sample_hotspot_row,
    high_risk_prediction_payload,
):
    alert = alert_service.create_alert_from_prediction(
        db=db_session,
        prediction=high_risk_prediction_payload,
        hotspot_id=sample_hotspot_row.id,
        saved_prediction_id=None,
    )

    updated = alert_service.update_alert_status(
        db=db_session,
        alert_id=alert.id,
        status="ACKNOWLEDGED",
    )

    assert updated is not None
    assert updated.status == "ACKNOWLEDGED"
    assert updated.updated_at is not None


def test_update_alert_status_to_resolved_sets_resolved_at(
    db_session,
    sample_hotspot_row,
    high_risk_prediction_payload,
):
    alert = alert_service.create_alert_from_prediction(
        db=db_session,
        prediction=high_risk_prediction_payload,
        hotspot_id=sample_hotspot_row.id,
        saved_prediction_id=None,
    )

    updated = alert_service.update_alert_status(
        db=db_session,
        alert_id=alert.id,
        status="RESOLVED",
    )

    assert updated is not None
    assert updated.status == "RESOLVED"
    assert updated.updated_at is not None
    assert updated.resolved_at is not None


def test_close_alert_sets_closed_and_resolved_at(
    db_session,
    sample_hotspot_row,
    high_risk_prediction_payload,
):
    alert = alert_service.create_alert_from_prediction(
        db=db_session,
        prediction=high_risk_prediction_payload,
        hotspot_id=sample_hotspot_row.id,
        saved_prediction_id=None,
    )

    closed = alert_service.close_alert(
        db=db_session,
        alert_id=alert.id,
    )

    assert closed is not None
    assert closed.status == "CLOSED"
    assert closed.updated_at is not None
    assert closed.resolved_at is not None


def test_update_non_existing_alert_returns_none(db_session):
    result = alert_service.update_alert_status(
        db=db_session,
        alert_id=999999999,
        status="CLOSED",
    )

    assert result is None


def test_close_non_existing_alert_returns_none(db_session):
    result = alert_service.close_alert(
        db=db_session,
        alert_id=999999999,
    )

    assert result is None


def test_invalid_alert_status_raises_value_error(
    db_session,
    sample_hotspot_row,
    high_risk_prediction_payload,
):
    alert = alert_service.create_alert_from_prediction(
        db=db_session,
        prediction=high_risk_prediction_payload,
        hotspot_id=sample_hotspot_row.id,
        saved_prediction_id=None,
    )

    with pytest.raises(ValueError):
        alert_service.update_alert_status(
            db=db_session,
            alert_id=alert.id,
            status="WRONG_STATUS",
        )
