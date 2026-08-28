"""Locate the Themis repo and research tree."""
from __future__ import annotations

from pathlib import Path


def repo_root(start: Path | None = None) -> Path:
    here = (start or Path.cwd()).resolve()
    for cand in [here, *here.parents]:
        if (cand / "docs" / "open-spec.md").exists() or (cand / "questions.md").exists():
            return cand
    pkg = Path(__file__).resolve()
    guess = pkg.parents[3]
    if (guess / "questions.md").exists() or (guess / "docs" / "open-spec.md").exists():
        return guess
    return here


def research_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "research"


def cache_dir(root: Path | None = None) -> Path:
    return research_dir(root) / ".cache"


def runs_dir(root: Path | None = None) -> Path:
    return research_dir(root) / "runs"


def jobs_dir(root: Path | None = None) -> Path:
    return research_dir(root) / "jobs"


def questions_dir(root: Path | None = None) -> Path:
    return research_dir(root) / "questions"


def specs_dir(root: Path | None = None) -> Path:
    return research_dir(root) / "specs"


def python_dir(root: Path | None = None) -> Path:
    return research_dir(root) / "python"
