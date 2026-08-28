"""themis CLI."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from themis import auth
from themis.ask import AskError, run_ask
from themis.compiler import CompileError, compile_bank, compile_english
from themis.runner import RunError, compare, fetch, report, run_strategy, tune, validate, walkforward


def _series(args: argparse.Namespace) -> dict[str, str]:
    return {
        "provider": args.provider,
        "symbol": args.symbol,
        "timeframe": args.timeframe,
        "exchange": getattr(args, "exchange", None) or "binanceusdm",
    }


def _print(obj: Any) -> None:
    if isinstance(obj, (dict, list)):
        print(json.dumps(obj, indent=2, default=str))
    else:
        print(obj)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="themis")
    sub = p.add_subparsers(dest="cmd", required=True)

    login = sub.add_parser("login")
    login.add_argument("provider", choices=["xai", "openai"])
    logout = sub.add_parser("logout")
    logout.add_argument("provider", choices=["xai", "openai"])
    sub.add_parser("whoami")

    comp = sub.add_parser("compile")
    comp.add_argument("--english", default="")
    comp.add_argument("--id", dest="case_id", default="")
    comp.add_argument("--provider", default="binance")
    comp.add_argument("--symbol", default="XAUUSDT")
    comp.add_argument("--timeframe", default="4h")
    comp.add_argument("--exchange", default="binanceusdm")
    comp.add_argument("--backend", default="mock", choices=["mock", "xai", "openai"])
    comp.add_argument("--bank", action="store_true")
    comp.add_argument("--no-write", action="store_true")

    fet = sub.add_parser("fetch")
    fet.add_argument("--spec", required=True)
    fet.add_argument("--offline", action="store_true")

    askp = sub.add_parser("ask")
    askp.add_argument("--spec", default=None)
    askp.add_argument("--english", default=None)
    askp.add_argument("--offline", action="store_true")
    askp.add_argument("--csv", default=None)

    runp = sub.add_parser("run")
    runp.add_argument("--spec", required=True)
    runp.add_argument("--thin", action="store_true")
    runp.add_argument("--offline", action="store_true")
    runp.add_argument("--csv", default=None)

    val = sub.add_parser("validate")
    val.add_argument("--spec", required=True)
    val.add_argument("--from-run", required=True)
    val.add_argument("--offline", action="store_true")

    wf = sub.add_parser("walkforward")
    wf.add_argument("--spec", required=True)
    wf.add_argument("--offline", action="store_true")
    wf.add_argument("--csv", default=None)

    cmpp = sub.add_parser("compare")
    cmpp.add_argument("--family", required=True)

    tun = sub.add_parser("tune")
    tun.add_argument("--spec", required=True)
    tun.add_argument("--offline", action="store_true")
    tun.add_argument("--csv", default=None)

    rep = sub.add_parser("report")
    rep.add_argument("--run", required=True)

    args = p.parse_args(argv)
    try:
        if args.cmd == "login":
            _print(auth.login(args.provider))
            return 0
        if args.cmd == "logout":
            _print(auth.logout(args.provider))
            return 0
        if args.cmd == "whoami":
            _print(auth.whoami())
            return 0
        if args.cmd == "compile":
            series = _series(args)
            if args.bank:
                jobs = compile_bank(series, write=not args.no_write)
                summary = {k: {"status": v.get("status"), "path": v.get("path"), "n_plan": len(v.get("plan") or [])} for k, v in jobs.items()}
                _print(summary)
                return 0
            english = args.english or args.case_id
            if not english:
                print("compile needs --english or --id", file=sys.stderr)
                return 2
            job = compile_english(english, series, backend=args.backend, write=not args.no_write)
            out = {k: job[k] for k in job if k not in ("questions", "strategies")}
            _print(out)
            return 0 if job.get("status") in ("ok", "needs_human") else 1
        if args.cmd == "fetch":
            s = fetch(args.spec, network=not args.offline)
            _print(s.meta())
            return 0
        if args.cmd == "ask":
            if args.english and not args.spec:
                t = args.english.lower()
                if any(w in t for w in ("what is the return", "pnl", "drawdown", "expectancy")):
                    print("ask refuses a return question with no strategy spec", file=sys.stderr)
                    return 1
                print("ask refuses a return question with no strategy spec" if "return" in t else "ask needs --spec", file=sys.stderr)
                if "return" in t or "pnl" in t:
                    return 1
                print("ask requires --spec", file=sys.stderr)
                return 2
            if not args.spec:
                print("ask requires --spec", file=sys.stderr)
                return 2
            folder = run_ask(args.spec, network=not args.offline, csv_path=args.csv)
            print(str(folder))
            metrics = json.loads((folder / "metrics.json").read_text())
            _print(metrics)
            return 0
        if args.cmd == "run":
            folder = run_strategy(args.spec, network=not args.offline, thin=args.thin, csv_path=args.csv)
            print(str(folder))
            _print(json.loads((folder / "metrics.json").read_text()))
            return 0
        if args.cmd == "validate":
            folder = validate(args.spec, args.from_run, network=not args.offline)
            print(str(folder))
            return 0
        if args.cmd == "walkforward":
            folder = walkforward(args.spec, network=not args.offline, csv_path=args.csv)
            print(str(folder))
            return 0
        if args.cmd == "compare":
            folder = compare(args.family)
            print(str(folder))
            _print(json.loads((folder / "metrics.json").read_text()))
            return 0
        if args.cmd == "tune":
            folder = tune(args.spec, network=not args.offline, csv_path=args.csv)
            print(str(folder))
            return 0
        if args.cmd == "report":
            path = report(args.run)
            print(str(path))
            return 0
        return 2
    except (CompileError, AskError, RunError, auth.AuthError) as e:
        print(str(e), file=sys.stderr)
        return 1
