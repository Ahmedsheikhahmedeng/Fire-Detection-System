from datetime import date

import pytest

import app.services.prediction_service as prediction_service_module
from app.models.alert import Alert
from app.models.hotspot import Hotspot
from app.models.prediction import Prediction
from app.models.weather import WeatherData
from app.services.prediction_service import prediction_service


def _payload_from_hotspot(hotspot, id_as_string=False):
    hotspot_id = str(hotspot.id) if id_as_string else hotspot.id

    return {
        "id": hotspot_id,
        "hotspot_id": hotspot_id,
        "latitude": float(hotspot.latitude),
        "longitude": float(hotspot.longitude),
        "brightness": float(hotspot.brightness),
        "bright_ti4": float(hotspot.brightness),
        "bright_ti5": float(hotspot.bright_ti5 or hotspot.brightness),
        "frp": float(hotspot.frp or 0),
        "scan": float(hotspot.scan or 1),
        "track": float(hotspot.track or 1),
        "confidence": hotspot.confidence or "h",
        "satellite": hotspot.satellite or "N",
        "instrument": hotspot.instrument or "VIIRS",
        "acq_date": hotspot.acq_date.isoformat(),
        "acq_time": str(hotspot.acq_time).replace(".0", "").zfill(4),
        "daynight": hotspot.daynight or "D",
        "type": hotspot.type or 0,
    }


def _fake_prediction(decision_level=0, probability=0.05, weather_ok=True):
    decision_names = {
        0: "low_risk_no_fire",
        1: "watch_early_warning",
        2: "medium_risk_fire",
        3: "high_risk_fire",
        4: "critical_fire_alert",
    }

    weather_features = {
        "weather_fetch_ok": 1 if weather_ok else 0,
        "temp_mean_24h": 30.0,
        "rh_mean_24h": 35.0,
        "wind_mean_24h": 12.0,
        "precip_sum_24h": 0.0,
    }

    return {
        "success": True,
        "model_version": "v3-test",
        "probabilities": {
            "ensemble_fire_probability": probability,
            "hgb_core_probability": probability,
            "xgboost_probability": probability,
            "lightgbm_probability": probability,
            "catboost_probability": probability,
            "rf_fire_probability": probability,
            "extratrees_fire_probability": probability,
        },
        "decision": {
            "decision_level": decision_level,
            "decision_name": decision_names[decision_level],
        },
        "feature_status": {
            "weather": weather_features,
        },
        "validation": {
            "is_valid": True,
        },
    }


def _get_alert_level(alert):
    if hasattr(alert, "risk_level"):
        return alert.risk_level
    if hasattr(alert, "alert_level"):
        return alert.alert_level
    if hasattr(alert, "level"):
        return alert.level
    return None


def test_build_history_hotspots_excludes_current_and_counts_nearby(
    db_session,
    sample_hotspot_row,
):
    nearby = Hotspot(
        latitude=38.401,
        longitude=27.101,
        brightness=331,
        bright_ti5=296,
        frp=80,
        scan=0.5,
        track=0.5,
        confidence="h",
        daynight="D",
        satellite="N",
        instrument="VIIRS",
        firms_source="VIIRS_SNPP_NRT",
        type=0,
        version=2,
        acq_date=date(2025, 8, 1),
        acq_time="1200",
        city="Izmir",
    )

    old_far = Hotspot(
        latitude=40.0,
        longitude=30.0,
        brightness=320,
        bright_ti5=290,
        frp=20,
        scan=0.5,
        track=0.5,
        confidence="n",
        daynight="D",
        satellite="N",
        instrument="VIIRS",
        firms_source="VIIRS_SNPP_NRT",
        type=0,
        version=2,
        acq_date=date(2025, 7, 20),
        acq_time="1200",
        city="Other",
    )

    db_session.add_all([nearby, old_far])
    db_session.commit()

    payload = _payload_from_hotspot(sample_hotspot_row)

    history = prediction_service.build_history_hotspots(
        db=db_session,
        current_hotspot=payload,
        max_hours=72,
    )

    assert len(history) == 1
    assert history[0]["hotspot_id"] == str(nearby.id)
    assert history[0]["frp"] == 80.0


def test_low_risk_prediction_is_saved_without_alert(
    monkeypatch,
    db_session,
    sample_hotspot_row,
):
    captured_payload = {}

    def fake_predict_raw_hotspot(payload):
        captured_payload.update(payload)
        return _fake_prediction(decision_level=0, probability=0.05, weather_ok=True)

    monkeypatch.setattr(
        prediction_service_module,
        "predict_raw_hotspot",
        fake_predict_raw_hotspot,
    )

    payload = _payload_from_hotspot(sample_hotspot_row)

    result = prediction_service.predict_hotspot_with_db_context(
        db=db_session,
        hotspot_payload=payload,
    )

    assert result["success"] is True
    assert result["created_alert_id"] is None
    assert "saved_prediction_id" in result
    assert "context_status" in result
    assert "history_hotspots" in captured_payload

    saved_prediction = (
        db_session.query(Prediction)
        .filter(Prediction.id == result["saved_prediction_id"])
        .first()
    )

    assert saved_prediction is not None
    assert saved_prediction.hotspot_id == sample_hotspot_row.id
    assert saved_prediction.risk_level == "LOW"
    assert saved_prediction.decision_level == 0
    assert saved_prediction.decision_name == "low_risk_no_fire"
    assert saved_prediction.fire_probability == pytest.approx(0.05)

    alert_count = db_session.query(Alert).count()
    assert alert_count == 0


def test_high_risk_prediction_saves_prediction_weather_and_alert(
    monkeypatch,
    db_session,
    sample_hotspot_row,
):
    def fake_predict_raw_hotspot(payload):
        return _fake_prediction(decision_level=3, probability=0.88, weather_ok=True)

    monkeypatch.setattr(
        prediction_service_module,
        "predict_raw_hotspot",
        fake_predict_raw_hotspot,
    )

    payload = _payload_from_hotspot(sample_hotspot_row)

    result = prediction_service.predict_hotspot_with_db_context(
        db=db_session,
        hotspot_payload=payload,
    )

    assert result["success"] is True
    assert result["created_alert_id"] is not None
    assert result["saved_prediction_id"] is not None

    saved_prediction = (
        db_session.query(Prediction)
        .filter(Prediction.id == result["saved_prediction_id"])
        .first()
    )

    assert saved_prediction is not None
    assert saved_prediction.hotspot_id == sample_hotspot_row.id
    assert saved_prediction.risk_level == "HIGH"
    assert saved_prediction.decision_level == 3
    assert saved_prediction.decision_name == "high_risk_fire"
    assert saved_prediction.fire_probability == pytest.approx(0.88)

    weather = (
        db_session.query(WeatherData)
        .filter(WeatherData.hotspot_id == sample_hotspot_row.id)
        .first()
    )

    assert weather is not None
    assert weather.temperature == pytest.approx(30.0)
    assert weather.humidity == pytest.approx(35.0)
    assert weather.wind_speed == pytest.approx(12.0)

    alert = (
        db_session.query(Alert)
        .filter(Alert.id == result["created_alert_id"])
        .first()
    )

    assert alert is not None
    assert alert.hotspot_id == sample_hotspot_row.id
    assert alert.status == "ACTIVE"
    assert _get_alert_level(alert) == "HIGH"


def test_string_hotspot_id_is_normalized_and_saved_as_int(
    monkeypatch,
    db_session,
    sample_hotspot_row,
):
    def fake_predict_raw_hotspot(payload):
        return _fake_prediction(decision_level=0, probability=0.05, weather_ok=True)

    monkeypatch.setattr(
        prediction_service_module,
        "predict_raw_hotspot",
        fake_predict_raw_hotspot,
    )

    payload = _payload_from_hotspot(sample_hotspot_row, id_as_string=True)

    result = prediction_service.predict_hotspot_with_db_context(
        db=db_session,
        hotspot_payload=payload,
    )

    saved_prediction = (
        db_session.query(Prediction)
        .filter(Prediction.id == result["saved_prediction_id"])
        .first()
    )

    assert saved_prediction is not None
    assert saved_prediction.hotspot_id == sample_hotspot_row.id


def test_weather_snapshot_not_saved_when_weather_fetch_failed(
    monkeypatch,
    db_session,
    sample_hotspot_row,
):
    def fake_predict_raw_hotspot(payload):
        return _fake_prediction(decision_level=0, probability=0.05, weather_ok=False)

    monkeypatch.setattr(
        prediction_service_module,
        "predict_raw_hotspot",
        fake_predict_raw_hotspot,
    )

    payload = _payload_from_hotspot(sample_hotspot_row)

    result = prediction_service.predict_hotspot_with_db_context(
        db=db_session,
        hotspot_payload=payload,
    )

    assert result["success"] is True

    weather_count = (
        db_session.query(WeatherData)
        .filter(WeatherData.hotspot_id == sample_hotspot_row.id)
        .count()
    )

    assert weather_count == 0


def test_medium_risk_creates_medium_alert(
    monkeypatch,
    db_session,
    sample_hotspot_row,
):
    def fake_predict_raw_hotspot(payload):
        return _fake_prediction(decision_level=2, probability=0.62, weather_ok=True)

    monkeypatch.setattr(
        prediction_service_module,
        "predict_raw_hotspot",
        fake_predict_raw_hotspot,
    )

    payload = _payload_from_hotspot(sample_hotspot_row)

    result = prediction_service.predict_hotspot_with_db_context(
        db=db_session,
        hotspot_payload=payload,
    )

    assert result["success"] is True
    assert result["created_alert_id"] is not None

    alert = (
        db_session.query(Alert)
        .filter(Alert.id == result["created_alert_id"])
        .first()
    )

    assert alert is not None
    assert _get_alert_level(alert) == "MEDIUM"


def test_critical_risk_creates_critical_alert(
    monkeypatch,
    db_session,
    sample_hotspot_row,
):
    def fake_predict_raw_hotspot(payload):
        return _fake_prediction(decision_level=4, probability=0.97, weather_ok=True)

    monkeypatch.setattr(
        prediction_service_module,
        "predict_raw_hotspot",
        fake_predict_raw_hotspot,
    )

    payload = _payload_from_hotspot(sample_hotspot_row)

    result = prediction_service.predict_hotspot_with_db_context(
        db=db_session,
        hotspot_payload=payload,
    )

    assert result["success"] is True
    assert result["created_alert_id"] is not None

    alert = (
        db_session.query(Alert)
        .filter(Alert.id == result["created_alert_id"])
        .first()
    )

    assert alert is not None
    assert _get_alert_level(alert) == "CRITICAL"


def test_prediction_service_risk_mapping():
    assert prediction_service._risk_level_from_decision(0) == "LOW"
    assert prediction_service._risk_level_from_decision(1) == "WATCH"
    assert prediction_service._risk_level_from_decision(2) == "MEDIUM"
    assert prediction_service._risk_level_from_decision(3) == "HIGH"
    assert prediction_service._risk_level_from_decision(4) == "CRITICAL"
