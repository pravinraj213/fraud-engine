from dataclasses import dataclass

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.engine.engine import EngineResult
from app.enums import ReviewStatus, RiskLevel
from app.models import RiskAssessment, RuleHit, Transaction

OPEN_STATUSES = (ReviewStatus.FLAGGED, ReviewStatus.REVIEWED, ReviewStatus.CLEARED)


@dataclass(frozen=True)
class FlagFilter:
    status: str = "FLAGGED"          # FLAGGED | REVIEWED | CLEARED | ALL (every non-CLEAN)
    risk_level: RiskLevel | None = None
    account_id: str | None = None
    sort: str = "score"              # score | newest
    limit: int = 50
    offset: int = 0


def add_assessment(session: Session, transaction_id: str, result: EngineResult) -> RiskAssessment:
    assessment = RiskAssessment(
        transaction_id=transaction_id, total_score=result.total_score,
        risk_level=result.risk_level, status=result.status,
    )
    assessment.rule_hits = [
        RuleHit(rule_name=h.result.rule_name, score=h.result.score, weight=h.weight,
                reason=h.result.reason[:255], details=h.result.details)
        for h in result.hits
    ]
    session.add(assessment)
    return assessment


def get_by_transaction(session: Session, transaction_id: str) -> RiskAssessment | None:
    return session.scalar(select(RiskAssessment).where(RiskAssessment.transaction_id == transaction_id))


def get_assessment(session: Session, assessment_id: str) -> RiskAssessment | None:
    return session.get(RiskAssessment, assessment_id)


def _filtered(stmt: Select, f: FlagFilter) -> Select:
    statuses = OPEN_STATUSES if f.status == "ALL" else (ReviewStatus(f.status),)
    stmt = stmt.where(RiskAssessment.status.in_(statuses))
    if f.risk_level:
        stmt = stmt.where(RiskAssessment.risk_level == f.risk_level)
    if f.account_id:
        stmt = stmt.where(Transaction.account_id == f.account_id)
    return stmt


def list_flags(session: Session, f: FlagFilter) -> tuple[list[RiskAssessment], int]:
    base = select(RiskAssessment).join(Transaction)
    order = ([RiskAssessment.total_score.desc(), Transaction.occurred_at.desc()] if f.sort == "score"
             else [Transaction.occurred_at.desc()])
    items = session.scalars(_filtered(base, f).order_by(*order, RiskAssessment.id)
                            .limit(f.limit).offset(f.offset)).all()
    total = session.scalar(_filtered(select(func.count()).select_from(RiskAssessment).join(Transaction), f))
    return list(items), int(total or 0)


def count_by_status(session: Session) -> dict[str, int]:
    rows = session.execute(select(RiskAssessment.status, func.count()).group_by(RiskAssessment.status))
    return {status.value: n for status, n in rows}


def count_open_by_level(session: Session) -> dict[str, int]:
    rows = session.execute(select(RiskAssessment.risk_level, func.count())
                           .where(RiskAssessment.status == ReviewStatus.FLAGGED)
                           .group_by(RiskAssessment.risk_level))
    return {level.value: n for level, n in rows}
