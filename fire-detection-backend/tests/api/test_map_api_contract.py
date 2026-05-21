def test_map_status_endpoint_contract(client):
    response = client.get("/map/status")

    assert response.status_code == 200

    data = response.json()

    expected_keys = [
        "is_running",
        "current_task",
        "last_nasa_fetch",
        "last_weather_refresh",
        "last_ml_scan",
        "nasa_hotspots_inserted",
        "v3_prediction_count",
        "v3_alert_count",
        "ml_processed",
        "ml_high_risk",
    ]

    for key in expected_keys:
        assert key in data


def test_map_hotspots_endpoint_returns_list(client):
    response = client.get("/map/hotspots")

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)

    if data:
        item = data[0]

        expected_keys = [
            "id",
            "latitude",
            "longitude",
            "city",
            "temperature",
            "humidity",
            "wind_speed",
            "risk_level",
            "fire_probability",
            "risk_percent",
            "decision_level",
            "decision_name",
            "has_active_alert",
            "alert_id",
            "alert",
            "ml_source",
        ]

        for key in expected_keys:
            assert key in item


def test_map_stats_endpoint_has_v3_risk_distribution(client):
    response = client.get("/map/stats")

    assert response.status_code == 200

    data = response.json()

    assert "risk_distribution" in data

    risk_distribution = data["risk_distribution"]

    expected_risk_keys = [
        "CRITICAL",
        "HIGH",
        "MEDIUM",
        "WATCH",
        "LOW",
        "UNKNOWN",
    ]

    for key in expected_risk_keys:
        assert key in risk_distribution
