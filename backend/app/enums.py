from enum import StrEnum


class RiskLevel(StrEnum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ReviewStatus(StrEnum):
    CLEAN = "CLEAN"
    FLAGGED = "FLAGGED"
    REVIEWED = "REVIEWED"
    CLEARED = "CLEARED"


class ReviewAction(StrEnum):
    REVIEWED = "REVIEWED"
    CLEARED = "CLEARED"


class NotificationStatus(StrEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
