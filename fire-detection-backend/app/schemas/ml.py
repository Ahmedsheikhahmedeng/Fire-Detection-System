from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class EngineeredPredictionRequest(BaseModel):
    features: Dict[str, Any] = Field(
        ...,
        description="Modelin beklediği engineered feature dictionary",
    )


class RawHotspotPredictionRequest(BaseModel):
    id: Optional[Union[int, str]] = None
    hotspot_id: Optional[Union[int, str]] = None

    latitude: float
    longitude: float
    acq_date: str
    acq_time: Union[str, int]

    frp: Optional[float] = None
    brightness: Optional[float] = None
    bright_ti4: Optional[float] = None
    bright_ti5: Optional[float] = None
    scan: Optional[float] = None
    track: Optional[float] = None

    confidence: Optional[str] = None
    daynight: Optional[str] = None
    satellite: Optional[str] = None
    instrument: Optional[str] = None
    firms_source: Optional[str] = None
    type: Optional[float] = None
    version: Optional[float] = None
    history_hotspots: Optional[List[Dict[str, Any]]] = None


class PredictionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    success: bool
    model_version: Optional[str] = None
    probabilities: Optional[Dict[str, float]] = None
    decision: Optional[Dict[str, Any]] = None
    validation: Optional[Dict[str, Any]] = None
    feature_status: Optional[Dict[str, Any]] = None
    context_status: Optional[Dict[str, Any]] = None
    saved_prediction_id: Optional[int] = None
    created_alert_id: Optional[int] = None
    websocket_broadcast_queued: Optional[bool] = None
    websocket_broadcast_sent: Optional[bool] = None
    error: Optional[str] = None
