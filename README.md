# Themis

**Themis** is a research loop you can talk to. You ask in English. It freezes a YAML, pulls the OHLC you named, measures, and only then lets a trade exist. The spec is the law. A named run is the verdict.

This repository is **Themis**. The package and CLI name is `themis`.

The implementation spec is [`docs/open-spec.md`](docs/open-spec.md). It supersedes [`prompt.md`](prompt.md) for implementation. Research notes sit under [`docs/themis-research/`](docs/themis-research/).

Go-live means **this conversation works**, not that an order is sent.

YAML is **not** executable. v1 venue is **Binance USD-M** (`binanceusdm`).

## Build brief

Start with [`docs/open-spec.md`](docs/open-spec.md). That is the implementation spec. It supersedes [`prompt.md`](prompt.md).

Example English lives in [`questions.md`](questions.md). Compiler contract: [`docs/themis-research/compiler/interface.md`](docs/themis-research/compiler/interface.md).
