from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import BACKEND_DIR, Settings
from app.database import configure_database
from app.engine.engine import RuleEngine
from app.engine.registry import RULE_REGISTRY, discover_rules
from tests.fakes import FakeNotifier

RULES_YAML = BACKEND_DIR / "rules.yaml"


@pytest.fixture
def clean_registry() -> Iterator[None]:
    """Restore the rule registry after a test registers its own rules."""
    discover_rules()
    saved = dict(RULE_REGISTRY)
    yield
    RULE_REGISTRY.clear()
    RULE_REGISTRY.update(saved)


@pytest.fixture
def engine() -> RuleEngine:
    """The real engine with the three real rules and the repo's rules.yaml."""
    return RuleEngine.from_config(RULES_YAML, high_threshold=70)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(_env_file=None, database_url=f"sqlite:///{tmp_path / 'test.db'}",
                    rules_config_path=RULES_YAML, notifier="log",
                    console_base_url="http://console.test")


@pytest.fixture
def notifier() -> FakeNotifier:
    return FakeNotifier()


@pytest.fixture
def client(settings: Settings, notifier: FakeNotifier) -> Iterator[TestClient]:
    """API client on a temporary SQLite file, with a FakeNotifier that records alerts."""
    from app.main import create_app

    db_engine = configure_database(settings.database_url)
    with TestClient(create_app(settings, notifier)) as c:
        yield c
    db_engine.dispose()
