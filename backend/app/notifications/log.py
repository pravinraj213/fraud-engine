import logging

from app.notifications.base import AlertPayload, Notifier, SendResult
from app.notifications.templates import render_subject, render_text

logger = logging.getLogger(__name__)


class LogNotifier(Notifier):
    """Writes the alert to the server log instead of sending it. Default for local work and tests."""

    channel = "log"

    def send_high_risk_alert(self, alert: AlertPayload) -> SendResult:
        logger.warning("%s\n%s", render_subject(alert), render_text(alert))
        return SendResult(True)
