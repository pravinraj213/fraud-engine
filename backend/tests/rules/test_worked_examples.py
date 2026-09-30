"""Every row of the plan's worked-examples table, run through the real engine and rules.yaml."""
from app.engine.engine import RuleEngine
from app.enums import ReviewStatus, RiskLevel
from tests.fakes import InMemoryHistoryProvider, make_txn

BASELINE = [200, 500, 1000, 3000, 6000] * 2  # median 1,000, spread over past days


def baseline() -> list:
    return [make_txn(minutes=-1440 * (i + 1), amount=a) for i, a in enumerate(BASELINE)]


def recent(count: int, amount: float = 1000) -> list:
    return [make_txn(minutes=-5 + i * 0.5, amount=amount) for i in range(count)]


def run(engine: RuleEngine, history: list, **txn):
    result = engine.evaluate(make_txn(**txn), InMemoryHistoryProvider(history))
    return {h.result.rule_name: h.result.score for h in result.hits}, result.total_score, result.risk_level


def test_six_in_ten_minutes(engine: RuleEngine) -> None:
    assert run(engine, recent(5)) == ({"velocity": 40}, 40, RiskLevel.MEDIUM)


def test_eight_in_ten_minutes(engine: RuleEngine) -> None:
    assert run(engine, recent(7)) == ({"velocity": 70}, 70, RiskLevel.HIGH)


def test_amount_six_times_median(engine: RuleEngine) -> None:
    assert run(engine, baseline(), amount=6000) == ({"unusual_amount": 50}, 50, RiskLevel.MEDIUM)


def test_amount_twelve_times_median(engine: RuleEngine) -> None:
    assert run(engine, baseline(), amount=12_000) == ({"unusual_amount": 80}, 80, RiskLevel.HIGH)


def test_new_account_large_amount(engine: RuleEngine) -> None:
    assert run(engine, [], amount=150_000) == ({"unusual_amount": 50}, 50, RiskLevel.MEDIUM)


def test_chennai_then_london(engine: RuleEngine) -> None:
    history = [make_txn("Chennai, IN", minutes=-45)]
    assert run(engine, history, city="London, GB") == ({"impossible_travel": 90}, 90, RiskLevel.HIGH)


def test_chennai_then_bengaluru_six_hours_later_is_clean(engine: RuleEngine) -> None:
    history = [make_txn("Chennai, IN", minutes=-360)]
    result = engine.evaluate(make_txn("Bengaluru, IN"), InMemoryHistoryProvider(history))
    assert (result.total_score, result.risk_level, result.status) == (0, RiskLevel.NONE, ReviewStatus.CLEAN)


def test_velocity_plus_amount_capped_at_100(engine: RuleEngine) -> None:
    hits, total, level = run(engine, baseline() + recent(6), amount=6000)
    assert hits == {"velocity": 55, "unusual_amount": 50}
    assert (total, level) == (100, RiskLevel.HIGH)
