"""YAML is structure, not executed. Load and reject-invalid."""

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

ASK_PNL_KEYS = frozenset(
    {
        "pnl",
        "net_return",
        "expectancy",
        "profit",
        "return",
        "net_pnl",
        "calmar",
        "cagr",
        "sortino",
        "sharpe",
        "profit_factor",
    }
)


class SpecError(ValueError):
    pass


def load_yaml(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise SpecError(f"no spec: {p}")
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SpecError(f"spec is not a mapping: {p}")
    return data


def dump_yaml(obj: Any, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        yaml.safe_dump(obj, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def validate_question(spec: dict[str, Any]) -> None:
    missing = [k for k in QUESTION_REQUIRED if k not in spec]
    if missing:
        raise SpecError(f"question spec missing {missing}")
    if spec.get("kind") != "question":
        raise SpecError(f"expected kind=question, got {spec.get('kind')}")
    defs = spec.get("definitions") or {}
    if not isinstance(defs, dict) or not defs:
        raise SpecError("definitions must be explicit (no empty, no ...)")
    if any(v == "..." or v is None for v in defs.values()):
        raise SpecError("definitions must be explicit; no '...'" )


def validate_strategy(spec: dict[str, Any]) -> None:
    missing = [k for k in STRATEGY_REQUIRED if k not in spec]
    if missing:
        raise SpecError(f"strategy spec missing {missing}")
    if spec.get("kind") != "strategy":
        raise SpecError(f"expected kind=strategy, got {spec.get('kind')}")
    rules = spec.get("rules") or {}
    for key in ("fill", "entry", "stop", "target"):
        if key not in rules:
            raise SpecError(f"strategy rules missing {key}")


def validate_spec(spec: dict[str, Any]) -> None:
    kind = spec.get("kind")
    if kind == "question":
        validate_question(spec)
    elif kind == "strategy":
        validate_strategy(spec)
    else:
        raise SpecError(f"unknown kind {kind!r}; no spec, no run")


def looks_like_return_question(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in ("return", "pnl", "drawdown", "expectancy", "what is the edge"))


def reject_ask_pnl(metrics: dict[str, Any]) -> None:
    bad = [k for k in metrics.keys() if k.lower() in ASK_PNL_KEYS or k.lower().startswith("pnl")]
    if bad:
        raise SpecError(f"ask must not write pnl keys: {bad}")
