"""Floors from actual loaded bars. Do not hard-code 'gold never validates'."""

from __future__ import annotations

from typing import Any

ASK_MIN_BARS = 100
RUN_MIN_BARS = 200
THIN_BARS = 4000
VALIDATE_HOLDOUT_MIN_BARS = 500
WALKFORWARD_MIN_BARS = 4000
WALKFORWARD_MIN_FOLDS = 3

KILL_DEFAULT = {
    "min_trades": 30,
    "max_drawdown_pct": 40,
    "min_net_return": 0,
}

LIKELY_SHORT_VISION = frozenset({"XAUUSDT", "SPYUSDT", "QQQUSDT"})


class FloorError(RuntimeError):
    """Named floor failed. Message includes the floor and actual n_bars."""


def is_thin(n_bars: int) -> bool:
    return int(n_bars) < THIN_BARS


def compile_time_flags(symbol: str) -> dict[str, bool]:
    """YAML flags when bars have not been loaded yet.

    Not 'gold never validates'. Short-history names today are typically thin;
    the engine still enforces numeric floors on actual n_bars.
    """
    short = (symbol or "").upper() in LIKELY_SHORT_VISION
    return {
        "run_eligible": not short,
        "walkforward_eligible": not short,
        "tune_eligible": False if short else True,
        "thin": short,
    }


def identity_label(symbol: str) -> str:
    s = (symbol or "").upper()
    if s == "XAUUSDT":
        return "Binance USD-M XAUUSDT perp. Not COMEX. Not another venue."
    if s == "SPYUSDT":
        return "Binance USD-M SPYUSDT ETF perp. Not ES. Not e-mini."
    if s == "QQQUSDT":
        return "Binance USD-M QQQUSDT ETF perp. Not NQ. Not e-mini."
    if s == "BTCUSDT":
        return "Binance USD-M BTCUSDT perp."
    if s == "SOLUSDT":
        return "Binance USD-M SOLUSDT perp."
    return f"Binance USD-M {s} perp."


def check_ask(n_bars: int) -> None:
    if n_bars < ASK_MIN_BARS:
        raise FloorError(f"ask floor n_bars>={ASK_MIN_BARS} failed: n_bars={n_bars}")


def check_run(n_bars: int, costs: Any, thin_ok: bool, yaml_run_eligible: bool | None) -> dict[str, Any]:
    if n_bars < RUN_MIN_BARS:
        raise FloorError(f"run floor n_bars>={RUN_MIN_BARS} failed: n_bars={n_bars}")
    if not _costs_written(costs):
        raise FloorError("run floor costs written failed: no costs (zero only as written 0 plus a reason)")
    thin = is_thin(n_bars)
    blocked = thin or (yaml_run_eligible is False)
    if blocked and not thin_ok:
        raise FloorError(
            f"run_eligible false / thin series n_bars={n_bars} < {THIN_BARS}; "
            "pass --thin (kept still impossible)"
        )
    return {"thin": thin, "run_ok": True, "kept_possible": (not thin)}


def check_validate(n_bars: int, holdout_n_bars: int | None) -> None:
    h = 0 if holdout_n_bars is None else int(holdout_n_bars)
    if h < VALIDATE_HOLDOUT_MIN_BARS:
        raise FloorError(
            f"validate floor holdout_n_bars>={VALIDATE_HOLDOUT_MIN_BARS} failed: "
            f"holdout_n_bars={h} n_bars={n_bars}"
        )


def check_walkforward(n_bars: int, n_folds: int = WALKFORWARD_MIN_FOLDS) -> None:
    reasons = []
    if n_bars < WALKFORWARD_MIN_BARS:
        reasons.append(f"walkforward floor n_bars>={WALKFORWARD_MIN_BARS} failed: n_bars={n_bars}")
    if n_folds < WALKFORWARD_MIN_FOLDS:
        reasons.append(f"walkforward floor n_folds>={WALKFORWARD_MIN_FOLDS} failed: n_folds={n_folds}")
    if reasons:
        raise FloorError("; ".join(reasons))


def check_tune(n_bars: int, n_folds: int, search_space: Any, yaml_wf_eligible: bool | None = None) -> None:
    empty = search_space is None or search_space == {} or search_space == []
    if empty:
        raise FloorError("tune requires nonempty search_space")
    try:
        check_walkforward(n_bars, n_folds)
        wf_ok = True
    except FloorError as e:
        wf_ok = False
        wf_msg = str(e)
    if yaml_wf_eligible is False:
        wf_ok = False
        wf_msg = (
            f"tune requires walkforward_eligible; yaml walkforward_eligible=false "
            f"n_bars={n_bars}"
        )
    if not wf_ok:
        raise FloorError(f"tune requires walkforward_eligible: {wf_msg}")


def kept_possible(thin: bool, kill_passed: bool = False, validated: bool = False) -> tuple[bool, str]:
    if thin:
        return False, "kept impossible: thin=true"
    if not kill_passed:
        return False, "kept impossible: kill not passed"
    if not validated:
        return False, "kept impossible: no successful validate"
    return True, ""


def _costs_written(costs: Any) -> bool:
    if not isinstance(costs, dict) or not costs:
        return False
    val = costs.get("commission_per_side", costs.get("commission", costs.get("fee")))
    if val is None:
        return False
    try:
        if float(val) == 0.0 and not costs.get("reason") and not costs.get("notes"):
            return False
    except (TypeError, ValueError):
        return False
    return True
