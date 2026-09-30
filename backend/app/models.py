import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.enums import ReviewAction, ReviewStatus, RiskLevel
from app.timeutils import utcnow


def new_id() -> str:
    return str(uuid.uuid4())


def _enum(cls: type) -> Enum:
    return Enum(cls, native_enum=False, length=16)


class Transaction(Base):
    """One incoming transaction. Never edited after insert."""

    __tablename__ = "transactions"
    __table_args__ = (Index("ix_transactions_account_occurred", "account_id", "occurred_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(String(64), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    merchant: Mapped[str] = mapped_column(String(128))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    location_label: Mapped[str | None] = mapped_column(String(128))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    assessment: Mapped["RiskAssessment"] = relationship(back_populates="transaction", uselist=False)


class RiskAssessment(Base):
    """The engine's verdict for one transaction, plus its review status."""

    __tablename__ = "risk_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"), unique=True)
    total_score: Mapped[int] = mapped_column(Integer)
    risk_level: Mapped[RiskLevel] = mapped_column(_enum(RiskLevel))
    status: Mapped[ReviewStatus] = mapped_column(_enum(ReviewStatus), index=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    transaction: Mapped[Transaction] = relationship(back_populates="assessment", lazy="joined")
    rule_hits: Mapped[list["RuleHit"]] = relationship(
        back_populates="assessment", lazy="selectin", order_by="RuleHit.score.desc()")
    reviews: Mapped[list["ReviewActionRecord"]] = relationship(
        lazy="selectin", order_by="ReviewActionRecord.created_at.desc()")
    notification: Mapped["Notification | None"] = relationship(lazy="selectin", uselist=False)


class RuleHit(Base):
    """One rule that triggered for an assessment. Rules that did not trigger are not stored."""

    __tablename__ = "rule_hits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("risk_assessments.id"), index=True)
    rule_name: Mapped[str] = mapped_column(String(64))
    score: Mapped[int] = mapped_column(Integer)
    weight: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(255))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    assessment: Mapped[RiskAssessment] = relationship(back_populates="rule_hits")


class ReviewActionRecord(Base):
    """Append-only audit trail of reviewer decisions."""

    __tablename__ = "review_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("risk_assessments.id"), index=True)
    action: Mapped[ReviewAction] = mapped_column(_enum(ReviewAction))
    from_status: Mapped[ReviewStatus] = mapped_column(_enum(ReviewStatus))
    to_status: Mapped[ReviewStatus] = mapped_column(_enum(ReviewStatus))
    reviewer: Mapped[str] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Notification(Base):
    """At most one alert per assessment; the unique constraint prevents duplicates."""

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("risk_assessments.id"), unique=True)
    channel: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    provider_message_id: Mapped[str | None] = mapped_column(String(128))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
