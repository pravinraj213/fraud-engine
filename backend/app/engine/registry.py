import importlib
import pkgutil

from app.engine.base import Rule

RULE_REGISTRY: dict[str, type[Rule]] = {}


def register_rule(cls: type[Rule]) -> type[Rule]:
    if cls.name in RULE_REGISTRY:
        raise ValueError(f"Duplicate rule name: {cls.name}")
    RULE_REGISTRY[cls.name] = cls
    return cls


def discover_rules(package: str = "app.engine.rules") -> None:
    """Import every module in the rules package so their @register_rule decorators run."""
    pkg = importlib.import_module(package)
    for module in pkgutil.iter_modules(pkg.__path__):
        if not module.name.startswith("_"):
            importlib.import_module(f"{package}.{module.name}")
