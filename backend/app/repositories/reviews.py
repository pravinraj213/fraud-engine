from sqlalchemy.orm import Session

from app.enums import ReviewAction, ReviewStatus
from app.models import ReviewActionRecord


def add_review(session: Session, assessment_id: str, action: ReviewAction, from_status: ReviewStatus,
               to_status: ReviewStatus, reviewer: str, note: str | None) -> ReviewActionRecord:
    record = ReviewActionRecord(assessment_id=assessment_id, action=action, from_status=from_status,
                                to_status=to_status, reviewer=reviewer, note=note)
    session.add(record)
    return record
