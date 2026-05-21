from datetime import datetime, timedelta

from app.core.time_utils import utc_now_naive
from app.models.fire_cluster import FireCluster


def _cluster(last_seen_at, *, status, latitude=37.12):
    return FireCluster(
        center_latitude=latitude,
        center_longitude=36.45,
        first_seen_at=last_seen_at,
        last_seen_at=last_seen_at,
        hotspot_count=8,
        max_fire_probability=0.82,
        max_risk_level="HIGH",
        sources=["VIIRS_SNPP_NRT", "VIIRS_NOAA21_NRT"],
        satellites=["N", "N21"],
        status=status,
        created_at=last_seen_at,
        updated_at=last_seen_at,
    )


def test_clusters_endpoint_empty_db(client):
    response = client.get("/api/hotspots/clusters")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["cluster_count"] == 0
    assert data["matching_count"] == 0
    assert data["returned_count"] == 0
    assert data["status_counts"] == {"active": 0, "monitoring": 0, "resolved": 0}
    assert data["filters"]["status"] == "active,monitoring"
    assert data["clusters"] == []


def test_clusters_endpoint_returns_active_clusters(client, db_session):
    seen_at = datetime(2026, 5, 19, 12, 0)
    cluster = _cluster(seen_at, status="active")
    db_session.add(cluster)
    db_session.commit()

    response = client.get("/api/hotspots/clusters")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["cluster_count"] == 1
    assert data["matching_count"] == 1
    item = data["clusters"][0]
    assert item["id"] == cluster.id
    assert item["hotspot_count"] == 8
    assert item["max_risk_level"] == "HIGH"
    assert item["max_fire_probability"] == 0.82
    assert item["sources"] == ["VIIRS_SNPP_NRT", "VIIRS_NOAA21_NRT"]
    assert item["satellites"] == ["N", "N21"]


def test_clusters_endpoint_defaults_to_active_and_monitoring(client, db_session):
    now = utc_now_naive()
    active = _cluster(now - timedelta(hours=2), status="active", latitude=37.1)
    monitoring = _cluster(now - timedelta(hours=36), status="monitoring", latitude=37.2)
    resolved = _cluster(now - timedelta(hours=90), status="resolved", latitude=37.3)
    db_session.add_all([active, monitoring, resolved])
    db_session.commit()

    response = client.get("/api/hotspots/clusters")

    assert response.status_code == 200
    data = response.json()
    returned_statuses = {item["status"] for item in data["clusters"]}
    assert data["cluster_count"] == 3
    assert data["matching_count"] == 2
    assert data["returned_count"] == 2
    assert data["status_counts"] == {"active": 1, "monitoring": 1, "resolved": 1}
    assert data["filters"]["status"] == "active,monitoring"
    assert returned_statuses == {"active", "monitoring"}


def test_clusters_endpoint_status_all_returns_all_clusters(client, db_session):
    now = utc_now_naive()
    db_session.add_all([
        _cluster(now - timedelta(hours=2), status="active", latitude=37.1),
        _cluster(now - timedelta(hours=36), status="monitoring", latitude=37.2),
        _cluster(now - timedelta(hours=90), status="resolved", latitude=37.3),
    ])
    db_session.commit()

    response = client.get("/api/hotspots/clusters?status=all")

    assert response.status_code == 200
    data = response.json()
    assert data["cluster_count"] == 3
    assert data["matching_count"] == 3
    assert data["returned_count"] == 3
    assert data["filters"]["status"] == "all"


def test_clusters_endpoint_status_resolved_and_limit(client, db_session):
    now = utc_now_naive()
    db_session.add_all([
        _cluster(now - timedelta(hours=90), status="resolved", latitude=37.1),
        _cluster(now - timedelta(hours=96), status="resolved", latitude=37.2),
        _cluster(now - timedelta(hours=2), status="active", latitude=37.3),
    ])
    db_session.commit()

    response = client.get("/api/hotspots/clusters?status=resolved&limit=1")

    assert response.status_code == 200
    data = response.json()
    assert data["cluster_count"] == 3
    assert data["matching_count"] == 2
    assert data["returned_count"] == 1
    assert data["filters"] == {"status": "resolved", "limit": 1}
    assert [item["status"] for item in data["clusters"]] == ["resolved"]
