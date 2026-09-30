import pytest

from app.config import BACKEND_DIR
from app.engine.base import HistoryProvider, Rule, RuleResult, TransactionData
from app.engine.engine import RuleEngine
from app.engine.registry import RULE_REGISTRY, register_rule
from tests.fakes import InMemoryHistoryProvider, make_txn


@pytest.mark.usefixtures("clean_registry")
def test_new_rule_runs_without_editing_engine() -> None:
    """The extensibility requirement: a rule defined only here is discovered and run."""

    @register_rule
    class DummyRule(Rule):
        name = "dummy"
        description = "Always triggers (test only)."

        def evaluate(self, txn: TransactionData, history: HistoryProvider) -> RuleResult:
            return RuleResult(self.name, True, 25, "dummy fired")

    engine = RuleEngine.from_config(BACKEND_DIR / "rules.yaml", high_threshold=70)
    result = engine.evaluate(make_txn(), InMemoryHistoryProvider())
    assert [h.result.rule_name for h in result.hits] == ["dummy"]
    assert any(d["name"] == "dummy" for d in engine.describe())


@pytest.mark.usefixtures("clean_registry")
def test_duplicate_rule_name_raises() -> None:
    class Twin(Rule):
        name = "velocity"
        description = "duplicate"

        def evaluate(self, txn: TransactionData, history: HistoryProvider) -> RuleResult:
            return RuleResult(self.name, False)

    with pytest.raises(ValueError, match="Duplicate rule name: velocity"):
        register_rule(Twin)


@pytest.mark.usefixtures("clean_registry")
def test_discovery_finds_the_three_rules() -> None:
    assert {"velocity", "unusual_amount", "impossible_travel"} <= RULE_REGISTRY.keys()
