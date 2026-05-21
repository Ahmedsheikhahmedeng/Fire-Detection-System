from datetime import date

from app.models.hotspot import Hotspot
from app.models.nasa_fetch_run import NasaFetchRun
from app.services import nasa_service
from app.services.nasa_fetch_run_service import save_nasa_fetch_run


class FakeNASAResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class FakeNASAClient:
    def __init__(self, csv_text):
        self.csv_text = csv_text

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def get(self, url, timeout=None):
        return FakeNASAResponse(self.csv_text)


def test_save_nasa_fetch_run_persists_summary(db_session):
    from app.core.time_utils import utc_now_naive

    started_at = utc_now_naive()
    run = save_nasa_fetch_run(
        db_session,
        started_at=started_at,
        result={
            "received_count": 10,
            "inserted_count": 7,
            "duplicate_count": 3,
            "source_error_count": 0,
            "row_error_count": 0,
            "v3_prediction_count": 5,
            "prediction_limit_per_fetch": 100,
            "prediction_limit_applied": False,
            "received_by_source": {"VIIRS_SNPP_NRT": 10},
        },
    )

    assert run is not None
    assert run.status == "success"
    assert db_session.query(NasaFetchRun).count() == 1
    assert db_session.query(NasaFetchRun).first().received_by_source["VIIRS_SNPP_NRT"] == 10


def test_nasa_fetch_records_run_and_logging_failure_does_not_break_fetch(monkeypatch, db_session):
    monkeypatch.setattr(nasa_service.settings, "ENABLE_V3_PREDICTION_ON_NASA_FETCH", False)
    monkeypatch.setattr(nasa_service, "FIRMS_SOURCES", ["VIIRS_SNPP_NRT"])
    monkeypatch.setattr(
        nasa_service.httpx,
        "Client",
        lambda: FakeNASAClient(
            """latitude,longitude,bright_ti4,bright_ti5,frp,scan,track,confidence,daynight,satellite,instrument,acq_date,acq_time,type,version
38.4,27.1,330,295,45,0.5,0.5,h,D,N,VIIRS,2026-05-19,1230,0,2
"""
        ),
    )

    result = nasa_service.fetch_hotspots_from_nasa(db_session, days=1)

    assert result["inserted_count"] == 1
    assert db_session.query(Hotspot).filter(Hotspot.acq_date == date(2026, 5, 19)).count() == 1
    assert db_session.query(NasaFetchRun).count() == 1

    def fail_save(*args, **kwargs):
        raise RuntimeError("run logging down")

    monkeypatch.setattr("app.services.nasa_fetch_run_service.save_nasa_fetch_run", fail_save)

    result = nasa_service.fetch_hotspots_from_nasa(db_session, days=1)

    assert result["duplicate_count"] == 1
    assert db_session.query(NasaFetchRun).count() == 1
