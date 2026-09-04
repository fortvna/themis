"""§18 strategy metrics. Bar-indexed equity. Never ask. Never 252 on a perp."""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

NOT_MODELED = [
    "perp funding",
    "intra-bar stop/target path",
]

# Binance USD-M v1 books. Overridden by costs.tick_size when written.
DEFAULT_TICK_SIZE = {
    "BTCUSDT": 0.1,
    "SOLUSDT": 0.01,
    "XAUUSDT": 0.01,
    "SPYUSDT": 0.01,
    "QQQUSDT": 0.01,
}

MUST = (
    "n_trades",
    "pnl",
    "net_return",
    "max_drawdown_pct",
    "cagr",
    "calmar",
    "sharpe",
    "sortino",
    "profit_factor",
    "expectancy",
    "win_rate",
    "payoff_ratio",
    "kill_pass",
)


def _num(x: Any) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return v


def hours_per_bar(timeframe: str) -> float:
    s = (timeframe or "4h").strip().lower().replace("min", "m")
    if s in {"d", "1day", "daily"}:
        return 24.0
    if s.endswith("h") and s[:-1]:
        return float(s[:-1])
    if s.endswith("m") and s[:-1]:
        return float(s[:-1]) / 60.0
    if s.endswith("d") and s[:-1]:
        return float(s[:-1]) * 24.0
    return 4.0


def periods_per_year(timeframe: str) -> float:
    tf = (timeframe or "4h").strip().lower()
    table = {"1h": 8760.0, "4h": 2190.0, "1d": 365.0, "d": 365.0, "daily": 365.0}
    if tf in table:
        return table[tf]
    h = hours_per_bar(tf)
    if h <= 0:
        return 2190.0
    return 365.0 * 24.0 / h


def window_years(index: pd.Index | None) -> float:
    if index is None or len(index) < 2:
        return 0.0
    a, b = index[0], index[-1]
    try:
        sec = (pd.Timestamp(b) - pd.Timestamp(a)).total_seconds()
    except Exception:
        return 0.0
    if sec <= 0:
        return 0.0
    return float(sec) / (365.25 * 86400.0)


def tick_size(symbol: str | None, costs: dict[str, Any] | None) -> float:
    costs = costs or {}
    if costs.get("tick_size") is not None:
        v = _num(costs.get("tick_size"))
        if v is not None and v >= 0:
            return v
    return float(DEFAULT_TICK_SIZE.get((symbol or "").upper(), 0.01))


def slip_price(symbol: str | None, costs: dict[str, Any] | None) -> float:
    costs = costs or {}
    ticks = _num(costs.get("slippage_ticks")) or 0.0
    if ticks <= 0:
        return 0.0
    return float(ticks) * tick_size(symbol, costs)


def equity_on_bars(n_bars: int, e0: float, exit_i: list[int] | np.ndarray, pnls: list[float] | np.ndarray) -> np.ndarray:
    """E[i] = e0 + sum of pnl for trades with exit_i <= i. Length n_bars."""
    n = int(n_bars)
    if n <= 0:
        return np.array([], dtype=float)
    add = np.zeros(n, dtype=float)
    for i, p in zip(exit_i, pnls):
        ii = int(i)
        if 0 <= ii < n:
            add[ii] += float(p)
    return float(e0) + np.cumsum(add)


def max_drawdown_pct(equity: np.ndarray, e0: float | None = None) -> float | None:
    if equity is None:
        return None
    eq = np.asarray(equity, dtype=float)
    if eq.size == 0:
        return None
    if e0 is not None and math.isfinite(float(e0)):
        seq = np.concatenate(([float(e0)], eq))
    else:
        seq = eq
    peak = seq[0]
    worst = 0.0
    for x in seq:
        if x > peak:
            peak = x
        if peak > 0:
            dd = (peak - x) / peak
            if dd > worst:
                worst = dd
    return float(worst * 100.0)


def _kill(metrics: dict[str, Any], kill: dict[str, Any] | None) -> tuple[bool, list[str]]:
    kill = kill or {}
    failed: list[str] = []
    min_trades = int(kill.get("min_trades") or 30)
    max_dd = float(kill.get("max_drawdown_pct") if kill.get("max_drawdown_pct") is not None else 40)
    min_ret = float(kill.get("min_net_return") if kill.get("min_net_return") is not None else 0)
    n = int(metrics.get("n_trades") or 0)
    dd = metrics.get("max_drawdown_pct")
    nr = metrics.get("net_return")
    if n < min_trades:
        failed.append("min_trades")
    if dd is None or float(dd) > max_dd:
        failed.append("max_drawdown_pct")
    if nr is None or float(nr) < min_ret:
        failed.append("min_net_return")
    return (len(failed) == 0), failed


def strategy_metrics(
    *,
    trades: pd.DataFrame,
    equity: np.ndarray,
    e0: float,
    index: pd.Index,
    timeframe: str,
    kill: dict[str, Any] | None = None,
    rf: float = 0.0,
    mar: float = 0.0,
    n_ambiguous: int = 0,
    n_gap: int = 0,
    symbol: str | None = None,
    costs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Canon keys. Missing ratios go in not_computed with a reason. Never invent."""
    not_computed: dict[str, str] = {}
    e0f = float(e0) if e0 is not None else 0.0
    eq = np.asarray(equity, dtype=float)
    n_tr = 0 if trades is None else int(len(trades))
    pnls = np.asarray(trades["pnl"].to_numpy(dtype=float) if n_tr and "pnl" in trades.columns else [], dtype=float)
    pnl = float(pnls.sum()) if n_tr else 0.0
    e_end = float(eq[-1]) if eq.size else e0f

    out: dict[str, Any] = {
        "n_trades": n_tr,
        "pnl": round(pnl, 6),
        "notional": "1_unit",
        "pnl_unit": "price",
        "calmar_window": "full_sample",
        "n_ambiguous": int(n_ambiguous),
        "n_gap": int(n_gap),
        "same_bar_policy": "ambiguous_tagged_fill_stop",
        "gap_policy": "fill_at_open",
    }

    if e0f <= 0:
        out["net_return"] = None
        not_computed["net_return"] = "E0 <= 0"
    else:
        out["net_return"] = round((e_end - e0f) / e0f, 6)

    if eq.size == 0:
        out["max_drawdown_pct"] = None
        not_computed["max_drawdown_pct"] = "empty equity"
        dd = None
    else:
        dd = max_drawdown_pct(eq, e0=e0f)
        out["max_drawdown_pct"] = None if dd is None else round(dd, 4)

    wy = window_years(index)
    out["window_years"] = round(wy, 6)
    out["short_window"] = bool(wy < 1.0)
    ppy = periods_per_year(timeframe)
    out["periods_per_year"] = ppy
    out["timeframe"] = timeframe

    if wy < (1.0 / 365.0) or e0f <= 0 or e_end <= 0:
        reasons = []
        if wy < (1.0 / 365.0):
            reasons.append("window_years < 1/365")
        if e0f <= 0:
            reasons.append("E0 <= 0")
        if e_end <= 0:
            reasons.append("E_end <= 0")
        not_computed["cagr"] = "; ".join(reasons)
    else:
        out["cagr"] = round((e_end / e0f) ** (1.0 / wy) - 1.0, 6)

    if "cagr" not in out:
        not_computed.setdefault("calmar", "cagr not_computed")
    elif out.get("max_drawdown_pct") is None:
        not_computed["calmar"] = "empty equity"
    elif float(out["max_drawdown_pct"]) == 0:
        not_computed["calmar"] = "max_drawdown_pct=0"
    else:
        out["calmar"] = round(float(out["cagr"]) / (float(out["max_drawdown_pct"]) / 100.0), 6)

    # Bar returns: r_i = E_i / E_{i-1} - 1. Prepend E0 so bar-0 exits have a step.
    if eq.size == 0 or e0f <= 0:
        r = np.array([], dtype=float)
    else:
        path = np.concatenate(([e0f], eq))
        prev = path[:-1]
        cur = path[1:]
        ok = prev > 0
        r = np.where(ok, cur / prev - 1.0, np.nan)
        r = r[np.isfinite(r)]

    n_ret = int(r.size)
    out["n_returns"] = n_ret
    rf_period = float(rf) / ppy if ppy else 0.0
    mar_p = float(mar)
    out["rf"] = float(rf)
    out["mar"] = mar_p

    if n_ret < 2:
        not_computed["sharpe"] = "n_returns < 2"
        not_computed["sortino"] = "n_returns < 2"
    else:
        mu = float(r.mean())
        sig = float(r.std(ddof=1))
        if sig == 0:
            not_computed["sharpe"] = "std=0"
        else:
            out["sharpe"] = round(((mu - rf_period) / sig) * math.sqrt(ppy), 6)
        dd_dev = float(np.sqrt(np.mean(np.minimum(r - mar_p, 0.0) ** 2)))
        if dd_dev == 0:
            not_computed["sortino"] = "downside_dev=0"
        else:
            out["sortino"] = round(((mu - mar_p) / dd_dev) * math.sqrt(ppy), 6)

    wins = pnls[pnls > 0] if n_tr else np.array([])
    losses = pnls[pnls < 0] if n_tr else np.array([])
    n_win = int(wins.size)
    n_loss = int(losses.size)
    out["n_win"] = n_win
    out["n_loss"] = n_loss

    if n_tr == 0:
        not_computed["profit_factor"] = "no trades"
        not_computed["expectancy"] = "no trades"
        not_computed["win_rate"] = "no trades"
        not_computed["payoff_ratio"] = "no trades"
    else:
        out["expectancy"] = round(float(pnls.mean()), 6)
        out["win_rate"] = round(n_win / n_tr, 6)
        if n_loss == 0:
            not_computed["profit_factor"] = "no_losses"
        else:
            gp = float(wins.sum()) if n_win else 0.0
            gl = abs(float(losses.sum()))
            out["profit_factor"] = round(gp / gl, 6) if gl else None
            if out["profit_factor"] is None:
                not_computed["profit_factor"] = "no_losses"
        if n_win == 0 or n_loss == 0:
            not_computed["payoff_ratio"] = "no wins or no losses"
        else:
            mw = float(wins.mean())
            ml = abs(float(losses.mean()))
            out["payoff_ratio"] = round(mw / ml, 6) if ml else None
            if out["payoff_ratio"] is None:
                not_computed["payoff_ratio"] = "no wins or no losses"

    kill_pass, kill_failed = _kill(out, kill)
    out["kill_pass"] = bool(kill_pass)
    out["kill_failed"] = kill_failed

    if costs is not None:
        out["costs_applied"] = {
            "commission_per_side": _num((costs or {}).get("commission_per_side")) or 0.0,
            "slippage_ticks": _num((costs or {}).get("slippage_ticks")) or 0.0,
            "tick_size": tick_size(symbol, costs),
            "slip_price": slip_price(symbol, costs),
        }

    out["not_computed"] = not_computed
    out["not_modeled"] = list(NOT_MODELED)
    return out
