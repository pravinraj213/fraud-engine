from app.engine.rules.unusual_amount import UnusualAmountRule
from tests.fakes import InMemoryHistoryProvider, make_txn

VARIABLE = [200, 500, 1000, 3000, 6000]   # median 1000, large stdev
TIGHT = [1000, 1010, 990, 1005, 995]      # median 1000, stdev ~7


def history(amounts: list[float]) -> InMemoryHistoryProvider:
    return InMemoryHistoryProvider([make_txn(minutes=-1440 * (i + 1), amount=a) for i, a in enumerate(amounts)])


def check(amounts: list[float], amount: float):
    return UnusualAmountRule().evaluate(make_txn(amount=amount), history(amounts))


def test_cold_start_below_threshold() -> None:
    assert not check([1000] * 3, 99_999.99).triggered


def test_cold_start_at_threshold() -> None:
    result = check([1000] * 3, 100_000)
    assert result.triggered and result.score == 50
    assert "INR 100,000.00 exceeds the INR 100,000.00 limit" in result.reason
    assert "(3 prior transactions)" in result.reason


def test_ratio_exactly_five_low_z_scores_50() -> None:
    result = check(VARIABLE, 5000)
    assert result.triggered and result.score == 50
    assert result.details["ratio"] == 5.0 and result.details["z_score"] < 6


def test_ratio_ten_scores_80() -> None:
    result = check(VARIABLE, 10_000)
    assert result.triggered and result.score == 80


def test_high_z_low_ratio_scores_50() -> None:
    result = check(TIGHT, 1030)
    assert result.triggered and result.score == 50
    assert result.details["z_score"] >= 3 and result.details["ratio"] < 5


def test_identical_history_slightly_higher_not_triggered() -> None:
    result = check([1000] * 5, 1001)
    assert not result.triggered


def test_identical_history_large_ratio_still_triggers_without_z() -> None:
    result = check([1000] * 5, 6000)
    assert result.triggered and result.details["z_score"] is None
    assert "z-score" not in result.reason


def test_lower_amount_not_triggered() -> None:
    assert not check(VARIABLE, 100).triggered


def test_reason_format() -> None:
    result = check([4000] * 4 + [4100], 48_000)
    assert result.reason.startswith("INR 48,000.00 is 12.0× this account's median of INR 4,000.00")
