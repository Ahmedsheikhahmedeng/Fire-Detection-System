from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.services.cluster_service import cluster_service
from app.services.alert_service import alert_service
from app.services.ml_service import predict_raw_hotspot

logger = logging.getLogger("fire_detection.prediction")


class PredictionService:
    """
    Hotspot için DB'den geçmiş hotspot context çıkarır, V3 prediction üretir
    ve sonucu mevcut predictions tablosuna kaydeder.
    """

    def build_history_hotspots(
        self,
        db: Session,
        current_hotspot: Dict[str, Any],
        max_hours: int = 72,
    ) -> List[Dict[str, Any]]:
        try:
            from app.models.hotspot import Hotspot
        except Exception:
            logger.exception("Hotspot modeli import edilemedi; history context boş dönecek.")
            return []

        current_time = self._parse_datetime(current_hotspot)
        start_time = current_time - timedelta(hours=max_hours)

        lat = float(current_hotspot["latitude"])
        lon = float(current_hotspot["longitude"])

        lat_min = lat - 0.15
        lat_max = lat + 0.15
        lon_min = lon - 0.15
        lon_max = lon + 0.15

        query = (
            db.query(Hotspot)
            .filter(Hotspot.latitude >= lat_min)
            .filter(Hotspot.latitude <= lat_max)
            .filter(Hotspot.longitude >= lon_min)
            .filter(Hotspot.longitude <= lon_max)
        )

        if hasattr(Hotspot, "acq_date"):
            query = query.filter(Hotspot.acq_date >= start_time.date())
            query = query.filter(Hotspot.acq_date <= current_time.date())

        rows = query.all()

        history = []
        current_id = current_hotspot.get("hotspot_id") or current_hotspot.get("id")

        for hotspot in rows:
            if current_id is not None and str(getattr(hotspot, "id", "")) == str(current_id):
                continue

            hotspot_time = self._parse_hotspot_row_datetime(hotspot)
            if hotspot_time is None or not (start_time <= hotspot_time <= current_time):
                continue

            history.append({
                "hotspot_id": str(getattr(hotspot, "id", "")),
                "latitude": float(getattr(hotspot, "latitude")),
                "longitude": float(getattr(hotspot, "longitude")),
                "hotspot_datetime": hotspot_time.isoformat(),
                "frp": float(getattr(hotspot, "frp", 0) or 0),
            })

        return history

    def predict_hotspot_with_db_context(
        self,
        db: Session,
        hotspot_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        history_hotspots = self.build_history_hotspots(
            db=db,
            current_hotspot=hotspot_payload,
            max_hours=72,
        )

        enriched_payload = dict(hotspot_payload)
        enriched_payload["history_hotspots"] = history_hotspots

        prediction = predict_raw_hotspot(enriched_payload)

        if prediction.get("success"):
            prediction["context_status"] = {
                "history_hotspot_count": len(history_hotspots),
                "history_window_hours": 72,
                "history_source": "database",
            }

            hotspot_id = self._normalize_hotspot_id(
                hotspot_payload.get("id") or hotspot_payload.get("hotspot_id")
            )
            saved_prediction = self.save_prediction(
                db=db,
                hotspot_id=hotspot_id,
                prediction=prediction,
            )

            if saved_prediction:
                prediction["saved_prediction_id"] = saved_prediction.id

            self.save_weather_snapshot(
                db=db,
                hotspot_id=hotspot_id,
                prediction=prediction,
            )
            cluster = cluster_service.update_cluster_from_prediction(
                db=db,
                hotspot_id=hotspot_id,
                prediction=prediction,
            )
            if cluster:
                prediction["cluster_id"] = cluster.id

            created_alert = alert_service.create_alert_from_prediction(
                db=db,
                prediction=prediction,
                hotspot_id=hotspot_id,
                saved_prediction_id=saved_prediction.id if saved_prediction else None,
            )

            if created_alert:
                prediction["created_alert_id"] = created_alert.id
            else:
                prediction["created_alert_id"] = None

        return prediction

    def save_weather_snapshot(
        self,
        db: Session,
        hotspot_id: Optional[int],
        prediction: Dict[str, Any],
    ):
        if hotspot_id is None:
            return None

        weather_features = prediction.get("feature_status", {}).get("weather", {})
        if not weather_features or not weather_features.get("weather_fetch_ok"):
            return None

        try:
            from app.models.weather import WeatherData
        except Exception:
            logger.exception("WeatherData modeli import edilemedi; weather snapshot kaydedilmeyecek.")
            return None

        row = WeatherData(
            hotspot_id=hotspot_id,
            temperature=weather_features.get("temp_mean_24h"),
            humidity=weather_features.get("rh_mean_24h"),
            wind_speed=weather_features.get("wind_mean_24h"),
            pressure=None,
            rain_1h=weather_features.get("precip_sum_24h") or 0,
        )

        db.add(row)
        db.commit()
        db.refresh(row)

        return row

    def save_prediction(
        self,
        db: Session,
        hotspot_id: Optional[int],
        prediction: Dict[str, Any],
    ):
        try:
            from app.models.prediction import Prediction
        except Exception:
            logger.exception("Prediction modeli import edilemedi; prediction kaydı oluşturulamayacak.")
            return None

        probabilities = prediction.get("probabilities", {})
        decision = prediction.get("decision", {})
        decision_level = int(decision.get("decision_level", 0) or 0)
        decision_name = decision.get("decision_name")

        row = Prediction(
            hotspot_id=hotspot_id,
            fire_probability=probabilities.get("ensemble_fire_probability"),
            risk_level=self._risk_level_from_decision(decision_level),
            decision_level=decision_level,
            decision_name=decision_name,
            model_version=prediction.get("model_version", "v3"),
        )

        db.add(row)
        db.commit()
        db.refresh(row)

        return row

    def _risk_level_from_decision(self, decision_level: int) -> str:
        if decision_level >= 4:
            return "CRITICAL"
        if decision_level == 3:
            return "HIGH"
        if decision_level == 2:
            return "MEDIUM"
        if decision_level == 1:
            return "WATCH"
        return "LOW"

    def _normalize_hotspot_id(self, value: Any) -> Optional[int]:
        if value is None:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            logger.warning("Geçersiz hotspot_id değeri: %r", value)
            return None

    def _parse_datetime(self, hotspot: Dict[str, Any]) -> datetime:
        if hotspot.get("hotspot_datetime"):
            value = hotspot["hotspot_datetime"]
            if isinstance(value, datetime):
                return value.replace(tzinfo=None)

            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)

        acq_date = hotspot.get("acq_date")
        acq_time = str(hotspot.get("acq_time")).replace(".0", "").zfill(4)

        return datetime.strptime(f"{acq_date} {acq_time}", "%Y-%m-%d %H%M")

    def _parse_hotspot_row_datetime(self, hotspot: Any) -> Optional[datetime]:
        acq_datetime = getattr(hotspot, "acq_datetime", None)
        if acq_datetime is not None:
            if isinstance(acq_datetime, datetime):
                return acq_datetime.replace(tzinfo=None)
            return datetime.fromisoformat(str(acq_datetime).replace("Z", "+00:00")).replace(tzinfo=None)

        acq_date = getattr(hotspot, "acq_date", None)
        acq_time = getattr(hotspot, "acq_time", None)
        if acq_date is None or acq_time is None:
            return None

        acq_time_str = str(acq_time).replace(".0", "").zfill(4)
        return datetime.strptime(f"{acq_date} {acq_time_str}", "%Y-%m-%d %H%M")


prediction_service = PredictionService()
