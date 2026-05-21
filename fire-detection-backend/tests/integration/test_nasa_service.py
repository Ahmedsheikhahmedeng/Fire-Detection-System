from datetime import date

import pytest

from app.models.hotspot import Hotspot
from app.services import nasa_service
from app.core import config


class FakeNASAResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class FakeNASAClient:
    def __init__(self, csv_text):
        self.csv_text = csv_text
        self.requested_urls = []
        self.requested_timeout = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def get(self, url, timeout=None):
        self.requested_urls.append(url)
        self.requested_timeout = timeout
        return FakeNASAResponse(self.csv_text)


def _patch_nasa_client(monkeypatch, csv_text):
    fake_client = FakeNASAClient(csv_text)

    monkeypatch.setattr(
        nasa_service,
        "FIRMS_SOURCES",
        ["VIIRS_SNPP_NRT"],
    )

    monkeypatch.setattr(
        nasa_service.httpx,
        "Client",
        lambda: fake_client,
    )

    return fake_client


class MultiSourceFakeNASAClient:
    def __init__(self, responses_by_source):
        self.responses_by_source = responses_by_source
        self.requested_urls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def get(self, url, timeout=None):
        self.requested_urls.append(url)
        for source, response in self.responses_by_source.items():
            if f"/{source}/" in url:
                if isinstance(response, Exception):
                    raise response
                return FakeNASAResponse(response)
        return FakeNASAResponse("")


def test_nasa_fake_csv_inserts_valid_rows_skips_duplicate_and_reports_row_error(
    monkeypatch,
    db_session,
    fake_nasa_csv,
):
    """
    4 fake satir:
    - 1 normal insert
    - 1 ayni observation duplicate
    - 1 ayni koordinat farkli acq_time yeni insert
    - 1 bozuk latitude row_error
    """
    monkeypatch.setattr(
        nasa_service.settings,
        "ENABLE_V3_PREDICTION_ON_NASA_FETCH",
        False,
    )

    fake_client = _patch_nasa_client(monkeypatch, fake_nasa_csv)

    result = nasa_service.fetch_hotspots_from_nasa(
        db=db_session,
        country="TUR",
        days=1,
    )

    assert result["received_count"] == 4
    assert result["inserted_count"] == 2
    assert result["duplicate_count"] == 1
    assert result["row_error_count"] == 1
    assert isinstance(result["row_errors"], list)

    assert result["v3_prediction_count"] == 0
    assert result["v3_alert_count"] == 0

    rows = db_session.query(Hotspot).order_by(Hotspot.acq_time.asc()).all()

    assert len(rows) == 2

    assert rows[0].latitude == pytest.approx(38.4)
    assert rows[0].longitude == pytest.approx(27.1)
    assert rows[0].acq_date == date(2025, 8, 1)
    assert str(rows[0].acq_time).zfill(4) == "1230"

    assert rows[1].latitude == pytest.approx(38.4)
    assert rows[1].longitude == pytest.approx(27.1)
    assert rows[1].acq_date == date(2025, 8, 1)
    assert str(rows[1].acq_time).zfill(4) == "1231"

    assert fake_client.requested_timeout == 30.0


def test_nasa_duplicate_existing_db_row_is_skipped(
    monkeypatch,
    db_session,
):
    monkeypatch.setattr(
        nasa_service.settings,
        "ENABLE_V3_PREDICTION_ON_NASA_FETCH",
        False,
    )

    existing = Hotspot(
        latitude=38.4,
        longitude=27.1,
        brightness=330,
        bright_ti5=295,
        frp=45,
        scan=0.5,
        track=0.5,
        confidence="h",
        daynight="D",
        satellite="N",
        instrument="VIIRS",
        firms_source="VIIRS_SNPP_NRT",
        type=0,
        version=2,
        acq_date=date(2025, 8, 1),
        acq_time="1230",
        city=None,
    )

    db_session.add(existing)
    db_session.commit()

    csv_text = """latitude,longitude,bright_ti4,bright_ti5,frp,scan,track,confidence,daynight,satellite,instrument,acq_date,acq_time,type,version
38.4,27.1,330,295,45,0.5,0.5,h,D,N,VIIRS,2025-08-01,1230,0,2
"""

    _patch_nasa_client(monkeypatch, csv_text)

    result = nasa_service.fetch_hotspots_from_nasa(
        db=db_session,
        country="TUR",
        days=1,
    )

    assert result["received_count"] == 1
    assert result["inserted_count"] == 0
    assert result["duplicate_count"] == 1
    assert result["row_error_count"] == 0

    count = db_session.query(Hotspot).count()
    assert count == 1


def test_nasa_same_coordinates_different_acq_time_is_not_duplicate(
    monkeypatch,
    db_session,
):
    monkeypatch.setattr(
        nasa_service.settings,
        "ENABLE_V3_PREDICTION_ON_NASA_FETCH",
        False,
    )

    csv_text = """latitude,longitude,bright_ti4,bright_ti5,frp,scan,track,confidence,daynight,satellite,instrument,acq_date,acq_time,type,version
38.4,27.1,330,295,45,0.5,0.5,h,D,N,VIIRS,2025-08-01,1230,0,2
38.4,27.1,331,296,46,0.5,0.5,h,D,N,VIIRS,2025-08-01,1231,0,2
"""

    _patch_nasa_client(monkeypatch, csv_text)

    result = nasa_service.fetch_hotspots_from_nasa(
        db=db_session,
        country="TUR",
        days=1,
    )

    assert result["received_count"] == 2
    assert result["inserted_count"] == 2
    assert result["duplicate_count"] == 0
    assert result["row_error_count"] == 0

    rows = db_session.query(Hotspot).order_by(Hotspot.acq_time.asc()).all()

    assert len(rows) == 2
    assert str(rows[0].acq_time).zfill(4) == "1230"
    assert str(rows[1].acq_time).zfill(4) == "1231"


def test_nasa_same_time_different_satellite_is_not_duplicate(
    monkeypatch,
    db_session,
):
    monkeypatch.setattr(
        nasa_service.settings,
        "ENABLE_V3_PREDICTION_ON_NASA_FETCH",
        False,
    )

    csv_text = """latitude,longitude,bright_ti4,bright_ti5,frp,scan,track,confidence,daynight,satellite,instrument,acq_date,acq_time,type,version
38.4,27.1,330,295,45,0.5,0.5,h,D,N,VIIRS,2025-08-01,1230,0,2
38.4,27.1,331,296,46,0.5,0.5,h,D,J1,VIIRS,2025-08-01,1230,0,2
"""

    _patch_nasa_client(monkeypatch, csv_text)

    result = nasa_service.fetch_hotspots_from_nasa(
        db=db_session,
        country="TUR",
        days=1,
    )

    assert result["received_count"] == 2
    assert result["inserted_count"] == 2
    assert result["duplicate_count"] == 0
    assert result["row_error_count"] == 0

    rows = db_session.query(Hotspot).order_by(Hotspot.satellite.asc()).all()

    assert len(rows) == 2
    assert {row.satellite for row in rows} == {"N", "J1"}


def test_nasa_fetches_all_viirs_sources_and_keeps_source_in_duplicates(
    monkeypatch,
    db_session,
):
    monkeypatch.setattr(
        nasa_service.settings,
        "ENABLE_V3_PREDICTION_ON_NASA_FETCH",
        False,
    )

    monkeypatch.setattr(
        nasa_service,
        "FIRMS_SOURCES",
        ["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT"],
    )

    csv_text = """latitude,longitude,bright_ti4,bright_ti5,frp,scan,track,confidence,daynight,satellite,instrument,acq_date,acq_time,type,version
38.4,27.1,330,295,45,0.5,0.5,h,D,N21,VIIRS,2025-08-01,1230,0,2
"""

    fake_client = MultiSourceFakeNASAClient({
        "VIIRS_SNPP_NRT": csv_text,
        "VIIRS_NOAA20_NRT": csv_text,
        "VIIRS_NOAA21_NRT": csv_text,
    })
    monkeypatch.setattr(nasa_service.httpx, "Client", lambda: fake_client)

    result = nasa_service.fetch_hotspots_from_nasa(
        db=db_session,
        country="TUR",
        days=1,
    )

    assert len(fake_client.requested_urls) == 3
    assert all(source in url for source, url in zip(nasa_service.FIRMS_SOURCES, fake_client.requested_urls))
    assert result["received_count"] == 3
    assert result["inserted_count"] == 3
    assert result["duplicate_count"] == 0
    assert result["source_error_count"] == 0

    rows = db_session.query(Hotspot).order_by(Hotspot.firms_source.asc()).all()
    assert {row.firms_source for row in rows} == {
        "VIIRS_SNPP_NRT",
        "VIIRS_NOAA20_NRT",
        "VIIRS_NOAA21_NRT",
    }
    assert {row.instrument for row in rows} == {"VIIRS"}
    assert {row.satellite for row in rows} == {"N21"}


def test_nasa_source_failure_does_not_stop_other_sources(
    monkeypatch,
    db_session,
):
    monkeypatch.setattr(
        nasa_service.settings,
        "ENABLE_V3_PREDICTION_ON_NASA_FETCH",
        False,
    )

    monkeypatch.setattr(
        nasa_service,
        "FIRMS_SOURCES",
        ["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT"],
    )

    csv_text = """latitude,longitude,bright_ti4,bright_ti5,frp,scan,track,confidence,daynight,satellite,instrument,acq_date,acq_time,type,version
38.4,27.1,330,295,45,0.5,0.5,h,D,N,VIIRS,2025-08-01,1230,0,2
"""

    fake_client = MultiSourceFakeNASAClient({
        "VIIRS_SNPP_NRT": csv_text,
        "VIIRS_NOAA20_NRT": csv_text,
        "VIIRS_NOAA21_NRT": RuntimeError("NOAA21 unavailable"),
    })
    monkeypatch.setattr(nasa_service.httpx, "Client", lambda: fake_client)

    result = nasa_service.fetch_hotspots_from_nasa(
        db=db_session,
        country="TUR",
        days=1,
    )

    assert result["received_count"] == 2
    assert result["inserted_count"] == 2
    assert result["source_error_count"] == 1
    assert result["source_errors"][0]["source"] == "VIIRS_NOAA21_NRT"
    assert db_session.query(Hotspot).count() == 2


def test_nasa_prediction_limit_is_reported_by_source(
    monkeypatch,
    db_session,
):
    monkeypatch.setattr(
        nasa_service.settings,
        "ENABLE_V3_PREDICTION_ON_NASA_FETCH",
        True,
    )
    monkeypatch.setattr(
        nasa_service.settings,
        "V3_MAX_PREDICTIONS_PER_NASA_FETCH",
        2,
    )

    csv_text = """latitude,longitude,bright_ti4,bright_ti5,frp,scan,track,confidence,daynight,satellite,instrument,acq_date,acq_time,type,version
38.1,27.1,330,295,45,0.5,0.5,h,D,N,VIIRS,2025-08-01,1230,0,2
38.2,27.2,331,296,46,0.5,0.5,h,D,N,VIIRS,2025-08-01,1231,0,2
38.3,27.3,332,297,47,0.5,0.5,h,D,N,VIIRS,2025-08-01,1232,0,2
"""
    _patch_nasa_client(monkeypatch, csv_text)

    monkeypatch.setattr(
        nasa_service.prediction_service,
        "predict_hotspot_with_db_context",
        lambda db, hotspot_payload: {"success": True, "created_alert_id": None},
    )

    result = nasa_service.fetch_hotspots_from_nasa(
        db=db_session,
        country="TUR",
        days=1,
    )

    assert result["inserted_count"] == 3
    assert result["v3_prediction_count"] == 2
    assert result["prediction_limit_per_fetch"] == 2
    assert result["prediction_limit_applied"] is True
    assert result["prediction_limit_note"] == "Prediction processing limited to 2 records per fetch cycle"
    assert result["received_by_source"]["VIIRS_SNPP_NRT"] == 3
    assert result["inserted_by_source"]["VIIRS_SNPP_NRT"] == 3
    assert result["predictions_by_source"]["VIIRS_SNPP_NRT"] == 2


def test_nasa_empty_csv_returns_zero_counts(
    monkeypatch,
    db_session,
):
    monkeypatch.setattr(
        nasa_service.settings,
        "ENABLE_V3_PREDICTION_ON_NASA_FETCH",
        False,
    )

    csv_text = "latitude,longitude,bright_ti4,acq_date,acq_time\n"

    _patch_nasa_client(monkeypatch, csv_text)

    result = nasa_service.fetch_hotspots_from_nasa(
        db=db_session,
        country="TUR",
        days=1,
    )

    assert result["received_count"] == 0
    assert result["inserted_count"] == 0
    assert result["duplicate_count"] == 0
    assert result["row_error_count"] == 0
    assert result["v3_prediction_count"] == 0
    assert result["v3_alert_count"] == 0

    count = db_session.query(Hotspot).count()
    assert count == 0


def test_build_v3_payload_from_nasa_row_preserves_ml_fields(db_session):
    row = {
        "brightness": "335",
        "bright_ti4": "335",
        "bright_ti5": "295",
        "frp": "75",
        "scan": "0.6",
        "track": "0.7",
        "confidence": "h",
        "daynight": "D",
        "satellite": "N",
        "instrument": "VIIRS",
        "type": "0",
        "version": "2",
    }

    hotspot = Hotspot(
        id=123,
        latitude=38.4,
        longitude=27.1,
        brightness=335,
        bright_ti5=295,
        frp=75,
        scan=0.6,
        track=0.7,
        confidence="h",
        daynight="D",
        satellite="N",
        instrument="VIIRS",
        firms_source="VIIRS_SNPP_NRT",
        type=0,
        version=2,
        acq_date=date(2025, 8, 1),
        acq_time="1230",
        city=None,
    )

    payload = nasa_service._build_v3_payload_from_nasa_row(row, hotspot)

    assert payload["id"] == 123
    assert payload["hotspot_id"] == 123
    assert payload["latitude"] == pytest.approx(38.4)
    assert payload["longitude"] == pytest.approx(27.1)
    assert payload["brightness"] == pytest.approx(335.0)
    assert payload["bright_ti4"] == pytest.approx(335.0)
    assert payload["bright_ti5"] == pytest.approx(295.0)
    assert payload["frp"] == pytest.approx(75.0)
    assert payload["scan"] == pytest.approx(0.6)
    assert payload["track"] == pytest.approx(0.7)
    assert payload["confidence"] == "h"
    assert payload["daynight"] == "D"
    assert payload["satellite"] == "N"
    assert payload["instrument"] == "VIIRS"
    assert payload["firms_source"] == "VIIRS_SNPP_NRT"
    assert payload["acq_date"] == "2025-08-01"
    assert payload["acq_time"] == "1230"
