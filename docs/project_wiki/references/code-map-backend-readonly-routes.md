---
title: Backend Readonly Routes Code Map
category: references
tags: [backend, routes, readonly, code-map]
relationships:
  - target: "[[concepts/agent-daily-prompt-route]]"
    type: related_to
  - target: "[[concepts/readonly-safety-boundary]]"
    type: uses
  - target: "[[concepts/product-artifact-registry]]"
    type: related_to
sources: [/home/chuliyang/taiwan-stock-quant-platform/backend/app/routes/tw_stock.py, /home/chuliyang/taiwan-stock-quant-platform/backend/app/routes/readonly_replay_window.py, /home/chuliyang/taiwan-stock-quant-platform/backend/app/routes/readonly_replay_window_index.py, /home/chuliyang/taiwan-stock-quant-platform/backend/app/routes/readonly_strategy_snapshot.py, /home/chuliyang/taiwan-stock-quant-platform/backend/app/services/tw_stock_agent_daily_prompt.py, /home/chuliyang/taiwan-stock-quant-platform/backend/app/services/tw_stock_agent_simple_chat.py, /home/chuliyang/taiwan-stock-quant-platform/backend/app/services/tw_stock_agent_openai.py, /home/chuliyang/taiwan-stock-quant-platform/backend/app/services/tw_stock_current_strategy_context.py, /home/chuliyang/taiwan-stock-quant-platform/backend/app/services/readonly_replay_window.py, /home/chuliyang/taiwan-stock-quant-platform/backend/app/services/readonly_strategy_snapshot.py, /home/chuliyang/taiwan-stock-quant-platform/backend/app/services/tw_stock_paper_portfolio.py, /home/chuliyang/taiwan-stock-quant-platform/backend/app/services/tw_stock_sim_account.py]
summary: Backend route/service 静态映射，区分当前只读产品入口、模拟账户 gate 和 forbidden boundary source。
provenance:
  extracted: 0.9
  inferred: 0.1
  ambiguous: 0.0
base_confidence: 0.86
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: supporting
created: 2026-06-20T16:00:00Z
updated: 2026-06-20T16:00:00Z
---

# Backend Readonly Routes Code Map

本页是 W3 对 backend route/service 的静态映射，不代表运行验收。当前台股产品主线仍是 artifact-backed readonly research。

## Route / Service Map

| Route / capability | Code source | Wiki concept | Boundary |
|---|---|---|---|
| `POST /api/tw-stock/agent/simple-chat` | `backend/app/routes/tw_stock.py`, `backend/app/services/tw_stock_agent_simple_chat.py` | [[concepts/agent-daily-prompt-route]] | 只读研究解释；阻断 order、broker、target position/weight、provider/latest/monitor 意图 |
| DailyAgentPromptArtifact loader | `backend/app/services/tw_stock_agent_daily_prompt.py` | [[concepts/agent-daily-prompt-route]] | 读取 `data_tw/artifacts/agent_daily_prompt/latest.json`；校验 latest pointer、checksum、citations、readonly flags |
| OpenAI adapter | `backend/app/services/tw_stock_agent_openai.py` | [[concepts/agent-daily-prompt-route]] | backend-only；无 key 时 disabled/mock；前端不得直连 OpenAI |
| `GET /api/tw-stock/current-strategy-context` | `backend/app/routes/tw_stock.py`, `backend/app/services/tw_stock_current_strategy_context.py` | [[concepts/frontend-strategy-workbench]] | registry-backed 当前策略上下文；返回 readonly/no-order/no-target-position flags |
| `GET /api/tw-stock/readonly-strategy-snapshot` | `backend/app/routes/readonly_strategy_snapshot.py`, `backend/app/services/readonly_strategy_snapshot.py` | [[concepts/modular-artifact-chain]] | GET-only；校验 readonly snapshot latest pointer、checksum、no broker/order/no target position |
| `GET /api/tw-stock/readonly-replay-window-index` | `backend/app/routes/readonly_replay_window_index.py`, `backend/app/services/readonly_replay_window_index.py` | [[concepts/frontend-strategy-workbench]] | 读取 D7 window index；筛选 clean windows |
| `GET /api/tw-stock/readonly-replay-window` | `backend/app/routes/readonly_replay_window.py`, `backend/app/services/readonly_replay_window.py` | [[concepts/frontend-strategy-workbench]] | 读取已登记/已审计 replay window，不 on-demand 生成 replay |
| Product artifact registry | `backend/app/services/tw_stock_artifact_registry.py` | [[concepts/product-artifact-registry]] | 读取 `configs/tw_product_artifact_registry.yaml`，不切 default/latest |
| Daily auto-update status | `backend/app/services/tw_stock_daily_auto_update_status.py` | [[concepts/data-freshness-and-latest-pointers]] | 只读汇总 latest signal、pending asof、job status 和 cron hint |
| Paper portfolio apply/state | `backend/app/services/tw_stock_paper_portfolio.py` | [[concepts/frontend-strategy-workbench]] | 只应用 clean PaperOrderIntentArtifact 到模拟账户；需要 checksum、idempotency、用户确认 |
| Sim account ledger | `backend/app/services/tw_stock_sim_account.py` | [[concepts/readonly-safety-boundary]] | `simulation_only=true`，`connects_to_broker=false`，不提交真实市场指令 |

## Forbidden Boundary Sources

| Source | Why boundary only | W3 classification |
|---|---|---|
| `backend/app/routes/quick_trade.py` | 含 `/place-order`、`/close-position`、balance、position、history 以及 live trading execution 调用 | forbidden runtime action source；不是当前台股产品入口 |
| `backend/app/routes/credentials.py` | 管理 API key / secret / broker credential；可能区分 paper/live credential | credentials boundary；不得写入 wiki 敏感值 |
| `backend/app/services/live_trading/**` | 交易所 REST client、签名请求、place/cancel order | live trading boundary；只用于标记禁区 |
| `backend/app/services/exchange_execution.py` | 解析 credential、exchange config、secret masking | broker/credential boundary |
| `backend/app/services/trading_executor.py` | 含 live execution loop、exchange order、pending order、position update | live trading executor boundary |

## Important Downgrades

`backend/app/routes/tw_stock.py` 同时包含历史 monitor、ops、accepted latest scheduler、normal publish 和 legacy Agent routes。W3 将这些代码记录为“存在但非当前主线”：它们不能覆盖 W1/W2 固定的 Agent simple-chat、readonly workbench、strict E4 defaults 和只读安全边界。

## Sources

- `backend/app/routes/tw_stock.py`
- `backend/app/routes/readonly_replay_window.py`
- `backend/app/routes/readonly_replay_window_index.py`
- `backend/app/routes/readonly_strategy_snapshot.py`
- `backend/app/services/tw_stock_agent_daily_prompt.py`
- `backend/app/services/tw_stock_agent_simple_chat.py`
- `backend/app/services/tw_stock_agent_openai.py`
- `backend/app/services/tw_stock_current_strategy_context.py`
- `backend/app/services/readonly_replay_window.py`
- `backend/app/services/readonly_strategy_snapshot.py`
- `backend/app/services/tw_stock_paper_portfolio.py`
- `backend/app/services/tw_stock_sim_account.py`
