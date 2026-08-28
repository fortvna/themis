"""Gated ladder floors. Computed from loaded bars, not from prompt.md dates."""
from __future__ import annotations

from dataclasses import dataclass, field

ASK_MIN_BARS = 100
RUN_MIN_BARS = 200
THIN_BARS = 4000
VALIDATE_HOLDOUT_MIN_BARS = 500
WALKFORWARD_MIN_BARS = 4000
WALKFORWARD_MIN_FOLDS = 3
KILL_MIN_TRADES = 30
KILL_MAX_DRAWDOWN_PCT = 40.0
KILL_MIN_NET_RETURN = 0.0

THIN_SYMBOLS_TODAY = ("XAUUSDT", "SPYUSDT", "QQQUSDT")  # documentary; bars decide


@dataclass
class Eligibility:
    n_bars: int
    holdout_n_bars: int = 0
    holdout_unused: bool = True
    costs_written: bool = False
    search_space: dict | None = None
    n_folds: int = 3
    kill_min_trades_ok: bool = True
    thin: bool = False
    ask_ok: bool = False
    run_ok: bool = False
    validate_ok: bool = False
    walkforward_ok: bool = False
    tune_ok: bool = False
    kept_ok: bool = False
    reasons: dict[str, str] = field(default_factory=dict)

    def refuse_message(self, gate: str) -> str:
        n = self.n_bars
        mapping = {
            "ask": f"ask floor n_bars >= {ASK_MIN_BARS}; actual n_bars={n}",
            "run": f"run floor n_bars >= {RUN_MIN_BARS} and costs written; actual n_bars={n} costs_written={self.costs_written}",
            "validate": (
                f"validate floor holdout unused and holdout_n_bars >= {VALIDATE_HOLDOUT_MIN_BARS}; "
                f"actual n_bars={n} holdout_n_bars={self.holdout_n_bars} holdout_unused={self.holdout_unused}"
            ),
            "walkforward": (
                f"walkforward floor n_bars >= {WALKFORWARD_MIN_BARS} and n_folds >= {WALKFORWARD_MIN_FOLDS}; "
                f"actual n_bars={n} n_folds={self.n_folds}"
            ),
            "tune": (
                f"tune requires walkforward_eligible and nonempty search_space; "
                f"actual n_bars={n} walkforward_ok={self.walkforward_ok} search_space={self.search_space!r}"
            ),
            "kept": (
                f"kept requires not thin, kill passed, one validate; "
                f"actual n_bars={n} thin={self.thin} validate_ok={self.validate_ok}"
            ),
        }
        return mapping.get(gate, f"unknown gate {gate}; n_bars={n}")


def evaluate(
    n_bars: int,
    *,
    holdout_n_bars: int = 0,
    holdout_unused: bool = True,
    costs_written: bool = False,
    search_space: dict | None = None,
    n_folds: int = 3,
    kill_min_trades_ok: bool = True,
) -> Eligibility:
    el = Eligibility(
        n_bars=int(n_bars),
        holdout_n_bars=int(holdout_n_bars),
        holdout_unused=bool(holdout_unused),
        costs_written=bool(costs_written),
        search_space=search_space,
        n_folds=int(n_folds),
        kill_min_trades_ok=bool(kill_min_trades_ok),
    )
    el.thin = el.n_bars < THIN_BARS or not el.kill_min_trades_ok
    el.ask_ok = el.n_bars >= ASK_MIN_BARS
    el.run_ok = el.costs_written and el.n_bars >= RUN_MIN_BARS
    el.validate_ok = el.holdout_unused and el.holdout_n_bars >= VALIDATE_HOLDOUT_MIN_BARS
    el.walkforward_ok = el.n_bars >= WALKFORWARD_MIN_BARS and el.n_folds >= WALKFORWARD_MIN_FOLDS
    space_ok = bool(search_space)
    el.tune_ok = el.walkforward_ok and space_ok
    el.kept_ok = (not el.thin) and el.validate_ok and el.kill_min_trades_ok
    if not el.ask_ok:
        el.reasons["ask"] = el.refuse_message("ask")
    if not el.run_ok:
        el.reasons["run"] = el.refuse_message("run")
    if el.thin:
        el.reasons["thin"] = f"thin: n_bars={el.n_bars} < {THIN_BARS} (or kill.min_trades cannot clear). cannot keep."
    if not el.validate_ok:
        el.reasons["validate"] = el.refuse_message("validate")
    if not el.walkforward_ok:
        el.reasons["walkforward"] = el.refuse_message("walkforward")
    if not el.tune_ok:
        el.reasons["tune"] = el.refuse_message("tune")
    if not el.kept_ok:
        el.reasons["kept"] = el.refuse_message("kept")
    return el


class FloorError(RuntimeError):
    """Named floor failed. Message includes the floor and actual n_bars."""


LIKELY_SHORT_VISION = frozenset({"XAUUSDT", "SPYUSDT", "QQQUSDT"})
KILL_DEFAULT = {
    "min_trades": KILL_MIN_TRADES,
    "max_drawdown_pct": KILL_MAX_DRAWDOWN_PCT,
    "min_net_return": KILL_MIN_NET_RETURN,
}


def is_thin(n_bars: int) -> bool:
    return int(n_bars) < THIN_BARS


def compile_time_flags(symbol: str) -> dict:
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
    el = evaluate(n_bars)
    if not el.ask_ok:
        raise FloorError(el.refuse_message("ask"))


def check_run(n_bars: int, costs, thin_ok: bool, yaml_run_eligible: bool | None) -> dict:
    costs_written = bool(isinstance(costs, dict) and costs)
    el = evaluate(n_bars, costs_written=costs_written)
    if not el.run_ok:
        raise FloorError(el.refuse_message("run"))
    if el.thin and not thin_ok:
        raise FloorError(
            f"run_eligible false / thin series n_bars={n_bars} < {THIN_BARS}; "
            "pass --thin (kept still impossible)"
        )
    if yaml_run_eligible is False and not thin_ok:
        raise FloorError(
            f"run_eligible false / thin series n_bars={n_bars} < {THIN_BARS}; "
            "pass --thin (kept still impossible)"
        )
    return {"thin": el.thin, "run_ok": True, "kept_possible": (not el.thin)}


def check_validate(n_bars: int, holdout_n_bars: int | None) -> None:
    h = 0 if holdout_n_bars is None else int(holdout_n_bars)
    el = evaluate(n_bars, holdout_n_bars=h, holdout_unused=True)
    if not el.validate_ok:
        raise FloorError(el.refuse_message("validate"))


def check_walkforward(n_bars: int, n_folds: int = WALKFORWARD_MIN_FOLDS) -> None:
    el = evaluate(n_bars, n_folds=n_folds)
    if not el.walkforward_ok:
        raise FloorError(el.refuse_message("walkforward"))


def check_tune(n_bars: int, n_folds: int, search_space, yaml_wf_eligible: bool | None = None) -> None:
    el = evaluate(n_bars, n_folds=n_folds, search_space=search_space or None)
    if not el.tune_ok:
        raise FloorError(el.refuse_message("tune"))
    if yaml_wf_eligible is False:
        raise FloorError(
            f"tune requires walkforward_eligible; yaml walkforward_eligible=false n_bars={n_bars}"
        )


def kept_possible(thin: bool, kill_passed: bool = False, validated: bool = False):
    if thin:
        return False, "kept impossible: thin=true"
    if not kill_passed:
        return False, "kept impossible: kill not passed"
    if not validated:
        return False, "kept impossible: no successful validate"
    return True, ""
