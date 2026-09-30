import pytest

from app.engine.rules.velocity import VelocityRule
from tests.fakes import InMemoryHistoryProvider, make_txn


def burst(count: int, account: str = "ACC-1") -> InMemoryHistoryProvider:
    """`count` stored transactions in the 5 minutes before NOW."""
    return InMemoryHistoryProvider([make_txn(minutes=-5 + i * 0.5, account_id=account) for i in range(count)])


@pytest.mark.parametrize("prior, triggered, score", [
    (4, False, 0),     # 5 in window: exactly the limit
    (5, True, 40),     # 6
    (7, True, 70),     # 8
    (11, True, 100),   # 12, capped
])
def test_velocity_scores(prior: int, triggered: bool, score: int) -> None:
    result = VelocityRule().evaluate(make_txn(), burst(prior))
    assert result.triggered is triggered
    assert result.score == score


def test_velocity_reason_and_details() -> None:
    result = VelocityRule().evaluate(make_txn(), burst(6))
    assert result.reason == "7 transactions in 10 minutes (limit 5)"
    assert result.details == {"count": 7, "window_minutes": 10, "max_transactions": 5}


def test_transactions_outside_window_not_counted() -> None:
    history = InMemoryHistoryProvider([make_txn(minutes=-10.5 - i) for i in range(10)])
    assert not VelocityRule().evaluate(make_txn(), history).triggered


def test_other_accounts_not_counted() -> None:
    assert not VelocityRule().evaluate(make_txn(), burst(10, account="ACC-OTHER")).triggered
