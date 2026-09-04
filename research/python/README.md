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

## Notebook kernel (workspace only)

Every `ask` writes Markdown + **HTML** + a **notebook**. HTML is the review. The notebook is a live call of `themis.ask` (Themis .venv) so you can redefine the ask on a new spec id. All math stays in Python. Do not quote an edited cell.

Notebooks use the **Themis (.venv)** kernel, registered *inside* `research/python/.venv` (`ipykernel install --sys-prefix`). Never `--user`. Never Apple’s Python.

Workspace settings (`.vscode/settings.json`) point the interpreter at that venv. Open a notebook, pick **Themis (.venv)** once if asked — it is this tree, not a global kernel.

If the picker is empty, re-run `./bootstrap.sh`.

## Run tests

```bash
.venv/bin/pytest
```

