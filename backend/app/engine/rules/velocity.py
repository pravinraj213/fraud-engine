from datetime import timedelta

from app.engine.base import HistoryProvider, Rule, RuleResult, TransactionData
from app.engine.registry import register_rule


@register_rule
class VelocityRule(Rule):
    name = "velocity"
    description = "Too many transactions on one account in a short window."
    default_params = {"window_minutes": 10, "max_transactions": 5}

    def evaluate(self, txn: TransactionData, history: HistoryProvider) -> RuleResult:
        window = int(self.params["window_minutes"])
        limit = int(self.params["max_transactions"])
        start = txn.occurred_at - timedelta(minutes=window)
        count = history.count_in_window(txn.account_id, start, txn.occurred_at) + 1
        if count <= limit:
            return RuleResult(self.name, False)
        score = min(100, 40 + 15 * (count - limit - 1))
        return RuleResult(
            self.name, True, score,
            f"{count} transactions in {window} minutes (limit {limit})",
            {"count": count, "window_minutes": window, "max_transactions": limit},
        )
