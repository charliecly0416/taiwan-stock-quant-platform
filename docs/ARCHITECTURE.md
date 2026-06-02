# Architecture

## Data Flow

1. Taiwan stock data is collected and archived through backend scripts and data-source modules.
2. Daily bars and market metadata are validated, normalized, and exported for qlib-compatible research.
3. qlib Option C generates research signals and accepted latest artifacts.
4. Cross-analysis compares qlib scores, QuantDinger monitor state, trend metrics, quality warnings, and historical run data.
5. The Agent context service exposes safe, read-only answers from accepted latest and monitor data.
6. The Vue frontend displays rankings, chart windows, signal history, dry-run qlib ops, cross-analysis, and Agent Q&A.

## Main Backend Modules

- `backend/app/data_sources/tw_stock.py`: Taiwan stock market data source.
- `backend/app/routes/tw_stock.py`: Taiwan stock APIs.
- `backend/app/services/tw_stock_qlib_option_c*.py`: qlib Option C signal, scheduler, EOD, accepted latest, and ops services.
- `backend/app/services/tw_stock_cross_analysis*.py`: cross-analysis service and history.
- `backend/app/services/tw_stock_agent*.py`: Agent context, chat, OpenAI adapter, and guardrails.
- `backend/app/services/tw_stock_monitor*.py`: monitor configuration, alerts, worker, and scan flow.
- `backend/scripts/*tw_stock*.py`: data archive, validation, monitor, simulation, paper report, and research-stack scripts.

## Main Frontend Modules

- `frontend/src/views/tw-stock-monitor/index.vue`: primary Taiwan stock research monitor.
- `frontend/src/api/tw-stock.js`: API client contract.
- `frontend/tests/unit/tw-stock-*.mjs`: static and workflow checks.
- `frontend/.github/workflows/tw-stock-monitor-frontend.yml`: frontend CI.

## Research-Only Design

The platform separates research signals from trading execution. qlib output is displayed as ranking and observation data, not as orders or position targets. Human review remains the required decision point.
