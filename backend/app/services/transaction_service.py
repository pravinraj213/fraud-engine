import uuid

from sqlalchemy.orm import Session

from app.engine.base import TransactionData
from app.engine.engine import EngineResult, RuleEngine
from app.models import RiskAssessment
from app.repositories import assessments, transactions
from app.repositories.history import SqlHistoryProvider
from app.schemas import TransactionIn
from app.timeutils import as_utc, utcnow


def to_transaction_data(body: TransactionIn) -> TransactionData:
    return TransactionData(
        id=str(uuid.uuid4()), account_id=body.account_id, amount=body.amount, merchant=body.merchant,
        latitude=body.latitude, longitude=body.longitude,
        occurred_at=as_utc(body.occurred_at) if body.occurred_at else utcnow(),
        location_label=body.location_label or None,
    )


def ingest(session: Session, engine: RuleEngine, body: TransactionIn) -> tuple[RiskAssessment, EngineResult]:
    """Evaluate a transaction against stored history, then store it with its verdict in one commit.
    Evaluation runs before the insert, so history never contains the current transaction.
    The caller decides whether to schedule an alert (result.should_notify)."""
    txn = to_transaction_data(body)
    result = engine.evaluate(txn, SqlHistoryProvider(session))
    transactions.add_transaction(session, txn, body.currency)
    assessment = assessments.add_assessment(session, txn.id, result)
    session.commit()
    session.refresh(assessment)
    return assessment, result
