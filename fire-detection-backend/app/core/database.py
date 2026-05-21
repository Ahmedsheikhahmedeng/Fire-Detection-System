import logging
import time
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.base import Base

logger = logging.getLogger("fire_detection.database")

DATABASE_URL = settings.database_url


def wait_for_db(retries: int = 10, delay_seconds: int = 2):
    """Yerel startup'ta Postgres henüz ayağa kalkmadıysa kısa süre bekle."""
    last_error = None
    for _ in range(retries):
        test_engine = None
        try:
            test_engine = create_engine(DATABASE_URL)
            with test_engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except Exception as exc:
            last_error = exc
            time.sleep(delay_seconds)
        finally:
            if test_engine is not None:
                test_engine.dispose()
    if last_error is not None:
        raise last_error


wait_for_db()
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
) #paython postgres kopru bağlantı 

SessionLocal = sessionmaker( #Her request için ayrı session açılır.
    autocommit=False, #otomatik kaydetme kapalı 
    autoflush=False,#otomatik çekme kapalı 
    bind=engine #bağlayanak yer 
)

#Bu FastAPI dependency sistemi.                         
def get_db():                  
    db = SessionLocal()    #1.DB session açılır        
    try:                        
        yield db               #2.endpoint kullanır     #Yani memory leak olmaz. 
    finally:
        db.close()                  #3.iş bitince kapanır


from app.models.hotspot import Hotspot
from app.models.weather import WeatherData
from app.models.prediction import Prediction
from app.models.fire_cluster import FireCluster
from app.models.alert import Alert
from app.models.nasa_fetch_run import NasaFetchRun

Base.metadata.create_all(bind=engine)


def ensure_runtime_schema():
    """create_all yeni kolon eklemez; yerel Postgres şemasını ileri uyumlu tut."""
    hotspot_columns = {
        "bright_ti5": "DOUBLE PRECISION",
        "frp": "DOUBLE PRECISION",
        "scan": "DOUBLE PRECISION",
        "track": "DOUBLE PRECISION",
        "daynight": "VARCHAR(20)",
        "instrument": "VARCHAR(50)",
        "firms_source": "VARCHAR(100)",
        "type": "DOUBLE PRECISION",
        "version": "DOUBLE PRECISION",
        "cluster_id": "INTEGER",
    }
    alert_columns = {
        "cluster_id": "INTEGER",
        "updated_at": "TIMESTAMP",
        "resolved_at": "TIMESTAMP",
    }
    prediction_columns = {
        "decision_level": "INTEGER",
        "decision_name": "VARCHAR(100)",
    }
    weather_columns = {
        "wind_deg": "DOUBLE PRECISION",
    }

    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(hashtext('fire_detection_runtime_schema'))"))

        for column, column_type in hotspot_columns.items():
            connection.execute(
                text(f'ALTER TABLE hotspots ADD COLUMN IF NOT EXISTS "{column}" {column_type}')
            )
        for column, column_type in alert_columns.items():
            connection.execute(
                text(f'ALTER TABLE alerts ADD COLUMN IF NOT EXISTS "{column}" {column_type}')
            )
        for column, column_type in prediction_columns.items():
            connection.execute(
                text(f'ALTER TABLE predictions ADD COLUMN IF NOT EXISTS "{column}" {column_type}')
            )
        for column, column_type in weather_columns.items():
            connection.execute(
                text(f'ALTER TABLE weather_data ADD COLUMN IF NOT EXISTS "{column}" {column_type}')
            )

        logger.info("Runtime schema compatibility columns checked.")

        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS fire_clusters (
                    id SERIAL PRIMARY KEY,
                    center_latitude DOUBLE PRECISION NOT NULL,
                    center_longitude DOUBLE PRECISION NOT NULL,
                    first_seen_at TIMESTAMP NOT NULL,
                    last_seen_at TIMESTAMP NOT NULL,
                    hotspot_count INTEGER DEFAULT 0,
                    max_fire_probability DOUBLE PRECISION,
                    max_risk_level VARCHAR(20),
                    sources JSON DEFAULT '[]'::json,
                    satellites JSON DEFAULT '[]'::json,
                    status VARCHAR(20) DEFAULT 'active',
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
                """
            )
        )

        connection.execute(
            text('CREATE INDEX IF NOT EXISTS ix_alerts_status_created_at ON alerts (status, created_at DESC)')
        )
        connection.execute(
            text('CREATE INDEX IF NOT EXISTS ix_hotspots_cluster_id ON hotspots (cluster_id)')
        )
        connection.execute(
            text('CREATE INDEX IF NOT EXISTS ix_alerts_cluster_status ON alerts (cluster_id, status)')
        )
        connection.execute(
            text("DROP INDEX IF EXISTS ux_alerts_one_active_per_cluster")
        )
        connection.execute(
            text('CREATE INDEX IF NOT EXISTS ix_fire_clusters_status_last_seen ON fire_clusters (status, last_seen_at DESC)')
        )
        connection.execute(
            text('CREATE INDEX IF NOT EXISTS ix_fire_clusters_status ON fire_clusters (status)')
        )
        connection.execute(
            text('CREATE INDEX IF NOT EXISTS ix_fire_clusters_last_seen_at ON fire_clusters (last_seen_at DESC)')
        )
        connection.execute(
            text('CREATE INDEX IF NOT EXISTS ix_fire_clusters_max_risk_level ON fire_clusters (max_risk_level)')
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS scheduler_state (
                    key VARCHAR(100) PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS nasa_fetch_runs (
                    id SERIAL PRIMARY KEY,
                    started_at TIMESTAMP NOT NULL,
                    finished_at TIMESTAMP NOT NULL,
                    duration_seconds DOUBLE PRECISION,
                    status VARCHAR(20) NOT NULL,
                    received_count INTEGER DEFAULT 0,
                    inserted_count INTEGER DEFAULT 0,
                    duplicate_count INTEGER DEFAULT 0,
                    source_error_count INTEGER DEFAULT 0,
                    row_error_count INTEGER DEFAULT 0,
                    v3_prediction_count INTEGER DEFAULT 0,
                    prediction_limit_per_fetch INTEGER,
                    prediction_limit_applied BOOLEAN DEFAULT FALSE,
                    prediction_limit_note TEXT,
                    received_by_source JSON DEFAULT '{}'::json,
                    inserted_by_source JSON DEFAULT '{}'::json,
                    duplicates_by_source JSON DEFAULT '{}'::json,
                    row_errors_by_source JSON DEFAULT '{}'::json,
                    predictions_by_source JSON DEFAULT '{}'::json,
                    source_errors JSON DEFAULT '[]'::json,
                    weather_timeout_count INTEGER DEFAULT 0,
                    weather_fallback_count INTEGER DEFAULT 0,
                    weather_error_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text('CREATE INDEX IF NOT EXISTS ix_nasa_fetch_runs_finished_at ON nasa_fetch_runs (finished_at DESC)')
        )
        connection.execute(
            text('CREATE INDEX IF NOT EXISTS ix_nasa_fetch_runs_status ON nasa_fetch_runs (status)')
        )
        connection.execute(
            text('CREATE INDEX IF NOT EXISTS ix_alerts_hotspot_status ON alerts (hotspot_id, status)')
        )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_alerts_one_active_per_hotspot "
                "ON alerts (hotspot_id) WHERE status = 'ACTIVE' AND hotspot_id IS NOT NULL"
            )
        )
        connection.execute(
            text('CREATE INDEX IF NOT EXISTS ix_predictions_hotspot_id_id ON predictions (hotspot_id, id DESC)')
        )
        connection.execute(
            text("DROP INDEX IF EXISTS ix_hotspots_firms_observation")
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_hotspots_firms_observation "
                "ON hotspots (latitude, longitude, acq_date, acq_time, satellite, instrument, firms_source)"
            )
        )

        unique_index_exists = connection.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_indexes
                    WHERE tablename = 'hotspots'
                      AND indexname = 'ux_hotspots_firms_observation'
                )
                """
            )
        ).scalar()

        duplicate_observation_exists = connection.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM (
                        SELECT latitude, longitude, acq_date, acq_time, satellite, instrument, firms_source
                        FROM hotspots
                        WHERE acq_date IS NOT NULL
                          AND acq_time IS NOT NULL
                          AND satellite IS NOT NULL
                          AND instrument IS NOT NULL
                          AND firms_source IS NOT NULL
                        GROUP BY latitude, longitude, acq_date, acq_time, satellite, instrument, firms_source
                        HAVING COUNT(*) > 1
                        LIMIT 1
                    ) duplicates
                )
                """
            )
        ).scalar()

        if duplicate_observation_exists and not unique_index_exists:
            logger.warning(
                "Hotspot FIRMS unique index oluşturulmadı; mevcut duplicate gözlem kayıtları var."
            )

        connection.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM (
                            SELECT latitude, longitude, acq_date, acq_time, satellite, instrument, firms_source
                            FROM hotspots
                            WHERE acq_date IS NOT NULL
                              AND acq_time IS NOT NULL
                              AND satellite IS NOT NULL
                              AND instrument IS NOT NULL
                              AND firms_source IS NOT NULL
                            GROUP BY latitude, longitude, acq_date, acq_time, satellite, instrument, firms_source
                            HAVING COUNT(*) > 1
                            LIMIT 1
                        ) duplicates
                    )
                    THEN
                        DROP INDEX IF EXISTS ux_hotspots_firms_observation;
                        CREATE UNIQUE INDEX ux_hotspots_firms_observation
                        ON hotspots (latitude, longitude, acq_date, acq_time, satellite, instrument, firms_source)
                        WHERE acq_date IS NOT NULL
                          AND acq_time IS NOT NULL
                          AND satellite IS NOT NULL
                          AND instrument IS NOT NULL
                          AND firms_source IS NOT NULL;
                    END IF;
                END $$;
                """
            )
        )


ensure_runtime_schema()
