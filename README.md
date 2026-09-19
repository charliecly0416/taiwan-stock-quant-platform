# Taiwan Stock Quant Platform

A standalone packaged Taiwan stock research platform that combines QuantDinger backend services, qlib Option C signal consumption/ops integration, cross-analysis, an OpenAI-powered research agent, and a Vue monitoring frontend. It also documents the Scrapling/Yahoo data collection workflow used by the related qlib pipeline.

The project is designed for research and human review. It does not place broker orders by default, and the Taiwan stock monitor keeps generated recommendations in a read-only research workflow.

## Current Product Status

The active baseline is **Model A only** (`e4_frozen_qlib_2018_2022`) with `top50_exit_one_worst_sell`. B19R2R is a frozen LightGBM LambdaRank reranker over Model A's same-day Top50, using 78 PIT-safe features and excluding TW7769 without substitution. It is a research challenger in the readonly comparison workbench and an isolated automatic shadow, not the production default.

The daily lane maintains Model A artifacts; the weekday full lane captures orthogonal sources and attempts the A+B shadow. A shadow blocker must not change the baseline or the mainline pending state. Successful configuration checks do not prove a real scheduled shadow has completed. See [product and operations review](docs/PRODUCT_OPERATIONS_REVIEW_CN.md) for acceptance evidence and remaining limits.

The product helps a researcher inspect dated candidates, compare audited historical model/strategy results, and review a simulation account. Historical comparisons cannot be applied from the comparison page. Agent explanations are optional; inspecting artifacts does not require an LLM call.


## Chinese Documentation

- [项目介绍与原理](docs/PROJECT_INTRO_CN.md)
- [新 Codex 接手指南](docs/CODEX_HANDOFF_CN.md)
- [日常运维清单](docs/ops/DAILY_OPERATIONS_CHECKLIST_CN.md)
- [稳定运维手册](docs/ops/STABLE_OPERATIONS_RUNBOOK_CN.md)
- [开发接手指南](docs/DEVELOPMENT_ONBOARDING_CN.md)
- [当前项目文档入口与归档政策](docs/tw_modular_contracts/TW_CURRENT_PROJECT_DOC_ENTRY_AND_ARCHIVE_POLICY_CN.md)
- [使用文档](docs/USER_GUIDE_CN.md)
- [产品、工程与稳定运维审查](docs/PRODUCT_OPERATIONS_REVIEW_CN.md)
- [面试演示与工程说明](docs/INTERVIEW_DEMO_CN.md)
- [模块化研究管线未来开发规范](docs/tw_modular_contracts/TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md)
- [项目模块地图与链路串联说明](docs/tw_modular_contracts/TW_PROJECT_MODULE_MAP_AND_FLOW_CN.md)
- [开发、测试与实验手册](docs/tw_modular_contracts/TW_DEVELOPER_TEST_AND_EXPERIMENT_PLAYBOOK_CN.md)
- [当前策略上下文 API 字段字典](docs/tw_modular_contracts/TW_CURRENT_STRATEGY_CONTEXT_API_FIELD_DICTIONARY_CN.md)
- [新策略接入模板](docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md)
- [台股日更自动化 Runbook](docs/tw_modular_contracts/TW_DAILY_AUTO_UPDATE_RUNBOOK_CN.md)
- [每日自动更新闭环](docs/DAILY_AUTO_UPDATE_CN.md)
- [最大生产闭环说明](docs/FULL_PRODUCTION_CLOSED_LOOP_CN.md)

## What It Contains

- `backend/`: Flask/Python services extracted from QuantDinger for Taiwan stock data, qlib signals, cross-analysis, trend analysis, agent context, and safety guardrails.
- `frontend/`: Vue 2 + Vite monitoring UI extracted from QuantDinger-Vue.
- `docs/`: architecture, deployment, qlib integration, cross-analysis, Agent, frontend, and acceptance documents.
- `.github/workflows/`: CI checks for backend research stack and frontend monitor.
- `.env.example`: safe environment template. Do not commit real credentials.

## Core Capabilities

- Taiwan stock symbol sync and daily data archive.
- Executable FinMind/TWSE Taiwan stock archive and validation scripts.
- qlib Option C normalized data export, accepted latest artifact consumption, ops integration, EOD automation wrappers, and scheduler support.
- Built-in Yahoo/Scrapling crawler handoff scripts, FinMind/TWSE archive/export scripts, and qlib Option C production pipeline scripts.
- QuantDinger cross-analysis between qlib research signals, trend data, technical state, and entry-position risk.
- Read-only strategy replay using registered strategies and audited windows; the active rule is `top50_exit_one_worst_sell`. Historical research rules are not interchangeable production defaults.
- Taiwan stock simulation account workflow for research-only observation, manual review, K-line markers, and performance review.
- OpenAI Agent module for questions such as top ranked stocks, trend metrics, freshness, and research-only review context.
- Frontend dashboard focused on current Top30/Top50 ranking, today's review priorities, cross-analysis, K-line charts, strategy replay, Agent panel, and safety labels. Internal data-status, dry-run, and historical-run diagnostics are no longer part of the normal user-first page flow.
- Artifact contracts, validators and research evidence for model/strategy extensions; B19R2R development is frozen while its prospective shadow evidence accumulates.

## Safety Boundary

This repository is intended for research, analysis, and visualization only.

- No real broker credentials should be committed.
- `orders_enabled=false` is the expected Taiwan stock research mode.
- Generated recommendations are not orders.
- The UI and backend use explicit safety labels such as read-only, human review, dry-run only, and no trading.
- Any live broker integration must be handled outside this project with separate approval, credentials, and risk controls.

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
# Set a persistent SECRET_KEY and your own ADMIN_PASSWORD in backend/.env.
# Generate the signing key with: python -c "import secrets; print(secrets.token_hex(32))"
python run.py
```

### Frontend

```bash
cd frontend
corepack enable
pnpm install
pnpm dev
```

By default the frontend expects the backend API to be available through `/api` proxy settings in `vite.config.js`.


## Production Assets

Production data and frozen models are local assets and are not distributed in git. A fresh checkout cannot reproduce live predictions without supplying those assets. Demo fixtures verify reader contracts and must remain separate from live latest pointers. Do not run an asset replacement or demo generator against an operating deployment as a health check.

Use `GET /api/health` as the process liveness probe. Use `GET /api/ready` for local product readiness: it performs a read-only PostgreSQL probe and checks the registry and Model A -> readonly snapshot -> Agent prompt pointer chain. It never contacts a market-data provider or runs a model. A missing or inconsistent dependency returns HTTP 503 with bounded error codes and no filesystem paths, connection strings, or secret values.

The current product workbench has a self-contained fixture acceptance path. It builds the frontend, starts a temporary local preview, runs healthy and injected-failure desktop/tablet/mobile checks, then stops the preview:

```bash
cd frontend && corepack pnpm install
corepack pnpm exec playwright install chromium
corepack pnpm test:product-fixture
```

Evidence is written under `tmp/product_fixture_acceptance/`; the fixture dates are intentionally sealed demo data and are not evidence of live market freshness.

To reproduce the original local production effect with the existing qlib assets on this machine:

```bash
python scripts/bootstrap_full_production_assets.py --replace
python scripts/verify_full_production_loop.py
```

This bootstraps repo-local ignored assets under `qlib_pipeline/data_tw/` and `qlib_pipeline/mlruns/`, then validates the real Option C 150-stock accepted latest artifact and qlib provider dry-run. See `docs/FULL_PRODUCTION_CLOSED_LOOP_CN.md`.

Large market data and model artifacts are not committed to git. Publish them as GitHub Release artifacts or regenerate them with the included crawler/export/dump/signal scripts.

## Self-Contained Closed Loop

To verify the single-repository demo loop without external qlib/Scrapling projects:

```bash
python scripts/verify_self_contained_closed_loop.py
```

This generates local fixture market data, creates an accepted Option C style `latest_signal.json`, and validates that the QuantDinger backend reader can consume latest/top30/top50/health. See `docs/SELF_CONTAINED_CLOSED_LOOP_CN.md`.

For production daily operation, keep using or migrate the full qlib/Scrapling producer path. The included demo generator proves the repository contract and UI/backend consumption loop; it is not a replacement for production qlib LightGBM/Alpha158 training.

## Validation

Backend focused tests used during packaging:

```bash
cd backend
python -m pytest tests/test_tw_stock_agent_context.py tests/test_tw_stock_agent_chat.py tests/test_tw_stock_cross_analysis_service.py tests/test_tw_stock_cross_analysis_api.py tests/test_tw_stock_qlib_option_c_signals.py tests/test_tw_stock_quant_signal_api.py -q
```

Frontend focused checks:

```bash
cd frontend
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-agent-panel-check.mjs
node tests/unit/tw-stock-monitor-workflow-check.mjs
node tests/unit/tw-stock-monitor-qlib-ops-check.mjs
node tests/unit/tw-stock-cross-analysis-check.mjs
node tests/unit/tw-stock-rank-tech-portfolio-replay-check.mjs
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8000 node tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs
corepack pnpm build
```

The historical `tw-stock-full-scenario-readonly.mjs` script is kept as an old fixture for the previous diagnostic-heavy page. It is not the current one-click acceptance standard for the simplified user-first Taiwan stock page.

## Data Policy

The repository intentionally excludes generated market data and qlib binary artifacts.

Ignored examples:

- `data/`
- `data_tw/`
- `backend/data/`
- `backend/data_tw/`
- `frontend/dist/`
- caches and virtual environments

Use the scripts and docs to regenerate local data in your own environment. The repository now includes a self-contained demo loop under `scripts/verify_self_contained_closed_loop.py`; generated `data_tw/` artifacts remain ignored. For production-grade live Yahoo/Scrapling -> qlib LightGBM/Alpha158 training/prediction, migrate the full qlib `examples/tw/*option_c*` scripts into `qlib_pipeline/option_c/` or vendor them as a submodule.

## Attribution

This standalone project is packaged from work built on top of QuantDinger, QuantDinger-Vue, qlib research workflows, and Scrapling-style data collection. Keep upstream license notices and dependency licenses when publishing.
