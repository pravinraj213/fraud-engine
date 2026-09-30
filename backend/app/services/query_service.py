from sqlalchemy.orm import Session

from app.enums import NotificationStatus, ReviewStatus, RiskLevel
from app.models import RiskAssessment
from app.repositories import assessments, notifications
from app.repositories.assessments import FlagFilter
from app.schemas import (AssessmentOut, FlagListOut, FlagSummaryOut, NotificationOut, ReviewOut,
                         RuleHitOut, StatsOut, TransactionDetailOut, TransactionOut)
from app.services.errors import NotFoundError
from app.services.review_service import allowed_actions
from app.timeutils import as_utc


def build_detail(a: RiskAssessment) -> TransactionDetailOut:
    t = a.transaction
    n = a.notification
    return TransactionDetailOut(
        transaction=TransactionOut(
            id=t.id, account_id=t.account_id, amount=t.amount, currency=t.currency, merchant=t.merchant,
            latitude=t.latitude, longitude=t.longitude, location_label=t.location_label,
            occurred_at=as_utc(t.occurred_at), created_at=as_utc(t.created_at)),
        assessment=AssessmentOut(
            total_score=a.total_score, risk_level=a.risk_level, status=a.status,
            evaluated_at=as_utc(a.evaluated_at), updated_at=as_utc(a.updated_at)),
        rule_hits=[RuleHitOut(rule_name=h.rule_name, score=h.score, weight=h.weight,
                              weighted_score=round(h.score * h.weight, 2), reason=h.reason, details=h.details)
                   for h in a.rule_hits],
        reviews=[ReviewOut(action=r.action, from_status=r.from_status, to_status=r.to_status,
                           reviewer=r.reviewer, note=r.note, created_at=as_utc(r.created_at))
                 for r in a.reviews],
        notification=NotificationOut(channel=n.channel, status=n.status, created_at=as_utc(n.created_at),
                                     error=n.error) if n else None,
        allowed_actions=allowed_actions(a.status),
    )


def get_detail(session: Session, transaction_id: str) -> TransactionDetailOut:
    assessment = assessments.get_by_transaction(session, transaction_id)
    if assessment is None:
        raise NotFoundError("Transaction not found")
    return build_detail(assessment)


def _summary(a: RiskAssessment) -> FlagSummaryOut:
    t = a.transaction
    n = a.notification
    return FlagSummaryOut(
        transaction_id=t.id, account_id=t.account_id, amount=t.amount, currency=t.currency,
        merchant=t.merchant, location_label=t.location_label, occurred_at=as_utc(t.occurred_at),
        total_score=a.total_score, risk_level=a.risk_level, status=a.status,
        rules_triggered=[h.rule_name for h in a.rule_hits],
        notification_status=n.status if n and n.status != NotificationStatus.PENDING else None,
        notification_channel=n.channel if n else None,
    )


def list_flags(session: Session, f: FlagFilter) -> FlagListOut:
    items, total = assessments.list_flags(session, f)
    return FlagListOut(items=[_summary(a) for a in items], total=total)


def stats(session: Session) -> StatsOut:
    by_status = {s.value: 0 for s in ReviewStatus} | assessments.count_by_status(session)
    open_levels = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]
    by_level = {lvl.value: 0 for lvl in open_levels} | assessments.count_open_by_level(session)
    sent = notifications.count_by_status(session)
    return StatsOut(
        by_status=by_status,
        flagged_by_level=by_level,
        notifications={s: sent.get(s, 0) for s in (NotificationStatus.SENT, NotificationStatus.FAILED)},
    )
