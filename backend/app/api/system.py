from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_engine, get_notifier
from app.config import Settings
from app.database import get_db
from app.engine.engine import RuleEngine
from app.notifications.base import Notifier
from app.schemas import SystemOut
from app.services.notification_service import alerts_sent_last_24h

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
    )
