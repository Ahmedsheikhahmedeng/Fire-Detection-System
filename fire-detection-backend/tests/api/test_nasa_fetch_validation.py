def _fake_nasa_result(inserted_count=0):
    return {
        "inserted_count": inserted_count,
        "received_count": inserted_count,
        "duplicate_count": 0,
        "row_error_count": 0,
        "row_errors": [],
        "v3_prediction_count": 0,
        "v3_alert_count": 0,
        "v3_prediction_errors": [],
    }


def test_nasa_fetch_requires_api_key(client):
    response = client.post("/nasa/fetch-hotspots?country=turkey&days=3")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_nasa_fetch_rejects_invalid_country(client, api_key_headers):
    response = client.post(
        "/nasa/fetch-hotspots?country=france&days=3",
        headers=api_key_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported country. Supported values: turkey, greece, cyprus"


def test_nasa_fetch_rejects_too_low_days(client, api_key_headers):
    response = client.post(
        "/nasa/fetch-hotspots?country=turkey&days=0",
        headers=api_key_headers,
    )

    assert response.status_code in [400, 422]


def test_nasa_fetch_rejects_too_many_days(client, api_key_headers):
    response = client.post(
        "/nasa/fetch-hotspots?country=turkey&days=100",
        headers=api_key_headers,
    )

    assert response.status_code in [400, 422]


def test_nasa_fetch_defaults_to_turkey_and_five_days(client, api_key_headers, monkeypatch):
    from app.api import nasa

    captured = {}

    def fake_fetch(db, country="TUR", days=5):
        captured["country"] = country
        captured["days"] = days
        return _fake_nasa_result(inserted_count=0)

    monkeypatch.setattr(nasa, "fetch_hotspots_from_nasa", fake_fetch)

    response = client.post("/nasa/fetch-hotspots", headers=api_key_headers)

    assert response.status_code == 200
    assert captured == {"country": "TUR", "days": 5}
    assert response.json()["country"] == "turkey"
    assert response.json()["days"] == 5


def test_nasa_fetch_normalizes_turkiye_alias(client, api_key_headers, monkeypatch):
    from app.api import nasa

    captured = {}

    def fake_fetch(db, country="TUR", days=5):
        captured["country"] = country
        captured["days"] = days
        return _fake_nasa_result(inserted_count=2)

    monkeypatch.setattr(nasa, "fetch_hotspots_from_nasa", fake_fetch)

    response = client.post(
        "/nasa/fetch-hotspots?country=turkiye&days=3",
        headers=api_key_headers,
    )

    assert response.status_code == 200
    assert captured == {"country": "TUR", "days": 3}
    data = response.json()
    assert data["status"] == "success"
    assert data["country"] == "turkey"
    assert data["days"] == 3
    assert data["inserted"] == 2


def test_nasa_fetch_accepts_greece_and_cyprus(client, api_key_headers, monkeypatch):
    from app.api import nasa

    captured = []

    def fake_fetch(db, country="TUR", days=5):
        captured.append((country, days))
        return _fake_nasa_result(inserted_count=0)

    monkeypatch.setattr(nasa, "fetch_hotspots_from_nasa", fake_fetch)

    greece_response = client.post(
        "/nasa/fetch-hotspots?country=greece&days=1",
        headers=api_key_headers,
    )
    cyprus_response = client.post(
        "/nasa/fetch-hotspots?country=cyprus&days=2",
        headers=api_key_headers,
    )

    assert greece_response.status_code == 200
    assert cyprus_response.status_code == 200
    assert captured == [("GRC", 1), ("CYP", 2)]
