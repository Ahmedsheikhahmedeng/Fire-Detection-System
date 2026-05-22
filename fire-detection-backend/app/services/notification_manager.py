from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.models.alert import Alert
from app.services.email_service import email_alert_service
from app.services.telegram_service import telegram_alert_service
from app.services.twilio_sms_service import twilio_sms_alert_service

logger = logging.getLogger("fire_detection.notifications")


class NotificationManager:
    def send_alert(
        self,
        alert: Alert,
        prediction: Dict[str, Any],
        hotspot: Optional[Any] = None,
    ) -> Dict[str, bool]:
        results = {
            "telegram": telegram_alert_service.send_telegram_alert(
                alert=alert,
                prediction=prediction,
            ),
            "email": email_alert_service.send_email_alert(
                alert=alert,
                prediction=prediction,
            ),
            "sms": twilio_sms_alert_service.send_alert(
                alert=alert,
                prediction=prediction,
                hotspot=hotspot,
            ),
        }

        logger.info(
            "Alert notifications processed | alert_id=%s risk_level=%s telegram=%s email=%s sms=%s",
            alert.id,
            alert.risk_level,
            results["telegram"],
            results["email"],
            results["sms"],
        )
        return results


notification_manager = NotificationManager()
