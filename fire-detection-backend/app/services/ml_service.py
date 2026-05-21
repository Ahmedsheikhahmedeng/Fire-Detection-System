from pathlib import Path
from typing import Any, Dict, List

import logging
import math
from threading import Lock

import joblib
import pandas as pd

from app.core.config import settings
from app.core.json_loader import load_json_file

logger = logging.getLogger("fire_detection.ml")


class V3FireModelService:
    def __init__(self) -> None:
        self.model_dir = Path(settings.V3_MODEL_DIR)

        self.models: Dict[str, Any] = {}
        self.hgb_core_features: List[str] = []
        self.full_features: List[str] = []
        self.threshold_config: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}

        self.is_loaded = False
        self._load_lock = Lock()

    def load(self) -> None:
        if self.is_loaded:
            return

        with self._load_lock:
            if self.is_loaded:
                return

            if not settings.ENABLE_ML_PREDICTION:
                raise RuntimeError("ML prediction is disabled in settings.")

            if not self.model_dir.exists():
                raise FileNotFoundError(f"V3 model dir not found: {self.model_dir}")

            self.hgb_core_features = self._load_json(settings.V3_HGB_FEATURES)
            self.full_features = self._load_json(settings.V3_FULL_FEATURES)

            self.threshold_config = self._load_json(settings.V3_THRESHOLD_CONFIG)
            self.metadata = self._load_json(settings.V3_METADATA)

            self.models["hgb_core"] = joblib.load(self.model_dir / settings.V3_HGB_CORE_MODEL)
            self.models["xgboost"] = joblib.load(self.model_dir / settings.V3_XGBOOST_MODEL)
            self.models["lightgbm"] = joblib.load(self.model_dir / settings.V3_LIGHTGBM_MODEL)
            self.models["catboost"] = joblib.load(self.model_dir / settings.V3_CATBOOST_MODEL)
            self.models["rf"] = joblib.load(self.model_dir / settings.V3_RF_MODEL)
            self.models["extratrees"] = joblib.load(self.model_dir / settings.V3_EXTRATREES_MODEL)

            self.is_loaded = True

            logger.info(
                "V3 ML models loaded | HGB core features: %s | Full features: %s",
                len(self.hgb_core_features),
                len(self.full_features),
            )

    def _load_json(self, file_name: str) -> Any:
        path = self.model_dir / file_name

        if not path.exists():
            raise FileNotFoundError(f"JSON file not found: {path}")

        return load_json_file(path)

    def validate_engineered_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        required = sorted(set(self.hgb_core_features + self.full_features))

        missing = [c for c in required if c not in features]
        extra = [c for c in features.keys() if c not in required]

        return {
            "required_feature_count": len(required),
            "received_feature_count": len(features),
            "missing_features": missing,
            "extra_features": extra,
            "is_valid": len(missing) == 0,
        }

    def _prepare_dataframe(self, features: Dict[str, Any], feature_columns: List[str]) -> pd.DataFrame:
        missing = [c for c in feature_columns if c not in features]

        if missing:
            raise ValueError(f"Missing required features: {missing}")

        row = {c: features[c] for c in feature_columns}
        return pd.DataFrame([row], columns=feature_columns)

    def predict_engineered(self, features: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_loaded:
            self.load()

        validation = self.validate_engineered_features(features)

        if not validation["is_valid"]:
            return {
                "success": False,
                "error": "missing_required_features",
                "validation": validation,
            }

        x_hgb = self._prepare_dataframe(features, self.hgb_core_features)
        x_full = self._prepare_dataframe(features, self.full_features)

        hgb_prob = float(self.models["hgb_core"].predict_proba(x_hgb)[0, 1])
        xgb_prob = float(self.models["xgboost"].predict_proba(x_full)[0, 1])
        lgbm_prob = float(self.models["lightgbm"].predict_proba(x_full)[0, 1])
        cat_prob = float(self.models["catboost"].predict_proba(x_full)[0, 1])

        rf_prob = float(self.models["rf"].predict_proba(x_full)[0, 1])
        et_prob = float(self.models["extratrees"].predict_proba(x_full)[0, 1])

        ensemble_prob = float((hgb_prob + xgb_prob + lgbm_prob + cat_prob) / 4.0)

        decision = self._make_decision(
            ensemble_prob=ensemble_prob,
            lightgbm_prob=lgbm_prob,
            catboost_prob=cat_prob,
            xgboost_prob=xgb_prob,
            hgb_prob=hgb_prob,
            rf_prob=rf_prob,
            extratrees_prob=et_prob,
        )

        return {
            "success": True,
            "model_version": self.threshold_config.get("version", "v3"),
            "probabilities": {
                "ensemble_fire_probability": ensemble_prob,
                "hgb_core_probability": hgb_prob,
                "xgboost_probability": xgb_prob,
                "lightgbm_probability": lgbm_prob,
                "catboost_probability": cat_prob,
                "rf_fire_probability": rf_prob,
                "extratrees_fire_probability": et_prob,
            },
            "decision": decision,
            "validation": {
                "required_feature_count": validation["required_feature_count"],
                "received_feature_count": validation["received_feature_count"],
                "extra_feature_count": len(validation["extra_features"]),
            },
        }

    def _make_decision(
        self,
        ensemble_prob: float,
        lightgbm_prob: float,
        catboost_prob: float,
        xgboost_prob: float,
        hgb_prob: float,
        rf_prob: float,
        extratrees_prob: float,
    ) -> Dict[str, Any]:
        cfg = self.threshold_config

        lightgbm_watch = lightgbm_prob >= cfg["lightgbm_watch_threshold"]
        catboost_watch = catboost_prob >= cfg["catboost_watch_threshold"]
        xgboost_watch = xgboost_prob >= cfg["xgboost_watch_threshold"]
        hgb_watch = hgb_prob >= cfg["hgb_core_watch_threshold"]
        ensemble_watch = ensemble_prob >= cfg["ensemble_watch_threshold"]

        rf_balanced_gate = rf_prob >= cfg["rf_balanced_threshold"]
        rf_recall90_gate = rf_prob >= cfg.get("rf_recall90_threshold", cfg["rf_balanced_threshold"])

        extratrees_strict_gate = extratrees_prob >= cfg["extratrees_strict_threshold"]
        extratrees_recall90_gate = extratrees_prob >= cfg.get(
            "extratrees_recall90_threshold",
            cfg["extratrees_strict_threshold"],
        )

        watch_early_warning = bool(
            lightgbm_watch
            or catboost_watch
            or xgboost_watch
            or hgb_watch
            or ensemble_watch
        )

        if not watch_early_warning:
            decision_level = 0
            decision_name = cfg["decision_system"]["level_0"]
        elif extratrees_strict_gate and rf_balanced_gate:
            decision_level = 4
            decision_name = cfg["decision_system"]["level_4"]
        elif extratrees_strict_gate or extratrees_recall90_gate or rf_recall90_gate:
            decision_level = 3
            decision_name = cfg["decision_system"]["level_3"]
        elif rf_balanced_gate:
            decision_level = 2
            decision_name = cfg["decision_system"]["level_2"]
        else:
            decision_level = 1
            decision_name = cfg["decision_system"]["level_1"]

        return {
            "watch_early_warning": watch_early_warning,
            "lightgbm_watch": bool(lightgbm_watch),
            "catboost_watch": bool(catboost_watch),
            "xgboost_watch": bool(xgboost_watch),
            "hgb_core_watch": bool(hgb_watch),
            "ensemble_watch": bool(ensemble_watch),
            "rf_balanced_gate": bool(rf_balanced_gate),
            "rf_recall90_gate": bool(rf_recall90_gate),
            "extratrees_strict_gate": bool(extratrees_strict_gate),
            "extratrees_recall90_gate": bool(extratrees_recall90_gate),
            "decision_level": int(decision_level),
            "decision_name": decision_name,
        }


v3_fire_model_service = V3FireModelService()


def load_ml_model() -> None:
    """Backward-compatible loader for startup hooks."""
    v3_fire_model_service.load()


def predict_engineered(features: Dict[str, Any]) -> Dict[str, Any]:
    return v3_fire_model_service.predict_engineered(features)


def validate_engineered_features(features: Dict[str, Any]) -> Dict[str, Any]:
    if not v3_fire_model_service.is_loaded:
        v3_fire_model_service.load()
    return v3_fire_model_service.validate_engineered_features(features)


from app.services.feature_pipeline import v3_feature_pipeline


def predict_raw_hotspot(hotspot: Dict[str, Any]) -> Dict[str, Any]:
    if not settings.ENABLE_ML_PREDICTION:
        return predict_demo_hotspot(hotspot)

    features = v3_feature_pipeline.build_features_from_raw_hotspot(hotspot)
    feature_validation = v3_feature_pipeline.validate_output(features)

    if not feature_validation["is_valid"]:
        return {
            "success": False,
            "error": "feature_pipeline_failed",
            "feature_validation": feature_validation,
        }

    prediction = v3_fire_model_service.predict_engineered(features)

    if prediction.get("success"):
        prediction["feature_status"] = {
            "source": "raw_hotspot_feature_pipeline_v1",
            "note": (
                "Spatial context is computed from history_hotspots when provided. "
                "Weather/FWI features are fetched via weather_service; fallback is used only if weather fetch fails."
            ),
            "weather": {
                "weather_fetch_ok": features.get("weather_fetch_ok"),
                "weather_hours_24h": features.get("weather_hours_24h"),
                "weather_hours_3d": features.get("weather_hours_3d"),
                "weather_hours_7d": features.get("weather_hours_7d"),
                "weather_hour_count_7d": features.get("weather_hour_count_7d"),
                "temp_mean_24h": features.get("temp_mean_24h"),
                "rh_mean_24h": features.get("rh_mean_24h"),
                "wind_mean_24h": features.get("wind_mean_24h"),
                "precip_sum_24h": features.get("precip_sum_24h"),
            },
            "validation": feature_validation,
        }

    return prediction


def predict_demo_hotspot(hotspot: Dict[str, Any]) -> Dict[str, Any]:
    brightness = float(
        hotspot.get("brightness")
        or hotspot.get("bright_ti4")
        or hotspot.get("brightness_ti4")
        or 300
    )
    frp = float(hotspot.get("frp") or 0)
    confidence = str(hotspot.get("confidence") or "").lower()
    confidence_boost = 0.25 if confidence in {"h", "high"} else 0.1 if confidence in {"n", "nominal"} else 0

    raw_score = ((brightness - 315) / 12) + min(frp, 80) / 55 + confidence_boost
    probability = max(0.03, min(0.97, 1 / (1 + math.exp(-raw_score))))

    if probability >= 0.85:
        decision_level = 4
        decision_name = "very_strict_fire_alert"
    elif probability >= 0.70:
        decision_level = 3
        decision_name = "strict_fire_alert"
    elif probability >= 0.55:
        decision_level = 2
        decision_name = "high_confidence_balanced_fire"
    elif probability >= 0.35:
        decision_level = 1
        decision_name = "watch_early_warning"
    else:
        decision_level = 0
        decision_name = "low_risk_no_fire"

    return {
        "success": True,
        "model_version": "demo_auto_v1",
        "probabilities": {
            "ensemble_fire_probability": probability,
            "hgb_core_probability": probability,
            "xgboost_probability": probability,
            "lightgbm_probability": probability,
            "catboost_probability": probability,
            "rf_fire_probability": probability,
            "extratrees_fire_probability": probability,
        },
        "decision": {
            "watch_early_warning": decision_level >= 1,
            "lightgbm_watch": decision_level >= 1,
            "catboost_watch": decision_level >= 1,
            "xgboost_watch": decision_level >= 1,
            "hgb_core_watch": decision_level >= 1,
            "ensemble_watch": decision_level >= 1,
            "rf_balanced_gate": decision_level >= 2,
            "rf_recall90_gate": decision_level >= 3,
            "extratrees_strict_gate": decision_level >= 3,
            "extratrees_recall90_gate": decision_level >= 3,
            "decision_level": decision_level,
            "decision_name": decision_name,
        },
        "feature_status": {
            "source": "demo_auto_fallback",
            "note": "Real V3 ML loader is disabled; deterministic hotspot scoring is used for automatic demo flow.",
            "weather": {},
            "validation": {"is_valid": True},
        },
    }
