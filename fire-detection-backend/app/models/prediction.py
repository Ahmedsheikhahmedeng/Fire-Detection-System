from sqlalchemy import Column, Integer, Float, String, ForeignKey, DateTime
from app.core.time_utils import utc_now_naive
from app.models.base import Base

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    hotspot_id = Column(Integer, ForeignKey("hotspots.id"))
    fire_probability = Column(Float)
    risk_level = Column(String(20))
    decision_level = Column(Integer)
    decision_name = Column(String(100))
    model_version = Column(String(20), default="v1")
    created_at = Column(DateTime, default=utc_now_naive)
