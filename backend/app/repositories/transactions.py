from sqlalchemy.orm import Session

from app.engine.base import TransactionData
from app.models import Transaction


def add_transaction(session: Session, data: TransactionData, currency: str) -> Transaction:
    row = Transaction(
        id=data.id, account_id=data.account_id, amount=data.amount, currency=currency,
        merchant=data.merchant, latitude=data.latitude, longitude=data.longitude,
        location_label=data.location_label, occurred_at=data.occurred_at,
    )
    session.add(row)
    return row


def get_transaction(session: Session, transaction_id: str) -> Transaction | None:
    return session.get(Transaction, transaction_id)
