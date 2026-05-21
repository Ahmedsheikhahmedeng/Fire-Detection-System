import os
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

# Testlerde scheduler gibi arka plan islerinin yanlislikla calismasini engellemek icin.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ENABLE_SCHEDULER", "false")
os.environ.setdefault("ENABLE_V3_PREDICTION_ON_NASA_FETCH", "false")
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")
os.environ.setdefault("TELEGRAM_CHAT_ID", "")
os.environ.setdefault("SMTP_USERNAME", "")
os.environ.setdefault("SMTP_PASSWORD", "")
os.environ.setdefault("SMTP_FROM_EMAIL", "")
os.environ.setdefault("ALERT_EMAIL_TO", "")

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


if not TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL tanimli degil. Once terminalde sunu calistir:\n"
        'export TEST_DATABASE_URL="postgresql://user:password@localhost:5432/fire_detection_test"'
    )


if "test" not in TEST_DATABASE_URL.lower():
    raise RuntimeError(
        "Guvenlik nedeniyle TEST_DATABASE_URL icinde 'test' kelimesi olmali. "
        "Ana database uzerinde test calistirma."
    )


test_url = make_url(TEST_DATABASE_URL)
os.environ["DB_HOST"] = test_url.host or "localhost"
os.environ["DB_PORT"] = str(test_url.port or 5432)
os.environ["DB_NAME"] = test_url.database or ""
os.environ["DB_USER"] = test_url.username or ""
os.environ["DB_PASSWORD"] = test_url.password or ""

from app.main import app
from app.core.database import get_db
from app.models.base import Base

# Modeller metadata icine yuklensin diye import ediyoruz.
from app.models.hotspot import Hotspot
from app.models.fire_cluster import FireCluster
from app.models.weather import WeatherData
from app.models.prediction import Prediction
from app.models.alert import Alert
from app.models.nasa_fetch_run import NasaFetchRun


test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


def clean_database():
    """
    Her testten sonra tablolari temizler.
    Servisler db.commit() yapsa bile testler birbirini kirletmez.
    """
    with test_engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(
                text(f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE')
            )


@pytest.fixture(scope="session", autouse=True)
def prepare_test_database():
    """
    Test session basinda tablolari olusturur.
    Test session sonunda temizler.
    """
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    yield

    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    """
    Servis testleri icin direkt DB session fixture.
    Ornek:
        def test_x(db_session):
            db_session.add(...)
    """
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        clean_database()


@pytest.fixture
def client():
    """
    FastAPI endpoint testleri icin TestClient.
    app.core.database.get_db dependency'sini test DB ile degistirir.
    """

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    clean_database()


@pytest.fixture
def api_key_headers():
    return {"X-API-Key": "test-api-key"}


@pytest.fixture
def sample_raw_hotspot():
    """
    V3 raw FIRMS hotspot input ornegi.
    ML endpoint, feature pipeline ve prediction_service testlerinde kullanilir.
    """
    return {
        "id": "645",
        "hotspot_id": "645",
        "latitude": 38.4,
        "longitude": 27.1,
        "brightness": 330,
        "bright_ti4": 330,
        "bright_ti5": 295,
        "frp": 45,
        "scan": 0.5,
        "track": 0.5,
        "confidence": "h",
        "satellite": "N",
        "instrument": "VIIRS",
        "acq_date": "2025-08-01",
        "acq_time": "1230",
        "daynight": "D",
        "type": 0,
    }


@pytest.fixture
def sample_hotspot_row(db_session):
    """
    DB icinde kayitli gercek Hotspot objesi isteyen integration testleri icin.
    """
    hotspot = Hotspot(
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
        city="Izmir",
    )

    db_session.add(hotspot)
    db_session.commit()
    db_session.refresh(hotspot)

    return hotspot


@pytest.fixture
def low_risk_prediction_payload():
    return {
        "success": True,
        "model_version": "v3",
        "probabilities": {
            "ensemble_fire_probability": 0.05,
        },
        "decision": {
            "decision_level": 0,
            "decision_name": "low_risk_no_fire",
        },
    }


@pytest.fixture
def watch_prediction_payload():
    return {
        "success": True,
        "model_version": "v3",
        "probabilities": {
            "ensemble_fire_probability": 0.35,
        },
        "decision": {
            "decision_level": 1,
            "decision_name": "watch_early_warning",
        },
    }


@pytest.fixture
def medium_risk_prediction_payload():
    return {
        "success": True,
        "model_version": "v3",
        "probabilities": {
            "ensemble_fire_probability": 0.62,
        },
        "decision": {
            "decision_level": 2,
            "decision_name": "medium_risk_fire",
        },
    }


@pytest.fixture
def high_risk_prediction_payload():
    return {
        "success": True,
        "model_version": "v3",
        "probabilities": {
            "ensemble_fire_probability": 0.88,
        },
        "decision": {
            "decision_level": 3,
            "decision_name": "high_risk_fire",
        },
    }


@pytest.fixture
def critical_risk_prediction_payload():
    return {
        "success": True,
        "model_version": "v3",
        "probabilities": {
            "ensemble_fire_probability": 0.97,
        },
        "decision": {
            "decision_level": 4,
            "decision_name": "critical_fire_alert",
        },
    }


@pytest.fixture
def fake_nasa_csv():
    """
    NASA service testlerinde kullanilacak sahte CSV.
    4 satir:
    - 1 normal
    - 1 duplicate
    - 1 ayni koordinat farkli saat
    - 1 bozuk latitude
    """
    return """latitude,longitude,bright_ti4,bright_ti5,frp,scan,track,confidence,daynight,satellite,instrument,acq_date,acq_time,type,version
38.4,27.1,330,295,45,0.5,0.5,h,D,N,VIIRS,2025-08-01,1230,0,2
38.4,27.1,330,295,45,0.5,0.5,h,D,N,VIIRS,2025-08-01,1230,0,2
38.4,27.1,331,296,46,0.5,0.5,h,D,N,VIIRS,2025-08-01,1231,0,2
bad,27.1,331,296,46,0.5,0.5,h,D,N,VIIRS,2025-08-01,1232,0,2
"""
