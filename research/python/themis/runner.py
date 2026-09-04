"""fetch ask run validate walkforward compare tune report."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from themis.data import SeriesLoad, load_from_spec
from themis.eligibility import evaluate
from themis.fees import fee_schedule
from themis.fill import simulate_exit
from themis.implements import ImplementsError, load_implements
from themis.metrics import equity_on_bars, slip_price, strategy_metrics
from themis.paths import repo_root, runs_dir
from themis.report import write_report
from themis.spec import SpecError, dump_yaml, load_spec


class RunError(RuntimeError):
    pass


def _trades_from_implements(spec: dict[str, Any], df: pd.DataFrame, *, root: Path, symbol: str) -> pd.DataFrame:
    try:
        mod = load_implements(spec, root=root)
    except ImplementsError as e:
        raise RunError(str(e)) from e
    costs = spec.get("costs") or {}
    if costs.get("commission_per_side") is None:
        fill = (spec.get("rules") or {}).get("fill") or "next_open"
        law = fee_schedule(symbol, fill=fill)
        costs = {**law, **costs}
        costs["commission_per_side"] = law["commission_per_side"]
    commission = float(costs.get("commission_per_side") or 0)
    slip = slip_price(symbol, costs)
    try:
        trades = mod.trades(spec, df, commission=commission, slip=slip)
    except Exception as e:
        raise RunError(f"implements {spec.get('implements')} failed: {e}") from e
    if trades is None:
        return pd.DataFrame()
    if not isinstance(trades, pd.DataFrame):
        raise RunError(f"implements {spec.get('implements')} trades() must return a DataFrame")
    return trades


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


def run_strategy(spec_path: str | Path, *, root: Path | None = None, network: bool = True, thin: bool = False, stage: str = "discovery") -> Path:
    spec = load_spec(spec_path)
    if spec.get("kind") != "strategy":
        raise RunError("run refuses a question spec")
    inst = spec.get("instrument") or {}
    costs = spec.get("costs") or {}
    if costs.get("commission_per_side") is None:
        fill = (spec.get("rules") or {}).get("fill") or "next_open"
        law = fee_schedule(inst.get("symbol"), fill=fill)
        costs = {**law, **costs}
        costs["commission_per_side"] = law["commission_per_side"]
        spec["costs"] = costs
    if costs.get("commission_per_side") is None:
        raise RunError("no costs, no strategy run")
    root = root or repo_root()
    series = load_from_spec(spec, root=root, network=network)
    el = evaluate(series.n_bars, costs_written=True, search_space=spec.get("search_space") or None)
    if not el.run_ok:
        raise RunError(el.refuse_message("run"))
    if spec.get("run_eligible") is False and not thin:
        raise RunError(
            f"run_eligible is false; pass --thin to execute. kept still impossible. "
            f"actual n_bars={series.n_bars} thin={el.thin}"
        )
    if el.thin and not thin:
        raise RunError(
            f"run on this series is thin (n_bars={series.n_bars} < 4000). pass --thin to execute. kept still impossible."
        )
    _require_ask_folders(spec, root)
    trades = _trades_from_implements(spec, series.df, root=root, symbol=series.symbol)
    e0 = float(series.df["close"].iloc[0]) if len(series.df) else 0.0
    exit_i = trades["exit_i"].astype(int).tolist() if len(trades) and "exit_i" in trades.columns else []
    pnls = trades["pnl"].astype(float).tolist() if len(trades) else []
    equity = equity_on_bars(int(len(series.df)), e0, exit_i, pnls)
    n_amb = int(trades["ambiguous"].sum()) if len(trades) and "ambiguous" in trades.columns else 0
    n_gap = int(trades["gap"].sum()) if len(trades) and "gap" in trades.columns else 0
    tf = series.timeframe or (spec.get("instrument") or {}).get("timeframe") or "4h"
    metrics = strategy_metrics(
        trades=trades,
        equity=equity,
        e0=e0,
        index=series.df.index,
        timeframe=tf,
        kill=spec.get("kill") or {},
        n_ambiguous=n_amb,
        n_gap=n_gap,
        symbol=series.symbol,
        costs=costs,
    )
    metrics.update(
        {
            "kind": "strategy",
            "spec_id": spec["id"],
            "thin": el.thin,
            "short_window": bool(metrics.get("short_window")),
            "kept_possible": False if el.thin else bool(metrics.get("kill_pass") and el.kept_ok),
            "kept": False,
            "execution_ready": False,
            "note": (
                "Binance Regular table costs via themis.fees. not a live claim. "
                "same-bar stop+target tagged ambiguous and filled at stop. "
                "gap through a level fills at open. intra-bar path not modeled. no funding."
            ),
            "identity": series.identity,
            "implements": spec.get("implements"),
        }
    )
    folder = runs_dir(root) / f"{_stamp()}-{spec['id']}-{spec['id'][-8:] if len(spec['id'])>=8 else spec['id']}"
    folder.mkdir(parents=True, exist_ok=True)
    dump_yaml(spec, folder / "spec.yaml")
    meta = {
        "kind": "strategy",
        "stage": stage,
        "execution_ready": False,
        "spec_id": spec["id"],
        "actual_start": series.actual_start,
        "actual_end": series.actual_end,
        "n_bars": series.n_bars,
        "provider": series.provider,
        "source": series.source,
        "symbol": series.symbol,
        "thin": el.thin,
        "family": spec.get("family"),
        "implements": spec.get("implements"),
    }
    if series.symbol in ("SPYUSDT", "QQQUSDT"):
        meta["product"] = "etf_perp"
        meta["not"] = "not ES" if series.symbol == "SPYUSDT" else "not NQ"
    (folder / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    (folder / "metrics.json").write_text(json.dumps(metrics, indent=2, default=str) + "\n")
    if len(trades):
        trades.to_csv(folder / "trades.csv", index=False)
    else:
        pd.DataFrame(
            columns=["side", "entry_ts", "exit_ts", "entry", "exit", "pnl", "why", "ambiguous", "gap"]
        ).to_csv(folder / "trades.csv", index=False)
    eq_df = pd.DataFrame({"ts": series.df.index.astype(str), "equity": equity})
    peak = eq_df["equity"].cummax().replace(0, pd.NA)
    eq_df["drawdown_pct"] = ((peak - eq_df["equity"]) / peak * 100.0).fillna(0.0)
    eq_df.to_csv(folder / "equity.csv", index=False)
    (folder / "engine.log").write_text(
        f"run implements={spec.get('implements')}. shared fill + metrics. "
        "not modeled: perp funding, intra-bar path. "
        "same-bar stop+target: fill stop, tag ambiguous. gap: fill open.\n"
    )
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
        trades = _trades_from_implements(spec, sl, root=root, symbol=series.symbol)
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
    root = root or repo_root()
    series = load_from_spec(spec, root=root, network=network)
    el = evaluate(series.n_bars, costs_written=True, search_space=space or None)
    if not el.walkforward_ok or not el.tune_ok:
        msg = el.refuse_message("tune")
        if series.symbol in ("XAUUSDT", "SPYUSDT", "QQQUSDT") or el.thin:
            msg += " Point at BTC/SOL as the series that can tune the same family when bars clear the floor."
        raise RunError(msg)
    if not space:
        raise RunError(
            f"tune: empty search_space errors. actual n_bars={series.n_bars} "
            f"walkforward floor n_bars >= 4000"
        )
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
        row = {
            "run": p.name,
            "spec_id": meta.get("spec_id"),
            "n_bars": meta.get("n_bars"),
            "thin": meta.get("thin"),
            "n_trades": metrics.get("n_trades"),
            "net_return": metrics.get("net_return"),
            "pnl": metrics.get("pnl"),
            "max_drawdown_pct": metrics.get("max_drawdown_pct"),
            "kill_pass": metrics.get("kill_pass"),
        }
        for k in ("sharpe", "sortino", "calmar", "cagr", "profit_factor", "expectancy", "win_rate"):
            if k in metrics and k not in (metrics.get("not_computed") or {}):
                row[k] = metrics.get(k)
        rows.append(row)
    if not rows:
        raise RunError(f"no discovery strategy runs for family {family}")
    folder = runs_dir(root) / f"{_stamp()}-compare-{family}"
    folder.mkdir(parents=True, exist_ok=True)
    table = pd.DataFrame(rows)
    table.to_csv(folder / "table.csv", index=False)
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
