# WR-themis

Product: themis
Owner (human): Arafat
Commander: Caesar
Spec: Minerva
Tech: Prometheus
Build: Vulcan
Repo path: /workspace/fortuna/projects/themis
Remote: https://github.com/fortvna/themis

## Objective (this milestone)

SPEC.md v0 canon: idea → YAML → pandas screen → named slug → MD+HTML with charts + Sharpe/Sortino/Calmar. Named-stop pin. Stack named: ADR/stack-v1.md. Caesar accept. Vulcan parked until accept.

## Status

Caesar accepted SPEC.md v0 and ADR/stack-v1.md on 2026-09-01. M1 is live. Vulcan forges. Prometheus reviews commits. No push this turn.

## MUST in scope

- SPEC.md v0 with F-50 ideas, F-60 metrics, F-70 dual reports, F-80 prompt
- RESEARCH.md
- Git status clean
- No git push

## Out of scope

- Product code this turn
- Force-push / remote push
- Product stack change without ADR

## Decisions

- 2026-08-28 named-stop pin+refuse (see ADR/live-compile-named-stop.md)
- 2026-08-28 all Themis work stays in this repo. No other trees. Chat WR-themis. Remote: https://github.com/fortvna/themis.
- 2026-09-01 stack: Python 3.11 + pandas/numpy/pyyaml + inline SVG (`ADR/stack-v1.md`). matplotlib not runtime.
- 2026-09-01 Caesar accepted SPEC.md v0 + ADR/stack-v1.md. M1 unlocked.

## Blockers

none

## Next action (who, file)

Vulcan: M1 MUST in `research/python/` (F-50 ideas, F-60 metrics, F-70 reports, F-80 prompt, F-72 strategy SVG). Prometheus: review. No git push unless Arafat says this turn.

## Imported (2026-08-28 file-first)

Copied into this repo. Originals deleted 2026-08-28. SPEC.md was not filled.

| from | to |
| --- | --- |
| `/workspace/themis/docs/` | `docs/` |
| `/workspace/themis/research/` | `research/` (alongside existing `product-stack-map.md`) |
| `/workspace/themis/research/python/themis/` | `src/themis/` |
| `/workspace/themis/research/python/strategies/` | `src/strategies/` |
| `/workspace/themis/research/python/tests/` | `src/tests/` |
| `/workspace/themis/research/python/pyproject.toml` | `src/pyproject.toml` |
| `/workspace/themis/README.md` `_README.md` `_docs_open_spec.md` `.gitignore` | `imported/workspace-themis/` (README not smashed) |
| `/workspace/exam-ask.py` `exam-auth.py` `exam-cli.py` `exam-compiler.py` `exam-elig.py` `exam-runner.py` `check_bank.py` `r1_gold_ask.py` `r1_trial.py` | `spike/` (filenames kept) |
| `/workspace/exam-pkg/` | `imported/exam-pkg/` |
| `/workspace/themis-forge/` | `imported/workspace-themis-forge/` (`.venv` not copied) |
| `/workspace/themis-research/` | `imported/workspace-themis-research/` |
| `/workspace/git-land/` | `imported/git-land/` |
| `/workspace/r1_runs/` | `imported/r1_runs/` |
| `/tmp/themis-main/` | `imported/tmp-themis-main/` (GitHub snapshot labeled; not written into SPEC.md) |
| `/tmp/themis-main/prompt.md` `questions.md` `LICENSE` | repo root (filenames kept) |
| `/tmp/gh-themis/` | `imported/tmp-gh-themis/` |
| `/tmp/gh-final/` | `imported/tmp-gh-final/` |
| `/tmp/themis-gh/` | `imported/tmp-themis-gh/` |
| `/tmp/themis-land/` | `imported/tmp-themis-land/` |
| `/tmp/open-spec.md` and related tmp docs | `imported/tmp-docs/` |
| `/tmp/patch_*.py` and other tmp spike scripts | `imported/tmp-spikes/` |
| `/tmp/btc-vision/` | `imported/tmp-btc-vision/` |
| `/tmp/themis-synth-*.csv` `themis_fixture_xau_4h.csv` | `imported/tmp-fixtures/` |

Not copied (secrets): `~/.themis/auth.json`, `/tmp/themis-home-test/.themis/auth.json`, `/tmp/themis-xai-device.json`, `/tmp/xai_device.json`, `/tmp/xai_headers.txt`. See `/workspace/fortuna/SECRETS.md`.

Not copied (junk / not source): GitHub 404 JSON, GitHub API push payloads, pytest temp `themis-csv-*`, `/workspace/themis-trial/` venv, HTML scrapes, sand-* box files.

## Next action (who, file) — after import

Done. SPEC.md v0 is in the repo.
