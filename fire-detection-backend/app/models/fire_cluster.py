from sqlalchemy import Column, DateTime, Float, Integer, JSON, String

from app.core.time_utils import utc_now_naive
from app.models.base import Base


class FireCluster(Base):
    __tablename__ = "fire_clusters"

    id = Column(Integer, primary_key=True, index=True)
    center_latitude = Column(Float, nullable=False)
    center_longitude = Column(Float, nullable=False)
    first_seen_at = Column(DateTime, nullable=False)
    last_seen_at = Column(DateTime, nullable=False)
    hotspot_count = Column(Integer, default=0)
    max_fire_probability = Column(Float)
    max_risk_level = Column(String(20))
    sources = Column(JSON, default=list)
    satellites = Column(JSON, default=list)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)
