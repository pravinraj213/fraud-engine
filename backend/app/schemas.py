from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.enums import ReviewAction, ReviewStatus, RiskLevel

Text64 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
Text128 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]


class TransactionIn(BaseModel):
    account_id: Text64
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")] = "INR"
    merchant: Text128
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    location_label: Annotated[str, StringConstraints(strip_whitespace=True, max_length=128)] | None = None
    occurred_at: datetime | None = None


class TransactionOut(BaseModel):
    id: str
    account_id: str
    amount: Decimal
    currency: str
    merchant: str
    latitude: float
    longitude: float
    location_label: str | None
    occurred_at: datetime
    created_at: datetime


class AssessmentOut(BaseModel):
    total_score: int
    risk_level: RiskLevel
    status: ReviewStatus
    evaluated_at: datetime
    updated_at: datetime


class RuleHitOut(BaseModel):
    rule_name: str
    score: int
    weight: float
    weighted_score: float
    reason: str
    details: dict[str, Any]


class ReviewOut(BaseModel):
    action: ReviewAction
    from_status: ReviewStatus
    to_status: ReviewStatus
    reviewer: str
    note: str | None
    created_at: datetime


class NotificationOut(BaseModel):
    channel: str
    status: str
    created_at: datetime
    error: str | None


class TransactionDetailOut(BaseModel):
    transaction: TransactionOut
    assessment: AssessmentOut
    rule_hits: list[RuleHitOut]
    reviews: list[ReviewOut]
    notification: NotificationOut | None
    allowed_actions: list[ReviewAction]


class FlagSummaryOut(BaseModel):
    transaction_id: str
    account_id: str
    amount: Decimal
    currency: str
    merchant: str
    location_label: str | None
    occurred_at: datetime
    total_score: int
    risk_level: RiskLevel
    status: ReviewStatus
    rules_triggered: list[str]
    notification_status: str | None
    notification_channel: str | None    # "ses" (email) or "log" (server log only)


class FlagListOut(BaseModel):
    items: list[FlagSummaryOut]
    total: int


class ReviewIn(BaseModel):
    action: ReviewAction
    reviewer: Text64
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] | None = None


class StatsOut(BaseModel):
    by_status: dict[str, int]
    flagged_by_level: dict[str, int]
    notifications: dict[str, int]


class SystemOut(BaseModel):
    notifier: str               # "ses" sends real email, "log" only writes to the server log
    medium_threshold: int
    high_risk_threshold: int
    alert_recipients: list[str]
    email_configured: bool


class NotificationModeIn(BaseModel):
    model_config = {"extra": "forbid"}
    enabled: bool = Field(strict=True)


class TestEmailIn(BaseModel):
    model_config = {"extra": "forbid"}
    recipient: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=3,
            max_length=254,
            pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        ),
    ]
    consent_confirmed: Literal[True]


class TestEmailOut(BaseModel):
    sent: bool
    recipients: list[str]
    provider_message_id: str | None


class RuleOut(BaseModel):
    name: str
    description: str
    enabled: bool
    weight: float
    params: dict[str, Any]
