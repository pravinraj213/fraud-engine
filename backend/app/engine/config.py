import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DEFAULT_MEDIUM_THRESHOLD = 40


@dataclass(frozen=True)
class RuleSettings:
    enabled: bool = True
    weight: float = 1.0
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EngineConfig:
    medium_threshold: int = DEFAULT_MEDIUM_THRESHOLD
    rules: dict[str, RuleSettings] = field(default_factory=dict)

    def for_rule(self, name: str) -> RuleSettings:
        """Settings for one rule; a rule missing from the YAML runs enabled with its defaults."""
        return self.rules.get(name, RuleSettings())


def load_engine_config(path: Path | str | None) -> EngineConfig:
    if path is None or not Path(path).exists():
        logger.warning("Rules config %s not found; using defaults for every rule", path)
        return EngineConfig()
    raw = yaml.safe_load(Path(path).read_text()) or {}
    scoring = raw.get("scoring") or {}
    rules = {
        name: RuleSettings(
            enabled=bool(cfg.get("enabled", True)),
            weight=float(cfg.get("weight", 1.0)),
            params=dict(cfg.get("params") or {}),
        )
        for name, cfg in (raw.get("rules") or {}).items()
    }
    return EngineConfig(int(scoring.get("medium_threshold", DEFAULT_MEDIUM_THRESHOLD)), rules)
