from pydantic import BaseModel
from datetime import date
from typing import Optional


class HotspotResponse(BaseModel):
    id: int
    latitude: float
    longitude: float
    brightness: Optional[float] = None
    confidence: Optional[str] = None
    satellite: Optional[str] = None
    acq_date: Optional[date] = None

    class Config:
        from_attributes = True
