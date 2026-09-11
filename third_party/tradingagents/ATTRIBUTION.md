# TradingAgents Attribution

Vendored on: 2026-06-30

Upstream project: TradingAgents: Multi-Agents LLM Financial Trading Framework

Upstream source used for this vendor import:

```text
/home/chuliyang/TradingAgents
```

Upstream local git revision at import:

```text
85946c2f60768ab2dae23a5a36cd927662feef94
```

Upstream version declared in `pyproject.toml`:

```text
0.3.0
```

License:

```text
Apache License 2.0
```

The upstream `LICENSE`, `README.md`, `CHANGELOG.md`, source package, CLI package,
tests, scripts, and assets are vendored under `third_party/tradingagents/`.

This repository treats the vendored TradingAgents source as third-party code.
Project-specific Taiwan stock behavior must be implemented in repo-local
adapter, sanitizer, validator, and artifact-builder modules outside this
directory unless a vendored patch is explicitly documented here.

Runtime use from this project must not depend on `/home/chuliyang/TradingAgents`;
callers should use the repo-local vendored source or the project adapter.
