from app.api import scheduler as scheduler_api


def test_scheduler_status_public(client):
    response = client.get("/api/scheduler/status")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "enabled" in data
    assert "is_running" in data
    assert "last_run_at" in data
    assert "last_success_at" in data
    assert "last_error" in data


def test_scheduler_run_once_requires_api_key(client):
    response = client.post("/api/scheduler/run-once")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_scheduler_run_once_success(client, api_key_headers, monkeypatch):
    async def fake_run_full_cycle():
        return {"mock": True}

    monkeypatch.setattr(
        scheduler_api.scheduler_service,
        "run_full_cycle",
        fake_run_full_cycle,
    )
    monkeypatch.setattr(
        scheduler_api.scheduler_service,
        "get_scheduler_status",
        lambda: {"is_running": False},
    )

    response = client.post("/api/scheduler/run-once", headers=api_key_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["result"] == {"mock": True}


def test_scheduler_run_once_returns_409_when_already_running(client, api_key_headers, monkeypatch):
    monkeypatch.setattr(
        scheduler_api.scheduler_service,
        "get_scheduler_status",
        lambda: {"is_running": True},
    )

    response = client.post("/api/scheduler/run-once", headers=api_key_headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "Scheduler cycle is already running"


def test_scheduler_run_once_failure_returns_500(client, api_key_headers, monkeypatch):
    async def fake_run_full_cycle():
        raise RuntimeError("fake scheduler failure")

    monkeypatch.setattr(
        scheduler_api.scheduler_service,
        "run_full_cycle",
        fake_run_full_cycle,
    )
    monkeypatch.setattr(
        scheduler_api.scheduler_service,
        "get_scheduler_status",
        lambda: {"is_running": False},
    )

    response = client.post("/api/scheduler/run-once", headers=api_key_headers)

    assert response.status_code == 500
    assert response.json()["detail"] == "Scheduler full cycle failed"
