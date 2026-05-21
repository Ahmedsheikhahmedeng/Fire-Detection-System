def test_public_health_endpoint_does_not_require_api_key(client):
    response = client.get("/health")

    assert response.status_code == 200


def test_protected_nasa_endpoint_requires_api_key(client):
    response = client.post("/nasa/fetch-hotspots")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_protected_nasa_endpoint_accepts_valid_api_key(client, api_key_headers, monkeypatch):
    from app.api import nasa

    monkeypatch.setattr(
        nasa,
        "fetch_hotspots_from_nasa",
        lambda db, country="TUR", days=5: {
            "inserted_count": 0,
            "received_count": 0,
            "duplicate_count": 0,
            "row_error_count": 0,
            "row_errors": [],
            "v3_prediction_count": 0,
            "v3_alert_count": 0,
            "v3_prediction_errors": [],
        },
    )

    response = client.post("/nasa/fetch-hotspots", headers=api_key_headers)

    assert response.status_code == 200
    assert response.json()["inserted"] == 0
