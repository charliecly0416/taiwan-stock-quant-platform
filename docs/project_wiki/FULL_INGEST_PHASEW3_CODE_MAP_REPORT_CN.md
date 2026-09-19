---
title: Phasew3 Code Map Report
category: references
tags: [wiki, full-ingest, w3, report]
sources: []
summary: 源码、脚本、测试和配置静态映射的执行报告，作为项目 wiki 支线过程证据。
provenance:
  extracted: 1.0
  inferred: 0.0
  ambiguous: 0.0
base_confidence: 0.5
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: peripheral
created: 2026-06-20T19:00:00Z
updated: 2026-06-20T19:00:00Z
---

# Project Wiki Full Ingest Phase W3 执行报告

## 1. 本阶段结论

Phase W3 已完成源码、脚本、测试到 W1/W2 wiki 知识页的只读映射。当前主线未变化：`strict_e4_yz_product`，base model `e4_frozen_qlib_2018_2022`，treatment model `e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`，display alias `e4_frozen_qlib_2023_2025_ltr`，default strategy `top50_exit_one_worst_sell`，candidate boundary `qlib_top50`，ranking `ltr_rerank_within_qlib_top50`，execution price mode `next_open`。Agent 主线仍是 DailyAgentPromptArtifact -> backend simple-chat -> frontend readonly explanation；前端主线仍是 `/tw-stock-monitor` readonly strategy workbench。

本阶段没有运行服务、pytest、Playwright、训练、日更、数据刷新、provider publish、accepted latest switch、monitor 写入、broker/order、OpenAI smoke 或 artifact generation。

## 2. 读取的 source 范围

- W3 前置文档：总计划、W1/W2 报告与 review/follow-up、W3 work doc、`llm-wiki`、`wiki-ingest`、`wiki-lint`、`wiki-status` skill 指南。
- Backend route/service：`tw_stock.py`、readonly replay/snapshot routes、Agent daily prompt/simple-chat/OpenAI/guardrail services、artifact registry、current strategy context、daily auto-update status、readonly replay/snapshot services、paper portfolio、sim account。
- Frontend workbench/API：`frontend/src/api/tw-stock.js`、`frontend/src/views/tw-stock-monitor/index.vue`、ReadonlyStrategySnapshot/ReadonlyReplayWindow/PaperPortfolio/ReplayAuditDetail components。
- Scripts：Agent prompt builder/validator、modular validator/regression、daily update、readonly replay/window/snapshot/paper/sim scripts、provider staging scripts、archive inventory。
- Tests：backend Agent/simple-chat/readonly replay/snapshot tests、frontend e2e/unit readonly checks、modular unit validators、forbidden quick-trade/live/monitor boundary tests。

## 3. 明确排除的 source 范围

- 未执行任何 backend/frontend 服务、pytest、Playwright 或 smoke。
- 未读取 OpenAI key、broker credential、token、密码、真实账户 payload。
- 未触发真实数据拉取、provider refresh/publish、accepted latest switch、monitor config/scan/alerts 写入、broker/order/quick-trade、target position/weight 写入。
- 未运行 artifact builder、publisher、daily update、shadow daily、readonly snapshot publish、replay generation。
- `scripts/__pycache__`、二进制缓存、测试输出 artifact 未作为 source。

## 4. 新增 / 更新的 wiki 页面

新增：

- `references/code-map-backend-readonly-routes.md`
- `references/code-map-frontend-workbench.md`
- `references/code-map-scripts-and-tests.md`
- `FULL_INGEST_PHASEW3_CODE_MAP_REPORT_CN.md`

更新：

- `concepts/agent-daily-prompt-route.md`
- `concepts/frontend-strategy-workbench.md`
- `concepts/daily-update-data-flow.md`
- `concepts/data-freshness-and-latest-pointers.md`
- `concepts/modular-artifact-chain.md`
- `concepts/product-artifact-registry.md`
- `concepts/readonly-safety-boundary.md`
- `skills/readonly-e2e-acceptance-workflow.md`
- `skills/safety-boundary-review-workflow.md`
- `skills/modular-integration-regression-workflow.md`
- `skills/data-freshness-diagnosis-workflow.md`
- `synthesis/project-risk-map.md`
- `synthesis/current-mainline-vs-superseded-routes.md`
- `.manifest.json`、`index.md`、`hot.md`、`log.md`

## 5. manifest / index / hot / log 更新

- `index.md` 已补齐 W2 review、W2 follow-up、W2 follow-up review、W3 work、W3 report，并加入 3 个 W3 code-map references。
- `hot.md` 已更新 Recent Activity、Active Threads 和 Key Takeaways，提示 W3 后代码共址不改变当前主线。
- `log.md` 已追加 W3 ingest 记录。
- `.manifest.json` 已加入 W3 source entries，使用绝对 source path、content_hash、modified_at、size_bytes、pages_created/pages_updated。

## 6. 当前事实与历史事实边界

| Area | Current fact | Historical / boundary fact |
|---|---|---|
| Agent | `/api/tw-stock/agent/simple-chat` + `TWStockAgentSimpleChatService` | legacy `/agent/chat`、complex tool Agent 不是当前前端主线 |
| Frontend | `/tw-stock-monitor` readonly strategy workbench | 旧 monitor/ops UI 存在但不授权写入或刷新 |
| Model/strategy | strict E4 + `top50_exit_one_worst_sell` | old/fresh/adaptive/diagnostic strategies 不进入 product default |
| Latest | provider/qlib/snapshot/Agent latest 分离 | accepted latest scheduler/normal publish endpoints 是 ops boundary |
| Paper/sim | simulation-only account and paper portfolio gate | 不是 broker/order/target position |

## 7. 安全边界确认

| Forbidden source | Classification | Wiki handling |
|---|---|---|
| `backend/app/routes/quick_trade.py` | quick-trade/order runtime action | forbidden boundary only |
| `backend/app/routes/credentials.py` | credential/API key/broker policy | boundary only; no sensitive values copied |
| `backend/app/services/live_trading/**` | signed exchange REST clients | live trading boundary only |
| `backend/app/services/exchange_execution.py` | credential/exchange config resolution | broker/credential boundary only |
| `backend/app/services/trading_executor.py` | live execution/pending orders/positions | live executor boundary only |
| monitor config/scan/alerts routes | write-capable monitor code | historical/boundary, not current readonly route |
| provider staging/external scripts | data source/provider actions | diagnostic/boundary, not W3 execution |

## 8. 自检结果

| Check | Result |
|---|---|
| W3 report exists | pass |
| 3 new references have body `## Sources` | pass |
| index includes required W2/W3 Phase Reports | pass |
| manifest JSON parses | pass |
| No source/config/script/test/product files modified | pass by intended write scope; final git status limited to `docs/project_wiki` |
| Runtime forbidden actions avoided | pass |

## Backend route/service 映射表

| Route/service | File(s) | Concept |
|---|---|---|
| Agent simple-chat | `backend/app/routes/tw_stock.py`, `backend/app/services/tw_stock_agent_simple_chat.py` | [[concepts/agent-daily-prompt-route]] |
| Daily prompt loader | `backend/app/services/tw_stock_agent_daily_prompt.py` | [[concepts/agent-daily-prompt-route]] |
| Backend-only OpenAI adapter | `backend/app/services/tw_stock_agent_openai.py` | [[concepts/agent-daily-prompt-route]] |
| current strategy context | `backend/app/services/tw_stock_current_strategy_context.py` | [[concepts/frontend-strategy-workbench]] |
| readonly snapshot | `backend/app/routes/readonly_strategy_snapshot.py`, `backend/app/services/readonly_strategy_snapshot.py` | [[concepts/modular-artifact-chain]] |
| readonly replay window | `backend/app/routes/readonly_replay_window.py`, `backend/app/services/readonly_replay_window.py` | [[concepts/frontend-strategy-workbench]] |
| readonly replay index | `backend/app/routes/readonly_replay_window_index.py`, `backend/app/services/readonly_replay_window_index.py` | [[concepts/frontend-strategy-workbench]] |
| paper portfolio/sim | `backend/app/services/tw_stock_paper_portfolio.py`, `backend/app/services/tw_stock_sim_account.py` | [[concepts/readonly-safety-boundary]] |

## Frontend component/API 映射表

| File | Role | Boundary |
|---|---|---|
| `frontend/src/api/tw-stock.js` | API helper registry for current strategy, readonly snapshot/replay, simple-chat, paper/sim | simple-chat only goes backend; no browser OpenAI |
| `frontend/src/views/tw-stock-monitor/index.vue` | Main workbench composition | current path plus legacy/boundary blocks |
| `ReadonlyStrategySnapshotPanel.vue` | Candidate/snapshot display | checks readonly/no-order/no-target-position flags |
| `ReadonlyReplayWindowPanel.vue` | Historical simulation display | reads backend audited window; no frontend replay generation |
| `PaperPortfolioPanel.vue` | Simulation account/paper apply panel | simulation-only gate |
| `ReplayAuditDetail.vue` | Folded technical details | display only |

## Scripts 分类表

| Category | Scripts |
|---|---|
| current product path | `run_daily_tw_stock_auto_update.py`, `build_tw_agent_daily_prompt_artifact.py`, `build_tw_readonly_replay_window_index.py` |
| validator | `validate_tw_agent_daily_prompt_artifact.py`, `validate_tw_modular_artifact_contract.py`, `validate_tw_modular_registry_m2.py`, `validate_tw_modular_readonly_snapshot.py`, `validate_tw_readonly_replay_window_*` |
| builder | `build_tw_modular_order_intent_artifact.py`, `build_tw_readonly_replay_window_artifact.py`, `build_tw_paper_portfolio_decision_artifact.py` |
| readonly regression/dry-run | `run_tw_modular_contract_regression.py`, `run_tw_modular_shadow_daily.py`, `run_tw_modular_order_intent_replay*.py` |
| publisher with publish behavior | `publish_tw_modular_readonly_snapshot.py` |
| diagnostic/provider boundary | `fetch_tw_provider_external_data.py`, `pull_tw_provider_staging_data.py`, `validate_tw_provider_staging_data.py` |
| archive/historical | `scripts/archive/**` |

## Tests 分类表

| Category | Tests |
|---|---|
| Agent simple-chat | `backend/tests/test_tw_stock_agent_simple_chat.py`, `backend/tests/test_tw_stock_agent_daily_prompt_*`, `frontend/tests/e2e/tw-stock-agent-simple-chat-network.mjs`, `frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs` |
| readonly replay/snapshot | `backend/tests/test_tw_stock_readonly_replay_window_api.py`, `backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py`, frontend readonly replay/snapshot E2E/unit checks |
| modular contract | `tests/unit/test_tw_modular_m_contract_validators.py`, `test_validate_tw_modular_artifact_contract.py`, `test_tw_modular_m2_registry_validator.py`, `test_tw_modular_m3_daily_orchestrator.py` |
| readonly E2E/static checks | `frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs`, `tw-stock-phase-yz-productization-pending.mjs`, `tw-stock-phase-yz-productization-check.mjs` |
| forbidden/historical boundary | quick-trade/live/monitor/paper order tests; not current readonly product proof |

## Forbidden boundary source 表

| Source | Boundary reason |
|---|---|
| `quick_trade.py` | place/close order and exchange client paths |
| `credentials.py` | credential create/get/delete and API key handling |
| `live_trading/**` | signed exchange REST order clients |
| `exchange_execution.py` | credential/exchange config resolution |
| `trading_executor.py` | live/pending order and position executor |
| provider staging scripts | provider/data pull boundary |

## Fixture / mock / dynamic payload 降权说明

Playwright route fulfillment、mock OpenAI adapter、unit fixture、temporary latest pointer monkeypatch、synthetic network/console audit JSON、screenshot artifacts 和 dynamic payload 只证明测试场景的安全规则，不是生产 artifact、真实 latest pointer、真实 readonly snapshot、真实 replay 或交易证据。

## 9. 遗留问题

- W3 是静态 code map，没有运行测试或服务；如后续需要验收，应进入 readonly E2E/contract regression workflow，并继续遵守禁止项。
- `tw_stock.py` 和 `index.vue` 代码共址较重，容易让审查者误把旧 monitor/ops 路线读成当前主线；已在 synthesis 和 references 中标记。
- export scripts inventory 中部分 historical/外部路径可能已移动或不存在；W3 未把缺失路径写成当前事实。

## 10. 请求审查者审查的问题

- 是否同意将 quick-trade/credentials/live_trading/trading_executor 全部降级为 forbidden boundary source。
- 是否同意 fixture/mock/dynamic payload 的降权说明足以防止把测试数据当生产 artifact。
- 是否还需要在 W4 前进一步拆分 `tw_stock.py` 中 current readonly endpoints 与 legacy/ops endpoints 的文档边界。
