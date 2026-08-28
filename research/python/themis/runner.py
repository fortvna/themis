"""fetch ask run validate walkforward compare tune report."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from themis.data import SeriesLoad, load_from_spec
from themis.eligibility import evaluate
from themis.paths import repo_root, runs_dir
from themis.report import write_report
from themis.spec import SpecError, dump_yaml, load_spec

NOT_MODELED = ["perp funding", "intra-bar stop/target path"]
NOT_COMPUTED = ["calmar", "cagr", "sortino", "sharpe", "profit_factor"]


class RunError(RuntimeError):
    pass


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def fetch(spec_path: str | Path, *, root: Path | None = None, network: bool = True) -> SeriesLoad:
    spec = load_spec(spec_path)
    return load_from_spec(spec, root=root or repo_root(), network=network)


def _require_ask_folders(spec: dict[str, Any], root: Path) -> None:
    req = spec.get("requires_asks") or []
    if not req:
        return
    runs = runs_dir(root)
    if not runs.exists():
        raise RunError(f"missing requires_asks folders: {req}")
    names = [p.name for p in runs.iterdir() if p.is_dir()]
    missing = [rid for rid in req if not any(rid in n for n in names)]
    if missing:
        raise RunError(f"missing requires_asks folders: {missing}")


def _max_dd(equity: list[float]) -> float:
    peak = equity[0] if equity else 0.0
    dd = 0.0
    for x in equity:
        peak = max(peak, x)
        if peak:
            dd = min(dd, (x - peak) / peak)
    return round(abs(dd) * 100.0, 4)


def _swing_trades(df: pd.DataFrame, n: int, pct_low: float, pct_high: float, commission: float) -> pd.DataFrame:
    from themis.ask import fractals
    sh, sl = fractals(df, n)
    trades = []
    used: set[int] = set()
    opens = df["open"].to_numpy()
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    idx = df.index

    def fill_trade(side: str, touch: int, origin: float, extreme: float) -> None:
        entry_i = touch + 1
        if entry_i >= len(df):
            return
        entry = float(opens[entry_i])
        cost = abs(entry) * commission * 2
        exit_px = None
        why = "open_end"
        exit_i = len(df) - 1
        for k in range(entry_i, len(df)):
            if side == "long":
                hit_t = highs[k] >= extreme
                hit_s = lows[k] <= origin
                if hit_t and hit_s:
                    why, exit_px, exit_i = "ambiguous_same_bar", float(closes[k]), k
                    break
                if hit_t:
                    why, exit_px, exit_i = "target", float(extreme), k
                    break
                if hit_s:
                    why, exit_px, exit_i = "stop", float(origin), k
                    break
            else:
                hit_t = lows[k] <= extreme
                hit_s = highs[k] >= origin
                if hit_t and hit_s:
                    why, exit_px, exit_i = "ambiguous_same_bar", float(closes[k]), k
                    break
                if hit_t:
                    why, exit_px, exit_i = "target", float(extreme), k
                    break
                if hit_s:
                    why, exit_px, exit_i = "stop", float(origin), k
                    break
        if exit_px is None:
            exit_px = float(closes[-1])
        pnl = (exit_px - entry - cost) if side == "long" else (entry - exit_px - cost)
        trades.append({"side": side, "entry_ts": str(idx[entry_i]), "exit_ts": str(idx[exit_i]), "entry": entry, "exit": exit_px, "origin": origin, "extreme": extreme, "why": why, "pnl": pnl})

    for hi in sh:
        knowable = hi + n
        if knowable >= len(df) - 2:
            continue
        lows_before = [j for j in sl if j < hi]
        if not lows_before:
            continue
        lo = lows_before[-1]
        origin = float(df["low"].iloc[lo])
        extreme = float(df["high"].iloc[hi])
        rng = extreme - origin
        if rng <= 0:
            continue
        z_lo = extreme - pct_high * rng
        z_hi = extreme - pct_low * rng
        touched = None
        for i in range(knowable + 1, len(df) - 1):
            if lows[i] <= z_hi and highs[i] >= z_lo:
                touched = i
                break
            if closes[i] < origin:
                break
        if touched is None or touched in used:
            continue
        used.add(touched)
        fill_trade("long", touched, origin, extreme)

    used_s: set[int] = set()
    for lo in sl:
        knowable = lo + n
        if knowable >= len(df) - 2:
            continue
        highs_before = [j for j in sh if j < lo]
        if not highs_before:
            continue
        hi = highs_before[-1]
        origin = float(df["high"].iloc[hi])
        extreme = float(df["low"].iloc[lo])
        rng = origin - extreme
        if rng <= 0:
            continue
        z_hi = extreme + pct_high * rng
        z_lo = extreme + pct_low * rng
        touched = None
        for i in range(knowable + 1, len(df) - 1):
            if lows[i] <= z_hi and highs[i] >= z_lo:
                touched = i
                break
            if closes[i] > origin:
                break
        if touched is None or touched in used_s:
            continue
        used_s.add(touched)
        fill_trade("short", touched, origin, extreme)
    return pd.DataFrame(trades)


def run_strategy(spec_path: str | Path, *, root: Path | None = None, network: bool = True, thin: bool = False, stage: str = "discovery") -> Path:
    spec = load_spec(spec_path)
    if spec.get("kind") != "strategy":
        raise RunError("run refuses a question spec")
    costs = spec.get("costs") or {}
    if not costs:
        raise RunError("no costs, no strategy run")
    root = root or repo_root()
    series = load_from_spec(spec, root=root, network=network)
    el = evaluate(series.n_bars, costs_written=True, search_space=spec.get("search_space") or None)
    if not el.run_ok:
        raise RunError(el.refuse_message("run"))
    if el.thin and not thin:
        raise RunError(f"run on this series is thin (n_bars={series.n_bars} < 4000). pass --thin to execute. kept still impossible.")
    _require_ask_folders(spec, root)
    n = int(spec.get("fractal_n") or 5)
    pct_low = float(spec.get("pct_low") or 0.618)
    pct_high = float(spec.get("pct_high") or 0.725)
    commission = float(costs.get("commission_per_side") or 0)
    trades = _swing_trades(series.df, n, pct_low, pct_high, commission)
    pnl = float(trades["pnl"].sum()) if len(trades) else 0.0
    start_px = float(series.df["close"].iloc[0])
    net_return = pnl / start_px if start_px else 0.0
    equity = [start_px]
    if len(trades):
        running = start_px
        for x in trades["pnl"].tolist():
            running += x
            equity.append(running)
    dd = _max_dd(equity)
    metrics = {"kind": "strategy", "spec_id": spec["id"], "n_trades": int(len(trades)), "pnl": round(pnl, 6), "net_return": round(net_return, 6), "max_drawdown_pct": dd, "thin": el.thin, "kept_possible": False if el.thin else el.kept_ok, "not_modeled": NOT_MODELED, "not_computed": NOT_COMPUTED, "execution_ready": False, "note": "placeholder costs. not a live claim. 4h SL/TP from OHLC is optimistic.", "identity": series.identity}
    folder = runs_dir(root) / f"{_stamp()}-{spec['id']}-{spec['id'][-8:] if len(spec['id'])>=8 else spec['id']}"
    folder.mkdir(parents=True, exist_ok=True)
    dump_yaml(spec, folder / "spec.yaml")
    meta = {"kind": "strategy", "stage": stage, "execution_ready": False, "spec_id": spec["id"], "actual_start": series.actual_start, "actual_end": series.actual_end, "n_bars": series.n_bars, "provider": series.provider, "source": series.source, "symbol": series.symbol, "thin": el.thin, "family": spec.get("family")}
    if series.symbol in ("SPYUSDT", "QQQUSDT"):
        meta["product"] = "etf_perp"
        meta["not"] = "not ES" if series.symbol == "SPYUSDT" else "not NQ"
    (folder / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    (folder / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    if len(trades):
        trades.to_csv(folder / "trades.csv", index=False)
    else:
        pd.DataFrame(columns=["side", "entry_ts", "exit_ts", "entry", "exit", "pnl", "why"]).to_csv(folder / "trades.csv", index=False)
    (folder / "engine.log").write_text("run next-open fill. not modeled: perp funding, intra-bar path.\n")
    (folder / "status.json").write_text(json.dumps({"ok": True, "kind": "strategy", "thin": el.thin}, indent=2) + "\n")
    return folder


def validate(spec_path: str | Path, from_run: str | Path, *, root: Path | None = None, network: bool = True) -> Path:
    spec = load_spec(spec_path)
    root = root or repo_root()
    series = load_from_spec(spec, root=root, network=network)
    hold = spec.get("holdout") or {}
    hold_n = 0
    if hold.get("start") and hold.get("end"):
        df = series.df
        mask = (df.index >= pd.Timestamp(hold["start"], tz="UTC")) & (df.index <= pd.Timestamp(hold["end"], tz="UTC"))
        hold_n = int(mask.sum())
    el = evaluate(series.n_bars, holdout_n_bars=hold_n, holdout_unused=True, costs_written=True)
    if not el.validate_ok:
        raise RunError(el.refuse_message("validate"))
    return run_strategy(spec_path, root=root, network=network, thin=False, stage="validation")


def walkforward(spec_path: str | Path, *, root: Path | None = None, network: bool = True, n_folds: int = 3) -> Path:
    spec = load_spec(spec_path)
    root = root or repo_root()
    series = load_from_spec(spec, root=root, network=network)
    el = evaluate(series.n_bars, costs_written=True, n_folds=n_folds, search_space=spec.get("search_space"))
    if not el.walkforward_ok:
        raise RunError(el.refuse_message("walkforward"))
    df = series.df
    fold_size = len(df) // n_folds
    rows = []
    for i in range(n_folds):
        sl = df.iloc[: (i + 1) * fold_size] if i < n_folds - 1 else df
        n = int(spec.get("fractal_n") or 5)
        trades = _swing_trades(sl, n, float(spec.get("pct_low") or 0.618), float(spec.get("pct_high") or 0.725), float((spec.get("costs") or {}).get("commission_per_side") or 0))
        rows.append({"fold": i, "n_bars": int(len(sl)), "n_trades": int(len(trades)), "pnl": float(trades["pnl"].sum()) if len(trades) else 0.0})
    folder = runs_dir(root) / f"{_stamp()}-{spec['id']}-walkforward"
    folder.mkdir(parents=True, exist_ok=True)
    dump_yaml(spec, folder / "spec.yaml")
    (folder / "metrics.json").write_text(json.dumps({"kind": "walkforward", "folds": rows, "n_bars": series.n_bars}, indent=2) + "\n")
    (folder / "meta.json").write_text(json.dumps({"kind": "walkforward", "stage": "walkforward", "n_bars": series.n_bars}, indent=2) + "\n")
    (folder / "status.json").write_text(json.dumps({"ok": True}, indent=2) + "\n")
    (folder / "engine.log").write_text("walkforward folds. bars decide. not refused for being BTC/SOL.\n")
    pd.DataFrame(rows).to_csv(folder / "table.csv", index=False)
    return folder


def tune(spec_path: str | Path, *, root: Path | None = None, network: bool = True) -> Path:
    spec = load_spec(spec_path)
    space = spec.get("search_space") or {}
    if not space:
        raise RunError("tune: empty search_space errors")
    root = root or repo_root()
    series = load_from_spec(spec, root=root, network=network)
    el = evaluate(series.n_bars, costs_written=True, search_space=space)
    if not el.tune_ok:
        msg = el.refuse_message("tune")
        if series.symbol in ("XAUUSDT", "SPYUSDT", "QQQUSDT") or el.thin:
            msg += " Point at BTC/SOL as the series that can tune the same family when bars clear the floor."
        raise RunError(msg)
    raise RunError("tune stub: walkforward_eligible but candidate expansion is a later pass")


def compare(family: str, *, root: Path | None = None) -> Path:
    root = root or repo_root()
    runs = runs_dir(root)
    rows = []
    wf_eligible = True
    for p in sorted(runs.iterdir()) if runs.exists() else []:
        if not p.is_dir():
            continue
        meta_p = p / "meta.json"
        metrics_p = p / "metrics.json"
        if not meta_p.exists() or not metrics_p.exists():
            continue
        meta = json.loads(meta_p.read_text())
        metrics = json.loads(metrics_p.read_text())
        spec_p = p / "spec.yaml"
        fam = meta.get("family")
        if spec_p.exists():
            try:
                spec = load_spec(spec_p)
                fam = spec.get("family") or fam
                if spec.get("walkforward_eligible") is False:
                    wf_eligible = False
            except SpecError:
                pass
        if fam != family:
            if family not in str(fam or "") and family not in p.name:
                continue
        if meta.get("kind") != "strategy":
            continue
        if meta.get("stage") not in ("discovery", None):
            continue
        rows.append({"run": p.name, "spec_id": meta.get("spec_id"), "n_bars": meta.get("n_bars"), "thin": meta.get("thin"), "n_trades": metrics.get("n_trades"), "net_return": metrics.get("net_return"), "pnl": metrics.get("pnl"), "max_drawdown_pct": metrics.get("max_drawdown_pct")})
    if not rows:
        raise RunError(f"no discovery strategy runs for family {family}")
    folder = runs_dir(root) / f"{_stamp()}-compare-{family}"
    folder.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(folder / "table.csv", index=False)
    note = "compare lists discovery runs. does not claim validation."
    if not wf_eligible:
        note += " walkforward_eligible is false: do not claim best on this family."
    if any(r.get("thin") for r in rows):
        note += " thin: true. no single-winner."
    metrics = {"family": family, "n_runs": len(rows), "note": note, "claim_best": False, "claim_validation": False}
    (folder / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    (folder / "meta.json").write_text(json.dumps({"kind": "compare", "family": family, "stage": "discovery"}, indent=2) + "\n")
    (folder / "status.json").write_text(json.dumps({"ok": True}, indent=2) + "\n")
    (folder / "engine.log").write_text(note + "\n")
    return folder


def report(run: str | Path, *, root: Path | None = None) -> Path:
    root = root or repo_root()
    p = Path(run)
    if not p.is_absolute():
        p = (root / p) if (root / p).exists() else (runs_dir(root) / p)
    return write_report(p, root=root)
