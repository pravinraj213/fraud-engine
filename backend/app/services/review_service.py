from sqlalchemy.orm import Session

from app.enums import ReviewAction, ReviewStatus
from app.models import RiskAssessment
from app.repositories import assessments, reviews
from app.schemas import ReviewIn
from app.services.errors import ConflictError, NotFoundError
from app.timeutils import utcnow

# The only place the review lifecycle is defined: (current status, action) -> new status.
TRANSITIONS: dict[tuple[ReviewStatus, ReviewAction], ReviewStatus] = {
    (ReviewStatus.FLAGGED, ReviewAction.REVIEWED): ReviewStatus.REVIEWED,
    (ReviewStatus.FLAGGED, ReviewAction.CLEARED): ReviewStatus.CLEARED,
    (ReviewStatus.REVIEWED, ReviewAction.CLEARED): ReviewStatus.CLEARED,
}


def allowed_actions(status: ReviewStatus) -> list[ReviewAction]:
    return [action for (from_status, action) in TRANSITIONS if from_status == status]


def review_transaction(session: Session, transaction_id: str, body: ReviewIn) -> RiskAssessment:
    assessment = assessments.get_by_transaction(session, transaction_id)
    if assessment is None:
        raise NotFoundError("Transaction not found")
    current = assessment.status
    new_status = TRANSITIONS.get((current, body.action))
    if new_status is None:
        raise ConflictError(f"Cannot mark a {current.value} transaction as {body.action.value}")

    assessment.status = new_status
    assessment.updated_at = utcnow()
    reviews.add_review(session, assessment.id, body.action, current, new_status, body.reviewer, body.note or None)
    session.commit()
    session.refresh(assessment)
    return assessment
