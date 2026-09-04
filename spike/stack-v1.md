# Spike: v1 stack

Time-box: this turn. Verdict **ADOPT** (matplotlib **TRIAL**).

Ran: read `pyproject.toml`, `report.py`, `runner.py` on `main` (`0872d20` / GitHub `6310abd` WIP). Did not install new packages. Did not call a model. Did not spend.

- Runtime: pandas, numpy, pyyaml. No backtesting, no matplotlib import in report/runner.
- HTML charts: string SVG in `report.py`. Ask bars exist. Strategy equity/DD/hist **missing** (M1 gap, not a stack gap).
- License: pandas/numpy/pyyaml BSD. Ops: local. Edge: offline CSV/Vision; no CDN.

See `ADR/stack-v1.md`.
