from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.core.config import settings
from app.models.alert import Alert
from app.services.telegram_service import RISK_ORDER

logger = logging.getLogger("fire_detection.twilio_sms")


class TwilioSmsAlertService:
    def has_twilio_credentials(self) -> bool:
        return bool(
            settings.TWILIO_ACCOUNT_SID.strip()
            and settings.TWILIO_AUTH_TOKEN.strip()
            and settings.TWILIO_SMS_FROM.strip()
            and settings.ALERT_SMS_TO.strip()
        )

    def is_configured(self) -> bool:
        return bool(settings.TWILIO_ENABLE_SMS and self.has_twilio_credentials())

    def should_send_for_risk(self, risk_level: str) -> bool:
        normalized_risk = (risk_level or "").strip().upper()
        min_level = (settings.ALERT_MIN_RISK_LEVEL or "HIGH").strip().upper()
        return RISK_ORDER.get(normalized_risk, -1) >= RISK_ORDER.get(min_level, 3)

    def get_twilio_client(self):
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            raise ValueError("Twilio SID veya Auth Token eksik")

        from twilio.rest import Client

        return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    def send_sms(self, message: str) -> Optional[str]:
        if not self.is_configured():
            logger.info("Twilio SMS ayarlari eksik veya kapali oldugu icin bildirim atlandi.")
            return None

        client = self.get_twilio_client()
        sms = client.messages.create(
            body=message,
            from_=settings.TWILIO_SMS_FROM,
            to=settings.ALERT_SMS_TO,
        )

        logger.info("SMS gonderildi: %s", sms.sid)
        return sms.sid

    def build_fire_message(
        self,
        risk_level: str,
        probability: float,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        city: Optional[str] = None,
        hotspot_id: Optional[int] = None,
    ) -> str:
        probability_percent = round(probability * 100, 2)
        return (
            "[YanginIzle]\n"
            "YANGIN ALARMI\n"
            f"Risk: {risk_level}\n"
            f"Olasilik: %{probability_percent}\n"
            f"Bolge: {city or 'Bilinmeyen bolge'}\n"
            f"Konum: {latitude}, {longitude}"
        )

    def send_fire_sms_alert(
        self,
        risk_level: str,
        probability: float,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        city: Optional[str] = None,
        hotspot_id: Optional[int] = None,
    ) -> Optional[str]:
        if not self.should_send_for_risk(risk_level):
            return None

        return self.send_sms(
            self.build_fire_message(
                risk_level=risk_level,
                probability=probability,
                latitude=latitude,
                longitude=longitude,
                city=city,
                hotspot_id=hotspot_id,
            )
        )

    def send_alert(
        self,
        alert: Alert,
        prediction: Dict[str, Any],
        hotspot: Any = None,
    ) -> bool:
        probabilities = prediction.get("probabilities", {})
        probability = float(probabilities.get("ensemble_fire_probability") or 0)

        try:
            sid = self.send_fire_sms_alert(
                risk_level=alert.risk_level or "",
                probability=probability,
                latitude=getattr(hotspot, "latitude", None),
                longitude=getattr(hotspot, "longitude", None),
                city=getattr(hotspot, "city", None),
                hotspot_id=alert.hotspot_id,
            )
        except Exception:
            logger.exception("Twilio SMS mesaji gonderilemedi.")
            return False

        return bool(sid)


twilio_sms_alert_service = TwilioSmsAlertService()


def get_twilio_client():
    return twilio_sms_alert_service.get_twilio_client()


def send_sms_alert(message: str):
    return twilio_sms_alert_service.send_sms(message)


def send_fire_sms_alert(
    risk_level: str,
    probability: float,
    latitude: float,
    longitude: float,
    city: str | None = None,
):
    return twilio_sms_alert_service.send_fire_sms_alert(
        risk_level=risk_level,
        probability=probability,
        latitude=latitude,
        longitude=longitude,
        city=city,
    )
