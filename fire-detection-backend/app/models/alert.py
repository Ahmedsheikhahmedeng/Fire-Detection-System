from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from app.core.time_utils import utc_now_naive
from app.models.base import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    hotspot_id = Column(Integer, ForeignKey("hotspots.id"))
    cluster_id = Column(Integer, ForeignKey("fire_clusters.id"), nullable=True)
    risk_level = Column(String(20))
    message = Column(String(255))
    status = Column(String(20), default="ACTIVE")
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)
    resolved_at = Column(DateTime)
