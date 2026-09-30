from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import ClassVar


@dataclass(frozen=True)
class AlertPayload:
    assessment_id: str
    transaction_id: str
    account_id: str
    amount: Decimal
    currency: str
    merchant: str
    location_label: str | None
    occurred_at: datetime
    total_score: int
    risk_level: str
    hits: list[tuple[str, int, str]]   # (rule_name, score, reason)
    console_url: str                   # f"{CONSOLE_BASE_URL}/transactions/{transaction_id}"


@dataclass(frozen=True)
class SendResult:
    success: bool
    provider_message_id: str | None = None
    error: str | None = None


class Notifier(ABC):
    channel: ClassVar[str]

    @abstractmethod
    def send_high_risk_alert(self, alert: AlertPayload) -> SendResult: ...
