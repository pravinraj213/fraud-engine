import statistics
from decimal import Decimal

from app.engine.base import HistoryProvider, Rule, RuleResult, TransactionData
from app.engine.registry import register_rule


def inr(amount: Decimal | float) -> str:
    return f"INR {amount:,.2f}"


@register_rule
class UnusualAmountRule(Rule):
    name = "unusual_amount"
    description = "Amount far above what this account normally spends."
    default_params = {"min_history": 5, "lookback": 50, "z_threshold": 3.0,
                      "median_multiplier": 5, "absolute_threshold": 100000}

    def evaluate(self, txn: TransactionData, history: HistoryProvider) -> RuleResult:
        amounts = history.recent_amounts(txn.account_id, txn.occurred_at, int(self.params["lookback"]))
        if len(amounts) < int(self.params["min_history"]):
            return self._cold_start(txn, len(amounts))
        return self._against_history(txn, [float(a) for a in amounts])

    def _cold_start(self, txn: TransactionData, history_size: int) -> RuleResult:
        limit = Decimal(str(self.params["absolute_threshold"]))
        if txn.amount < limit:
            return RuleResult(self.name, False)
        return RuleResult(
            self.name, True, 50,
            f"{inr(txn.amount)} exceeds the {inr(limit)} limit for accounts with little history "
            f"({history_size} prior transactions)",
            {"amount": float(txn.amount), "absolute_threshold": float(limit), "history_size": history_size},
        )

    def _against_history(self, txn: TransactionData, amounts: list[float]) -> RuleResult:
        amount = float(txn.amount)
        z_limit = float(self.params["z_threshold"])
        multiplier = float(self.params["median_multiplier"])
        mean, median, stdev = statistics.fmean(amounts), statistics.median(amounts), statistics.pstdev(amounts)
        ratio = amount / median
        z = (amount - mean) / stdev if stdev > 0 else None  # identical history: ratio test only

        z_hit = z is not None and z >= z_limit
        if not (z_hit or ratio >= multiplier):
            return RuleResult(self.name, False)
        strong = (z is not None and z >= 2 * z_limit) or ratio >= 2 * multiplier
        z_text = f" (z-score {z:.1f})" if z is not None else ""
        return RuleResult(
            self.name, True, 80 if strong else 50,
            f"{inr(txn.amount)} is {ratio:.1f}× this account's median of {inr(median)}{z_text}",
            {"amount": round(amount, 2), "mean": round(mean, 2), "median": round(median, 2),
             "stdev": round(stdev, 2), "z_score": round(z, 2) if z is not None else None,
             "ratio": round(ratio, 2), "history_size": len(amounts)},
        )
