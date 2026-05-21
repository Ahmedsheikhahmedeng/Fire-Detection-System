from __future__ import annotations

import logging
from typing import Any, Dict

import requests

from app.core.config import settings
from app.models.alert import Alert

logger = logging.getLogger("fire_detection.telegram")

RISK_ORDER = {
    "LOW": 0,
    "WATCH": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}


class TelegramAlertService:
    def is_configured(self) -> bool:
        token = settings.TELEGRAM_BOT_TOKEN.strip()
        chat_id = settings.TELEGRAM_CHAT_ID.strip()
        return bool(token and chat_id and not token.startswith("BotFatherdan_"))

    def should_send_for_risk(self, risk_level: str) -> bool:
        normalized_risk = (risk_level or "").strip().upper()
        min_level = (settings.ALERT_MIN_RISK_LEVEL or "HIGH").strip().upper()
        return RISK_ORDER.get(normalized_risk, -1) >= RISK_ORDER.get(min_level, 3)

    def build_message(self, alert: Alert, prediction: Dict[str, Any]) -> str:
        probabilities = prediction.get("probabilities", {})
        decision = prediction.get("decision", {})
        probability = probabilities.get("ensemble_fire_probability")

        probability_line = ""
        if probability is not None:
            probability_line = f"\nOlasilik: %{float(probability) * 100:.1f}"

        return (
            "Yangin riski alarmi\n"
            f"Risk seviyesi: {alert.risk_level}"
            f"{probability_line}\n"
            f"Hotspot ID: {alert.hotspot_id}\n"
            f"Karar: {decision.get('decision_name', 'unknown')}\n"
            f"Mesaj: {alert.message}"
        )

    def send_message(self, text: str, risk_level: str = "HIGH") -> bool:
        if not self.is_configured():
            logger.info("Telegram ayarlari eksik oldugu icin bildirim atlandi.")
            return False

        if not self.should_send_for_risk(risk_level):
            return False

        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": text,
        }

        try:
            response = requests.post(url, data=payload, timeout=10)
            response.raise_for_status()
        except requests.RequestException:
            logger.exception("Telegram mesaji gonderilemedi.")
            return False

        return True

    def send_telegram_alert(self, alert: Alert, prediction: Dict[str, Any]) -> bool:
        return self.send_message(
            text=self.build_message(alert=alert, prediction=prediction),
            risk_level=alert.risk_level or "",
        )


telegram_alert_service = TelegramAlertService()


def send_telegram_alert(text: str, risk_level: str = "HIGH") -> bool:
    return telegram_alert_service.send_message(text=text, risk_level=risk_level)
