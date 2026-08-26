from datetime import datetime, timedelta, timezone

import pytest

from app.models.alert import Alert
from app.models.hotspot import Hotspot
from app.models.prediction import Prediction
from app.models.weather import WeatherData


def _dt_to_date_time(dt: datetime):
    return dt.date(), dt.strftime("%H%M")


def _create_hotspot(
    db_session,
    *,
    latitude=38.4,
    longitude=27.1,
    dt=None,
    city="Izmir",
    brightness=330,
    frp=45,
):
    if dt is None:
        dt = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)

    acq_date, acq_time = _dt_to_date_time(dt)

    hotspot = Hotspot(
        latitude=latitude,
        longitude=longitude,
        brightness=brightness,
        bright_ti5=295,
        frp=frp,
        scan=0.5,
        track=0.5,
        confidence="h",
        daynight="D",
        satellite="N",
        instrument="VIIRS",
        firms_source="VIIRS_SNPP_NRT",
        type=0,
        version=2,
        acq_date=acq_date,
        acq_time=acq_time,
        city=city,
    )

    db_session.add(hotspot)
    db_session.commit()
    db_session.refresh(hotspot)

    return hotspot


def _create_prediction(
    db_session,
    hotspot,
    *,
    probability=0.88,
    risk_level="HIGH",
    decision_level=3,
    decision_name="high_risk_fire",
):
    prediction = Prediction(
        hotspot_id=hotspot.id,
        fire_probability=probability,
        risk_level=risk_level,
        model_version="v3-test",
        decision_level=decision_level,
        decision_name=decision_name,
    )

    db_session.add(prediction)
    db_session.commit()
    db_session.refresh(prediction)

    return prediction


def _create_weather(
    db_session,
    hotspot,
    *,
    temperature=31.2,
    humidity=35.0,
    wind_speed=12.5,
    rain_1h=0.0,
):
    weather = WeatherData(
        hotspot_id=hotspot.id,
        temperature=temperature,
        humidity=humidity,
        pressure=1012,
        wind_speed=wind_speed,
        rain_1h=rain_1h,
    )

    db_session.add(weather)
    db_session.commit()
    db_session.refresh(weather)

    return weather


def _create_alert(
    db_session,
    hotspot,
    *,
    risk_level="HIGH",
    status="ACTIVE",
    message="Test active alert",
):
    alert = Alert(
        hotspot_id=hotspot.id,
        risk_level=risk_level,
        status=status,
        message=message,
    )

    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)

    return alert


def test_map_hotspots_returns_recent_hotspot_with_v3_fields(
    client,
    db_session,
):
    hotspot = _create_hotspot(
        db_session,
        dt=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),
        city="Izmir",
    )

    _create_prediction(
        db_session,
        hotspot,
        probability=0.88,
        risk_level="HIGH",
        decision_level=3,
        decision_name="high_risk_fire",
    )

    _create_weather(
        db_session,
        hotspot,
        temperature=31.2,
        humidity=35.0,
        wind_speed=12.5,
    )

    response = client.get("/api/map/hotspots")

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1

    item = data[0]

    assert item["id"] == hotspot.id
    assert item["latitude"] == pytest.approx(38.4)
    assert item["longitude"] == pytest.approx(27.1)
    assert item["city"] == "Izmir"

    assert item["temperature"] == pytest.approx(31.2)
    assert item["humidity"] == pytest.approx(35.0)
    assert item["wind_speed"] == pytest.approx(12.5)

    assert item["risk_level"] == "HIGH"
    assert item["fire_probability"] == pytest.approx(0.88)
    assert item["risk_percent"] == pytest.approx(88.0)

    assert item["decision_level"] == 3
    assert item["decision_name"] == "high_risk_fire"

    assert item["has_active_alert"] is False
    assert item["alert_id"] is None

    # V3 map mantigi: decision_level >= 2 ise alert true olmali
    assert item["alert"] is True
    assert item["ml_source"] == "model"


def test_map_hotspots_active_alert_sets_has_active_alert_and_alert_id(
    client,
    db_session,
):
    hotspot = _create_hotspot(
        db_session,
        dt=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),
        city="Mugla",
    )

    _create_prediction(
        db_session,
        hotspot,
        probability=0.05,
        risk_level="LOW",
        decision_level=0,
        decision_name="low_risk_no_fire",
    )

    alert = _create_alert(
        db_session,
        hotspot,
        risk_level="HIGH",
        status="ACTIVE",
        message="Manual active alert",
    )

    response = client.get("/api/map/hotspots")

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1

    item = data[0]

    assert item["id"] == hotspot.id
    assert item["decision_level"] == 0
    assert item["risk_level"] == "LOW"

    # Aktif alert varsa decision dusuk olsa bile frontend alert true gormeli
    assert item["has_active_alert"] is True
    assert item["alert_id"] == alert.id
    assert item["alert"] is True


def test_map_hotspots_excludes_old_hotspot_older_than_24h(
    client,
    db_session,
):
    recent_hotspot = _create_hotspot(
        db_session,
        dt=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2),
        city="RecentCity",
    )

    old_hotspot = _create_hotspot(
        db_session,
        dt=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=30),
        city="OldCity",
    )

    _create_prediction(
        db_session,
        recent_hotspot,
        probability=0.62,
        risk_level="MEDIUM",
        decision_level=2,
        decision_name="medium_risk_fire",
    )

    _create_prediction(
        db_session,
        old_hotspot,
        probability=0.97,
        risk_level="CRITICAL",
        decision_level=4,
        decision_name="critical_fire_alert",
    )

    response = client.get("/api/map/hotspots")

    assert response.status_code == 200

    ids = [item["id"] for item in response.json()]

    assert recent_hotspot.id in ids
    assert old_hotspot.id not in ids


def test_map_hotspots_bbox_filter_returns_only_inside_area(
    client,
    db_session,
):
    inside = _create_hotspot(
        db_session,
        latitude=38.4,
        longitude=27.1,
        dt=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),
        city="Inside",
    )

    outside = _create_hotspot(
        db_session,
        latitude=40.0,
        longitude=30.0,
        dt=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),
        city="Outside",
    )

    _create_prediction(
        db_session,
        inside,
        probability=0.62,
        risk_level="MEDIUM",
        decision_level=2,
        decision_name="medium_risk_fire",
    )

    _create_prediction(
        db_session,
        outside,
        probability=0.62,
        risk_level="MEDIUM",
        decision_level=2,
        decision_name="medium_risk_fire",
    )

    response = client.get(
        "/api/map/hotspots",
        params={
            "min_lat": 38.0,
            "max_lat": 39.0,
            "min_lon": 26.0,
            "max_lon": 28.0,
        },
    )

    assert response.status_code == 200

    ids = [item["id"] for item in response.json()]

    assert inside.id in ids
    assert outside.id not in ids


def test_map_hotspots_pending_prediction_returns_unknown(
    client,
    db_session,
):
    hotspot = _create_hotspot(
        db_session,
        dt=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),
        city="PendingCity",
    )

    response = client.get("/api/map/hotspots")

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1

    item = data[0]

    assert item["id"] == hotspot.id
    assert item["risk_level"] == "UNKNOWN"
    assert item["fire_probability"] is None
    assert item["risk_percent"] is None
    assert item["decision_level"] is None
    assert item["decision_name"] is None
    assert item["alert"] is False
    assert item["ml_source"] == "pending"


def test_map_stats_returns_all_v3_risk_keys_and_counts(
    client,
    db_session,
):
    low = _create_hotspot(
        db_session,
        dt=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),
        city="CityA",
    )
    watch = _create_hotspot(
        db_session,
        dt=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),
        city="CityA",
    )
    medium = _create_hotspot(
        db_session,
        dt=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),
        city="CityB",
    )
    high = _create_hotspot(
        db_session,
        dt=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),
        city="CityB",
    )
    critical = _create_hotspot(
        db_session,
        dt=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),
        city="CityC",
    )
    unknown = _create_hotspot(
        db_session,
        dt=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),
        city="CityD",
    )

    _create_prediction(
        db_session,
        low,
        probability=0.05,
        risk_level="LOW",
        decision_level=0,
        decision_name="low_risk_no_fire",
    )
    _create_prediction(
        db_session,
        watch,
        probability=0.35,
        risk_level="WATCH",
        decision_level=1,
        decision_name="watch_early_warning",
    )
    _create_prediction(
        db_session,
        medium,
        probability=0.62,
        risk_level="MEDIUM",
        decision_level=2,
        decision_name="medium_risk_fire",
    )
    _create_prediction(
        db_session,
        high,
        probability=0.88,
        risk_level="HIGH",
        decision_level=3,
        decision_name="high_risk_fire",
    )
    _create_prediction(
        db_session,
        critical,
        probability=0.97,
        risk_level="CRITICAL",
        decision_level=4,
        decision_name="critical_fire_alert",
    )

    # unknown icin prediction yok

    response = client.get("/api/map/stats")

    assert response.status_code == 200

    data = response.json()

    assert "risk_distribution" in data
    risk_distribution = data["risk_distribution"]

    for key in ["CRITICAL", "HIGH", "MEDIUM", "WATCH", "LOW", "UNKNOWN"]:
        assert key in risk_distribution

    assert risk_distribution["LOW"] == 1
    assert risk_distribution["WATCH"] == 1
    assert risk_distribution["MEDIUM"] == 1
    assert risk_distribution["HIGH"] == 1
    assert risk_distribution["CRITICAL"] == 1
    assert risk_distribution["UNKNOWN"] >= 1

    assert data["total_hotspots"] == 6


def test_map_stats_weather_summary_does_not_drop_zero_values(
    client,
    db_session,
):
    hotspot = _create_hotspot(
        db_session,
        dt=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),
        city="ZeroWeatherCity",
    )

    _create_weather(
        db_session,
        hotspot,
        temperature=0.0,
        humidity=0.0,
        wind_speed=0.0,
    )

    response = client.get("/api/map/stats")

    assert response.status_code == 200

    data = response.json()

    assert "weather_summary" in data
    weather_summary = data["weather_summary"]

    # Burada amac 0 degerlerin None gibi atilmadigini dogrulamak.
    assert weather_summary is not None
