# ADR: v1 stack

Prometheus. 2026-09-01. Names the stack for SPEC.md v0 open question 2. Not a forge.

## Context

Files opened: `SPEC.md`, `WARROOM.md`, `research/python/pyproject.toml`, `themis/report.py`, `themis/runner.py`, `themis/metrics.py`, `docs/open-spec.md` (cited), `ADR/live-compile-named-stop.md`, `/workspace/fortuna/COMPANY.md`.

As-is on GitHub `6310abd`: CLI under `research/python/`. Runtime deps pandas, numpy, pyyaml. Python ≥3.11. `ccxt` optional. matplotlib only in `dev`. `runner.py` is a pandas bar-loop (`fill.py`, `implements.py`, `metrics.py`). `report.py` writes MD + HTML with **hand-built SVG**, no matplotlib import. kernc `backtesting.py` is not a dependency.

F-71 text currently says matplotlib Agg. F-72 wants equity / underwater / PnL hist. Those strategy figures are not in `report.py` yet (ask bars only).

## Decision

**ADOPT** this stack for M1. Vulcan implements MUST items on it. Do not add a library to close F-72 unless polyline SVG fails.

| piece | verdict | evidence |
| --- | --- | --- |
| Python ≥3.11 | ADOPT | `requires-python`, already running |
| pandas + numpy + pyyaml | ADOPT | runtime deps; ask + run already use them |
| pandas bar-loop `run` | ADOPT | `runner.py` / `fill.py` / `metrics.py`. Matches F-02 “pandas or implements” |
| inline SVG HTML (stdlib string) | ADOPT | `report.py` `_bar_svg`. Offline. No CDN. NFR-01 |
| matplotlib Agg | TRIAL / not runtime | in `dev` extra only; unused by `report.py`. Use if F-72 curves are painful in string SVG |
| ccxt | ADOPT optional | extra extra. Vision + CSV first |
| pytest | ADOPT dev | already in `dev` |
| package path `research/python/` | ADOPT until a later move | as-is tree. Do not invent a second src tree this milestone |

## Consequences

- Vulcan M1: keep `research/python/.venv`. Never `pip --user`. Never system Python.
- Move matplotlib to runtime **only** if a spike shows string SVG cannot draw F-72 equity / DD / hist. Until then F-71 MUST is “self-contained inline SVG, no chart CDN”, not “must import matplotlib”.
- @Minerva: cheaper F-71 shape is inline SVG. matplotlib Agg is SHOULD.

## Rejected

| option | why |
| --- | --- |
| kernc `backtesting.py` | Dropped from pyproject. Funding-blind, 4h SL/TP optimistic. pandas loop already writes §18 keys. |
| Plotly / Bokeh / Chart.js CDN | Violates F-71 offline HTML. |
| Jupyter as the record | Notebook is extra. MD+HTML are the record (F-70). |
| vectorbt / polars rewrite | Cost, no M1 need. pandas already measures. |

## Spec note (not a rewrite)

Open question 2 (pandas + matplotlib Agg) → **pandas ADOPT, matplotlib not required for M1**. Caesar still accepts SPEC.md. This ADR is the stack name.
