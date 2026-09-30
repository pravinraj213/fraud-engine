from fastapi import Request

from app.config import Settings
from app.engine.engine import RuleEngine
from app.notifications.base import Notifier


def get_engine(request: Request) -> RuleEngine:
    return request.app.state.engine


def get_notifier(request: Request) -> Notifier:
    return request.app.state.notifier


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings
