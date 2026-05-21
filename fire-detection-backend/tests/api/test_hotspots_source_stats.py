from datetime import datetime, timedelta, timezone

from app.models.hotspot import Hotspot


def _hotspot(source, satellite, acq_datetime, latitude):
    return Hotspot(
        latitude=latitude,
        longitude=29.0,
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
        acq_date=acq_datetime.date(),
        acq_time=acq_datetime.strftime("%H%M"),
        city=None,
    )


def test_source_stats_endpoint_returns_empty_list_for_empty_db(client):
    response = client.get("/api/hotspots/source-stats")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["total_hotspot_count"] == 0
    assert data["source_count"] == 0
    assert data["sources"] == []
    assert data["prediction_limit_per_fetch"] == 100
    assert data["prediction_limit_note"] == "Prediction processing limited to 100 records per fetch cycle"


def test_source_stats_endpoint_returns_viirs_source_health(client, db_session):
    now_utc = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    rows = [
        _hotspot("VIIRS_SNPP_NRT", "N", now_utc - timedelta(hours=1), 38.1),
        _hotspot("VIIRS_SNPP_NRT", "N", now_utc - timedelta(hours=2), 38.2),
        _hotspot("VIIRS_NOAA20_NRT", "N20", now_utc - timedelta(hours=5), 39.1),
        _hotspot("VIIRS_NOAA21_NRT", "N21", now_utc - timedelta(hours=3), 40.1),
    ]
    db_session.add_all(rows)
    db_session.commit()

    response = client.get("/api/hotspots/source-stats")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["total_hotspot_count"] == 4
    assert data["source_count"] == 3

    sources = {item["firms_source"]: item for item in data["sources"]}
    assert set(sources) == {
        "VIIRS_SNPP_NRT",
        "VIIRS_NOAA20_NRT",
        "VIIRS_NOAA21_NRT",
    }

    snpp = sources["VIIRS_SNPP_NRT"]
    assert snpp["satellite"] == "N"
    assert snpp["instrument"] == "VIIRS"
    assert snpp["total_hotspots"] == 2
    assert snpp["latest_observation_utc"].endswith("Z")
    assert "+03:00" in snpp["latest_observation_trt"]
    assert isinstance(snpp["hours_since_latest_observation"], float)
    assert 0 <= snpp["hours_since_latest_observation"] <= 2
