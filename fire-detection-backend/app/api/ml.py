from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_api_key
from app.schemas.ml import (
    EngineeredPredictionRequest,
    PredictionResponse,
    RawHotspotPredictionRequest,
)
from app.services.ml_service import (
    predict_engineered,
    predict_raw_hotspot,
    validate_engineered_features,
    v3_fire_model_service,
)
from app.services.prediction_service import prediction_service

router = APIRouter(prefix="/ml", tags=["Machine Learning"])


@router.get("/status")
def ml_status():
    """
    ML servisinin yüklü olup olmadığını kontrol eder.
    """
    if not v3_fire_model_service.is_loaded:
        v3_fire_model_service.load()

    return {
        "success": True,
        "model_version": "v3",
        "is_loaded": v3_fire_model_service.is_loaded,
        "hgb_core_feature_count": len(v3_fire_model_service.hgb_core_features),
        "full_feature_count": len(v3_fire_model_service.full_features),
        "available_models": list(v3_fire_model_service.models.keys()),
        "threshold_config": v3_fire_model_service.threshold_config,
    }


@router.post("/validate-engineered")
def validate_engineered(
    payload: EngineeredPredictionRequest,
    _: bool = Depends(verify_api_key),
):
    """
    Gönderilen engineered feature seti model için uygun mu kontrol eder.
    Prediction yapmaz.
    """
    try:
        validation = validate_engineered_features(payload.features)
        return {
            "success": True,
            "validation": validation,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Feature validation failed: {str(e)}",
        )


@router.post("/predict-engineered", response_model=PredictionResponse)
def predict_engineered_endpoint(
    payload: EngineeredPredictionRequest,
    _: bool = Depends(verify_api_key),
):
    """
    Hazır engineered feature input ile V3 model tahmini yapar.

    Not:
    Bu endpoint ham FIRMS hotspot için değildir.
    Bu endpoint 101 engineered feature bekler.
    """
    try:
        result = predict_engineered(payload.features)

        if not result.get("success", False):
            raise HTTPException(status_code=400, detail=result)

        return result

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}",
        )


@router.post("/predict-hotspot", response_model=PredictionResponse)
def predict_hotspot_endpoint(
    payload: RawHotspotPredictionRequest,
    _: bool = Depends(verify_api_key),
):
    """
    Ham FIRMS hotspot input ile V3 tahmin yapar.

    Not:
    Weather/FWI özellikleri otomatik çekilir.
    Spatial context için payload içindeki history_hotspots kullanılır;
    weather servisi hata verirse kontrollü fallback özellikleri kullanılır.
    """
    try:
        result = predict_raw_hotspot(payload.model_dump())

        if not result.get("success", False):
            raise HTTPException(status_code=400, detail=result)

        return result

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Raw hotspot prediction failed: {str(e)}",
        )


@router.post("/predict-hotspot-db-context", response_model=PredictionResponse)
def predict_hotspot_db_context_endpoint(
    payload: RawHotspotPredictionRequest,
    _: bool = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """
    Ham FIRMS hotspot input alır.
    Geçmiş hotspotları DB'den otomatik bulur.
    V3 prediction döndürür.
    decision_level >= 2 ise alert oluşur ve WebSocket broadcast yapılır.
    """
    try:
        result = prediction_service.predict_hotspot_with_db_context(
            db=db,
            hotspot_payload=payload.model_dump(),
        )

        if not result.get("success", False):
            raise HTTPException(status_code=400, detail=result)

        result["websocket_broadcast_sent"] = result.get("created_alert_id") is not None

        return result

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"DB-context hotspot prediction failed: {str(e)}",
        )
