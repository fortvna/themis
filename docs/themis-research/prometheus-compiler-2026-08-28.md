# Addendum: compiler interface and gold example 1

Prometheus. 2026-08-28. Beside the open spec. Not a build. No SDK call. No spend.

Interface: `themis-research/compiler/interface.md`
Mock job: `themis-research/compiler/mock_job.json`
Frozen YAML: `themis-research/compiler/example-1/`

## Interface in one line

English (and later image/video) in. `themis.job.v1` out. YAML frozen before pandas runs. Default compiler is `mock`. `grok` and any OpenAI-compatible backend plug in when Amir gives a key. No vendor import in the core. No live call tonight.

## Example 1, frozen then measured

English: 4h swing high/low, enter retrace 61.8–72.5, stop swing low, target swing high.

Rivals: fractal `n=5` vs `n=3`. Swing at bar `i` is knowable at `i+n`. Zone touch after that. Target = swing extreme. Stop = swing origin. pandas path stats on Binance XAUUSDT 4h, 1396 bars, 2025-12-11 to 2026-07-31. Not pnl. Not a `run`.

| rival | n | target first | stop first | same-bar both | still open |
| --- | ---: | ---: | ---: | ---: | ---: |
| n=5 | 116 | 28.5% | 63.8% | 3.4% | 4.3% |
| n=3 | 178 | 31.5% | 60.1% | 6.2% | 2.2% |

Stop hits first about twice as often as target. n moves with the fractal. Same English. Do not promote. Strategy YAML exists and is marked `run_eligible: false`. Event tables stay off git (`r1_runs/example-1/`).

## What this does to the spec

The compiler is a YAML writer, not an oracle. Example 2–4 (sessions, ATR ±33%, best Po3/FVG) should emit rival asks the same way. “Best” is a family after `run`, and gold is not WF eligible, so “find the best Po3” on XAU must refuse `tune` and refuse a single-winner claim.
