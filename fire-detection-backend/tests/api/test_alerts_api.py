def test_alerts_list_endpoint_with_limit(client):
    response = client.get("/alerts?limit=2")

    assert response.status_code == 200

    data = response.json()

    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) <= 2


def test_active_alerts_endpoint_returns_list_or_paginated_result(client):
    response = client.get("/alerts/active?limit=2")

    assert response.status_code == 200

    data = response.json()

    if isinstance(data, list):
        assert len(data) <= 2
    else:
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) <= 2


def test_close_non_existing_alert_returns_404(client, api_key_headers):
    response = client.post("/alerts/999999999/close", headers=api_key_headers)

    assert response.status_code == 404


def test_invalid_alert_status_returns_400_or_404(client, api_key_headers):
    response = client.patch(
        "/alerts/999999999/status",
        json={"status": "WRONG_STATUS"},
        headers=api_key_headers,
    )

    assert response.status_code in [400, 404]
