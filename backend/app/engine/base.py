from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, ClassVar, Protocol


@dataclass(frozen=True)
class TransactionData:
    id: str
    account_id: str
    amount: Decimal
    merchant: str
    latitude: float
    longitude: float
    occurred_at: datetime
    location_label: str | None = None


@dataclass(frozen=True)
class RuleResult:
    rule_name: str
    triggered: bool
    score: int = 0            # 0-100, before weighting
    reason: str = ""          # one sentence for the reviewer
    details: dict[str, Any] = field(default_factory=dict)


class HistoryProvider(Protocol):
    """Read-only view of the account's STORED transactions.
    The transaction being evaluated is not stored yet, so it is never returned."""

    def count_in_window(self, account_id: str, start: datetime, end: datetime) -> int: ...
    def recent_amounts(self, account_id: str, at: datetime, limit: int) -> list[Decimal]: ...
    def previous_transaction(self, account_id: str, at: datetime) -> TransactionData | None: ...


class Rule(ABC):
    name: ClassVar[str]
    description: ClassVar[str]
    default_params: ClassVar[dict[str, Any]] = {}

    def __init__(self, params: dict[str, Any] | None = None, weight: float = 1.0) -> None:
        self.params = {**self.default_params, **(params or {})}
        self.weight = weight

    @abstractmethod
    def evaluate(self, txn: TransactionData, history: HistoryProvider) -> RuleResult: ...
