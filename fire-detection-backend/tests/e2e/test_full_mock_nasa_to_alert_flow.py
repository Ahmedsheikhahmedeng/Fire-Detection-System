from datetime import datetime, timedelta, timezone

import pytest

import app.services.prediction_service as prediction_service_module
from app.models.alert import Alert
from app.models.hotspot import Hotspot
from app.models.prediction import Prediction
from app.models.weather import WeatherData
from app.services import nasa_service


class FakeNASAResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class FakeNASAClient:
    def __init__(self, csv_text):
        self.csv_text = csv_text

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def get(self, *args, **kwargs):
        return FakeNASAResponse(self.csv_text)


def _make_recent_nasa_csv(
    *,
    latitude=38.4,
    longitude=27.1,
    bright_ti4=340,
    bright_ti5=300,
    frp=90,
    acq_datetime=None,
    satellite="N",
    instrument="VIIRS",
):
    if acq_datetime is None:
        acq_datetime = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)

    acq_date = acq_datetime.date().isoformat()
    acq_time = acq_datetime.strftime("%H%M")

    return f"""latitude,longitude,bright_ti4,bright_ti5,frp,scan,track,confidence,daynight,satellite,instrument,acq_date,acq_time,type,version
{latitude},{longitude},{bright_ti4},{bright_ti5},{frp},0.5,0.5,h,D,{satellite},{instrument},{acq_date},{acq_time},0,2
"""


def _patch_nasa_client(monkeypatch, csv_text):
    monkeypatch.setattr(
        nasa_service,
        "FIRMS_SOURCES",
        ["VIIRS_SNPP_NRT"],
    )
    monkeypatch.setattr(
        nasa_service.httpx,
        "Client",
        lambda: FakeNASAClient(csv_text),
    )


def _fake_prediction(decision_level=3, probability=0.88, weather_ok=True):
    decision_names = {
        0: "low_risk_no_fire",
        1: "watch_early_warning",
        2: "medium_risk_fire",
        3: "high_risk_fire",
        4: "critical_fire_alert",
    }

    return {
        "success": True,
        "model_version": "v3-e2e-test",
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
            "weather": {
                "weather_fetch_ok": 1 if weather_ok else 0,
                "temp_mean_24h": 31.0,
                "rh_mean_24h": 35.0,
                "wind_mean_24h": 12.0,
                "precip_sum_24h": 0.0,
            }
        },
        "validation": {
            "is_valid": True,
        },
    }


def _patch_prediction(monkeypatch, *, decision_level=3, probability=0.88, weather_ok=True):
    def fake_predict_raw_hotspot(payload):
        return _fake_prediction(
            decision_level=decision_level,
            probability=probability,
            weather_ok=weather_ok,
        )

    monkeypatch.setattr(
        prediction_service_module,
        "predict_raw_hotspot",
        fake_predict_raw_hotspot,
    )


def _enable_prediction_on_nasa_fetch(monkeypatch):
    monkeypatch.setattr(
        nasa_service.settings,
        "ENABLE_V3_PREDICTION_ON_NASA_FETCH",
        True,
    )
    monkeypatch.setattr(
        nasa_service.settings,
        "V3_MAX_PREDICTIONS_PER_NASA_FETCH",
        10,
    )


def _get_alert_level(alert):
    if hasattr(alert, "risk_level"):
        return alert.risk_level
    if hasattr(alert, "alert_level"):
        return alert.alert_level
    if hasattr(alert, "level"):
        return alert.level
    return None


def test_full_mock_nasa_high_risk_to_alert_and_map_flow(
    monkeypatch,
    client,
    db_session,
):
    """
    Full E2E:
    Fake NASA CSV
    -> DB hotspot
    -> prediction_service
    -> prediction DB save
    -> weather snapshot
    -> alert creation
    -> map/hotspots
    -> map/stats
    """
    csv_text = _make_recent_nasa_csv(
        latitude=38.4,
        longitude=27.1,
        bright_ti4=340,
        bright_ti5=300,
        frp=90,
    )

    _patch_nasa_client(monkeypatch, csv_text)
    _patch_prediction(
        monkeypatch,
        decision_level=3,
        probability=0.88,
        weather_ok=True,
    )
    _enable_prediction_on_nasa_fetch(monkeypatch)

    nasa_result = nasa_service.fetch_hotspots_from_nasa(
        db=db_session,
        country="TUR",
        days=1,
    )

    assert nasa_result["received_count"] == 1
    assert nasa_result["inserted_count"] == 1
    assert nasa_result["duplicate_count"] == 0
    assert nasa_result["row_error_count"] == 0
    assert nasa_result["v3_prediction_count"] == 1
    assert nasa_result["v3_alert_count"] == 1

    hotspot = db_session.query(Hotspot).first()
    assert hotspot is not None
    assert hotspot.latitude == pytest.approx(38.4)
    assert hotspot.longitude == pytest.approx(27.1)
    assert hotspot.frp == pytest.approx(90.0)

    prediction = db_session.query(Prediction).filter(
        Prediction.hotspot_id == hotspot.id
    ).first()

    assert prediction is not None
    assert prediction.fire_probability == pytest.approx(0.88)
    assert prediction.risk_level == "HIGH"
    assert prediction.decision_level == 3
    assert prediction.decision_name == "high_risk_fire"

    weather = db_session.query(WeatherData).filter(
        WeatherData.hotspot_id == hotspot.id
    ).first()

    assert weather is not None
    assert weather.temperature == pytest.approx(31.0)
    assert weather.humidity == pytest.approx(35.0)
    assert weather.wind_speed == pytest.approx(12.0)

    alert = db_session.query(Alert).filter(
        Alert.hotspot_id == hotspot.id
    ).first()

    assert alert is not None
    assert alert.status == "ACTIVE"
    assert _get_alert_level(alert) == "HIGH"

    map_response = client.get("/api/map/hotspots")
    assert map_response.status_code == 200

    map_data = map_response.json()
    assert isinstance(map_data, list)
    assert len(map_data) == 1

    item = map_data[0]

    assert item["id"] == hotspot.id
    assert item["risk_level"] == "HIGH"
    assert item["fire_probability"] == pytest.approx(0.88)
    assert item["risk_percent"] == pytest.approx(88.0)
    assert item["decision_level"] == 3
    assert item["decision_name"] == "high_risk_fire"
    assert item["has_active_alert"] is True
    assert item["alert_id"] == alert.id
    assert item["alert"] is True
    assert item["ml_source"] == "model"

    stats_response = client.get("/api/map/stats")
    assert stats_response.status_code == 200

    stats_data = stats_response.json()
    assert stats_data["risk_distribution"]["HIGH"] >= 1
    assert stats_data["total_hotspots"] == 1


def test_full_mock_nasa_low_risk_creates_prediction_without_alert(
    monkeypatch,
    client,
    db_session,
):
    csv_text = _make_recent_nasa_csv(
        latitude=38.5,
        longitude=27.2,
        bright_ti4=310,
        bright_ti5=295,
        frp=5,
    )

    _patch_nasa_client(monkeypatch, csv_text)
    _patch_prediction(
        monkeypatch,
        decision_level=0,
        probability=0.05,
        weather_ok=True,
    )
    _enable_prediction_on_nasa_fetch(monkeypatch)

    nasa_result = nasa_service.fetch_hotspots_from_nasa(
        db=db_session,
        country="TUR",
        days=1,
    )

    assert nasa_result["inserted_count"] == 1
    assert nasa_result["v3_prediction_count"] == 1
    assert nasa_result["v3_alert_count"] == 0

    hotspot = db_session.query(Hotspot).first()
    assert hotspot is not None

    prediction = db_session.query(Prediction).filter(
        Prediction.hotspot_id == hotspot.id
    ).first()

    assert prediction is not None
    assert prediction.risk_level == "LOW"
    assert prediction.decision_level == 0
    assert prediction.decision_name == "low_risk_no_fire"

    alert_count = db_session.query(Alert).count()
    assert alert_count == 0

    map_response = client.get("/api/map/hotspots")
    assert map_response.status_code == 200

    data = map_response.json()
    assert len(data) == 1

    item = data[0]

    assert item["risk_level"] == "LOW"
    assert item["decision_level"] == 0
    assert item["alert"] is False
    assert item["has_active_alert"] is False
    assert item["alert_id"] is None


def test_full_mock_nasa_duplicate_second_fetch_does_not_duplicate_hotspot(
    monkeypatch,
    db_session,
):
    recent_dt = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)

    csv_text = _make_recent_nasa_csv(
        latitude=38.6,
        longitude=27.3,
        bright_ti4=335,
        bright_ti5=299,
        frp=70,
        acq_datetime=recent_dt,
        satellite="N",
        instrument="VIIRS",
    )

    _patch_nasa_client(monkeypatch, csv_text)
    _patch_prediction(
        monkeypatch,
        decision_level=3,
        probability=0.88,
        weather_ok=True,
    )
    _enable_prediction_on_nasa_fetch(monkeypatch)

    first_result = nasa_service.fetch_hotspots_from_nasa(
        db=db_session,
        country="TUR",
        days=1,
    )

    second_result = nasa_service.fetch_hotspots_from_nasa(
        db=db_session,
        country="TUR",
        days=1,
    )

    assert first_result["inserted_count"] == 1
    assert first_result["duplicate_count"] == 0

    assert second_result["inserted_count"] == 0
    assert second_result["duplicate_count"] == 1

    hotspot_count = db_session.query(Hotspot).count()
    prediction_count = db_session.query(Prediction).count()
    alert_count = db_session.query(Alert).count()

    assert hotspot_count == 1
    assert prediction_count == 1
    assert alert_count == 1
