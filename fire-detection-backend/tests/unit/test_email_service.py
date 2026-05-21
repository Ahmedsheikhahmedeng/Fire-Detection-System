from app.models.alert import Alert
from app.services.email_service import EmailAlertService


def test_email_service_is_not_configured_without_recipients(monkeypatch):
    service = EmailAlertService()

    monkeypatch.setattr("app.services.email_service.settings.SMTP_USERNAME", "sender@gmail.com")
    monkeypatch.setattr("app.services.email_service.settings.SMTP_PASSWORD", "app-password")
    monkeypatch.setattr("app.services.email_service.settings.ALERT_EMAIL_TO", "")

    assert service.is_configured() is False


def test_email_service_parses_multiple_recipients(monkeypatch):
    service = EmailAlertService()

    monkeypatch.setattr(
        "app.services.email_service.settings.ALERT_EMAIL_TO",
        "first@example.com, second@example.com,",
    )

    assert service.get_recipients() == ["first@example.com", "second@example.com"]


def test_email_service_sends_message_with_smtp(monkeypatch):
    sent_messages = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            self.host = host
            self.port = port
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self):
            return None

        def login(self, username, password):
            self.username = username
            self.password = password

        def send_message(self, message):
            sent_messages.append(message)

    monkeypatch.setattr("app.services.email_service.smtplib.SMTP", FakeSMTP)
    monkeypatch.setattr("app.services.email_service.settings.SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setattr("app.services.email_service.settings.SMTP_PORT", 587)
    monkeypatch.setattr("app.services.email_service.settings.SMTP_USERNAME", "sender@gmail.com")
    monkeypatch.setattr("app.services.email_service.settings.SMTP_PASSWORD", "app-password")
    monkeypatch.setattr("app.services.email_service.settings.SMTP_FROM_EMAIL", "alerts@example.com")

    service = EmailAlertService()

    result = service.send_email(
        to_emails=["user@example.com"],
        subject="Yangin Uyarisi",
        message="Yangin riski tespit edildi.",
    )

    assert result is True
    assert len(sent_messages) == 1
    assert sent_messages[0]["From"] == "alerts@example.com"
    assert sent_messages[0]["To"] == "user@example.com"
    assert sent_messages[0]["Subject"] == "Yangin Uyarisi"


def test_email_alert_respects_min_risk_level(monkeypatch):
    service = EmailAlertService()
    alert = Alert(risk_level="MEDIUM", hotspot_id=1, message="test")

    monkeypatch.setattr("app.services.email_service.settings.ALERT_MIN_RISK_LEVEL", "HIGH")

    assert service.should_send_for_risk(alert.risk_level) is False
