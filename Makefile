SHELL := /bin/bash

PYTHON ?= python3
BACKEND_PORT ?= 5000
FRONTEND_PORT ?= 8000
BACKEND_URL ?= http://127.0.0.1:$(BACKEND_PORT)

.DEFAULT_GOAL := help
.PHONY: help start test verify demo

help:
	@printf '%s\n' \
		'Taiwan Stock Quant Platform' \
		'' \
		'  make start   Start the local backend and frontend (requires DB, .env, and local assets)' \
		'  make test    Run fast self-contained backend and frontend checks' \
		'  make verify  Run full local release gates (requires frozen/runtime/golden assets)' \
		'  make demo    Run the fresh-checkout fixture UI (requires dependencies and Playwright)' \
		'' \
		'Common overrides:' \
		'  PYTHON=python BACKEND_PORT=5000 FRONTEND_PORT=8000 BACKEND_URL=http://127.0.0.1:5000'

start:
	@set -euo pipefail; \
	cleanup() { \
		kill "$${backend_pid:-}" "$${frontend_pid:-}" 2>/dev/null || true; \
		wait "$${backend_pid:-}" "$${frontend_pid:-}" 2>/dev/null || true; \
	}; \
	trap cleanup EXIT INT TERM; \
	( \
		cd backend; \
		env \
			PYTHON_API_HOST=127.0.0.1 \
			PYTHON_API_PORT="$(BACKEND_PORT)" \
			AGENT_LIVE_TRADING_ENABLED=false \
			ENABLE_PENDING_ORDER_WORKER=false \
			ENABLE_PORTFOLIO_MONITOR=false \
			ENABLE_TW_STOCK_MONITOR_WORKER=false \
			ENABLE_REFLECTION_WORKER=false \
			ENABLE_OFFLINE_AI_CALIBRATION=false \
			DISABLE_RESTORE_RUNNING_STRATEGIES=true \
			POSITION_SYNC_ENABLED=false \
			USDT_PAY_ENABLED=false \
			"$(PYTHON)" run.py \
	) & backend_pid=$$!; \
	( \
		cd frontend; \
		VITE_DEV_PROXY_TARGET="$(BACKEND_URL)" corepack pnpm dev --host 127.0.0.1 --port "$(FRONTEND_PORT)" --strictPort \
	) & frontend_pid=$$!; \
	printf 'Workbench: http://127.0.0.1:%s/#/tw-stock-monitor\n' "$(FRONTEND_PORT)"; \
	printf 'Press Ctrl+C to stop both services.\n'; \
	wait -n $$backend_pid $$frontend_pid

test:
	@PYTHONPATH=.:backend "$(PYTHON)" -m pytest -q backend/tests/test_research_startup_safety.py
	@PYTHONPATH=.:backend "$(PYTHON)" -m pytest -q \
		tests/unit/test_tw_portfolio_state_contract_wf5b.py \
		-k compatibility_facade_restores_child_configuration
	@cd frontend && node tests/unit/tw-stock-monitor-static-check.mjs
	@cd frontend && node tests/unit/tw-stock-monitor-workflow-check.mjs

verify: test
	@PYTHONPATH=.:backend "$(PYTHON)" backend/scripts/verify_tw_stock_research_stack.py
	@"$(PYTHON)" scripts/validate_arch1_baseline_descriptor.py --json
	@"$(PYTHON)" scripts/validate_tw_modular_m_contracts.py --run-golden --json
	@"$(PYTHON)" scripts/validate_tw_modular_registry_m2.py --json
	@"$(PYTHON)" scripts/validate_tw_daily_orchestrator_m3.py --run-golden --json
	@cd frontend && node tests/unit/tw-stock-monitor-qlib-ops-check.mjs
	@cd frontend && node tests/unit/tw-stock-cross-analysis-check.mjs
	@cd frontend && corepack pnpm build

demo:
	@cd frontend && corepack pnpm test:product-fixture
