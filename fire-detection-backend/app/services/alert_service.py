from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.time_utils import utc_now_naive
from app.models.prediction import Prediction
from app.models.alert import Alert
from app.models.hotspot import Hotspot
from app.services.notification_manager import notification_manager
from app.websocket.manager import manager

logger = logging.getLogger("fire_detection.alerts")

ALERT_RISK_ORDER = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}


class AlertService:
    """
    V3 prediction sonucuna göre alert oluşturur.

    decision_level:
      0 = no alert
      1 = watch only
      2 = MEDIUM
      3 = HIGH
      4 = CRITICAL
    """

    def should_create_alert(self, prediction: Dict[str, Any]) -> bool:
        decision = prediction.get("decision", {})
        decision_level = int(decision.get("decision_level", 0) or 0)
        return decision_level >= 2

    def map_decision_to_alert_level(self, decision_level: int) -> str:
        if decision_level >= 4:
            return "CRITICAL"
        if decision_level == 3:
            return "HIGH"
        if decision_level == 2:
            return "MEDIUM"
        return "LOW"

    def build_alert_message(self, prediction: Dict[str, Any]) -> str:
        decision = prediction.get("decision", {})
        probabilities = prediction.get("probabilities", {})

        decision_name = decision.get("decision_name", "unknown")
        ensemble_prob = probabilities.get("ensemble_fire_probability", 0) or 0

        return (
            f"V3 fire alert: {decision_name} "
            f"(ensemble_probability={ensemble_prob:.3f})"
        )

    def build_websocket_payload(
        self,
        alert: Alert,
        prediction: Dict[str, Any],
        saved_prediction_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        decision = prediction.get("decision", {})
        probabilities = prediction.get("probabilities", {})

        return {
            "type": "NEW_FIRE_ALERT",
            "alert_id": alert.id,
            "prediction_id": saved_prediction_id,
            "hotspot_id": alert.hotspot_id,
            "cluster_id": getattr(alert, "cluster_id", None),
            "risk_level": alert.risk_level,
            "message": alert.message,
            "status": alert.status,
            "model_version": prediction.get("model_version", "v3"),
            "decision_level": decision.get("decision_level"),
            "decision_name": decision.get("decision_name"),
            "ensemble_fire_probability": probabilities.get("ensemble_fire_probability"),
            "lightgbm_probability": probabilities.get("lightgbm_probability"),
            "catboost_probability": probabilities.get("catboost_probability"),
            "rf_fire_probability": probabilities.get("rf_fire_probability"),
            "extratrees_fire_probability": probabilities.get("extratrees_fire_probability"),
        }

    def broadcast_alert(
        self,
        alert: Alert,
        prediction: Dict[str, Any],
        saved_prediction_id: Optional[int] = None,
    ) -> None:
        payload = self.build_websocket_payload(
            alert=alert,
            prediction=prediction,
            saved_prediction_id=saved_prediction_id,
        )
        manager.broadcast_threadsafe(payload)

    def get_active_alert_for_hotspot(
        self,
        db: Session,
        hotspot_id: Optional[int],
    ) -> Optional[Alert]:
        if hotspot_id is None:
            return None

        return (
            db.query(Alert)
            .filter(Alert.hotspot_id == hotspot_id, Alert.status == "ACTIVE")
            .order_by(Alert.created_at.desc(), Alert.id.desc())
            .first()
        )

    def get_active_alert_for_cluster(
        self,
        db: Session,
        cluster_id: Optional[int],
    ) -> Optional[Alert]:
        if cluster_id is None:
            return None

        return (
            db.query(Alert)
            .filter(Alert.cluster_id == cluster_id, Alert.status == "ACTIVE")
            .order_by(Alert.created_at.desc(), Alert.id.desc())
            .first()
        )

    def get_hotspot_cluster_id(self, db: Session, hotspot_id: Optional[int]) -> Optional[int]:
        if hotspot_id is None:
            return None
        hotspot = db.query(Hotspot).filter(Hotspot.id == hotspot_id).first()
        return getattr(hotspot, "cluster_id", None) if hotspot else None

    def maybe_escalate_cluster_alert(
        self,
        db: Session,
        alert: Alert,
        alert_level: str,
        message: str,
        hotspot_id: Optional[int],
    ) -> Alert:
        existing_rank = ALERT_RISK_ORDER.get(str(alert.risk_level or "LOW").upper(), 0)
        next_rank = ALERT_RISK_ORDER.get(alert_level, 0)
        if next_rank > existing_rank:
            alert.risk_level = alert_level
            alert.message = message
            alert.hotspot_id = hotspot_id
            alert.updated_at = utc_now_naive()
            db.commit()
            db.refresh(alert)
        return alert

    def create_alert_from_prediction(
        self,
        db: Session,
        prediction: Dict[str, Any],
        hotspot_id: Optional[int] = None,
        saved_prediction_id: Optional[int] = None,
        broadcast: bool = True,
    ):
        if not self.should_create_alert(prediction):
            return None

        if hotspot_id is None:
            return None

        decision = prediction.get("decision", {})
        probabilities = prediction.get("probabilities", {})

        decision_level = int(decision.get("decision_level", 0) or 0)
        alert_level = self.map_decision_to_alert_level(decision_level)
        message = self.build_alert_message(prediction)

        cluster_id = self.get_hotspot_cluster_id(db, hotspot_id)
        existing_cluster_alert = self.get_active_alert_for_cluster(db, cluster_id)
        if existing_cluster_alert:
            return self.maybe_escalate_cluster_alert(
                db=db,
                alert=existing_cluster_alert,
                alert_level=alert_level,
                message=message,
                hotspot_id=hotspot_id,
            )

        existing = self.get_active_alert_for_hotspot(db, hotspot_id)
        if existing:
            return existing

        row_kwargs = {}
        alert_columns = Alert.__table__.columns.keys()

        if "hotspot_id" in alert_columns:
            row_kwargs["hotspot_id"] = hotspot_id

        if "cluster_id" in alert_columns:
            row_kwargs["cluster_id"] = cluster_id

        if "prediction_id" in alert_columns:
            row_kwargs["prediction_id"] = saved_prediction_id

        if "alert_level" in alert_columns:
            row_kwargs["alert_level"] = alert_level

        if "level" in alert_columns:
            row_kwargs["level"] = alert_level

        if "risk_level" in alert_columns:
            row_kwargs["risk_level"] = alert_level

        if "status" in alert_columns:
            row_kwargs["status"] = "ACTIVE"

        if "alert_status" in alert_columns:
            row_kwargs["alert_status"] = "ACTIVE"

        if "message" in alert_columns:
            row_kwargs["message"] = message

        if "description" in alert_columns:
            row_kwargs["description"] = message

        if "fire_probability" in alert_columns:
            row_kwargs["fire_probability"] = probabilities.get("ensemble_fire_probability")

        if "probability" in alert_columns:
            row_kwargs["probability"] = probabilities.get("ensemble_fire_probability")

        if "model_version" in alert_columns:
            row_kwargs["model_version"] = prediction.get("model_version", "v3")

        if "decision_level" in alert_columns:
            row_kwargs["decision_level"] = decision_level

        if "decision_name" in alert_columns:
            row_kwargs["decision_name"] = decision.get("decision_name")

        row = Alert(**row_kwargs)

        db.add(row)
        try:
            db.commit()
            db.refresh(row)
        except IntegrityError:
            db.rollback()
            existing_cluster_alert = self.get_active_alert_for_cluster(db, cluster_id)
            if existing_cluster_alert:
                return existing_cluster_alert
            existing = self.get_active_alert_for_hotspot(db, hotspot_id)
            if existing:
                return existing
            raise
        except Exception:
            db.rollback()
            logger.exception("Alert oluşturulamadı | hotspot_id=%s", hotspot_id)
            raise

        if broadcast:
            self.broadcast_alert(
                alert=row,
                prediction=prediction,
                saved_prediction_id=saved_prediction_id,
            )

        notification_results = notification_manager.send_alert(
            alert=row,
            prediction=prediction,
        )
        logger.info(
            "Alert notification results | alert_id=%s risk_level=%s results=%s",
            row.id,
            row.risk_level,
            notification_results,
        )

        return row

    def update_alert_status(
        self,
        db: Session,
        alert_id: int,
        status: str,
    ) -> Optional[Alert]:
        normalized_status = status.strip().upper()
        allowed_statuses = {"ACTIVE", "ACKNOWLEDGED", "RESOLVED", "CLOSED"}

        if normalized_status not in allowed_statuses:
            raise ValueError(f"Invalid alert status: {status}")

        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return None

        alert.status = normalized_status
        alert.updated_at = utc_now_naive()
        if normalized_status in {"RESOLVED", "CLOSED"}:
            alert.resolved_at = utc_now_naive()

        db.commit()
        db.refresh(alert)
        return alert

    def close_alert(self, db: Session, alert_id: int) -> Optional[Alert]:
        return self.update_alert_status(db=db, alert_id=alert_id, status="CLOSED")


alert_service = AlertService()


def create_alert_for_hotspot(hotspot_id: int, db: Session, broadcast: bool = True):
    prediction = (
        db.query(Prediction)
        .filter(Prediction.hotspot_id == hotspot_id)
        .order_by(Prediction.created_at.desc())
        .first()
    )

    if not prediction:
        return None

    risk_to_decision_level = {
        "LOW": 0,
        "MEDIUM": 2,
        "HIGH": 3,
        "CRITICAL": 4,
    }
    decision_level = risk_to_decision_level.get((prediction.risk_level or "").upper(), 0)
    if decision_level < 2:
        return {"message": "No alert needed"}

    prediction_payload = {
        "model_version": prediction.model_version or "v3",
        "probabilities": {
            "ensemble_fire_probability": prediction.fire_probability or 0,
        },
        "decision": {
            "decision_level": decision_level,
            "decision_name": {
                2: "high_confidence_balanced_fire",
                3: "strict_fire_alert",
                4: "very_strict_fire_alert",
            }.get(decision_level, "low_risk_no_fire"),
        },
    }

    return alert_service.create_alert_from_prediction(
        db=db,
        prediction=prediction_payload,
        hotspot_id=hotspot_id,
        saved_prediction_id=prediction.id,
        broadcast=broadcast,
    )
