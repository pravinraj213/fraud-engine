"""The rule engine. It only knows the Rule interface: never edit this file to add a rule."""
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.engine.base import HistoryProvider, Rule, RuleResult, TransactionData
from app.engine.config import EngineConfig, load_engine_config
from app.engine.registry import RULE_REGISTRY, discover_rules
from app.enums import ReviewStatus, RiskLevel

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuleHitResult:
    result: RuleResult
    weight: float

    @property
    def weighted_score(self) -> float:
        return self.result.score * self.weight


@dataclass(frozen=True)
class EngineResult:
    total_score: int
    risk_level: RiskLevel
    status: ReviewStatus
    hits: list[RuleHitResult]

    @property
    def should_notify(self) -> bool:
        return self.risk_level == RiskLevel.HIGH


class RuleEngine:
    def __init__(self, rules: list[Rule], medium_threshold: int, high_threshold: int,
                 config: EngineConfig | None = None) -> None:
        self.rules = rules
        self.medium_threshold = medium_threshold
        self.high_threshold = high_threshold
        self._config = config or EngineConfig(medium_threshold)

    @classmethod
    def from_config(cls, path: Path | str | None, high_threshold: int) -> "RuleEngine":
        discover_rules()
        config = load_engine_config(path)
        for name in config.rules:
            if name not in RULE_REGISTRY:
                logger.warning("rules.yaml names unknown rule %r; ignoring it", name)
        rules = [
            rule_cls(params=s.params, weight=s.weight)
            for name, rule_cls in RULE_REGISTRY.items()
            if (s := config.for_rule(name)).enabled
        ]
        logger.info("Rule engine loaded: %s", ", ".join(r.name for r in rules) or "no rules")
        return cls(rules, config.medium_threshold, high_threshold, config)

    def evaluate(self, txn: TransactionData, history: HistoryProvider) -> EngineResult:
        hits: list[RuleHitResult] = []
        for rule in self.rules:
            try:
                result = rule.evaluate(txn, history)
            except Exception:
                logger.exception("Rule %s failed on transaction %s; skipping it", rule.name, txn.id)
                continue
            if result.triggered:
                hits.append(RuleHitResult(result, rule.weight))

        total = min(100, round(sum(h.weighted_score for h in hits)))
        level = self._level(total, bool(hits))
        status = ReviewStatus.FLAGGED if hits else ReviewStatus.CLEAN
        return EngineResult(total, level, status, hits)

    def _level(self, total: int, triggered: bool) -> RiskLevel:
        if not triggered:
            return RiskLevel.NONE
        if total >= self.high_threshold:
            return RiskLevel.HIGH
        if total >= self.medium_threshold:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def describe(self) -> list[dict[str, Any]]:
        active = {r.name: r for r in self.rules}
        described = []
        for name, rule_cls in RULE_REGISTRY.items():
            settings = self._config.for_rule(name)
            rule = active.get(name)
            described.append({
                "name": name,
                "description": rule_cls.description,
                "enabled": rule is not None,
                "weight": rule.weight if rule else settings.weight,
                "params": rule.params if rule else {**rule_cls.default_params, **settings.params},
            })
        return described
