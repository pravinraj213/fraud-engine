from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_engine, get_notifier
from app.config import Settings
from app.database import get_db
from app.engine.engine import RuleEngine
from app.notifications.base import Notifier
from app.schemas import ReviewIn, TransactionDetailOut, TransactionIn
from app.services import query_service, review_service, transaction_service
from app.services.notification_service import notify_high_risk

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=TransactionDetailOut, status_code=status.HTTP_201_CREATED)
def ingest_transaction(
    body: TransactionIn,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    engine: RuleEngine = Depends(get_engine),
    notifier: Notifier = Depends(get_notifier),
    settings: Settings = Depends(get_app_settings),
) -> TransactionDetailOut:
    assessment, result = transaction_service.ingest(db, engine, body)
    if result.should_notify:
        background.add_task(notify_high_risk, assessment.id, notifier, settings)
    return query_service.build_detail(assessment)


@router.get("/{transaction_id}", response_model=TransactionDetailOut)
def get_transaction(transaction_id: str, db: Session = Depends(get_db)) -> TransactionDetailOut:
    return query_service.get_detail(db, transaction_id)


@router.post("/{transaction_id}/review", response_model=TransactionDetailOut)
def review_transaction(transaction_id: str, body: ReviewIn, db: Session = Depends(get_db)) -> TransactionDetailOut:
    return query_service.build_detail(review_service.review_transaction(db, transaction_id, body))
