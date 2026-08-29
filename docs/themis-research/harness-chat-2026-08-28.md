# Harness chat vs Themis files

Research. 2026-08-28. Not a spec. Not a build.

A later GUI (Harness) should feel like a normal LLM chat: login `xai` or `openai`, projects, sessions, hypotheses. That UI does not get its own engine. It drives the loop already in `docs/open-spec.md`.

## Mapping

| Chat surface | Themis object |
| --- | --- |
| Project | a desk: series + costs + which ideas belong together |
| Session | one conversation thread |
| Hypothesis | **idea slug** (`h1-618`) with versions |
| One freeze | **spec id** (YAML) |
| One measurement | **run folder** |
| “How did it do?” | `report` from that folder |

Login already exists for compile. Chat still may not invent a 70% or a Sharpe.

## Ask vs run in chat

- “What happens after a 75% retrace?” → `ask` (path stats).
- “What’s the return at 1:1?” → `run` after costs, after the asks that pinned stop/impulse.
- Do not multiply hit-rate × R in the thread.

## Templates

Same shape, new numbers → same `implements`, numbers on the YAML.
New kind (ORB, FVG, Po3) → new `strategies/<family>.py` or `needs_human`.
Not a new `.py` per message. Not a notebook as the hypothesis.

A notebook, if the GUI shows one, is a **replay of a run folder** (swings, zone, fill, equity). Ratios still come from `metrics.json`.
