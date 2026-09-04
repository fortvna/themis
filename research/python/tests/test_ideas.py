"""Idea registry: slug rules, collision, screen, improve parent preserved."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from themis.ideas import (
    IdeaError,
    extract_call_it,
    list_ideas,
    load_idea,
    propose_slug,
    register,
    screen_from_folders,
    screen_one_metrics,
    slugify,
    validate_slug,
)
from themis.spec import dump_yaml


SERIES = {
    "provider": "binance",
    "symbol": "BTCUSDT",
    "timeframe": "4h",
    "exchange": "binanceusdm",
}


def test_slug_rules_accept_valid():
    assert validate_slug("g3-atr-react") == "g3-atr-react"
    assert validate_slug("h1-618") == "h1-618"
    assert slugify("G3 ATR React!!") == "g3-atr-react"


def test_slug_rules_reject_bad():
    with pytest.raises(IdeaError):
        validate_slug("-leading")
    with pytest.raises(IdeaError):
        validate_slug("trailing-")
    with pytest.raises(IdeaError):
        validate_slug("has--double")
    with pytest.raises(IdeaError):
        validate_slug("a")  # too short
    with pytest.raises(IdeaError):
        validate_slug("x" * 49)


def test_call_it_and_bank_stable():
    assert extract_call_it("Prior-day ATR, call it g3-loop-prove") == "g3-loop-prove"
    assert propose_slug(
        "Prior-day ATR, lines at -33% and +33%, does price react",
        SERIES,
    ) == "g3-atr-react"
    assert propose_slug(
        "4h swing high/low, enter retrace 61.8-72.5, stop swing low, target swing high",
        SERIES,
    ) == "g1-retrace-618-725"
    assert propose_slug("anything", SERIES, name="my-custom-slug") == "my-custom-slug"


def test_collision_on_new_idea(tmp_path: Path):
    # Minimal repo layout for ideas_dir
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "open-spec.md").write_text("# stub\n")
    (tmp_path / "research" / "ideas").mkdir(parents=True)

    register(
        "demo-slug",
        "english one",
        SERIES,
        spec_ids=["a"],
        root=tmp_path,
    )
    with pytest.raises(IdeaError) as ctx:
        register(
            "demo-slug",
            "english two",
            SERIES,
            spec_ids=["b"],
            root=tmp_path,
        )
    assert "already exists" in str(ctx.value)
    assert "demo-slug" in str(ctx.value)


def test_improve_preserves_parent(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "open-spec.md").write_text("# stub\n")
    (tmp_path / "research" / "ideas").mkdir(parents=True)

    register(
        "imp-slug",
        "parent english",
        SERIES,
        spec_ids=["spec-v1-a", "spec-v1-b"],
        root=tmp_path,
    )
    parent = load_idea("imp-slug", root=tmp_path)
    parent_ids = list(parent["versions"][0]["spec_ids"])
    parent["versions"][0]["runs"] = ["research/runs/fake-parent"]
    parent["versions"][0]["screen"] = "weak"
    from themis.ideas import save_idea

    save_idea(parent, root=tmp_path)

    register(
        "imp-slug",
        "child english stop 2 ATR",
        SERIES,
        spec_ids=["spec-v2-a", "spec-v2-b"],
        root=tmp_path,
        improve=True,
    )
    idea = load_idea("imp-slug", root=tmp_path)
    assert len(idea["versions"]) == 2
    assert idea["versions"][0]["spec_ids"] == parent_ids
    assert idea["versions"][0]["runs"] == ["research/runs/fake-parent"]
    assert idea["versions"][0]["screen"] == "weak"
    assert idea["versions"][1]["parent"] == parent_ids
    assert idea["versions"][1]["spec_ids"] == ["spec-v2-a", "spec-v2-b"]
    assert idea["versions"][1]["english"] == "child english stop 2 ATR"
    assert idea["current"]["version"] == 2


def _write_run(folder: Path, metrics: dict) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "metrics.json").write_text(json.dumps(metrics) + "\n")
    (folder / "meta.json").write_text(json.dumps({"kind": "question"}) + "\n")


def test_screen_dead_weak_continue(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "open-spec.md").write_text("# stub\n")

    # dead: n>=30, stop higher, CIs do not overlap
    # target 0.30 ± 0.05 → [0.25, 0.35]; stop 0.60 ± 0.05 → [0.55, 0.65]
    dead_dir = tmp_path / "research" / "runs" / "dead"
    _write_run(
        dead_dir,
        {
            "n": 100,
            "target_rate": 0.30,
            "stop_rate": 0.60,
            "target_rate_ci95": 0.05,
            "stop_rate_ci95": 0.05,
        },
    )
    assert screen_from_folders([dead_dir], root=tmp_path) == "dead"

    # continue: target higher, no overlap
    cont_dir = tmp_path / "research" / "runs" / "cont"
    _write_run(
        cont_dir,
        {
            "n": 100,
            "target_rate": 0.65,
            "stop_rate": 0.30,
            "target_rate_ci95": 0.05,
            "stop_rate_ci95": 0.05,
        },
    )
    assert screen_from_folders([cont_dir], root=tmp_path) == "continue"

    # weak: overlap
    weak_dir = tmp_path / "research" / "runs" / "weak"
    _write_run(
        weak_dir,
        {
            "n": 100,
            "target_rate": 0.48,
            "stop_rate": 0.50,
            "target_rate_ci95": 0.08,
            "stop_rate_ci95": 0.08,
        },
    )
    assert screen_from_folders([weak_dir], root=tmp_path) == "weak"

    # weak: n < 30
    thin_dir = tmp_path / "research" / "runs" / "thin"
    _write_run(
        thin_dir,
        {
            "n": 10,
            "target_rate": 0.90,
            "stop_rate": 0.10,
            "target_rate_ci95": 0.05,
            "stop_rate_ci95": 0.05,
        },
    )
    assert screen_from_folders([thin_dir], root=tmp_path) == "weak"


def test_screen_bounce_only_is_weak():
    # Documented: bounce_rate-only is not target-vs-stop → weak
    assert (
        screen_one_metrics({"n": 200, "bounce_rate": 0.55, "bounce_rate_ci95": 0.07})
        == "weak"
    )
    assert screen_one_metrics({"n": 10, "bounce_rate": 0.9}) == "weak"
    # G3-style react without target/stop → weak
    assert (
        screen_one_metrics(
            {"n_days": 100, "react_plus": 0.5, "react_minus": 0.55, "n_touch_plus33": 50}
        )
        == "weak"
    )


def test_list_ideas_emptyish(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "open-spec.md").write_text("# stub\n")
    (tmp_path / "research" / "ideas").mkdir(parents=True)
    assert list_ideas(root=tmp_path) == []
    register("aa", "e", SERIES, spec_ids=["x"], title="A", root=tmp_path)
    rows = list_ideas(root=tmp_path)
    assert len(rows) == 1
    assert rows[0]["slug"] == "aa"
