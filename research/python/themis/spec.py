"""Load and reject-invalid question / strategy YAML."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

QUESTION_REQUIRED = (
    "id",
    "kind",
    "instrument",
    "data",
    "discovery",
    "holdout",
    "population",
    "condition",
    "outcome",
    "definitions",
    "stats",
    "forbidden",
)
STRATEGY_REQUIRED = (
    "id",
    "kind",
    "family",
    "implements",
    "requires_asks",
    "instrument",
    "data",
    "discovery",
    "holdout",
    "costs",
    "rules",
    "forbidden",
    "kill",
    "search_space",
    "run_eligible",
    "walkforward_eligible",
    "tune_eligible",
)
RULE_KEYS = ("fill", "entry", "stop", "target")
PNL_KEYS = frozenset(
    {"pnl", "net_return", "expectancy", "return", "profit", "net_pnl", "equity"}
)


class SpecError(ValueError):
    pass


def load_yaml(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise SpecError(f"no spec: {p}")
    data = yaml.safe_load(p.read_text())
    if not isinstance(data, dict):
        raise SpecError(f"spec is not a mapping: {p}")
    return data


def dump_yaml(data: dict[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def _missing(spec: dict, required: tuple[str, ...]) -> list[str]:
    return [k for k in required if k not in spec]


def _ellipsis_in_definitions(defs: Any) -> bool:
    if isinstance(defs, str):
        return "..." in defs or defs.strip() == "…"
    if isinstance(defs, dict):
        return any(_ellipsis_in_definitions(v) for v in defs.values())
    if isinstance(defs, list):
        return any(_ellipsis_in_definitions(v) for v in defs)
    return False


def validate_question(spec: dict[str, Any]) -> dict[str, Any]:
    miss = _missing(spec, QUESTION_REQUIRED)
    if miss:
        raise SpecError(f"question missing {miss}")
    if spec.get("kind") != "question":
        raise SpecError(f"kind must be question, got {spec.get('kind')!r}")
    if _ellipsis_in_definitions(spec.get("definitions")):
        raise SpecError("definitions must be explicit; no '...' ".replace(" '", " '"))
    hold = spec.get("holdout") or {}
    if hold.get("start") is None and not hold.get("note"):
        raise SpecError("holdout may be null only with a note")
    inst = spec.get("instrument") or {}
    if not inst.get("symbol") or not (inst.get("venue") or inst.get("provider")):
        raise SpecError("instrument needs symbol and venue/provider")
    return spec


def validate_strategy(spec: dict[str, Any]) -> dict[str, Any]:
    miss = _missing(spec, STRATEGY_REQUIRED)
    if miss:
        raise SpecError(f"strategy missing {miss}")
    if spec.get("kind") != "strategy":
        raise SpecError(f"kind must be strategy, got {spec.get('kind')!r}")
    rules = spec.get("rules") or {}
    for k in RULE_KEYS:
        if k not in rules:
            raise SpecError(f"rules missing {k}")
    costs = spec.get("costs")
    if not isinstance(costs, dict) or not costs:
        raise SpecError("strategy costs must be written (zero only as 0 plus a reason)")
    return spec


def load_spec(path: str | Path) -> dict[str, Any]:
    spec = load_yaml(path)
    kind = spec.get("kind")
    if kind == "question":
        return validate_question(spec)
    if kind == "strategy":
        return validate_strategy(spec)
    raise SpecError(f"unknown kind {kind!r} in {path}")


def is_return_question(english_or_spec: Any) -> bool:
    """True when the operator asked for return/pnl with no strategy spec."""
    if isinstance(english_or_spec, dict):
        if english_or_spec.get("kind") == "strategy":
            return False
        blob = " ".join(
            str(english_or_spec.get(k, ""))
            for k in ("title", "hypothesis", "id")
        ).lower()
    else:
        blob = str(english_or_spec).lower()
    needles = ("return", "pnl", "drawdown", "expectancy", "edge after costs")
    return any(n in blob for n in needles)
