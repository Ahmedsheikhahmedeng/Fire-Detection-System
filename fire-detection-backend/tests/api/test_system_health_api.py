from datetime import timedelta

from app.core.time_utils import utc_now_naive
from app.models.fire_cluster import FireCluster
from app.models.hotspot import Hotspot
from app.models.nasa_fetch_run import NasaFetchRun


def _run(status="success", **overrides):
    now = utc_now_naive()
    data = {
        "started_at": now - timedelta(seconds=20),
        "finished_at": now,
        "duration_seconds": 20.0,
        "status": status,
        "received_count": 349,
        "inserted_count": 221,
        "duplicate_count": 128,
        "source_error_count": 0,
        "row_error_count": 0,
        "v3_prediction_count": 100,
        "prediction_limit_per_fetch": 100,
        "prediction_limit_applied": True,
        "prediction_limit_note": "Prediction processing limited to 100 records per fetch cycle",
        "received_by_source": {
            "VIIRS_SNPP_NRT": 99,
            "VIIRS_NOAA20_NRT": 154,
            "VIIRS_NOAA21_NRT": 96,
        },
        "inserted_by_source": {
            "VIIRS_SNPP_NRT": 45,
            "VIIRS_NOAA20_NRT": 100,
            "VIIRS_NOAA21_NRT": 76,
        },
        "duplicates_by_source": {
            "VIIRS_SNPP_NRT": 54,
            "VIIRS_NOAA20_NRT": 54,
            "VIIRS_NOAA21_NRT": 20,
        },
        "row_errors_by_source": {
            "VIIRS_SNPP_NRT": 0,
            "VIIRS_NOAA20_NRT": 0,
            "VIIRS_NOAA21_NRT": 0,
        },
        "predictions_by_source": {
            "VIIRS_SNPP_NRT": 45,
            "VIIRS_NOAA20_NRT": 40,
            "VIIRS_NOAA21_NRT": 15,
        },
        "source_errors": [],
        "weather_timeout_count": 0,
        "weather_fallback_count": 0,
        "weather_error_count": 0,
    }
    data.update(overrides)
    return NasaFetchRun(**data)


def _cluster(status):
    now = utc_now_naive()
    return FireCluster(
        center_latitude=38.4,
        center_longitude=27.1,
        first_seen_at=now - timedelta(hours=1),
        last_seen_at=now - timedelta(hours=1),
        hotspot_count=1,
        status=status,
        sources=["VIIRS_SNPP_NRT"],
        satellites=["N"],
    )


def test_system_health_empty_db_returns_degraded(client):
    response = client.get("/api/system/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["health"] == "degraded"
    assert data["last_fetch"] is None
    assert data["message"] == "No NASA fetch run recorded yet"


def test_system_health_success_returns_healthy_with_source_cluster_and_limit_data(client, db_session):
    db_session.add(_run("success"))
    db_session.add_all([_cluster("active"), _cluster("monitoring"), _cluster("resolved")])
    db_session.commit()
    db_session.add(Hotspot(latitude=38.4, longitude=27.1, cluster_id=1))
    db_session.commit()

    response = client.get("/api/system/health")

    assert response.status_code == 200
    data = response.json()
    assert data["health"] == "healthy"
    assert data["last_fetch"]["received_count"] == 349
    assert data["last_fetch"]["inserted_count"] == 221
    assert data["last_fetch"]["prediction_limit_per_fetch"] == 100
    assert data["last_fetch"]["prediction_limit_applied"] is True
    assert data["sources"]["VIIRS_SNPP_NRT"]["received"] == 99
    assert data["sources"]["VIIRS_NOAA20_NRT"]["inserted"] == 100
    assert data["sources"]["VIIRS_NOAA21_NRT"]["predictions"] == 15
    assert data["clusters"] == {"total": 3, "active": 1, "monitoring": 1, "resolved": 1}
    assert data["database"]["hotspots_total"] == 1
    assert data["database"]["hotspots_clustered"] == 1


def test_system_health_partial_returns_degraded(client, db_session):
    db_session.add(_run(
        "partial",
        source_error_count=1,
        source_errors=[{"source": "VIIRS_NOAA21_NRT", "error": "timeout"}],
    ))
    db_session.commit()

    response = client.get("/api/system/health")

    assert response.status_code == 200
    data = response.json()
    assert data["health"] == "degraded"
    assert data["sources"]["VIIRS_NOAA21_NRT"]["status"] == "error"


def test_system_health_failed_returns_error(client, db_session):
    db_session.add(_run("failed", source_error_count=3, received_count=0))
    db_session.commit()

    response = client.get("/api/system/health")

    assert response.status_code == 200
    assert response.json()["health"] == "error"
