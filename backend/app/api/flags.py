from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import RiskLevel
from app.repositories.assessments import FlagFilter
from app.schemas import FlagListOut
from app.services import query_service

router = APIRouter(tags=["flags"])


@router.get("/flags", response_model=FlagListOut)
def list_flags(
    status: Literal["FLAGGED", "REVIEWED", "CLEARED", "ALL"] = "FLAGGED",
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] | None = None,
    account_id: str | None = Query(None, max_length=64),
    sort: Literal["score", "newest"] = "score",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> FlagListOut:
    f = FlagFilter(status=status, risk_level=RiskLevel(risk_level) if risk_level else None,
                   account_id=account_id or None, sort=sort, limit=limit, offset=offset)
    return query_service.list_flags(db, f)
