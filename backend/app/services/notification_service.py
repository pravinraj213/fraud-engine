import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import Settings
from app.database import SessionLocal
from app.enums import RiskLevel
from app.models import RiskAssessment
from app.notifications.base import AlertPayload, Notifier
from app.repositories import assessments, notifications
from app.timeutils import as_utc, utcnow

logger = logging.getLogger(__name__)


def alerts_sent_last_24h(session: Session) -> int:
    return notifications.count_sent_since(session, utcnow() - timedelta(hours=24))


def build_payload(a: RiskAssessment, console_base_url: str) -> AlertPayload:
    t = a.transaction
    return AlertPayload(
        assessment_id=a.id, transaction_id=t.id, account_id=t.account_id, amount=t.amount,
        currency=t.currency, merchant=t.merchant, location_label=t.location_label,
        occurred_at=as_utc(t.occurred_at), total_score=a.total_score, risk_level=a.risk_level.value,
        hits=[(h.rule_name, h.score, h.reason) for h in a.rule_hits],
        console_url=f"{console_base_url.rstrip('/')}/transactions/{t.id}",
    )


def notify_high_risk(assessment_id: str, notifier: Notifier, settings: Settings) -> None:
    """Send at most one alert for a HIGH assessment. Runs as a background task and never raises.
    Claim first (insert PENDING, commit), then send, so a second call finds the claim and stops."""
    try:
        with SessionLocal() as session:  # the request's session is closed by now
            assessment = assessments.get_assessment(session, assessment_id)
            if assessment is None or assessment.risk_level != RiskLevel.HIGH:
                return
            claim = notifications.claim(session, assessment_id, notifier.channel)
            if claim is None:
                logger.info("Alert for assessment %s already claimed; skipping", assessment_id)
                return
            sent_today = alerts_sent_last_24h(session)
            if sent_today >= settings.alert_daily_limit:
                error = f"Daily alert limit reached ({settings.alert_daily_limit} per 24 h); not sent"
                notifications.finish(session, claim, False, None, error)
                logger.warning("Alert for assessment %s skipped: %s", assessment_id, error)
                return
            result = notifier.send_high_risk_alert(build_payload(assessment, settings.console_base_url))
            notifications.finish(session, claim, result.success, result.provider_message_id, result.error)
            logger.info("Alert for assessment %s: %s", assessment_id, "sent" if result.success else "failed")
    except Exception:
        logger.exception("Unexpected error while alerting on assessment %s", assessment_id)
