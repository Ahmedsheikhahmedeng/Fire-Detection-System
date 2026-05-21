from __future__ import annotations

import logging
from typing import Any, Dict

from app.models.alert import Alert
from app.services.email_service import email_alert_service
from app.services.telegram_service import telegram_alert_service

logger = logging.getLogger("fire_detection.notifications")


class NotificationManager:
    def send_alert(self, alert: Alert, prediction: Dict[str, Any]) -> Dict[str, bool]:
        results = {
            "telegram": telegram_alert_service.send_telegram_alert(
                alert=alert,
                prediction=prediction,
            ),
            "email": email_alert_service.send_email_alert(
                alert=alert,
                prediction=prediction,
            ),
        }

        logger.info(
            "Alert notifications processed | alert_id=%s risk_level=%s telegram=%s email=%s",
            alert.id,
            alert.risk_level,
            results["telegram"],
            results["email"],
        )
        return results


notification_manager = NotificationManager()
