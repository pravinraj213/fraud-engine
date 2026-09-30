from app.config import Settings
from app.notifications.base import Notifier
from app.notifications.log import LogNotifier
from app.notifications.ses import SESNotifier


def get_notifier(settings: Settings) -> Notifier:
    """Build the notifier NOTIFIER selects. Raises at startup rather than at the first alert."""
    if settings.notifier == "log":
        return LogNotifier()
    if settings.notifier == "ses":
        if not settings.ses_sender_email or not settings.alert_recipients:
            raise ValueError("NOTIFIER=ses needs SES_SENDER_EMAIL and ALERT_RECIPIENT_EMAIL")
        return SESNotifier(settings.ses_sender_email, settings.alert_recipients,
                           settings.aws_region, settings.aws_profile)
    raise ValueError(f"Unknown NOTIFIER {settings.notifier!r}; use 'log' or 'ses'")
