# Themis Python

Package and CLI live here. Python **3.11+**.

## Law: deps stay in this tree

All Python packages for Themis go into a **repo-local environment**. That is `research/python/.venv` (stdlib `venv`) or another tool aimed at this directory (`uv`, poetry). The env directory is gitignored. The lock of what we need is `pyproject.toml`.

Do **not**:

- `pip install --user`
- `sudo pip`
- install into Apple Command Line Tools / system Python
- install into `~/Library/Python/…`
- assume a global `pandas` / `pytest` is the desk

A user-site package left over from an earlier desk session is not the project env. Ignore it. Use `.venv`.

## Bootstrap

From this directory:

```bash
./bootstrap.sh
source .venv/bin/activate
themis --help
pytest
```

`bootstrap.sh` prefers `python3.13` / `3.12` / `3.11` over bare `python3`. Override with `PYTHON=/path/to/python3.12 ./bootstrap.sh`.

Manual equivalent:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -e ".[dev]"
```

`.[dev]` is pytest. `.[ccxt]` is optional fetch. Never add a paid SDK here.

## Family templates (`implements`)

YAML names the Python. The runner loads it. It does not own a retrace.

| File | Role |
| --- | --- |
| `themis/implements.py` | `load_implements` — file + `trades()` + `REQUIRED_SPEC_KEYS` |
| `themis/fill.py` | Shared next-open / gap / same-bar stop |
| `themis/metrics.py` | §18 ratios from bar equity |
| `strategies/retrace_swing.py` | v1 family. Reads `fractal_n` and `pct_low`/`pct_high` (or `retrace_pct`). No 0.618 default. |
| `strategies/sma_cross.py` | Stub. Must not run as retrace. |

Same English shape, new numbers → same module, new spec id. New kind → new `strategies/<family>.py` or `needs_human`. Never a new `.py` per chat line.

## Conversation command

`themis idea --english "…"` is the operator loop: compile → register slug → `ask` every plan question → HTML + notebook → screen from folders. Auto-`run` only if the English asked return / pnl / `"how good"` / `"backtest"`.

```bash
.venv/bin/themis idea --english "how many times has price bounced after a 75% retracement on gold 4h" \
  --provider binance --symbol XAUUSDT --timeframe 4h --exchange binanceusdm
.venv/bin/themis idea list
.venv/bin/themis idea show --name r1-bounce-75
.venv/bin/themis idea improve --name r1-bounce-75 --english "same bounce, impulse 12 bars"
```

Grok Build runs that path via `/themis-loop` (`.grok/skills/themis-loop/SKILL.md`). Quote metrics only from run folders.

## Notebook kernel (workspace only)

Every `ask` writes Markdown + **HTML** + a **notebook**. HTML is the review. The notebook is a live call of `themis.ask` (Themis .venv) so you can redefine the ask on a new spec id. All math stays in Python. Do not quote an edited cell.

Notebooks declare kernel **python3** so Cursor/VS Code Execute Cell can bind to a Python environment. `ipykernel` lives *inside* `research/python/.venv`. Never `pip install --user`. Never Apple’s Python.

Workspace settings point the interpreter at that venv. Bootstrap also makes `/.venv` a symlink to `research/python/.venv` so the editor finds it at the workspace root.

Enable the suggested extensions: **Python**, **Pylance**, **Jupyter**. Then pick interpreter `research/python/.venv/bin/python` (Command Palette → Python: Select Interpreter). Execute Cell should use that environment. Do not let the UI pip-install into system Python.

## Run tests

```bash
.venv/bin/pytest
```

