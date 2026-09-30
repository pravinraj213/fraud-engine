import uuid
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from app.engine.base import TransactionData
from app.notifications.base import AlertPayload, Notifier, SendResult

NOW = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)

CITIES: dict[str, tuple[float, float]] = {
    "Chennai, IN": (13.0827, 80.2707),
    "Bengaluru, IN": (12.9716, 77.5946),
    "Delhi, IN": (28.6139, 77.2090),
    "London, GB": (51.5072, -0.1276),
}


def make_txn(city: str = "Chennai, IN", minutes: float = 0, **overrides: Any) -> TransactionData:
    """A transaction with sensible defaults: Chennai, INR 1,000, at NOW + minutes."""
    lat, lon = CITIES[city]
    base = TransactionData(
        id=str(uuid.uuid4()), account_id="ACC-1", amount=Decimal("1000.00"), merchant="Test Store",
        latitude=lat, longitude=lon, occurred_at=NOW + timedelta(minutes=minutes), location_label=city,
    )
    if "amount" in overrides:
        overrides["amount"] = Decimal(str(overrides["amount"]))
    return replace(base, **overrides)


class InMemoryHistoryProvider:
    """HistoryProvider over a list of TransactionData, with the exact semantics of SqlHistoryProvider."""

    def __init__(self, transactions: list[TransactionData] | None = None) -> None:
        self.transactions = list(transactions or [])

    def _account(self, account_id: str, at: datetime) -> list[TransactionData]:
        rows = [t for t in self.transactions if t.account_id == account_id and t.occurred_at <= at]
        return sorted(rows, key=lambda t: t.occurred_at, reverse=True)

    def count_in_window(self, account_id: str, start: datetime, end: datetime) -> int:
        return sum(1 for t in self.transactions
                   if t.account_id == account_id and start <= t.occurred_at <= end)

    def recent_amounts(self, account_id: str, at: datetime, limit: int) -> list[Decimal]:
        return [t.amount for t in self._account(account_id, at)[:limit]]

    def previous_transaction(self, account_id: str, at: datetime) -> TransactionData | None:
        rows = self._account(account_id, at)
        return rows[0] if rows else None


class FakeNotifier(Notifier):
    """Records every alert; optionally fails."""

    channel = "log"

    def __init__(self, fail_with: str | None = None) -> None:
        self.sent: list[AlertPayload] = []
        self.fail_with = fail_with

    def send_high_risk_alert(self, alert: AlertPayload) -> SendResult:
        self.sent.append(alert)
        if self.fail_with:
            return SendResult(False, error=self.fail_with)
        return SendResult(True, provider_message_id=f"fake-{len(self.sent)}")
