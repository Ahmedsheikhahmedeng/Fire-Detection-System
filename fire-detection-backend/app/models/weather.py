from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime
from app.core.time_utils import utc_now_naive
from app.models.base import Base


class WeatherData(Base):
    __tablename__ = "weather_data"

    id = Column(Integer, primary_key=True, index=True)
    hotspot_id = Column(Integer, ForeignKey("hotspots.id"))
    temperature = Column(Float)
    humidity = Column(Float)
    wind_speed = Column(Float)
    wind_deg = Column(Float)
    pressure = Column(Float)
    rain_1h = Column(Float, default=0)
    created_at = Column(DateTime, default=utc_now_naive)
