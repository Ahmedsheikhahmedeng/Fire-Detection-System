def test_get_hotspot_not_found_returns_404(client):
    response = client.get("/hotspots/999999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Hotspot not found"


def test_update_alert_without_api_key_returns_401(client):
    response = client.patch(
        "/alerts/999999999/status",
        json={"status": "RESOLVED"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_update_alert_not_found_returns_404(client, api_key_headers):
    response = client.patch(
        "/alerts/999999999/status",
        json={"status": "RESOLVED"},
        headers=api_key_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Alert not found"


def test_close_alert_not_found_returns_404(client, api_key_headers):
    response = client.post(
        "/alerts/999999999/close",
        headers=api_key_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Alert not found"


def test_weather_enrich_not_found_returns_404(client, api_key_headers):
    response = client.post(
        "/weather/enrich/999999999",
        headers=api_key_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Hotspot not found"


def test_weather_enrich_without_api_key_returns_401(client):
    response = client.post("/weather/enrich/999999999")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_nasa_invalid_country_still_returns_400(client, api_key_headers):
    response = client.post(
        "/nasa/fetch-hotspots?country=france&days=3",
        headers=api_key_headers,
    )

    assert response.status_code == 400
    assert "Unsupported country" in response.json()["detail"]


def test_nasa_invalid_days_still_returns_422(client, api_key_headers):
    response = client.post(
        "/nasa/fetch-hotspots?country=turkey&days=100",
        headers=api_key_headers,
    )

    assert response.status_code == 422


def test_scheduler_run_once_without_api_key_returns_401(client):
    response = client.post("/scheduler/run-once")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_scheduler_run_once_already_running_returns_409(client, api_key_headers, monkeypatch):
    from app.api import scheduler as scheduler_api

    monkeypatch.setattr(
        scheduler_api.scheduler_service,
        "get_scheduler_status",
        lambda: {"is_running": True},
    )

    response = client.post("/scheduler/run-once", headers=api_key_headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "Scheduler cycle is already running"


def test_map_hotspots_empty_data_returns_200(client):
    response = client.get("/map/hotspots")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
