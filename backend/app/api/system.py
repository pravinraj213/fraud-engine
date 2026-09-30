from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_engine, get_notifier
from app.config import Settings
from app.database import get_db
from app.engine.engine import RuleEngine
from app.notifications.base import Notifier
from app.schemas import NotificationModeIn, SystemOut
from app.services.notification_service import alerts_sent_last_24h, configured_notifier

router = APIRouter(tags=["system"])


@router.get("/system", response_model=SystemOut)
def system(
    db: Session = Depends(get_db),
    engine: RuleEngine = Depends(get_engine),
    notifier: Notifier = Depends(get_notifier),
    settings: Settings = Depends(get_app_settings),
) -> SystemOut:
    """How alerts are delivered and the scoring thresholds, so the console can warn before email goes out."""
    return SystemOut(
        notifier=notifier.channel,
        alert_daily_limit=settings.alert_daily_limit,
        alerts_sent_24h=alerts_sent_last_24h(db),
        medium_threshold=engine.medium_threshold,
        high_risk_threshold=engine.high_threshold,
        alert_recipients=settings.alert_recipients,
        email_configured=bool(settings.ses_sender_email and settings.alert_recipients),
    )


@router.put("/system/notifications", response_model=SystemOut)
def update_notifications(
    body: NotificationModeIn,
    request: Request,
    db: Session = Depends(get_db),
    engine: RuleEngine = Depends(get_engine),
    settings: Settings = Depends(get_app_settings),
) -> SystemOut:
    """Change delivery for this process. Restarting restores the configured startup mode."""
    notifier = configured_notifier(settings, body.enabled)
    request.app.state.notifier = notifier
    return system(db, engine, notifier, settings)
