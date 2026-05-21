from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PredictionCreate(BaseModel):
    latitude: float
    longitude: float
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None

class PredictionResponse(PredictionCreate):
    id: int
    prediction_result: float
    predicted_at: datetime
    
    class Config:
        from_attributes = True
