import logging
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.notifications.base import AlertPayload, Notifier, SendResult
from app.notifications.templates import (
    render_html,
    render_subject,
    render_test_html,
    render_test_subject,
    render_test_text,
    render_text,
)

logger = logging.getLogger(__name__)


class SESNotifier(Notifier):
    """Sends alerts through the Amazon SES v2 API."""

    channel = "ses"

    def __init__(self, sender: str, recipients: list[str], region: str,
                 profile: str | None = None, client: Any = None) -> None:
        self.sender = sender
        self.recipients = recipients
        self.client = client or boto3.Session(profile_name=profile or None, region_name=region).client("sesv2")

    def send_high_risk_alert(self, alert: AlertPayload) -> SendResult:
        return self._send(render_subject(alert), render_text(alert), render_html(alert), alert.assessment_id)

    def send_test_email(self, recipient: str) -> SendResult:
        """Send a delivery test without creating a transaction or notification record."""
        return self._send(
            render_test_subject(),
            render_test_text(),
            render_test_html(),
            "test email",
            recipients=[recipient],
        )

    def _send(
        self,
        subject: str,
        text: str,
        html: str,
        context: str,
        recipients: list[str] | None = None,
    ) -> SendResult:
        try:
            response = self.client.send_email(
                FromEmailAddress=self.sender,
                Destination={"ToAddresses": recipients if recipients is not None else self.recipients},
                Content={"Simple": {
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": text, "Charset": "UTF-8"},
                             "Html": {"Data": html, "Charset": "UTF-8"}},
                }},
            )
        except (ClientError, BotoCoreError) as exc:
            logger.error("SES send failed for %s: %s", context, exc)
            return SendResult(False, error=str(exc))
        return SendResult(True, provider_message_id=response.get("MessageId"))
