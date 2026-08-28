"""Markdown from a run folder. Artifacts only. No invented metrics."""
from __future__ import annotations

import json
from pathlib import Path

from themis.paths import repo_root, research_dir


def write_report(run_dir: Path, *, root: Path | None = None) -> Path:
    run_dir = Path(run_dir)
    if not run_dir.exists():
        raise FileNotFoundError(run_dir)
    meta = json.loads((run_dir / "meta.json").read_text()) if (run_dir / "meta.json").exists() else {}
    metrics = json.loads((run_dir / "metrics.json").read_text()) if (run_dir / "metrics.json").exists() else {}
    ident = metrics.get("identity") or {}
    lines = [
        f"# Report `{run_dir.name}`",
        "",
        f"- kind: `{meta.get('kind')}`",
        f"- stage: `{meta.get('stage')}`",
        f"- spec: `{meta.get('spec_id')}`",
        f"- n_bars: `{meta.get('n_bars')}` actual_start `{meta.get('actual_start')}` actual_end `{meta.get('actual_end')}`",
        f"- provider `{meta.get('provider')}` source `{meta.get('source')}`",
        f"- thin: `{meta.get('thin')}`",
        f"- execution_ready: `{meta.get('execution_ready')}`",
        "",
        "Metrics quoted only from this folder.",
        "",
        "```json",
        json.dumps(metrics, indent=2),
        "```",
        "",
    ]
    if ident.get("product") == "etf_perp" or meta.get("symbol") in ("SPYUSDT", "QQQUSDT"):
        lines.insert(2, "- product: ETF perp, **not ES**, **not NQ**.")
    root = root or repo_root()
    out_dir = research_dir(root) / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{run_dir.name}.md"
    out.write_text("\n".join(lines) + "\n")
    return out


def render(run_dir, root=None):
    p = Path(run_dir)
    return write_report(p, root=root)
