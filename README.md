# Taiwan Stock Quant Platform

A standalone packaged Taiwan stock research platform that combines QuantDinger backend services, qlib Option C signal consumption/ops integration, cross-analysis, an OpenAI-powered research agent, and a Vue monitoring frontend. It also documents the Scrapling/Yahoo data collection workflow used by the related qlib pipeline.

The project is designed for research and human review. It does not place broker orders by default, and the Taiwan stock monitor keeps generated recommendations in a read-only research workflow.

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
- Built-in Yahoo/Scrapling crawler handoff scripts and a self-contained Option C style demo artifact generator.
- QuantDinger cross-analysis between qlib research signals and monitor/trend data.
- Read-only backtest templates and historical simulation.
- OpenAI Agent module for questions such as top ranked stocks, trend metrics, and buy/sell research suggestions.
- Frontend dashboard with qlib rankings, trend charts, cross-analysis, dry-run operations, Agent panel, and safety labels.

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
corepack pnpm build
```

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
