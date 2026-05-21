from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Any, Dict, List

from app.core.config import settings
from app.models.alert import Alert
from app.services.telegram_service import RISK_ORDER

logger = logging.getLogger("fire_detection.email")


class EmailAlertService:
    def has_smtp_credentials(self) -> bool:
        return bool(
            settings.SMTP_HOST.strip()
            and settings.SMTP_PORT
            and settings.SMTP_USERNAME.strip()
            and settings.SMTP_PASSWORD.strip()
        )

    def is_configured(self) -> bool:
        return bool(self.has_smtp_credentials() and self.get_recipients())

    def get_sender(self) -> str:
        return settings.SMTP_FROM_EMAIL.strip() or settings.SMTP_USERNAME.strip()

    def get_recipients(self) -> List[str]:
        return [
            recipient.strip()
            for recipient in settings.ALERT_EMAIL_TO.split(",")
            if recipient.strip()
        ]

    def should_send_for_risk(self, risk_level: str) -> bool:
        normalized_risk = (risk_level or "").strip().upper()
        min_level = (settings.ALERT_MIN_RISK_LEVEL or "HIGH").strip().upper()
        return RISK_ORDER.get(normalized_risk, -1) >= RISK_ORDER.get(min_level, 3)

    def build_subject(self, alert: Alert) -> str:
        return f"Yangin Uyarisi - {alert.risk_level}"

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

    def send_email(self, to_emails: List[str], subject: str, message: str) -> bool:
        sender = self.get_sender()

        email_message = EmailMessage()
        email_message["Subject"] = subject
        email_message["From"] = sender
        email_message["To"] = ", ".join(to_emails)
        email_message.set_content(message)

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(email_message)
        except (OSError, smtplib.SMTPException):
            logger.exception("Email mesaji gonderilemedi.")
            return False

        return True

    def send_email_alert(self, alert: Alert, prediction: Dict[str, Any]) -> bool:
        if not self.is_configured():
            logger.info("Email ayarlari eksik oldugu icin bildirim atlandi.")
            return False

        if not self.should_send_for_risk(alert.risk_level or ""):
            return False

        return self.send_email(
            to_emails=self.get_recipients(),
            subject=self.build_subject(alert),
            message=self.build_message(alert=alert, prediction=prediction),
        )


email_alert_service = EmailAlertService()


def send_email(to_email: str, subject: str, message: str) -> bool:
    return email_alert_service.send_email(
        to_emails=[to_email],
        subject=subject,
        message=message,
    )
