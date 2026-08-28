# ADR: live compile must not rewrite a named stop

Minerva. 2026-08-28. ADR + MUST. Not a forge. No spend.

Users: Amir, Themis operators (War Room).
Open spec (Caesar): live compile must not rewrite a named stop.

## Context (files opened)

Amir English (named): 1h highs/lows, retrace 61.8, stop = swing low + 1 ATR, TP = swing high. Binance XAUUSDT.

| folder | what it measured | stop in YAML |
| --- | --- | --- |
| `/workspace/r1_runs/h1-618/` (Prometheus) | that English | `rules.stop: swing low + 1*ATR(14)` in `themis-research/compiler/h1-618/retrace-618-n5-atrstop-xau-1h-strategy.yaml` |
| `/workspace/themis/research/jobs/20260828T181247Z-live/` (xAI grok-4) | a different job | `research/specs/xauusdt_1h_retrace_swing.yaml` `rules.stop: 1 ATR beyond the swing origin (long: low - ATR)` |

Job `source.english` still says `low + 1 atr`. YAML wrote `low - ATR`. Fractal rivals became 2 vs 5 (Prometheus used 5 vs 3). Live report: `research/reports/20260828-xau-1h-618-live.md`. Both jobs fail. Do not mix. Do not tune. Not kept.

Law already on file (`docs/open-spec.md` / `/workspace/themis-research/open-spec.md`): freeze YAML before metrics; rival asks for **vague** English; compiler writes YAML only; quote only run folders.

## Decision

**a + b, enforced by c.**

- **(a) Pin** every field the English **names** (stop, target, entry, side, retrace pct, timeframe, symbol) into frozen YAML **before** any model rewrite.
- **(b) Rivals** only for fields the English did **not** name (fractal n, ATR period if unstated). Each rival is a **new spec id**. Cousins copy the pinned named fields. They are extra, not replacements.
- **(c) Refuse** `compile` if English named a stop/target and the written YAML differs. No mock fallback. `status: error`.

Do not pick (b) alone: that is how live xAI replaced `low+1 ATR` with `low−ATR` and still said `status: ok`.
Do not pick (c) as string-equality on the whole YAML: models reword. Compare **normalized named fields**, not prose.
Do not pick (a) without (c): pin without a gate will drift again.

## Bake-off

| option | what happens on this English | trade-off |
| --- | --- | --- |
| a only | YAML must say stop = low + 1 ATR | Unnamed fractal n still needs rivals. No hard fail if the model overwrites after pin. |
| b only | fractal 2 vs 5 as cousins | Named stop becomes “just another rival.” Silent hypothesis swap. **Reject as default.** |
| c only | refuse if YAML stop ≠ English stop | Correct gate. Needs a pin/extract step or every live compile errors on wording. |
| **a+b+c (chosen)** | pin stop/target/pct; rival fractal n (new ids); refuse if stop formula ≠ named | Measures what Amir said. Rivals stay for vagueness. Drift is a compile error, not a cousin. |

## MUST

1. **MUST** parse English into `job.named` before write. Required keys when present in English: `side`, `entry`, `stop`, `target`, `retrace_pct`, `timeframe`, `symbol`. This job: `stop: swing_low + 1*ATR`, `target: swing_high`, `retrace_pct: 0.618`, `timeframe: 1h`.
2. **MUST** overlay `job.named` onto every question and strategy YAML in the plan **after** the model returns and **before** files are written.
3. **MUST NOT** let the model change a named stop or target. `low + 1 ATR` is not `low − ATR`. Sign is part of the name.
4. **MUST** emit rivals only for **unnamed** keys. New spec ids. Cousins **MUST** copy `job.named`. ATR period unstated → 14 vs 20 is allowed. Stop formula named → not a rival.
5. **MUST** `compile` exit nonzero if a named field is missing or disagrees after overlay. Message names the field and both values. Do not fall back to mock. Do not `status: ok`.
6. **MUST** apply the same pin+refuse rules to `mock`, `xai`, and `openai`.
7. **MUST NOT** mix folders. Amir’s English stays `r1_runs/h1-618`. Live `low−ATR` folders are a different spec id. Quote paths. Do not `tune` a named-stop failure into a different stop.
8. **MUST NOT** treat a geometrically tight stop as a bug to “fix.” If 61.8 entry leaves no room for `low+1 ATR`, that is the hypothesis. Measure it. Do not rewrite it.

## Out of scope / not opened

- Google Drive (skipped).
- Raw xAI prompt/response bytes (not on disk as a prompt file; only job YAML + report).
- `fortvna/argus`, `stake`, `university`, `ts-console` (404).
- Changing `docs/open-spec.md` on git (this ADR is the revision input; Caesar routes the spec patch; Vulcan forges).
- Re-running either job.

## Spec patch (when Caesar says)

Add to compiler gates: `named_fields_pinned: true`. Add refuse rule to §3. Rivals_min still applies to unnamed definitions only.
