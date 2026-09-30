import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import flags, health, rules, stats, system, transactions
from app.config import Settings, get_settings
from app.database import create_tables
from app.engine.engine import RuleEngine
from app.notifications.base import Notifier
from app.notifications.factory import get_notifier
from app.services.errors import ConflictError, NotFoundError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app(settings: Settings | None = None, notifier: Notifier | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        create_tables()
        app.state.settings = settings
        app.state.engine = RuleEngine.from_config(settings.rules_config_path, settings.high_risk_threshold)
        app.state.notifier = notifier or get_notifier(settings)
        yield

    app = FastAPI(title="Fraud Rule Engine", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list,
                       allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(NotFoundError)
    async def not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ConflictError)
    async def conflict(_: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    api = APIRouter(prefix="/api")
    for module in (health, transactions, flags, stats, rules, system):
        api.include_router(module.router)
    app.include_router(api)
    return app


app = create_app()
