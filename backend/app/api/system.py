from fastapi import APIRouter, Depends, Request

from app.api.deps import get_app_settings, get_engine, get_notifier
from app.config import Settings
from app.engine.engine import RuleEngine
from app.notifications.base import Notifier
from app.schemas import NotificationModeIn, SystemOut, TestEmailIn, TestEmailOut
from app.services.notification_service import configured_notifier, send_test_email

router = APIRouter(tags=["system"])


@router.get("/system", response_model=SystemOut)
def system(
    engine: RuleEngine = Depends(get_engine),
    notifier: Notifier = Depends(get_notifier),
    settings: Settings = Depends(get_app_settings),
) -> SystemOut:
    """How alerts are delivered and the scoring thresholds, so the console can warn before email goes out."""
    return SystemOut(
        notifier=notifier.channel,
        medium_threshold=engine.medium_threshold,
        high_risk_threshold=engine.high_threshold,
        alert_recipients=settings.alert_recipients,
        email_configured=bool(settings.ses_sender_email and settings.alert_recipients),
    )


@router.put("/system/notifications", response_model=SystemOut)
def update_notifications(
    body: NotificationModeIn,
    request: Request,
    engine: RuleEngine = Depends(get_engine),
    settings: Settings = Depends(get_app_settings),
) -> SystemOut:
    """Change delivery for this process. Restarting restores the configured startup mode."""
    notifier = configured_notifier(settings, body.enabled)
    request.app.state.notifier = notifier
    return system(engine, notifier, settings)


@router.post("/system/notifications/test", response_model=TestEmailOut)
def test_notifications(
    body: TestEmailIn,
    settings: Settings = Depends(get_app_settings),
) -> TestEmailOut:
    """Send one test through SES without changing the current alert mode."""
    message_id = send_test_email(settings, body.recipient)
    return TestEmailOut(sent=True, recipients=[body.recipient], provider_message_id=message_id)
