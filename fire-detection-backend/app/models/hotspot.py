from sqlalchemy import Column, Integer, Float, String, Date, ForeignKey
from app.models.base import Base


class Hotspot(Base):
    __tablename__ = "hotspots"

    id = Column(Integer, primary_key=True, index=True)
    cluster_id = Column(Integer, ForeignKey("fire_clusters.id"), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    brightness = Column(Float)
    bright_ti5 = Column(Float)
    frp = Column(Float)
    scan = Column(Float)
    track = Column(Float)
    confidence = Column(String(50))
    daynight = Column(String(20))
    satellite = Column(String(50))
    instrument = Column(String(50))
    firms_source = Column(String(100))
    type = Column(Float)
    version = Column(Float)
    acq_date = Column(Date)
    acq_time = Column(String(50))
    city = Column(String(100))
