#!/usr/bin/env bash
# Create research/python/.venv and install Themis into it.
# Never pip install --user. Never the system interpreter.
set -euo pipefail
cd "$(dirname "$0")"

pick_python() {
  if [[ -n "${PYTHON:-}" ]]; then
    echo "$PYTHON"
    return
  fi
  local c
  for c in python3.13 python3.12 python3.11 python3; do
    if command -v "$c" >/dev/null 2>&1; then
      echo "$c"
      return
    fi
  done
  echo "bootstrap: no python3 found" >&2
  exit 1
}

PY="$(pick_python)"
VER="$("$PY" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
MAJOR="${VER%%.*}"
MINOR="${VER#*.}"
if [[ "$MAJOR" -lt 3 || ( "$MAJOR" -eq 3 && "$MINOR" -lt 11 ) ]]; then
  echo "bootstrap: need Python >= 3.11, got $VER ($PY). Set PYTHON= to a 3.11+ binary." >&2
  exit 1
fi

if [[ -e .venv && ! -d .venv ]]; then
  echo "bootstrap: .venv exists and is not a directory" >&2
  exit 1
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
echo "bootstrap: $PY ($VER) -> $HERE/.venv"
"$PY" -m venv .venv
# Workspace-root .venv so Cursor/VS Code auto-discovers the interpreter.
ln -sfn research/python/.venv "$REPO/.venv"
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -e ".[dev]"
# Kernel packages stay in this venv. Never pip --user.
.venv/bin/python -m ipykernel install --sys-prefix --name themis --display-name "Themis (.venv)"
# Pin argv to this venv's python (do not Path.resolve() — that follows out of the venv).
# Copy the spec into the user Jupyter data dir so Cursor/VS Code can find name "themis"
# without installing packages globally. argv still launches this venv.
.venv/bin/python -c '
import json, shutil, sys
from pathlib import Path
exe = str(Path(sys.prefix) / "bin" / "python")
prefix = Path(sys.prefix) / "share" / "jupyter" / "kernels"
for name in ("themis", "python3"):
    p = prefix / name / "kernel.json"
    if not p.exists():
        continue
    spec = json.loads(p.read_text())
    argv = spec.get("argv") or []
    if argv:
        argv[0] = exe
        spec["argv"] = argv
    p.write_text(json.dumps(spec, indent=1) + "\n")
src = prefix / "themis"
try:
    from jupyter_core.paths import jupyter_data_dir
    dest = Path(jupyter_data_dir()) / "kernels" / "themis"
except Exception:
    dest = Path.home() / "Library" / "Jupyter" / "kernels" / "themis"
if src.is_dir():
    dest.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        shutil.copy2(f, dest / f.name)
    print("bootstrap: editor kernel spec ->", dest)
'
echo "bootstrap: ok. source $HERE/.venv/bin/activate"
echo "bootstrap: $HERE/.venv/bin/pytest"
echo "bootstrap: notebook kernel -> $HERE/.venv (workspace .venv -> research/python/.venv)"
