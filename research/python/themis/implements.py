"""Load the Python named by spec.implements. YAML is not executed."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

from themis.paths import python_dir, repo_root


class ImplementsError(RuntimeError):
    pass


def resolve_implements(spec: dict[str, Any], *, root: Path | None = None) -> Path:
    rel = spec.get("implements")
    if not rel or not str(rel).strip():
        raise ImplementsError("no implements, no run. YAML is not executed.")
    rel_s = str(rel).replace("\\", "/").lstrip("/")
    root = root or repo_root()
    pkg_root = Path(__file__).resolve().parent.parent
    candidates = [
        python_dir(root) / rel_s,
        pkg_root / rel_s,
        root / rel_s,
        root / "research" / "python" / rel_s,
    ]
    for c in candidates:
        if c.is_file():
            return c.resolve()
    raise ImplementsError(f"implements not found: {rel_s}. looked in {candidates[:2]}")


def load_implements(spec: dict[str, Any], *, root: Path | None = None) -> ModuleType:
    path = resolve_implements(spec, root=root)
    name = "themis_impl_" + path.stem.replace("-", "_")
    loaded = importlib.util.spec_from_file_location(name, path)
    if loaded is None or loaded.loader is None:
        raise ImplementsError(f"cannot load implements: {path}")
    mod = importlib.util.module_from_spec(loaded)
    loaded.loader.exec_module(mod)
    if not callable(getattr(mod, "trades", None)):
        raise ImplementsError(
            f"{spec.get('implements')} has no trades(spec, df, **costs). "
            "YAML is structure. The implements module is the strategy."
        )
    required = tuple(getattr(mod, "REQUIRED_SPEC_KEYS", ()) or ())
    missing = [k for k in required if spec.get(k) is None]
    if missing:
        raise ImplementsError(
            f"YAML and implements disagree: {spec.get('implements')} requires {missing}. "
            "Do not default a retrace. Freeze the numbers in the spec."
        )
    return mod
