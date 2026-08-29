"""Shared fill. Not a strategy. Next-open, gap at open, same-bar stop wins."""
from __future__ import annotations

from typing import Any


def simulate_exit(
    side: str,
    entry_i: int,
    stop: float,
    target: float,
    opens: Any,
    highs: Any,
    lows: Any,
    closes: Any,
    *,
    slip: float = 0.0,
    commission: float = 0.0,
) -> dict[str, Any] | None:
    """Next-open fill. Gap through a level fills at open. Same-bar stop+target → stop (tagged)."""
    n = len(opens)
    if entry_i < 0 or entry_i >= n:
        return None
    raw_entry = float(opens[entry_i])
    if side == "long":
        entry = raw_entry + slip
    else:
        entry = raw_entry - slip
    why = "open_end"
    exit_px = float(closes[-1])
    exit_i = n - 1
    ambiguous = False
    gap = False
    for k in range(entry_i, n):
        o = float(opens[k])
        h = float(highs[k])
        l = float(lows[k])
        if side == "long":
            gap_stop = o <= stop
            gap_tgt = o >= target
            hit_s = l <= stop
            hit_t = h >= target
        else:
            gap_stop = o >= stop
            gap_tgt = o <= target
            hit_s = h >= stop
            hit_t = l <= target
        if gap_stop and gap_tgt:
            why, exit_px, exit_i, ambiguous, gap = "ambiguous_same_bar", o, k, True, True
            break
        if gap_stop:
            why, exit_px, exit_i, gap = "stop_gap", o, k, True
            break
        if gap_tgt:
            why, exit_px, exit_i, gap = "target_gap", o, k, True
            break
        if hit_t and hit_s:
            why, exit_px, exit_i, ambiguous = "ambiguous_same_bar", float(stop), k, True
            break
        if hit_t:
            why, exit_px, exit_i = "target", float(target), k
            break
        if hit_s:
            why, exit_px, exit_i = "stop", float(stop), k
            break
    if side == "long":
        fill_exit = exit_px - slip
        pnl = fill_exit - entry - commission * (abs(entry) + abs(fill_exit))
    else:
        fill_exit = exit_px + slip
        pnl = entry - fill_exit - commission * (abs(entry) + abs(fill_exit))
    return {
        "side": side,
        "entry_i": int(entry_i),
        "exit_i": int(exit_i),
        "entry": entry,
        "exit": fill_exit,
        "exit_level": exit_px,
        "stop": float(stop),
        "target": float(target),
        "why": why,
        "ambiguous": bool(ambiguous),
        "gap": bool(gap),
        "pnl": float(pnl),
    }
