from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.engine.base import TransactionData
from app.models import Transaction
from app.timeutils import as_utc


def to_transaction_data(row: Transaction) -> TransactionData:
    return TransactionData(
        id=row.id, account_id=row.account_id, amount=row.amount, merchant=row.merchant,
        latitude=row.latitude, longitude=row.longitude, occurred_at=as_utc(row.occurred_at),
        location_label=row.location_label,
    )


class SqlHistoryProvider:
    """HistoryProvider backed by the transactions table (read-only)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def count_in_window(self, account_id: str, start: datetime, end: datetime) -> int:
        stmt = select(func.count()).select_from(Transaction).where(
            Transaction.account_id == account_id,
            Transaction.occurred_at >= as_utc(start),
            Transaction.occurred_at <= as_utc(end),
        )
        return int(self.session.scalar(stmt) or 0)

    def recent_amounts(self, account_id: str, at: datetime, limit: int) -> list[Decimal]:
        stmt = (select(Transaction.amount)
                .where(Transaction.account_id == account_id, Transaction.occurred_at <= as_utc(at))
                .order_by(Transaction.occurred_at.desc()).limit(limit))
        return list(self.session.scalars(stmt))

    def previous_transaction(self, account_id: str, at: datetime) -> TransactionData | None:
        stmt = (select(Transaction)
                .where(Transaction.account_id == account_id, Transaction.occurred_at <= as_utc(at))
                .order_by(Transaction.occurred_at.desc(), Transaction.created_at.desc()).limit(1))
        row = self.session.scalar(stmt)
        return to_transaction_data(row) if row else None
