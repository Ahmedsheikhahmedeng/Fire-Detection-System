from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String, Text

from app.core.time_utils import utc_now_naive
from app.models.base import Base


class NasaFetchRun(Base):
    __tablename__ = "nasa_fetch_runs"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=False)
    duration_seconds = Column(Float)
    status = Column(String(20), nullable=False)
    received_count = Column(Integer, default=0)
    inserted_count = Column(Integer, default=0)
    duplicate_count = Column(Integer, default=0)
    source_error_count = Column(Integer, default=0)
    row_error_count = Column(Integer, default=0)
    v3_prediction_count = Column(Integer, default=0)
    prediction_limit_per_fetch = Column(Integer)
    prediction_limit_applied = Column(Boolean, default=False)
    prediction_limit_note = Column(Text)
    received_by_source = Column(JSON, default=dict)
    inserted_by_source = Column(JSON, default=dict)
    duplicates_by_source = Column(JSON, default=dict)
    row_errors_by_source = Column(JSON, default=dict)
    predictions_by_source = Column(JSON, default=dict)
    source_errors = Column(JSON, default=list)
    weather_timeout_count = Column(Integer, default=0)
    weather_fallback_count = Column(Integer, default=0)
    weather_error_count = Column(Integer, default=0)
    error_message = Column(Text)
    created_at = Column(DateTime, default=utc_now_naive)
