"""Markdown from a run folder. Artifacts only. Never ES/NQ for SPY/QQQ."""

from __future__ import annotations

import json
from pathlib import Path

from themis.data import research_root


def _never_emini(text: str, symbol: str) -> str:
    s = (symbol or "").upper()
    if s in {"SPYUSDT", "QQQUSDT"}:
        for bad in (" e-mini", " emini", " ES", " NQ", "ES ", "NQ "):
            text = text.replace(bad, " ETF perp ")
        text = text.replace("ES/NQ", "ETF perp")
    return text


def render(run_dir: str | Path, root: Path | None = None) -> Path:
    run = Path(run_dir)
    if not run.exists():
        root = root or research_root()
        alt = root / run_dir
        if alt.exists():
            run = alt
        else:
            alt2 = root / "research" / "runs" / Path(run_dir).name
            if alt2.exists():
                run = alt2
            else:
                raise FileNotFoundError(run_dir)
    meta = json.loads((run / "meta.json").read_text(encoding="utf-8")) if (run / "meta.json").exists() else {}
    metrics = json.loads((run / "metrics.json").read_text(encoding="utf-8")) if (run / "metrics.json").exists() else {}
    symbol = meta.get("symbol") or ""
    thin = bool(meta.get("thin") or metrics.get("thin"))
    lines = [
        f"# Report `{run.name}`",
        "",
        f"- kind: {meta.get('kind')}",
        f"- spec: {meta.get('spec_id')}",
        f"- provider: {meta.get('provider')} symbol: {symbol} source: {meta.get('source')}",
        f"- actual_start: {meta.get('actual_start')} actual_end: {meta.get('actual_end')} n_bars: {meta.get('n_bars')}",
        f"- identity: {meta.get('identity') or ''}",
        f"- thin: {str(thin).lower()}",
        f"- execution_ready: {meta.get('execution_ready', False)}",
        f"- kept: {meta.get('kept', False)}",
        "",
        "Numbers below are copied from the run folder. Chat did not invent them.",
        "",
        "## metrics.json",
        "",
        "```json",
        json.dumps(metrics, indent=2, default=str),
        "```",
        "",
    ]
    if symbol.upper() in {"SPYUSDT", "QQQUSDT"}:
        lines.append("This series is an ETF perp, not ES, not NQ, not e-mini.")
        lines.append("")
    body = _never_emini("\n".join(lines), symbol)
    root = root or research_root()
    out_dir = root / "research" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{run.name}.md"
    out.write_text(body, encoding="utf-8")
    print(f"report wrote {out}")
    return out
