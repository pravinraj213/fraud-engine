import logging
from pathlib import Path
from typing import ClassVar

import pytest

from app.engine.base import HistoryProvider, Rule, RuleResult, TransactionData
from app.engine.engine import RuleEngine
from app.enums import ReviewStatus, RiskLevel
from tests.fakes import InMemoryHistoryProvider, make_txn


class FixedRule(Rule):
    """Test-only rule (not registered) that always returns the given score."""

    name: ClassVar[str] = "fixed"
    description: ClassVar[str] = "test"

    def __init__(self, score: int, weight: float = 1.0, name: str = "fixed") -> None:
        super().__init__(weight=weight)
        self.fixed = score
        self.name = name  # type: ignore[misc]

    def evaluate(self, txn: TransactionData, history: HistoryProvider) -> RuleResult:
        return RuleResult(self.name, self.fixed > 0, self.fixed, "fixed")


class BrokenRule(FixedRule):
    def evaluate(self, txn: TransactionData, history: HistoryProvider) -> RuleResult:
        raise RuntimeError("boom")


def evaluate(*rules: Rule):
    return RuleEngine(list(rules), medium_threshold=40, high_threshold=70).evaluate(make_txn(), InMemoryHistoryProvider())


def test_no_hits_is_clean() -> None:
    result = evaluate(FixedRule(0))
    assert (result.total_score, result.risk_level, result.status, result.hits) == (0, RiskLevel.NONE, ReviewStatus.CLEAN, [])
    assert not result.should_notify


@pytest.mark.parametrize("score, level", [(39, RiskLevel.LOW), (40, RiskLevel.MEDIUM),
                                          (69, RiskLevel.MEDIUM), (70, RiskLevel.HIGH)])
def test_level_boundaries(score: int, level: RiskLevel) -> None:
    result = evaluate(FixedRule(score))
    assert result.risk_level == level and result.status == ReviewStatus.FLAGGED
    assert result.should_notify is (level == RiskLevel.HIGH)


def test_weights_and_sum() -> None:
    result = evaluate(FixedRule(40, weight=0.5, name="a"), FixedRule(30, weight=1.5, name="b"))
    assert result.total_score == 65  # 20 + 45
    assert [h.weighted_score for h in result.hits] == [20, 45]


def test_total_capped_at_100() -> None:
    assert evaluate(FixedRule(90, name="a"), FixedRule(90, name="b")).total_score == 100


def test_broken_rule_is_skipped(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        result = evaluate(BrokenRule(50, name="broken"), FixedRule(45, name="ok"))
    assert [h.result.rule_name for h in result.hits] == ["ok"]
    assert "Rule broken failed" in caplog.text


def write_yaml(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "rules.yaml"
    path.write_text(text)
    return path


def test_yaml_disables_and_overrides(tmp_path: Path) -> None:
    path = write_yaml(tmp_path, """
scoring: { medium_threshold: 30 }
rules:
  velocity: { enabled: false }
  unusual_amount: { weight: 0.5, params: { absolute_threshold: 500 } }
""")
    engine = RuleEngine.from_config(path, high_threshold=70)
    names = {r.name for r in engine.rules}
    assert "velocity" not in names and {"unusual_amount", "impossible_travel"} <= names
    amount_rule = next(r for r in engine.rules if r.name == "unusual_amount")
    assert amount_rule.weight == 0.5
    assert amount_rule.params["absolute_threshold"] == 500 and amount_rule.params["lookback"] == 50
    assert engine.medium_threshold == 30


def test_unknown_rule_in_yaml_only_warns(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    path = write_yaml(tmp_path, "rules:\n  no_such_rule: { enabled: true }\n")
    with caplog.at_level(logging.WARNING):
        engine = RuleEngine.from_config(path, high_threshold=70)
    assert "no_such_rule" in caplog.text
    assert len(engine.rules) >= 3


def test_describe_lists_every_rule(engine: RuleEngine) -> None:
    described = {d["name"]: d for d in engine.describe()}
    assert {"velocity", "unusual_amount", "impossible_travel"} <= described.keys()
    assert described["velocity"]["params"] == {"window_minutes": 10, "max_transactions": 5}
    assert described["velocity"]["enabled"] is True
