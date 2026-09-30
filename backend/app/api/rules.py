from fastapi import APIRouter, Depends

from app.api.deps import get_engine
from app.engine.engine import RuleEngine
from app.schemas import RuleOut

router = APIRouter(tags=["rules"])


@router.get("/rules", response_model=list[RuleOut])
def list_rules(engine: RuleEngine = Depends(get_engine)) -> list[RuleOut]:
    return [RuleOut(**r) for r in engine.describe()]
