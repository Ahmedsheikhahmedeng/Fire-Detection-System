import asyncio
import copy

import pytest

from app.services import scheduler


@pytest.fixture(autouse=True)
def restore_scheduler_status():
    """
    Scheduler global status dict kullandigi icin her testten sonra eski hale aliyoruz.
    Boylece testler birbirini etkilemez.
    """
    old_status = copy.deepcopy(scheduler.scheduler_status)

    yield

    scheduler.scheduler_status.clear()
    scheduler.scheduler_status.update(old_status)


def test_scheduler_status_contains_expected_fields():
    status = scheduler.get_scheduler_status()

    expected_keys = [
        "last_nasa_fetch",
        "last_weather_refresh",
        "last_ml_scan",
        "nasa_hotspots_inserted",
        "v3_prediction_count",
        "v3_alert_count",
        "ml_processed",
        "ml_high_risk",
        "is_running",
        "current_task",
        "last_error",
        "last_nasa_error",
        "last_refresh_error",
        "last_city_resolve_error",
        "last_cycle_error",
        "last_cycle_started_at",
        "last_cycle_finished_at",
        "last_cycle_type",
    ]

    for key in expected_keys:
        assert key in status


@pytest.mark.asyncio
async def test_run_refresh_cycle_uses_mock_refresh_and_updates_status(monkeypatch):
    async def fake_refresh_weather_and_ml():
        return {
            "processed": 3,
            "high_risk": 1,
            "total": 5,
            "skipped": False,
            "mode": "test_refresh",
        }

    monkeypatch.setattr(
        scheduler,
        "_refresh_weather_and_ml",
        fake_refresh_weather_and_ml,
    )
    monkeypatch.setattr(
        scheduler,
        "_resolve_cities_background",
        lambda: asyncio.sleep(0),
    )

    result = await scheduler.run_refresh_cycle()

    assert result is not None
    assert result.get("processed") == 3
    assert result.get("high_risk") == 1
    assert result.get("skipped") is False

    status = scheduler.get_scheduler_status()

    assert status["is_running"] is False
    assert status["last_cycle_type"] == "refresh"
    assert status["last_cycle_started_at"] is not None
    assert status["last_cycle_finished_at"] is not None
    assert status["last_cycle_error"] is None


@pytest.mark.asyncio
async def test_run_full_cycle_uses_mock_steps_and_broadcasts(monkeypatch):
    broadcasts = []

    async def fake_fetch_nasa_data():
        scheduler.scheduler_status["nasa_hotspots_inserted"] = 2
        scheduler.scheduler_status["v3_prediction_count"] = 2
        scheduler.scheduler_status["v3_alert_count"] = 1

        return {
            "inserted_count": 2,
            "v3_prediction_count": 2,
            "v3_alert_count": 1,
        }

    async def fake_refresh_weather_and_ml():
        scheduler.scheduler_status["ml_processed"] = 2
        scheduler.scheduler_status["ml_high_risk"] = 1

        return {
            "processed": 2,
            "high_risk": 1,
            "total": 2,
            "skipped": False,
            "mode": "test_full_cycle",
        }

    async def fake_resolve_cities_background():
        return 0

    async def fake_broadcast(data):
        broadcasts.append(data)

    monkeypatch.setattr(
        scheduler,
        "_fetch_nasa_data",
        fake_fetch_nasa_data,
    )
    monkeypatch.setattr(
        scheduler,
        "_refresh_weather_and_ml",
        fake_refresh_weather_and_ml,
    )
    monkeypatch.setattr(
        scheduler,
        "_resolve_cities_background",
        fake_resolve_cities_background,
    )
    monkeypatch.setattr(
        scheduler.manager,
        "broadcast",
        fake_broadcast,
    )

    result = await scheduler.run_full_cycle()

    assert result is not None
    assert result.get("skipped") is False

    status = scheduler.get_scheduler_status()

    assert status["is_running"] is False
    assert status["last_cycle_type"] == "full"
    assert status["nasa_hotspots_inserted"] == 2
    assert status["v3_prediction_count"] == 2
    assert status["v3_alert_count"] == 1
    assert status["ml_processed"] == 2
    assert status["ml_high_risk"] == 1

    assert len(broadcasts) >= 1
    assert broadcasts[0]["type"] == "HOTSPOT_UPDATED"


@pytest.mark.asyncio
async def test_scheduler_cycle_lock_skips_refresh_when_cycle_already_running():
    """
    Bir cycle calisirken ikinci cycle baslamamali.
    Beklenen:
    {"skipped": True, "reason": "scheduler_cycle_already_running"}
    """
    lock = getattr(scheduler, "_scheduler_cycle_lock", None)

    assert lock is not None, "scheduler.py icinde _scheduler_cycle_lock bulunamadi."

    await lock.acquire()

    try:
        result = await scheduler.run_refresh_cycle()
    finally:
        lock.release()

    assert result["skipped"] is True
    assert result["reason"] == "scheduler_cycle_already_running"


@pytest.mark.asyncio
async def test_start_scheduler_called_twice_returns_same_task(monkeypatch):
    """
    start_scheduler iki kere cagrilirsa ikinci background task acilmamali.
    Ayni task donmeli.
    """
    async def fake_scheduler_loop():
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            raise

    monkeypatch.setattr(
        scheduler,
        "_scheduler_loop",
        fake_scheduler_loop,
    )

    scheduler._scheduler_task = None

    task1 = scheduler.start_scheduler()
    task2 = scheduler.start_scheduler()

    assert task1 is task2
    assert task1.done() is False

    task1.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task1

    scheduler._scheduler_task = None


@pytest.mark.asyncio
async def test_run_refresh_cycle_error_sets_last_refresh_error(monkeypatch):
    async def fake_refresh_weather_and_ml():
        raise RuntimeError("fake refresh failure")

    monkeypatch.setattr(
        scheduler,
        "_refresh_weather_and_ml",
        fake_refresh_weather_and_ml,
    )

    result = await scheduler.run_refresh_cycle()

    assert result is not None
    assert result.get("skipped") is False
    assert result.get("error") is not None

    status = scheduler.get_scheduler_status()

    assert status["is_running"] is False
    assert status["last_refresh_error"] is not None
    assert "fake refresh failure" in status["last_refresh_error"]


@pytest.mark.asyncio
async def test_run_full_cycle_error_sets_last_cycle_error(monkeypatch):
    async def fake_fetch_nasa_data():
        raise RuntimeError("fake nasa failure")

    monkeypatch.setattr(
        scheduler,
        "_fetch_nasa_data",
        fake_fetch_nasa_data,
    )

    result = await scheduler.run_full_cycle()

    assert result is not None
    assert result.get("skipped") is False
    assert result.get("error") is not None

    status = scheduler.get_scheduler_status()

    assert status["is_running"] is False
    assert status["last_cycle_error"] is not None
    assert "fake nasa failure" in status["last_cycle_error"]
