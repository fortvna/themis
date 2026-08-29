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

echo "bootstrap: $PY ($VER) -> $(pwd)/.venv"
"$PY" -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -e ".[dev]"
# Kernel lives in this venv only. Never --user. Never the system Jupyter.
.venv/bin/python -m ipykernel install --sys-prefix --name themis --display-name "Themis (.venv)"
echo "bootstrap: ok. source $(pwd)/.venv/bin/activate"
echo "bootstrap: .venv/bin/pytest"
echo "bootstrap: notebook kernel Themis (.venv) -> $(pwd)/.venv"
