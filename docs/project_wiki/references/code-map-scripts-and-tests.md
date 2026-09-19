---
title: Scripts And Tests Code Map
category: references
tags: [scripts, tests, validators, code-map]
relationships:
  - target: "[[concepts/modular-artifact-chain]]"
    type: related_to
  - target: "[[skills/modular-integration-regression-workflow]]"
    type: related_to
  - target: "[[skills/readonly-e2e-acceptance-workflow]]"
    type: related_to
sources: [/home/chuliyang/taiwan-stock-quant-platform/scripts/build_tw_agent_daily_prompt_artifact.py, /home/chuliyang/taiwan-stock-quant-platform/scripts/validate_tw_agent_daily_prompt_artifact.py, /home/chuliyang/taiwan-stock-quant-platform/scripts/validate_tw_modular_artifact_contract.py, /home/chuliyang/taiwan-stock-quant-platform/scripts/run_tw_modular_contract_regression.py, /home/chuliyang/taiwan-stock-quant-platform/scripts/run_daily_tw_stock_auto_update.py, /home/chuliyang/taiwan-stock-quant-platform/scripts/publish_tw_modular_readonly_snapshot.py, /home/chuliyang/taiwan-stock-quant-platform/backend/tests/test_tw_stock_agent_simple_chat.py, /home/chuliyang/taiwan-stock-quant-platform/backend/tests/test_tw_stock_readonly_replay_window_api.py, /home/chuliyang/taiwan-stock-quant-platform/backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py, /home/chuliyang/taiwan-stock-quant-platform/frontend/tests/e2e/tw-stock-agent-simple-chat-network.mjs, /home/chuliyang/taiwan-stock-quant-platform/frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs]
summary: Scripts/tests 静态分类表，区分 current product path、validator、builder、diagnostic、readonly dry-run、legacy/archive 和 forbidden runtime action。
provenance:
  extracted: 0.86
  inferred: 0.14
  ambiguous: 0.0
base_confidence: 0.82
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: supporting
created: 2026-06-20T16:00:00Z
updated: 2026-06-20T16:00:00Z
---

# Scripts And Tests Code Map

W3 对 scripts/tests 只做静态分类，未运行测试、服务、日更、数据刷新、provider publish、accepted latest switch 或 artifact generation。

## Scripts Classification

| Class | Representative scripts | Notes |
|---|---|---|
| current product path | `run_daily_tw_stock_auto_update.py`, `build_tw_agent_daily_prompt_artifact.py`, `build_tw_readonly_replay_window_index.py` | 产品路线相关入口；W3 不运行 |
| builder | `build_tw_agent_daily_prompt_artifact.py`, `build_tw_modular_order_intent_artifact.py`, `build_tw_readonly_replay_window_artifact.py`, `build_tw_paper_portfolio_decision_artifact.py` | 生成 artifact 的脚本，W3 只映射职责 |
| validator | `validate_tw_agent_daily_prompt_artifact.py`, `validate_tw_modular_artifact_contract.py`, `validate_tw_modular_registry_m2.py`, `validate_tw_modular_readonly_snapshot.py`, `validate_tw_readonly_replay_window_artifact.py`, `validate_tw_readonly_replay_window_index.py`, `validate_tw_readonly_replay_window_query.py` | 守合同、schema、forbidden field、readonly flags |
| readonly regression / static audit | `run_tw_modular_contract_regression.py`, `validate_tw_frontend_readonly_m4.py`, `validate_tw_daily_orchestrator_m3.py` | 聚合 validator/static checks；可能写实验报告，W3 不执行 |
| readonly dry-run / shadow | `run_tw_modular_shadow_daily.py`, `run_tw_modular_order_intent_replay.py`, `run_tw_modular_order_intent_replay_parity.py` | 只读/shadow/replay 证据路径；不是实盘 |
| publisher with publish behavior | `publish_tw_modular_readonly_snapshot.py` | 只读 snapshot publisher；W3 不运行，且不代表 provider publish 或 accepted latest switch |
| provider staging / external | `fetch_tw_provider_external_data.py`, `pull_tw_provider_staging_data.py`, `validate_tw_provider_staging_data.py` | 数据源/staging 边界；不得在 W3 或只读验收中触发 |
| archive/historical | `scripts/archive/**` | 历史研究/旧路线；不得提升为当前主线 |
| forbidden runtime action | broker/order/quick-trade/live trading scripts or code paths if present | 仅作为禁区证据，不是台股当前能力 |

## Tests Classification

| Class | Representative tests | Evidence role |
|---|---|---|
| Agent simple-chat | `backend/tests/test_tw_stock_agent_simple_chat.py`, `backend/tests/test_tw_stock_agent_daily_prompt_*`, `frontend/tests/e2e/tw-stock-agent-simple-chat-network.mjs`, `frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs` | 后端 blocked intent、citation/unsafe answer、前端只走 `/agent/simple-chat`、无 OpenAI direct/broker/monitor/provider requests |
| readonly replay/snapshot API | `backend/tests/test_tw_stock_readonly_replay_window_api.py`, `backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py` | GET-only、readonly flags、拒绝训练窗口/旧模型/诊断策略、无 write methods |
| frontend readonly E2E/static | `frontend/tests/e2e/tw-stock-readonly-replay-window-readonly.mjs`, `frontend/tests/e2e/tw-stock-readonly-strategy-snapshot-readonly.mjs`, `frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs`, `frontend/tests/unit/tw-stock-readonly-*` | network/console/文本安全审计；fixture routed |
| modular contracts | `tests/unit/test_tw_modular_m_contract_validators.py`, `test_validate_tw_modular_artifact_contract.py`, `test_tw_modular_m2_registry_validator.py`, `test_tw_modular_m3_daily_orchestrator.py` | 合同 validator、registry、daily orchestrator forbidden reachability |
| order intent/replay parity | `tests/unit/test_tw_modular_order_intent_artifact.py`, `test_tw_modular_order_intent_replay.py`, `test_tw_modular_order_intent_replay_parity.py` | 只读 replay/parity 语义；不是真实订单 |
| forbidden/superseded route tests | `backend/tests/test_agent_v1_twstock_quick_trade.py`, `test_preflight_tw_stock_ibkr_live.py`, `test_tw_stock_live_smoke.py`, `test_tw_stock_monitor_safety_audit.py`, `test_run_tw_stock_monitor_scan.py`, `test_submit_tw_stock_paper_orders.py` | 作为历史/边界测试读取；不能当 W1/W2 当前 readonly 能力 |

## Fixture / Mock / Dynamic Payload Demotion

测试中的 fixture、mock adapter、dynamic payload、Playwright route fulfillment、temporary latest pointer monkeypatch、network_audit JSON 和 screenshot artifact 只能证明测试规则、UI 结构和 forbidden request count。它们不得写成生产 `ReadonlyStrategySnapshot`、`DailyAgentPromptArtifact`、provider latest、qlib accepted latest 或真实交易证据。

## Sources

- `scripts/build_tw_agent_daily_prompt_artifact.py`
- `scripts/validate_tw_agent_daily_prompt_artifact.py`
- `scripts/validate_tw_modular_artifact_contract.py`
- `scripts/run_tw_modular_contract_regression.py`
- `scripts/run_daily_tw_stock_auto_update.py`
- `scripts/publish_tw_modular_readonly_snapshot.py`
- `backend/tests/test_tw_stock_agent_simple_chat.py`
- `backend/tests/test_tw_stock_readonly_replay_window_api.py`
- `backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py`
- `frontend/tests/e2e/tw-stock-agent-simple-chat-network.mjs`
- `frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs`
