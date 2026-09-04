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
    root = root or research_root()
    md = render(run_dir, root=root)
    write_html(run_dir, root=root)
    run = Path(md).with_suffix("")  # not the run dir
    # resolve run folder again for kind
    p = Path(run_dir)
    if not p.exists():
        p = root / "research" / "runs" / Path(run_dir).name
    meta = {}
    if (p / "meta.json").exists():
        meta = json.loads((p / "meta.json").read_text())
    if meta.get("kind") == "question":
        write_ask_notebook(p, root=root)
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


_IDEA_RATE_KEYS = (
    "bounce_rate",
    "complete_rate",
    "target_rate",
    "stop_rate",
    "neither_rate",
    "react_plus",
    "react_minus",
)


def _idea_folder_row(folder: Path) -> dict:
    metrics = json.loads((folder / "metrics.json").read_text()) if (folder / "metrics.json").exists() else {}
    meta = json.loads((folder / "meta.json").read_text()) if (folder / "meta.json").exists() else {}
    spec_id = meta.get("spec_id") or metrics.get("spec_id") or folder.name
    n = metrics.get("n")
    if n is None:
        n = metrics.get("n_days") or metrics.get("n_events") or metrics.get("n_trades")
    rates = []
    for k in _IDEA_RATE_KEYS:
        if metrics.get(k) is not None:
            rates.append((k, metrics.get(k), metrics.get(f"{k}_ci95")))
    primary = rates[0] if rates else None
    return {
        "label": spec_id,
        "n": n,
        "rates": rates,
        "complete_rate": (primary[1] if primary else 0) or 0,
        "ci": primary[2] if primary else None,
        "folder": folder.name,
        "metrics": metrics,
        "meta": meta,
        "identity": metrics.get("identity") or meta.get("identity") or "",
        "symbol": meta.get("symbol") or "",
        "kind": meta.get("kind") or metrics.get("kind") or "question",
        "thin": bool(meta.get("thin") or metrics.get("thin")),
    }


def write_idea_html(slug: str, folders: list[Path], *, root: Path | None = None, title: str = "") -> Path:
    root = root or research_root()
    rows = [_idea_folder_row(p) for p in folders if Path(p).is_dir()]
    svg = _bar_svg(rows) if any(r["rates"] for r in rows) else "<p>No rate graphic (folders have no bounce/complete/target rate).</p>"
    table_rows = []
    for r in rows:
        if r["rates"]:
            rate_s = "; ".join(
                f"{k}={float(v):.1%}" + (f" ± {float(ci):.1%}" if ci is not None else "")
                for k, v, ci in r["rates"]
            )
        else:
            rate_s = "—"
        table_rows.append(
            f"<tr><td>{_esc(r['label'])}</td><td>{_esc(r['n'])}</td>"
            f"<td>{_esc(rate_s)}</td><td><code>{_esc(r['folder'])}</code></td></tr>"
        )
    first = rows[0] if rows else {}
    symbol = str(first.get("symbol") or "")
    ident_obj = first.get("identity") or {}
    if isinstance(ident_obj, dict):
        identity = " ".join(
            str(x)
            for x in (
                ident_obj.get("provider"),
                ident_obj.get("symbol") or symbol,
                ident_obj.get("timeframe"),
                ident_obj.get("not"),
            )
            if x
        )
    else:
        identity = str(ident_obj or "")
    thin = any(r.get("thin") for r in rows)
    if symbol.upper() == "XAUUSDT" and "COMEX" not in identity:
        identity = (identity + " Binance USD-M XAUUSDT perp, not COMEX.").strip()
    if symbol.upper() in {"SPYUSDT", "QQQUSDT"}:
        identity = (identity + f" ETF perp, not {'ES' if symbol.upper()=='SPYUSDT' else 'NQ'}.").strip()
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
<div class="banner"><span>thin: {str(thin).lower()}</span><span>execution_ready: false</span><span>kept: false</span><span>ask / path stats</span><span>not pnl</span></div>
<p>{_esc(identity)}</p>
<h2>Rival rates from run folders</h2>
{svg}
<table><thead><tr><th>spec</th><th>n</th><th>rates (folder)</th><th>folder</th></tr></thead>
<tbody>{"".join(table_rows)}</tbody></table>
<p>Quote only these folders. A rate is not return. Screen is not kept.</p>
</body></html>
"""
    dest = root / "research" / "ideas" / slug
    dest.mkdir(parents=True, exist_ok=True)
    out = dest / "latest.html"
    out.write_text(_never_emini(html, symbol), encoding="utf-8")
    reports = root / "research" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / f"{slug}.html").write_text(_never_emini(html, symbol), encoding="utf-8")
    return out


def write_ask_notebook(run_dir: str | Path, *, root: Path | None = None) -> Path:
    """Per-ask notebook: call measure() on the frozen spec. Redefine via new YAML, not cells."""
    import json as _json

    root = root or research_root()
    run = Path(run_dir)
    if not run.exists():
        run = root / "research" / "runs" / Path(run_dir).name
    rel = str(run.resolve().relative_to(root.resolve())) if run.exists() else str(run)
    cells = [
        _md(
            """# Ask review

This notebook **represents** `themis.ask.measure` on the frozen spec in this run folder. Kernel: Themis (.venv).

To **redefine the ask**: change `definitions` / `condition` on a **new** spec id (same idea slug), then `themis ask` again. Do not edit a rate in a cell and quote it."""
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

from themis.spec import load_spec
from themis.data import load_from_spec
from themis.ask import measure

RUN = repo / {rel!r}
spec = load_spec(RUN / "spec.yaml")
spec.get("id"), spec.get("measure") or spec.get("condition"), spec.get("definitions")"""
        ),
        _code(
            """series = load_from_spec(spec, root=repo, network=False)
metrics, table = measure(spec, series)
metrics"""
        ),
        _code(
            """table.head(20) if table is not None and len(table) else table"""
        ),
        _md(
            """Chat quotes `RUN/metrics.json`. If this cell disagrees with the folder, the folder wins until you freeze a new spec."""
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
    out_dir = root / "research" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{run.name}.ipynb"
    out.write_text(_json.dumps(nb, indent=1) + "\n", encoding="utf-8")
    return out


def write_idea_bundle(slug: str, *, root: Path | None = None, english: str = "") -> Path:
    """latest.md + html + ipynb from idea.yaml runs."""
    import yaml

    root = root or research_root()
    idea_p = root / "research" / "ideas" / slug / "idea.yaml"
    if not idea_p.exists():
        raise FileNotFoundError(idea_p)
    idea = yaml.safe_load(idea_p.read_text()) or {}
    runs = []
    versions = idea.get("versions") or []
    if versions:
        runs = list(versions[-1].get("runs") or [])
    folders = []
    for r in runs:
        p = Path(r)
        if not p.is_absolute():
            p = root / r
        if p.is_dir():
            folders.append(p)
    title = idea.get("title") or slug
    eng = english or idea.get("english_origin") or ""
    dest = root / "research" / "ideas" / slug
    dest.mkdir(parents=True, exist_ok=True)
    if folders:
        write_idea_html(slug, folders, root=root, title=title)
        write_idea_notebook(slug, folders, root=root, english=eng)
    last = versions[-1] if versions else {}
    md_lines = [
        f"# Idea `{slug}`",
        "",
        f"- title: {title}",
        f"- screen: {last.get('screen')}",
        f"- version: {(idea.get('current') or {}).get('version') or last.get('version')}",
        f"- english: {eng or last.get('english') or idea.get('english_origin') or ''}",
        "",
        "Numbers live in run folders. Chat did not invent them.",
        "",
        "## runs",
        "",
    ]
    for r in runs:
        md_lines.append(f"- `{r}`")
    if not runs:
        md_lines.append("- (none yet)")
    md_lines.extend(["", "See latest.html and latest.ipynb.", ""])
    (dest / "latest.md").write_text("\n".join(md_lines), encoding="utf-8")
    return dest / "latest.html"


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
    """Representation of Python ask logic. Cells call themis.ask.measure; they do not reimplement it."""
    import json as _json

    root = root or research_root()
    rels: list[str] = []
    for f in folders:
        p = Path(f)
        try:
            rels.append(str(p.resolve().relative_to(root.resolve())))
        except ValueError:
            rels.append(str(p))
    cells = [
        _md(
            f"""# Idea `{slug}`

This notebook **represents** `themis.ask.measure` on the frozen specs for this idea. Kernel: Themis (.venv).

English: *{english}*

To **redefine the ask**: `themis idea improve --name {slug}` (new spec ids, same slug). Do not edit a rate in a cell and quote it. The run folder wins."""
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

from themis.spec import load_spec
from themis.data import load_from_spec
from themis.ask import measure

RUNS = {rels!r}
rows = []
for rel in RUNS:
    run = repo / rel
    spec = load_spec(run / "spec.yaml")
    series = load_from_spec(spec, root=repo, network=False)
    metrics, table = measure(spec, series)
    rows.append((spec.get("id"), series.identity, metrics, table))
[(r[0], r[1], {{k: r[2].get(k) for k in ("n", "n_days", "bounce_rate", "target_rate", "stop_rate", "complete_rate") if k in r[2]}}) for r in rows]"""
        ),
        _md(
            """Chat quotes `research/runs/<id>/metrics.json`. If a cell disagrees with the folder, the folder wins until you freeze a new spec."""
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

