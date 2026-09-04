"""Idea registry: slug rules, collision, screen, improve parent preserved."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from themis.ask import AskError
from themis.ideas import (
    IdeaError,
    english_wants_run,
    extract_call_it,
    list_ideas,
    load_idea,
    propose_slug,
    register,
    run_idea_loop,
    save_idea,
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
    gold = {
        "provider": "binance",
        "symbol": "XAUUSDT",
        "timeframe": "1h",
        "exchange": "binanceusdm",
    }
    assert (
        propose_slug(
            "find highs and lows of the 1h and wait retrace until 61.8 percent, "
            "is the low + 1 atr as stop loss and the high as take profit",
            gold,
        )
        == "xau-1h-618-low-plus-1atr"
    )


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


def test_english_wants_run():
    assert english_wants_run("what is the return / pnl / drawdown")
    assert english_wants_run("how good is this after costs")
    assert english_wants_run("backtest this retrace")
    assert not english_wants_run(
        "How many times has price bounced after a 75% retracement on this series"
    )


def test_screen_run_fail_kill(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "open-spec.md").write_text("# stub\n")
    d = tmp_path / "research" / "runs" / "s"
    d.mkdir(parents=True)
    (d / "metrics.json").write_text(
        json.dumps({"kill_pass": False, "kill_failed": ["min_trades"], "n_trades": 2})
    )
    (d / "meta.json").write_text(json.dumps({"kind": "strategy"}))
    assert screen_from_folders([d], root=tmp_path) == "fail_kill"

    cand = tmp_path / "research" / "runs" / "c"
    cand.mkdir(parents=True)
    (cand / "metrics.json").write_text(
        json.dumps({"kill_pass": True, "thin": False, "short_window": False, "n_trades": 40})
    )
    (cand / "meta.json").write_text(json.dumps({"kind": "strategy", "thin": False}))
    assert screen_from_folders([cand], root=tmp_path) == "candidate"


def test_run_idea_loop_needs_human(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "open-spec.md").write_text("# stub\n")
    (tmp_path / "research" / "ideas").mkdir(parents=True)
    out = run_idea_loop(
        "paint me a unicorn order block on mars",
        SERIES,
        root=tmp_path,
        offline=True,
    )
    assert out["status"] == "needs_human"
    assert list_ideas(root=tmp_path) == []


def test_run_idea_loop_asks_and_screens(tmp_path: Path, monkeypatch):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "open-spec.md").write_text("# stub\n")
    asked: list[str] = []

    def fake_ask(spec_path, **_kw):
        asked.append(str(spec_path))
        folder = tmp_path / "research" / "runs" / f"ask-{len(asked)}"
        folder.mkdir(parents=True)
        (folder / "metrics.json").write_text(
            json.dumps(
                {
                    "n": 100,
                    "target_rate": 0.30,
                    "stop_rate": 0.60,
                    "target_rate_ci95": 0.05,
                    "stop_rate_ci95": 0.05,
                }
            )
        )
        (folder / "meta.json").write_text(json.dumps({"kind": "question"}))
        return folder

    def boom(*_a, **_k):
        raise AssertionError("bounce English must not auto-run")

    def fake_bundle(slug, **_kw):
        d = tmp_path / "research" / "ideas" / slug
        d.mkdir(parents=True, exist_ok=True)
        html = d / "latest.html"
        md = d / "latest.md"
        html.write_text("<html></html>\n")
        md.write_text("# stub\n")
        return {"html": html, "md": md}

    monkeypatch.setattr("themis.ideas.run_ask", fake_ask)
    monkeypatch.setattr("themis.ideas.run_strategy", boom)
    monkeypatch.setattr("themis.ideas.write_idea_bundle", fake_bundle)

    out = run_idea_loop(
        "How many times has price bounced after a 75% retracement on this series, this timeframe?",
        SERIES,
        root=tmp_path,
        offline=True,
    )
    assert out["status"] == "ok"
    assert out["slug"] == "r1-bounce-75"
    assert len(asked) >= 2
    assert out["screen"] == "dead"
    assert "html" in out["reports"] and "md" in out["reports"]
    assert "ipynb" not in out["reports"]
    idea = load_idea("r1-bounce-75", root=tmp_path)
    assert idea["versions"][0]["screen"] == "dead"
    assert len(idea["versions"][0]["runs"]) >= 2


def test_run_idea_loop_auto_run_on_pnl(tmp_path: Path, monkeypatch):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "open-spec.md").write_text("# stub\n")
    ran: list[str] = []
    asked: list[str] = []

    def fake_ask(spec_path, **_kw):
        asked.append(str(spec_path))
        folder = tmp_path / "research" / "runs" / f"ask-{len(asked)}-q"
        folder.mkdir(parents=True)
        (folder / "metrics.json").write_text(
            json.dumps(
                {
                    "n": 100,
                    "target_rate": 0.65,
                    "stop_rate": 0.30,
                    "target_rate_ci95": 0.05,
                    "stop_rate_ci95": 0.05,
                }
            )
        )
        (folder / "meta.json").write_text(json.dumps({"kind": "question"}))
        return folder

    def fake_run(spec_path, **_kw):
        ran.append(str(spec_path))
        folder = tmp_path / "research" / "runs" / f"strat-{len(ran)}"
        folder.mkdir(parents=True)
        (folder / "metrics.json").write_text(
            json.dumps({"kill_pass": True, "thin": True, "short_window": False, "n_trades": 40})
        )
        (folder / "meta.json").write_text(json.dumps({"kind": "strategy", "thin": True}))
        return folder

    def fake_bundle(slug, **_kw):
        d = tmp_path / "research" / "ideas" / slug
        d.mkdir(parents=True, exist_ok=True)
        html = d / "latest.html"
        md = d / "latest.md"
        html.write_text("<html></html>\n")
        md.write_text("# stub\n")
        return {"html": html, "md": md}

    monkeypatch.setattr("themis.ideas.run_ask", fake_ask)
    monkeypatch.setattr("themis.ideas.run_strategy", fake_run)
    monkeypatch.setattr("themis.ideas.write_idea_bundle", fake_bundle)

    out = run_idea_loop(
        "From the 75% retracement, 1:1 R — what is the return / pnl / drawdown?",
        SERIES,
        root=tmp_path,
        offline=True,
        thin=True,
    )
    assert out["status"] == "ok"
    assert out["slug"] == "b0-75-1r-return"
    assert ran, "return English must auto-run the strategy spec"
    assert out["screen"] == "weak"  # thin


def test_skill_file_present():
    root = Path(__file__).resolve().parents[3]
    skill = root / ".grok" / "skills" / "themis-loop" / "SKILL.md"
    text = skill.read_text()
    assert skill.exists()
    assert text.startswith("---\nname: themis-loop\n")
    assert "themis idea" in text
    assert "research/python/.venv/bin/themis" in text
    assert "/themis-loop" in text


def test_write_idea_bundle_generic_rates(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "open-spec.md").write_text("# stub\n")
    run = tmp_path / "research" / "runs" / "r1fold"
    run.mkdir(parents=True)
    (run / "metrics.json").write_text(
        json.dumps(
            {
                "n": 40,
                "bounce_rate": 0.4,
                "bounce_rate_ci95": 0.15,
                "identity": {
                    "provider": "binance",
                    "symbol": "XAUUSDT",
                    "timeframe": "4h",
                    "not": "not COMEX",
                },
            }
        )
    )
    (run / "meta.json").write_text(
        json.dumps({"kind": "question", "spec_id": "r1-imp8", "symbol": "XAUUSDT", "thin": True})
    )
    idea_dir = tmp_path / "research" / "ideas" / "demo-r1"
    idea_dir.mkdir(parents=True)
    dump_yaml(
        {
            "schema": "themis.idea.v1",
            "slug": "demo-r1",
            "title": "demo bounce",
            "english_origin": "75% bounce",
            "current": {"version": 1, "spec_ids": ["r1-imp8"]},
            "versions": [
                {
                    "version": 1,
                    "english": "75% bounce",
                    "spec_ids": ["r1-imp8"],
                    "runs": ["research/runs/r1fold"],
                    "screen": "weak",
                }
            ],
        },
        idea_dir / "idea.yaml",
    )
    from themis.report import write_idea_bundle

    written = write_idea_bundle("demo-r1", root=tmp_path, english="75% bounce")
    assert "html" in written and "ipynb" in written and "md" in written
    html = (idea_dir / "latest.html").read_text()
    assert "bounce_rate=40.0%" in html
    assert "COMEX" in html
    assert "atr_complete" not in html
    md = (idea_dir / "latest.md").read_text()
    assert "screen: weak" in md
    assert "research/runs/r1fold" in md
    assert "See latest.html and latest.ipynb." in md
    nb = (idea_dir / "latest.ipynb").read_text()
    assert "themis.ask.measure" in nb
    assert '"name": "python3"' in nb
    assert "metrics.json" in nb
    assert "atr_complete_rivals" not in nb
    assert "react_plus" in nb
    assert "react_minus" in nb


def test_write_idea_bundle_includes_g3_react_rates(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "open-spec.md").write_text("# stub\n")
    run = tmp_path / "research" / "runs" / "g3fold"
    run.mkdir(parents=True)
    (run / "metrics.json").write_text(
        json.dumps(
            {
                "n_days": 2415,
                "n_touch_plus33": 800,
                "n_touch_minus33": 790,
                "react_plus": 0.412,
                "react_minus": 0.455,
                "react_plus_ci95": 0.034,
                "react_minus_ci95": 0.035,
                "identity": {
                    "provider": "binance",
                    "symbol": "BTCUSDT",
                    "timeframe": "4h",
                    "not": "not COMEX",
                },
            }
        )
    )
    (run / "meta.json").write_text(
        json.dumps(
            {
                "kind": "question",
                "spec_id": "g3-atr14-through-btc-4h-v1",
                "symbol": "BTCUSDT",
                "thin": False,
            }
        )
    )
    idea_dir = tmp_path / "research" / "ideas" / "g3-atr-react"
    idea_dir.mkdir(parents=True)
    dump_yaml(
        {
            "schema": "themis.idea.v1",
            "slug": "g3-atr-react",
            "title": "G3 react",
            "english_origin": "Prior-day ATR, lines at -33% and +33%, does price react",
            "current": {"version": 1, "spec_ids": ["g3-atr14-through-btc-4h-v1"]},
            "versions": [
                {
                    "version": 1,
                    "english": "Prior-day ATR, lines at -33% and +33%, does price react",
                    "spec_ids": ["g3-atr14-through-btc-4h-v1"],
                    "runs": ["research/runs/g3fold"],
                    "screen": "weak",
                }
            ],
        },
        idea_dir / "idea.yaml",
    )
    from themis.report import write_idea_bundle

    written = write_idea_bundle("g3-atr-react", root=tmp_path)
    html = written["html"].read_text()
    assert "react_plus=41.2%" in html
    assert "react_minus=45.5%" in html
    assert "BTCUSDT" in html
    nb = written["ipynb"].read_text()
    assert "react_plus" in nb
    assert "react_minus" in nb
    assert "metrics.json" in nb
    assert "themis.ask.measure" in nb
    assert "atr_complete_rivals" not in nb


def test_write_idea_bundle_empty_runs_does_not_advertise_html(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "open-spec.md").write_text("# stub\n")
    idea_dir = tmp_path / "research" / "ideas" / "empty-idea"
    idea_dir.mkdir(parents=True)
    (idea_dir / "latest.html").write_text("<html>stale COMEX residue</html>\n")
    (idea_dir / "latest.ipynb").write_text("{}\n")
    dump_yaml(
        {
            "schema": "themis.idea.v1",
            "slug": "empty-idea",
            "title": "empty",
            "english_origin": "none",
            "current": {"version": 1, "spec_ids": []},
            "versions": [
                {
                    "version": 1,
                    "english": "none",
                    "spec_ids": [],
                    "runs": [],
                    "screen": None,
                }
            ],
        },
        idea_dir / "idea.yaml",
    )
    from themis.report import write_idea_bundle

    written = write_idea_bundle("empty-idea", root=tmp_path)
    assert set(written) == {"md"}
    assert written["md"] == idea_dir / "latest.md"
    md = written["md"].read_text()
    assert "See latest.html and latest.ipynb." not in md
    assert "were not written" in md
    assert not (idea_dir / "latest.html").exists()
    assert not (idea_dir / "latest.ipynb").exists()


R1_ENGLISH = (
    "How many times has price bounced after a 75% retracement on this series, this timeframe?"
)


def test_run_idea_loop_ask_fail_first_create_leaves_no_idea(tmp_path: Path, monkeypatch):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "open-spec.md").write_text("# stub\n")
    (tmp_path / "research" / "ideas").mkdir(parents=True)

    def fail_ask(*_a, **_k):
        raise AskError("no bars")

    monkeypatch.setattr("themis.ideas.run_ask", fail_ask)
    monkeypatch.setattr("themis.ideas.write_idea_bundle", lambda *a, **k: {"md": tmp_path})

    with pytest.raises(IdeaError, match="ask failed"):
        run_idea_loop(R1_ENGLISH, SERIES, root=tmp_path, offline=True)
    yaml_p = tmp_path / "research" / "ideas" / "r1-bounce-75" / "idea.yaml"
    assert not yaml_p.exists()


def test_run_idea_loop_ask_fail_partial_records_runs(tmp_path: Path, monkeypatch):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "open-spec.md").write_text("# stub\n")
    asked: list[str] = []

    def fake_ask(spec_path, **_kw):
        asked.append(str(spec_path))
        if len(asked) >= 2:
            raise AskError("second rival failed")
        folder = tmp_path / "research" / "runs" / "ask-partial"
        _write_run(
            folder,
            {
                "n": 100,
                "target_rate": 0.30,
                "stop_rate": 0.60,
                "target_rate_ci95": 0.05,
                "stop_rate_ci95": 0.05,
            },
        )
        return folder

    monkeypatch.setattr("themis.ideas.run_ask", fake_ask)
    monkeypatch.setattr("themis.ideas.write_idea_bundle", lambda *a, **k: {"md": tmp_path})

    with pytest.raises(IdeaError, match="ask failed"):
        run_idea_loop(R1_ENGLISH, SERIES, root=tmp_path, offline=True)
    idea = load_idea("r1-bounce-75", root=tmp_path)
    assert len(idea["versions"][0]["runs"]) == 1
    assert idea["versions"][0]["runs"][0].endswith("ask-partial")
    assert idea["versions"][0]["screen"] == "dead"
    assert "ask failed" in (idea["versions"][0].get("screen_note") or "")
    assert "second rival failed" in (idea["versions"][0].get("screen_note") or "")


def test_run_idea_loop_ask_fail_improve_keeps_history(tmp_path: Path, monkeypatch):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "open-spec.md").write_text("# stub\n")
    (tmp_path / "research" / "ideas").mkdir(parents=True)
    register(
        "r1-bounce-75",
        "parent english",
        SERIES,
        spec_ids=["r1-old-a", "r1-old-b"],
        root=tmp_path,
    )
    parent = load_idea("r1-bounce-75", root=tmp_path)
    parent["versions"][0]["runs"] = ["research/runs/fake-parent"]
    parent["versions"][0]["screen"] = "weak"
    save_idea(parent, root=tmp_path)

    def fail_ask(*_a, **_k):
        raise AskError("improve boom")

    monkeypatch.setattr("themis.ideas.run_ask", fail_ask)
    monkeypatch.setattr("themis.ideas.write_idea_bundle", lambda *a, **k: {"md": tmp_path})

    with pytest.raises(IdeaError, match="ask failed"):
        run_idea_loop(
            R1_ENGLISH,
            SERIES,
            name="r1-bounce-75",
            improve=True,
            root=tmp_path,
            offline=True,
        )
    idea = load_idea("r1-bounce-75", root=tmp_path)
    assert len(idea["versions"]) == 2
    assert idea["versions"][0]["runs"] == ["research/runs/fake-parent"]
    assert idea["versions"][0]["screen"] == "weak"
    assert idea["versions"][1]["screen"] == "weak"
    assert idea["versions"][1]["runs"] == []
    assert "ask failed" in (idea["versions"][1].get("screen_note") or "")
    assert "improve boom" in (idea["versions"][1].get("screen_note") or "")


def test_g3_atr_react_prove_package_is_tracked():
    """Vendored prove runs travel with git. No gitignored research/runs/ paths."""
    root = Path(__file__).resolve().parents[3]
    idea_dir = root / "research" / "ideas" / "g3-atr-react"
    idea = load_idea("g3-atr-react", root=root)
    runs = list((idea.get("versions") or [{}])[-1].get("runs") or [])
    assert runs, "g3-atr-react must list prove run folders"
    html = (idea_dir / "latest.html").read_text()
    nb = (idea_dir / "latest.ipynb").read_text()
    assert "BTCUSDT" in html
    assert "metrics.json" in nb
    for rel in runs:
        assert rel.startswith("research/ideas/g3-atr-react/runs/"), rel
        assert not rel.startswith("research/runs/"), rel
        folder = root / rel
        assert folder.is_dir(), rel
        metrics_p = folder / "metrics.json"
        assert metrics_p.exists(), rel
        assert (folder / "meta.json").exists(), rel
        assert (folder / "spec.yaml").exists(), rel
        metrics = json.loads(metrics_p.read_text())
        rp = metrics.get("react_plus")
        rm = metrics.get("react_minus")
        assert rp is not None and rm is not None, rel
        assert f"react_plus={float(rp):.1%}" in html
        assert f"react_minus={float(rm):.1%}" in html
        assert rel in nb
    from themis.report import write_idea_bundle

    written = write_idea_bundle("g3-atr-react", root=root)
    html2 = written["html"].read_text()
    for rel in runs:
        metrics = json.loads((root / rel / "metrics.json").read_text())
        assert f"react_plus={float(metrics['react_plus']):.1%}" in html2


def test_cli_idea_defaults_gold():
    src = (Path(__file__).resolve().parents[1] / "themis" / "cli.py").read_text()
    assert 'idea_p.add_argument("--symbol", default="XAUUSDT")' in src
    assert 'imp_p.add_argument("--symbol", default="XAUUSDT")' in src
