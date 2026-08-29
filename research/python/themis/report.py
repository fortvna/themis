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


def write_report(run_dir, *, root=None):
    md = render(run_dir, root=root)
    try:
        write_html(run_dir, root=root or research_root())
    except Exception:
        pass
    return md


def _esc(s: object) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _bar_svg(rows: list[dict], *, value_key: str = "complete_rate", label_key: str = "label") -> str:
    if not rows:
        return "<p>no rival rates to graph</p>"
    w, h, left, bar_h, gap = 640, 48 + 36 * len(rows), 220, 22, 12
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">']
    parts.append('<rect width="100%" height="100%" fill="#0f1115"/>')
    max_v = 1.0
    for i, row in enumerate(rows):
        y = 20 + i * (bar_h + gap)
        v = float(row.get(value_key) or 0)
        ci = row.get("ci")
        bw = max(0.0, min(1.0, v / max_v)) * (w - left - 80)
        parts.append(f'<text x="12" y="{y + 16}" fill="#c8cdd8" font-size="12" font-family="ui-sans-serif,system-ui">{_esc(row.get(label_key))}</text>')
        parts.append(f'<rect x="{left}" y="{y}" width="{bw:.1f}" height="{bar_h}" fill="#5b8def" rx="3"/>')
        cap = f"{v:.1%}"
        if ci is not None:
            cap += f" ± {float(ci):.1%}"
        parts.append(f'<text x="{left + bw + 8:.1f}" y="{y + 16}" fill="#e8eaed" font-size="12" font-family="ui-sans-serif,system-ui">{_esc(cap)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def write_html(run_dir: str | Path, *, root: Path | None = None, extra_rivals: list[Path] | None = None) -> Path:
    run = Path(run_dir)
    root = root or research_root()
    if not run.exists():
        run = root / "research" / "runs" / Path(run_dir).name
    meta = json.loads((run / "meta.json").read_text()) if (run / "meta.json").exists() else {}
    metrics = json.loads((run / "metrics.json").read_text()) if (run / "metrics.json").exists() else {}
    symbol = str(meta.get("symbol") or "")
    rivals = extra_rivals or []
    bars = []
    for p in [run, *rivals]:
        p = Path(p)
        if not (p / "metrics.json").exists():
            continue
        m = json.loads((p / "metrics.json").read_text())
        label = f"ATR{m.get('atr_n')} {m.get('complete_def') or m.get('spec_id') or p.name}"
        if "complete_rate" in m:
            bars.append({"label": label, "complete_rate": m.get("complete_rate") or 0, "ci": m.get("complete_rate_ci95")})
        elif "target_rate" in m:
            bars.append({"label": str(m.get("spec_id") or p.name), "complete_rate": m.get("target_rate") or 0, "ci": m.get("target_rate_ci95")})
    thin = bool(meta.get("thin") or metrics.get("thin"))
    banners = [
        f"thin: {str(thin).lower()}",
        "execution_ready: false",
        "kept: false",
        "kind: ask" if meta.get("kind") == "question" else f"kind: {meta.get('kind')}",
        "notional: 1_unit" if meta.get("kind") == "strategy" else "path stats, not pnl",
    ]
    svg = _bar_svg(bars) if bars else "<p>No rate graphic (folder has no complete_rate / target_rate).</p>"
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><title>Themis report {_esc(run.name)}</title>
<style>
body {{ font-family: ui-sans-serif, system-ui, sans-serif; background:#0f1115; color:#e8eaed; margin:24px; max-width:900px; }}
.banner {{ display:flex; flex-wrap:wrap; gap:8px; margin:12px 0 20px; }}
.banner span {{ background:#1e2430; border:1px solid #2c3444; padding:4px 8px; border-radius:4px; font-size:12px; }}
pre {{ background:#161b22; padding:12px; overflow:auto; font-size:12px; }}
a {{ color:#8ab4f8; }}
table {{ border-collapse:collapse; }}
td,th {{ border:1px solid #2c3444; padding:6px 10px; font-size:13px; }}
</style></head><body>
<h1>Themis report <code>{_esc(run.name)}</code></h1>
<div class="banner">{"".join(f"<span>{_esc(b)}</span>" for b in banners)}</div>
<p>Copied from the run folder. Chat did not invent these numbers. Binance USD-M { _esc(symbol) } is this venue's gold perp, not COMEX.</p>
<p>spec: {_esc(meta.get("spec_id"))} · { _esc(meta.get("actual_start")) } → {_esc(meta.get("actual_end"))} · n_bars={_esc(meta.get("n_bars"))} · source={_esc(meta.get("source"))}</p>
<h2>Rates</h2>
{svg}
<h2>metrics.json</h2>
<pre>{_esc(json.dumps(metrics, indent=2, default=str))}</pre>
<p>Markdown twin: <code>research/reports/{_esc(run.name)}.md</code></p>
</body></html>
"""
    out_dir = root / "research" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{run.name}.html"
    out.write_text(_never_emini(html, symbol), encoding="utf-8")
    return out


def write_idea_html(slug: str, folders: list[Path], *, root: Path | None = None, title: str = "") -> Path:
    root = root or research_root()
    rows = []
    for p in folders:
        m = json.loads((p / "metrics.json").read_text())
        rows.append({
            "label": f"ATR{m.get('atr_n')} / {m.get('complete_def')}",
            "complete_rate": m.get("complete_rate") or 0,
            "ci": m.get("complete_rate_ci95"),
            "n": m.get("n") or m.get("n_days"),
            "n_complete": m.get("n_complete"),
            "window_start": m.get("window_start"),
            "window_end": m.get("window_end"),
            "folder": p.name,
            "metrics": m,
        })
    svg = _bar_svg(rows)
    table_rows = "".join(
        f"<tr><td>{_esc(r['label'])}</td><td>{r['n']}</td><td>{r['n_complete']}</td>"
        f"<td>{float(r['complete_rate']):.1%} ± {float(r['ci'] or 0):.1%}</td>"
        f"<td><code>{_esc(r['folder'])}</code></td></tr>"
        for r in rows
    )
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><title>Themis idea {_esc(slug)}</title>
<style>
body {{ font-family: ui-sans-serif, system-ui, sans-serif; background:#0f1115; color:#e8eaed; margin:24px; max-width:960px; }}
.banner span {{ background:#1e2430; border:1px solid #2c3444; padding:4px 8px; border-radius:4px; font-size:12px; margin-right:6px; }}
table {{ border-collapse:collapse; margin:16px 0; }}
td,th {{ border:1px solid #2c3444; padding:6px 10px; font-size:13px; }}
pre {{ background:#161b22; padding:12px; overflow:auto; font-size:12px; }}
</style></head><body>
<h1>{_esc(title or slug)}</h1>
<div class="banner"><span>thin: true</span><span>execution_ready: false</span><span>kept: false</span><span>ask / path stats</span><span>not pnl</span></div>
<p>Binance USD-M <strong>XAUUSDT</strong> perp, not COMEX. Outcome window is the last calendar month of bars actually loaded. August 2026 Vision zip was HTTP 404 from this desk.</p>
<h2>Rival complete rates</h2>
{svg}
<table><thead><tr><th>definition</th><th>n days</th><th>n complete</th><th>rate (Wald 95% CI half-width)</th><th>folder</th></tr></thead>
<tbody>{table_rows}</tbody></table>
<p>Quote only these folders. A rate is not return. No strategy was run.</p>
</body></html>
"""
    dest = root / "research" / "ideas" / slug
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / "latest.html"
    out.write_text(html, encoding="utf-8")
    reports = root / "research" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / f"{slug}.html").write_text(html, encoding="utf-8")
    return out


def _md(text: str) -> dict:
    lines = text.split("\n")
    src = [ln + "\n" for ln in lines[:-1]] + ([lines[-1] + "\n"] if lines[-1] else [])
    if not src:
        src = ["\n"]
    return {"cell_type": "markdown", "metadata": {}, "source": src}


def _code(text: str) -> dict:
    lines = text.split("\n")
    src = [ln + "\n" for ln in lines[:-1]]
    if lines:
        src.append(lines[-1] + ("\n" if lines[-1] else ""))
    return {
        "cell_type": "code",
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": src or ["\n"],
    }


def write_idea_notebook(slug: str, folders: list[Path], *, root: Path | None = None, english: str = "") -> Path:
    """Representation of Python ask logic. Cells call themis.*; they do not compute ATR."""
    import json as _json

    root = root or research_root()
    run_spec = ""
    if folders:
        sp = (Path(folders[0]) / "spec.yaml").resolve()
        try:
            run_spec = str(sp.relative_to(root.resolve()))
        except ValueError:
            run_spec = str(sp)
    cells = [
        _md(
            f"""# Idea `{slug}`

This notebook is a **live representation** of Python in `themis.ask`. Run All on the Themis (.venv) kernel. It does not reimplement ATR.

English: *{english}*

**Ask, not a trade.** Logic: `atr_path_days`, `atr_complete_table`, `atr_complete_rivals`. Families (`strategies/*`, fill, metrics) stay shared and unused here.

Unnamed keys (frozen in `ATR_COMPLETE_RIVALS`): ATR 14 vs 20; complete = daily range vs from-open. Window: last calendar month of loaded bars."""
        ),
        _code(
            f"""from pathlib import Path
import os

here = Path.cwd()
repo = here
while repo != repo.parent and not (repo / "docs" / "open-spec.md").exists():
    repo = repo.parent
os.environ["THEMIS_ROOT"] = str(repo)
os.chdir(repo)

from themis.data import load_from_spec
from themis.spec import load_spec
from themis.ask import (
    atr_path_days,
    atr_complete_rivals,
    plot_range_vs_prior_atr,
)

SPEC = repo / {run_spec!r}
spec = load_spec(SPEC)
spec["id"], spec.get("measure"), spec.get("instrument")"""
        ),
        _md(
            """## 1. Series

`themis.data` loads the frozen spec. Binance `XAUUSDT` perp, not COMEX."""
        ),
        _code(
            """series = load_from_spec(spec, root=repo, network=False)
ohlc = series.df
series.identity"""
        ),
        _md(
            """## 2. Path frame (Python)

`atr_path_days` builds UTC daily OHLC, range, from-open, ATR, **prior_atr = atr.shift(1)**."""
        ),
        _code(
            """path = atr_path_days(ohlc, atr_n=14)
path[["open", "high", "low", "close", "day_range", "from_open", "atr", "prior_atr"]].tail(8)"""
        ),
        _md(
            """## 3. Rivals (Python catalog)

`atr_complete_rivals` applies `ATR_COMPLETE_RIVALS` and the last-calendar-month window."""
        ),
        _code(
            """summary, tables = atr_complete_rivals(ohlc)
summary"""
        ),
        _md(
            """## 4. One rival, day by day"""
        ),
        _code(
            """july = tables[(14, "day_range")]
july[["open", "high", "low", "close", "prior_atr", "day_range", "from_open", "complete", "range_over_atr"]]"""
        ),
        _code(
            """plot_range_vs_prior_atr(
    july,
    title="XAUUSDT daily range vs prior-day ATR(14) — last calendar month",
)"""
        ),
        _md(
            """Chat quotes **run folders**. This notebook calls the same functions. If they disagree, the folder wins.

Do not multiply `complete_rate` by R. Screen is weak on n≈30."""
        ),
    ]
    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Themis (.venv)",
                "language": "python",
                "name": "themis",
            },
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "cells": cells,
    }
    dest = root / "research" / "ideas" / slug
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / "latest.ipynb"
    out.write_text(_json.dumps(nb, indent=1) + "\n", encoding="utf-8")
    return out

