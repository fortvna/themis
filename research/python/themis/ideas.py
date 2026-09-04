"""Idea registry: slug, register, list, show, improve, run loop, screen from folders."""
from __future__ import annotations

import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from themis.ask import AskError, run_ask
from themis.compiler import BANK, compile_english, match_case
from themis.named import parse_named
from themis.paths import ideas_dir, repo_root
from themis.report import write_idea_bundle
from themis.runner import RunError, run_strategy
from themis.spec import dump_yaml, load_yaml

SCHEMA = "themis.idea.v1"

# Stable bank slugs (open-spec §17). Same English → same slug.
BANK_STABLE_SLUGS: dict[str, str] = {
    "G1": "g1-retrace-618-725",
    "G3": "g3-atr-react",
    "R1": "r1-bounce-75",
    "R2": "r2-reaction-n",
    "R3": "r3-mae-mfe",
    "G2": "g2-session-points",
    "G4": "g4-best-po3-fvg",
    "B0": "b0-75-1r-return",
    "U1": "u1-monday-move",
    "U2": "u2-yesterday-today",
    "U6": "u6-daily-open-break",
    "S1": "s1-monday-friday",
    "S2": "s2-three-down",
    "S5": "s5-top-decile",
    "S12": "s12-session-fraction",
    "L1": "l1-asia-london",
    "L2": "l2-session-share",
    "L3": "l3-asia-narrow",
    "L4": "l4-london-breaks-asia",
    "L5": "l5-london-open",
}

_CALL_IT_RE = re.compile(
    r"\b(?:call it|name this|call this|name it)\s+([a-z0-9][a-z0-9-]{0,46}[a-z0-9]|[a-z0-9]{2})\b",
    re.IGNORECASE,
)
_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9]|-(?!-))*[a-z0-9]$|^[a-z0-9]{2}$")

RETURN_NEEDLES = (
    "what is the return",
    "what's the return",
    "pnl",
    "how good",
    "backtest",
    "drawdown",
    "expectancy",
    "edge after costs",
)


class IdeaError(RuntimeError):
    """Idea registry / loop failure."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _instrument_from_series(series: dict[str, str]) -> dict[str, str]:
    return {
        "provider": series.get("provider") or "binance",
        "symbol": series.get("symbol") or "XAUUSDT",
        "timeframe": series.get("timeframe") or "4h",
        "exchange": series.get("exchange") or "binanceusdm",
    }


def validate_slug(slug: str) -> str:
    """Return slug if valid; raise IdeaError otherwise. Rules: [a-z0-9-]{2,48}, no leading/trailing hyphen, no --."""
    s = (slug or "").strip().lower()
    if len(s) < 2 or len(s) > 48:
        raise IdeaError(f"slug length must be 2–48, got {len(s)}: {slug!r}")
    if s[0] == "-" or s[-1] == "-":
        raise IdeaError(f"slug may not lead/trail with hyphen: {slug!r}")
    if "--" in s:
        raise IdeaError(f"slug may not contain '--': {slug!r}")
    if not re.fullmatch(r"[a-z0-9-]+", s):
        raise IdeaError(f"slug must match [a-z0-9-]{{2,48}}: {slug!r}")
    if not _SLUG_RE.match(s):
        raise IdeaError(f"invalid slug: {slug!r}")
    return s


def slugify(text: str) -> str:
    """Normalize arbitrary text into a valid slug (may truncate)."""
    s = (text or "").lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    if len(s) < 2:
        s = (s + "xx")[:2]
    if len(s) > 48:
        s = s[:48].rstrip("-")
        if len(s) < 2:
            s = "idea-xx"
    return validate_slug(s)


def extract_call_it(english: str) -> str | None:
    m = _CALL_IT_RE.search(english or "")
    if not m:
        return None
    try:
        return validate_slug(m.group(1).lower())
    except IdeaError:
        return None


def _stop_tag(named: dict[str, Any]) -> str:
    stop = named.get("stop")
    if not isinstance(stop, dict):
        if isinstance(stop, str) and stop.strip():
            return slugify(stop)[:24]
        return "stop"
    anchor = str(stop.get("anchor") or "stop").replace("_", "-")
    if "low" in anchor:
        short = "low"
    elif "high" in anchor:
        short = "high"
    else:
        short = slugify(anchor)[:16]
    op = stop.get("op")
    k = stop.get("k")
    unit = str(stop.get("unit") or "")
    if unit.upper() == "ATR" and op:
        op_word = "plus" if op == "+" else ("minus" if op == "-" else slugify(str(op)))
        if k in (None, 1, 1.0):
            k_s = "1"
        else:
            k_s = f"{float(k):g}".replace(".", "p")
        return f"{short}-{op_word}-{k_s}atr"
    return short


def _retrace_tag(named: dict[str, Any]) -> str:
    pct = named.get("retrace_pct")
    if pct is None:
        return "path"
    v = float(pct)
    if v <= 1:
        hundred = v * 100.0
        if abs(hundred - round(hundred)) < 1e-6:
            return str(int(round(hundred)))
        return f"{hundred:.1f}".replace(".", "")
    return str(int(v))


def _sym_tag(symbol: str) -> str:
    s = (symbol or "xau").lower()
    s = re.sub(r"usdt$", "", s)
    return slugify(s) if s else "xau"


def propose_slug(
    english: str,
    series: dict[str, str],
    *,
    name: str | None = None,
) -> str:
    """Operator --name / call-it, else stable bank slug, else {sym}-{tf}-{retrace}-{stop-tag}."""
    if name:
        return validate_slug(name)
    call = extract_call_it(english)
    if call:
        return call
    cid, _rec = match_case(english)
    if cid and cid in BANK_STABLE_SLUGS:
        return BANK_STABLE_SLUGS[cid]
    named = parse_named(english)
    sym = _sym_tag(str(named.get("symbol") or series.get("symbol") or "XAUUSDT"))
    tf = str(named.get("timeframe") or series.get("timeframe") or "4h").lower()
    retr = _retrace_tag(named)
    stop = _stop_tag(named)
    return slugify(f"{sym}-{tf}-{retr}-{stop}")


def english_wants_run(english: str) -> bool:
    t = (english or "").lower()
    return any(n in t for n in RETURN_NEEDLES)


def idea_yaml_path(slug: str, *, root: Path | None = None) -> Path:
    return ideas_dir(root) / validate_slug(slug) / "idea.yaml"


def load_idea(slug: str, *, root: Path | None = None) -> dict[str, Any]:
    p = idea_yaml_path(slug, root=root)
    if not p.exists():
        raise IdeaError(f"idea not found: {slug}")
    return load_yaml(p)


def save_idea(idea: dict[str, Any], *, root: Path | None = None) -> Path:
    slug = validate_slug(str(idea.get("slug") or ""))
    p = ideas_dir(root) / slug / "idea.yaml"
    dump_yaml(idea, p)
    return p


def show_idea(slug: str, *, root: Path | None = None) -> dict[str, Any]:
    return load_idea(slug, root=root)


def list_ideas(*, root: Path | None = None) -> list[dict[str, Any]]:
    d = ideas_dir(root)
    if not d.exists():
        return []
    rows: list[dict[str, Any]] = []
    for child in sorted(p for p in d.iterdir() if p.is_dir()):
        yp = child / "idea.yaml"
        if not yp.exists():
            continue
        idea = load_yaml(yp)
        cur = idea.get("current") or {}
        vers = idea.get("versions") or []
        last = vers[-1] if vers else {}
        rows.append(
            {
                "slug": idea.get("slug") or child.name,
                "title": idea.get("title"),
                "screen": last.get("screen"),
                "version": cur.get("version") or last.get("version"),
                "spec_ids": cur.get("spec_ids") or last.get("spec_ids") or [],
            }
        )
    return rows


def _job_rel(job: str | Path | None, root: Path) -> str | None:
    if not job:
        return None
    p = Path(job)
    if p.is_dir():
        y = p / "job.yaml"
        if y.exists():
            p = y
    return _rel(p, root)


def register(
    slug: str,
    english: str,
    series: dict[str, str],
    spec_ids: list[str] | None = None,
    *,
    title: str | None = None,
    named: dict[str, Any] | None = None,
    job: str | Path | None = None,
    case_id: str | None = None,
    improve: bool = False,
    screen: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    slug = validate_slug(slug)
    root = root or repo_root()
    dest_dir = ideas_dir(root) / slug
    dest = dest_dir / "idea.yaml"
    spec_ids = list(spec_ids or [])
    job_rel = _job_rel(job, root)

    if dest.exists() and not improve:
        raise IdeaError(
            f"idea already exists: {slug}. use themis idea improve --name {slug}"
        )

    if improve:
        if not dest.exists():
            raise IdeaError(f"cannot improve missing idea: {slug}")
        idea = load_yaml(dest)
        cur = idea.get("current") or {}
        parent_ids = list(cur.get("spec_ids") or [])
        ver = int(cur.get("version") or len(idea.get("versions") or [])) + 1
        rec: dict[str, Any] = {
            "version": ver,
            "english": english,
            "parent": parent_ids,
            "named": named or {},
            "spec_ids": spec_ids,
            "job": job_rel,
            "runs": [],
            "screen": screen,
        }
        idea.setdefault("versions", []).append(rec)
        idea["current"] = {"version": ver, "spec_ids": spec_ids, "job": job_rel}
        idea["instrument"] = {**(idea.get("instrument") or {}), **_instrument_from_series(series)}
        if named is not None:
            idea["named"] = named
        if case_id:
            idea["case_id"] = case_id
        save_idea(idea, root=root)
        return idea

    dest_dir.mkdir(parents=True, exist_ok=True)
    rec = {
        "version": 1,
        "english": english,
        "parent": None,
        "named": named or {},
        "spec_ids": spec_ids,
        "job": job_rel,
        "runs": [],
        "screen": screen,
    }
    idea = {
        "schema": SCHEMA,
        "slug": slug,
        "title": title or ((english or "").strip()[:120] or slug),
        "english_origin": english,
        "created_utc": _utc_now(),
        "instrument": _instrument_from_series(series),
        "current": {"version": 1, "spec_ids": spec_ids, "job": job_rel},
        "versions": [rec],
        "named": named or {},
    }
    if case_id:
        idea["case_id"] = case_id
    save_idea(idea, root=root)
    return idea


def _metrics_n(metrics: dict[str, Any]) -> int:
    for k in ("n", "n_days", "n_events", "n_trades"):
        v = metrics.get(k)
        if v is not None:
            try:
                return int(v)
            except (TypeError, ValueError):
                continue
    return 0


def _ci_span(rate: Any, ci: Any) -> tuple[float, float] | None:
    if rate is None or ci is None:
        return None
    try:
        r = float(rate)
        c = float(ci)
    except (TypeError, ValueError):
        return None
    return (r - c, r + c)


def _spans_overlap(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return not (a[1] < b[0] or b[1] < a[0])


def screen_one_metrics(metrics: dict[str, Any]) -> str:
    """Ask screen: dead | weak | continue. Bounce-only / no target-vs-stop → weak."""
    n = _metrics_n(metrics)
    t = metrics.get("target_rate")
    s = metrics.get("stop_rate")
    if t is None or s is None:
        return "weak"
    if n < 30:
        return "weak"
    ti = _ci_span(t, metrics.get("target_rate_ci95"))
    si = _ci_span(s, metrics.get("stop_rate_ci95"))
    if ti is None or si is None:
        return "weak"
    if _spans_overlap(ti, si):
        return "weak"
    if float(s) > float(t):
        return "dead"
    if float(t) > float(s):
        return "continue"
    return "weak"


def _screen_one_run(metrics: dict[str, Any], meta: dict[str, Any] | None = None) -> str:
    """Run screen: fail_kill | weak | candidate. Not kept."""
    meta = meta or {}
    failed = list(metrics.get("kill_failed") or [])
    kill_pass = metrics.get("kill_pass")
    if kill_pass is False or failed:
        return "fail_kill"
    thin = bool(metrics.get("thin") or meta.get("thin"))
    short = bool(metrics.get("short_window") or meta.get("short_window"))
    if thin or short:
        return "weak"
    if kill_pass:
        return "candidate"
    return "weak"


def _combine_ask(labels: list[str]) -> str:
    if not labels:
        return "weak"
    uniq = set(labels)
    if uniq == {"dead"}:
        return "dead"
    if uniq == {"continue"}:
        return "continue"
    return "weak"


def _combine_run(labels: list[str]) -> str:
    if not labels:
        return "weak"
    if "fail_kill" in labels:
        return "fail_kill"
    if "weak" in labels:
        return "weak"
    if uniq := set(labels):
        if uniq == {"candidate"}:
            return "candidate"
    return "weak"


def _resolve_folder(folder: str | Path, root: Path | None) -> Path:
    p = Path(folder)
    if p.is_dir():
        return p
    if root is not None:
        alt = root / folder
        if alt.is_dir():
            return alt
        alt2 = root / "research" / "runs" / p.name
        if alt2.is_dir():
            return alt2
    return p


def screen_from_folders(folders: list[str | Path], *, root: Path | None = None) -> str:
    """Screen from run folders. Strategy folders use run labels; else ask labels."""
    root = root or repo_root()
    ask_labels: list[str] = []
    run_labels: list[str] = []
    for folder in folders:
        p = _resolve_folder(folder, root)
        mp = p / "metrics.json"
        if not mp.exists():
            continue
        try:
            metrics = json.loads(mp.read_text())
        except json.JSONDecodeError:
            continue
        if not isinstance(metrics, dict):
            continue
        meta: dict[str, Any] = {}
        meta_p = p / "meta.json"
        if meta_p.exists():
            try:
                loaded = json.loads(meta_p.read_text())
                if isinstance(loaded, dict):
                    meta = loaded
            except json.JSONDecodeError:
                meta = {}
        kind = meta.get("kind") or metrics.get("kind")
        if kind == "strategy":
            run_labels.append(_screen_one_run(metrics, meta))
        else:
            ask_labels.append(screen_one_metrics(metrics))
    if run_labels:
        return _combine_run(run_labels)
    return _combine_ask(ask_labels)


def _spec_with_csv(spec_path: str | Path, csv_path: str | Path | None) -> str | Path:
    if not csv_path:
        return spec_path
    spec = load_yaml(spec_path)
    data = dict(spec.get("data") or {})
    data["source"] = "csv"
    data["csv_path"] = str(csv_path)
    spec["data"] = data
    tmp = Path(tempfile.mkdtemp(prefix="themis-csv-")) / Path(spec_path).name
    dump_yaml(spec, tmp)
    return tmp


def _title_for(english: str, case_id: str | None) -> str:
    if case_id and case_id in BANK and case_id != "NAMED":
        return f"{case_id}: {BANK[case_id]['english']}"
    return (english or "").strip()[:120] or "idea"


def run_idea_loop(
    english: str,
    series: dict[str, str],
    *,
    name: str | None = None,
    backend: str = "mock",
    offline: bool = False,
    csv_path: str | None = None,
    thin: bool = False,
    improve: bool = False,
    root: Path | None = None,
) -> dict[str, Any]:
    """compile → register slug → ask every plan question → screen → report. Auto-run only on return English."""
    if not (english or "").strip():
        raise IdeaError("idea needs --english")
    root = root or repo_root()
    job = compile_english(english, series, backend=backend, write=True, root=root)
    status = job.get("status")
    if status != "ok":
        return {
            "status": status,
            "note": job.get("note"),
            "case_id": job.get("case_id"),
            "english": english,
            "named": job.get("named") or {},
            "job": _job_rel(job.get("written"), root),
        }

    slug = propose_slug(english, series, name=name)
    named = dict(job.get("named") or parse_named(english) or {})
    if improve:
        parent = load_idea(slug, root=root)
        parent_named = {}
        vers = parent.get("versions") or []
        if vers:
            parent_named = dict(vers[-1].get("named") or parent.get("named") or {})
        elif parent.get("named"):
            parent_named = dict(parent["named"])
        named = {**parent_named, **{k: v for k, v in named.items() if v is not None}}

    spec_ids = [str(p["id"]) for p in (job.get("plan") or []) if p.get("id")]
    case_id = job.get("case_id")
    idea = register(
        slug,
        english,
        series,
        spec_ids=spec_ids,
        title=_title_for(english, case_id if isinstance(case_id, str) else None),
        named=named,
        job=job.get("written"),
        case_id=case_id if isinstance(case_id, str) and case_id != "NAMED" else None,
        improve=improve,
        root=root,
    )

    network = not offline
    run_folders: list[Path] = []
    notes: list[str] = []
    for step in job.get("plan") or []:
        if step.get("kind") != "question":
            continue
        yaml_rel = step.get("yaml")
        if not yaml_rel:
            raise IdeaError(f"plan question {step.get('id')} has no yaml (compile write failed)")
        spec_path = root / yaml_rel
        if not spec_path.exists():
            raise IdeaError(f"missing question yaml: {yaml_rel}")
        try:
            folder = run_ask(_spec_with_csv(spec_path, csv_path), root=root, network=network)
        except AskError as e:
            raise IdeaError(f"ask failed for {step.get('id')}: {e}") from e
        run_folders.append(folder)

    if english_wants_run(english):
        ran_any = False
        for step in job.get("plan") or []:
            if step.get("kind") != "strategy":
                continue
            yaml_rel = step.get("yaml")
            if not yaml_rel:
                notes.append(f"strategy {step.get('id')} has no yaml")
                continue
            spec_path = root / yaml_rel
            if not spec_path.exists():
                notes.append(f"missing strategy yaml: {yaml_rel}")
                continue
            try:
                folder = run_strategy(
                    _spec_with_csv(spec_path, csv_path),
                    root=root,
                    network=network,
                    thin=thin,
                )
            except RunError as e:
                notes.append(f"run skipped {step.get('id')}: {e}")
                continue
            run_folders.append(folder)
            ran_any = True
        if not ran_any:
            notes.append("english asked return/pnl but no strategy run wrote a folder")

    screen = screen_from_folders(run_folders, root=root)
    rel_runs = [_rel(f, root) for f in run_folders]
    has_strategy = any(
        (json.loads((f / "meta.json").read_text()).get("kind") == "strategy")
        if (f / "meta.json").exists()
        else False
        for f in run_folders
    )
    screen_note = (
        "run screen from strategy folders. not kept. quote metrics.json."
        if has_strategy
        else "ask only. rates are outcomes, not edge. not pnl."
    )
    if notes:
        screen_note = screen_note + " " + "; ".join(notes)

    idea = load_idea(slug, root=root)
    if idea.get("versions"):
        idea["versions"][-1]["runs"] = rel_runs
        idea["versions"][-1]["screen"] = screen
        idea["versions"][-1]["screen_note"] = screen_note
        idea["versions"][-1]["named"] = named
    save_idea(idea, root=root)

    dest = ideas_dir(root) / slug
    try:
        bundle = write_idea_bundle(slug, root=root, english=english)
    except Exception as e:
        notes.append(f"report bundle failed: {e}")
        bundle = dest / "latest.html"
        screen_note = screen_note + " " + "; ".join(notes)
        if idea.get("versions"):
            idea["versions"][-1]["screen_note"] = screen_note
            save_idea(idea, root=root)
    return {
        "status": "ok",
        "slug": slug,
        "screen": screen,
        "screen_note": screen_note,
        "spec_ids": spec_ids,
        "runs": rel_runs,
        "idea": _rel(dest / "idea.yaml", root),
        "job": _job_rel(job.get("written"), root),
        "reports": {
            "html": _rel(dest / "latest.html", root),
            "md": _rel(dest / "latest.md", root),
            "ipynb": _rel(dest / "latest.ipynb", root),
            "bundle": _rel(Path(bundle), root) if bundle else None,
        },
        "note": "quote metrics only from run folders. screen is not kept.",
    }
