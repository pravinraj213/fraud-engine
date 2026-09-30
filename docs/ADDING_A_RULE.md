# Adding a rule

Adding a fraud rule means adding **one file** to `backend/app/engine/rules/`. You never edit
`engine.py`, the API, or the database: the engine discovers the file at startup, and the rule's
hits are stored and shown in the console like any other.

## 1. Write the rule

Worked example: flag purchases at merchants on a blocked list.

```python
# backend/app/engine/rules/blocked_merchant.py
from app.engine.base import HistoryProvider, Rule, RuleResult, TransactionData
from app.engine.registry import register_rule


@register_rule
class BlockedMerchantRule(Rule):
    name = "blocked_merchant"
    description = "Transaction at a merchant on the blocked list."
    default_params = {"merchants": ["Shady Crypto Exchange"]}

    def evaluate(self, txn: TransactionData, history: HistoryProvider) -> RuleResult:
        blocked = {m.lower() for m in self.params["merchants"]}
        if txn.merchant.lower() in blocked:
            return RuleResult(self.name, True, 60, f"Merchant '{txn.merchant}' is on the blocked list")
        return RuleResult(self.name, False)
```

The contract:

- `name` must be unique; registering a duplicate raises `ValueError` at startup.
- `evaluate` returns `RuleResult(name, triggered, score 0–100, reason, details)`. `reason` is one
  sentence a reviewer reads; `details` is a JSON-safe dict (no `inf`/`nan`).
- Use `history` for anything about past transactions. It only returns **stored** transactions, never
  the one being evaluated:
  - `count_in_window(account_id, start, end)`: count with `start <= occurred_at <= end`
  - `recent_amounts(account_id, at, limit)`: amounts with `occurred_at <= at`, newest first
  - `previous_transaction(account_id, at)`: the latest one with `occurred_at <= at`
- If the rule raises, the engine logs it and skips the rule, so one bug never blocks ingestion.

## 2. Configure it (optional)

A rule missing from `backend/rules.yaml` runs enabled, with weight 1.0 and its `default_params`.
To tune it, add an entry:

```yaml
rules:
  blocked_merchant:
    enabled: true
    weight: 1.0
    params: { merchants: ["Shady Crypto Exchange", "Totally Legit Gift Cards"] }
```

The weighted scores of every triggered rule are summed and capped at 100: LOW below 40, MEDIUM from 40,
HIGH (email alert) from `HIGH_RISK_THRESHOLD` (70).

## 3. Test it

Unit-test it with `tests/fakes.py` (`make_txn`, `InMemoryHistoryProvider`); no database needed:

```python
from app.engine.rules.blocked_merchant import BlockedMerchantRule
from tests.fakes import InMemoryHistoryProvider, make_txn


def test_blocked_merchant() -> None:
    rule = BlockedMerchantRule()
    assert rule.evaluate(make_txn(merchant="Shady Crypto Exchange"), InMemoryHistoryProvider()).score == 60
    assert not rule.evaluate(make_txn(), InMemoryHistoryProvider()).triggered
```

Then restart the API (`--reload` picks up the new file) and check it is listed at
`GET /api/rules`.
