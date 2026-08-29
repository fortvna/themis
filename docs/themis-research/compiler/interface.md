# Compiler interface

English in. Structured job out. YAML is frozen before any metric is spoken.
Grok-capable. Mock until Amir logs in. No spend. No paid vendor lock.

This is not a spec. Minerva writes `open-spec.md`. This is the compiler contract Prometheus tried.

## Shape

```
compile(english, series, media=[]) -> Job
```

- `english`: operator words.
- `series`: `{provider, symbol, timeframe}` as named. Compiler does not pick a venue.
- `media`: later. `[{type: image|video, path}]`. Mock returns `unsupported` and still compiles the text. Do not block the text path on media.

`Job` is a plan, not a number.

```yaml
schema: themis.job.v1
source:
  english: "..."
  media: []
  compiler: mock          # mock | xai | openai
  model: grok-mock
instrument:
  provider: binance       # required, as named
  symbol: XAUUSDT
  timeframe: 4h
plan:
  - kind: question        # pandas ask
    id: ...
    purpose: rival_definition | path_stats
    yaml: path
  - kind: strategy        # only after required asks
    id: ...
    requires: [question ids]
    yaml: path
    run_eligible: false   # gold 4h: false until gates pass
gates:
  freeze_yaml_before_metrics: true
  rivals_min: 2
  ask_before_run: true
  tune_requires: walkforward_eligible
forbidden:
  - inventing_a_metric_in_chat
  - running_strategy_before_rival_asks
  - calling_a_paid_sdk_from_mock
```

## Providers

One protocol. Swap the backend. Do not import a vendor SDK in the harness core.

| id | when | spend |
| --- | --- | --- |
| `mock` | default now | none. maps known English to frozen YAML. Never networks. |
| `xai` | after `themis login xai` | none until Amir says to compile live |
| `openai` | after `themis login openai` | none until Amir says to compile live |

OAuth device-code. Tokens in `~/.themis/auth.json`, never git. Live compile refuses if not logged in. Mock ignores login.

Unknown English under mock: return `status: needs_human` with a blank Job skeleton. Do not invent definitions.

## What the compiler may write

YAML only. Question specs and, if the English is a trade, a strategy spec marked `run_eligible` from the gated ladder.

It may not write `metrics.json`. pandas `ask` or `run` (load `implements` → fill → metrics) does that after the YAML exists. Retrace-swing English points at `strategies/retrace_swing.py`. A new kind of idea needs a new family module, not a silent retrace.

## Gold example 1 (tried)

English: *4h swing high/low, enter retrace 61.8–72.5, stop swing low, target swing high.*

Mock emits two rival question YAMLs (`n=5`, `n=3` fractals, confirmation delay `i+n`) and one strategy YAML (`run_eligible: false`, `tune_eligible: false`). pandas then measures path stats on Binance XAUUSDT 4h Vision bars. See `example-1/` and the addendum.
