from datetime import date

from app.api import scheduler as scheduler_api
from app.models.hotspot import Hotspot
from app.services import nasa_service


class FakeLocation:
    def __init__(self, address):
        self.raw = {"address": address}


def add_hotspot(db_session, *, city=None, latitude=38.4, longitude=27.1):
    hotspot = Hotspot(
        latitude=latitude,
        longitude=longitude,
        brightness=330,
        satellite="N",
        instrument="VIIRS",
        acq_date=date(2025, 8, 1),
        acq_time="1230",
        city=city,
    )
    db_session.add(hotspot)
    db_session.commit()
    db_session.refresh(hotspot)
    return hotspot


def test_resolver_processes_only_city_null_records(db_session, monkeypatch):
    null_city_hotspot = add_hotspot(db_session, city=None, latitude=38.4, longitude=27.1)
    unknown_city_hotspot = add_hotspot(db_session, city="Bilinmiyor", latitude=39.0, longitude=28.0)

    class FakeNominatim:
        def __init__(self, *args, **kwargs):
            pass

        def reverse(self, *args, **kwargs):
            return FakeLocation({"city": "Izmir"})

    monkeypatch.setattr("geopy.geocoders.Nominatim", FakeNominatim)
    monkeypatch.setattr(nasa_service.time, "sleep", lambda *_: None)

    resolved = nasa_service.resolve_missing_cities(db_session, batch_size=50)

    db_session.refresh(null_city_hotspot)
    db_session.refresh(unknown_city_hotspot)

    assert resolved == 1
    assert null_city_hotspot.city == "Izmir"
    assert unknown_city_hotspot.city == "Bilinmiyor"


def test_resolver_sets_unknown_when_geocoding_fails(db_session, monkeypatch):
    hotspot = add_hotspot(db_session, city=None)

    class FailingNominatim:
        def __init__(self, *args, **kwargs):
            pass

        def reverse(self, *args, **kwargs):
            raise RuntimeError("geocoding unavailable")

    monkeypatch.setattr("geopy.geocoders.Nominatim", FailingNominatim)
    monkeypatch.setattr(nasa_service.time, "sleep", lambda *_: None)

    resolved = nasa_service.resolve_missing_cities(db_session, batch_size=50)

    db_session.refresh(hotspot)

    assert resolved == 0
    assert hotspot.city == "Bilinmiyor"


def test_resolve_cities_once_requires_api_key(client):
    response = client.post("/api/scheduler/resolve-cities-once")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_resolve_cities_once_success(client, api_key_headers, monkeypatch):
    monkeypatch.setattr(
        scheduler_api,
        "_resolve_cities_once_sync",
        lambda batch_size: 3,
    )

    response = client.post(
        "/api/scheduler/resolve-cities-once?batch_size=10",
        headers=api_key_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["resolved"] == 3
    assert data["batch_size"] == 10
    assert data["message"] == "City resolve completed"
