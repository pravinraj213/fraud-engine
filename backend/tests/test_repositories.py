from collections.abc import Iterator
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.database import SessionLocal, configure_database, create_tables
from app.repositories.history import SqlHistoryProvider
from app.repositories.transactions import add_transaction
from tests.fakes import NOW, make_txn


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    engine = configure_database(f"sqlite:///{tmp_path / 'repo.db'}")
    create_tables()
    assert set(inspect(engine).get_table_names()) == {
        "transactions", "risk_assessments", "rule_hits", "review_actions", "notifications"}
    with SessionLocal() as s:
        yield s
    engine.dispose()


def store(session: Session, *txns) -> None:
    for t in txns:
        add_transaction(session, t, "INR")
    session.commit()


def test_count_in_window_is_inclusive_and_per_account(session: Session) -> None:
    store(session,
          make_txn(minutes=-10), make_txn(minutes=-5), make_txn(minutes=0),
          make_txn(minutes=-11), make_txn(minutes=-3, account_id="ACC-2"))
    history = SqlHistoryProvider(session)
    assert history.count_in_window("ACC-1", NOW - timedelta(minutes=10), NOW) == 3


def test_recent_amounts_newest_first_with_limit(session: Session) -> None:
    store(session, make_txn(minutes=-30, amount=1), make_txn(minutes=-20, amount=2),
          make_txn(minutes=-10, amount=3), make_txn(minutes=5, amount=99))
    assert SqlHistoryProvider(session).recent_amounts("ACC-1", NOW, 2) == [Decimal("3.00"), Decimal("2.00")]


def test_previous_transaction_latest_at_or_before(session: Session) -> None:
    earlier, latest = make_txn(minutes=-30), make_txn("London, GB", minutes=-1)
    store(session, earlier, latest, make_txn(minutes=10))
    prev = SqlHistoryProvider(session).previous_transaction("ACC-1", NOW)
    assert prev is not None and prev.id == latest.id
    assert prev.occurred_at == latest.occurred_at  # timezone-aware UTC after the round trip
    assert SqlHistoryProvider(session).previous_transaction("ACC-NONE", NOW) is None
