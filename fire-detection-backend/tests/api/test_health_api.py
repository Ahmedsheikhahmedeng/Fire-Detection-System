def test_health_endpoint_returns_200(client):
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] in ["ok", "degraded"]
    assert "app" in data
    assert "environment" in data
    assert data["version"] == "v3"
    assert data["database"] in ["connected", "disconnected"]
    assert data["ml_model"] in ["loaded", "not_loaded", "unknown"]
    assert data["scheduler"] in ["enabled", "disabled", "running", "stopped", "unknown"]
    assert data["security"] in ["enabled", "not_configured"]


def test_health_endpoint_is_public_without_api_key(client):
    response = client.get("/health")

    assert response.status_code == 200
