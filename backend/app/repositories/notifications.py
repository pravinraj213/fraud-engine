from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.enums import NotificationStatus
from app.models import Notification


def claim(session: Session, assessment_id: str, channel: str) -> Notification | None:
    """Insert a PENDING row and commit. Returns None when this assessment already has one;
    the unique constraint on assessment_id is what makes duplicate alerts impossible."""
    row = Notification(assessment_id=assessment_id, channel=channel, status=NotificationStatus.PENDING)
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return None
    return row


def finish(session: Session, row: Notification, success: bool,
           message_id: str | None, error: str | None) -> None:
    row.status = NotificationStatus.SENT if success else NotificationStatus.FAILED
    row.provider_message_id = message_id
    row.error = error
    session.commit()


def count_sent_since(session: Session, since: datetime) -> int:
    stmt = select(func.count()).select_from(Notification).where(
        Notification.status == NotificationStatus.SENT, Notification.created_at >= since)
    return int(session.scalar(stmt) or 0)


def count_by_status(session: Session) -> dict[str, int]:
    rows = session.execute(select(Notification.status, func.count()).group_by(Notification.status))
    return {status: n for status, n in rows}
