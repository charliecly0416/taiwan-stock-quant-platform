---
title: Daily Update Data Flow
category: concepts
tags: [daily-update, data-flow, qlib, ltr, frontend]
aliases: [日更数据链路]
relationships:
  - target: "[[references/real-sample-20260618]]"
    type: derived_from
  - target: "[[concepts/modular-artifact-chain]]"
    type: implements
  - target: "[[concepts/frontend-strategy-workbench]]"
    type: related_to
sources: ['/home/chuliyang/taiwan-stock-quant-platform/docs/tw_new_model_strategy_pre_rnd/TW_DAILY_UPDATE_DATA_FLOW_REAL_SAMPLE_20260618_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_new_model_strategy_pre_rnd/TW_DAILY_UPDATE_DATA_FLOW_EXPLAINED_FOR_BEGINNERS_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_PRODUCTIZATION_MAINLINE_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_FINAL_ACCEPTANCE_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEYZ_STRICT_E4_PRODUCTIZATION_FINAL_SUMMARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEYZ4_FINAL_CLOSURE_SUMMARY_FOR_COORDINATION_CN.md']
summary: 日更当前路线是 readonly daily chain，生成 daily artifacts、readonly latest/run registry 和 GET-only 前端展示，不切 provider/accepted latest。
provenance:
  extracted: 0.88
  inferred: 0.12
  ambiguous: 0.0
base_confidence: 0.88
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: core
created: 2026-06-20T00:00:00Z
updated: 2026-06-20T16:00:00Z
---

# Daily Update Data Flow

当前可验证链路是：标准化价格 / qlib provider -> qlib 基础模型 Model A -> qlib top50 候选门 -> strict E4 scoped orthogonal LTR -> LTR Model B 重新排序 -> next_open execution price readiness -> readonly strategy snapshot -> GET-only API / frontend strategy workbench。

## Current Route

模块化日更产品化最终验收确认：U1 产出 daily data / feature / model signal staging，U2 产出 daily order intent / readonly snapshot / run registry / readonly latest pointer，U3 串入只读日更入口、GET-only API 与前端展示。

当前推荐读取点：

```text
latest pointer: data_tw/artifacts/daily_readonly_latest/latest.json
run registry: data_tw/artifacts/daily_run_registry/
readonly snapshots: data_tw/artifacts/daily_readonly_snapshots/
```

## Clean E4 Productization

YZ/YZ4 收口确认 clean E4 产品化链路已建立：production models 只保留 `e4_frozen_qlib_2018_2022` 与 `e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`，production strategy 只保留 `top50_exit_one_worst_sell`，execution price mode 固化为 `next_open`。

当 next_open 缺失时，不得 fallback 到 next_close、signal close、0、空值、上一日价格或手写价格。`execution_price_unavailable` 时 paper apply 必须被后端阻断。YZ4 pending replay artifact 是 clean readonly 展示产物，不证明 2026 收益表现。

## Key Ideas

- `signal_asof` 是模型信号日期，`target_date` 是策略快照面向的复盘日期。
- qlib Model A 先对候选股票打基础分，再通过 qlib top50 门筛入 LTR。
- LTR 只在 qlib top50 内重排，不从 top50 外拉股票回来。
- 执行价 readiness 会阻止用旧价格冒充目标日期价格。
- Frontend 展示的是 readonly candidate，不是买卖指令。

## Concrete Sample

- `TW2330` 在 `2026-06-17` qlib Model A 中 `score_rank=103`，未进入 top50，因此没有 LTR 特征、LTR 分数或前端 top candidate。
- `TW3481` 在 `2026-06-17` qlib rank 31，进入 top50，经 LTR 重排为 score rank 1，进入 `2026-06-18` readonly strategy snapshot 前端候选第 1。
- 本地没有 `2026-06-18` 的真实执行价格，因此该候选仍是只读研究展示，不是交易指令。

## W3 Code Evidence

- `backend/app/services/tw_stock_current_strategy_context.py` 从 product registry 和 artifact manifests 拼装当前策略上下文，输出 `readonly_only`、`not_order`、`not_target_position`、`does_not_touch_provider_accepted_latest`、`does_not_touch_qlib_accepted_latest`。
- `backend/app/services/tw_stock_daily_auto_update_status.py` 只读 summarise latest signal、pending asof、last job 和 cron status。
- `scripts/run_daily_tw_stock_auto_update.py` 是日更相关入口，W3 不运行；任何启用都必须走 dry-run/gate 和 readonly safety review。
- `scripts/validate_tw_daily_orchestrator_m3.py`、`tests/unit/test_tw_modular_m3_daily_orchestrator.py` 是 daily orchestrator forbidden reachability 的静态/单元证据。

## Sources

- [[references/real-sample-20260618|Real Sample 2026-06-18]]
- [[references/code-map-backend-readonly-routes|Backend Readonly Routes Code Map]]
- [[references/code-map-scripts-and-tests|Scripts And Tests Code Map]]
- `docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_FINAL_ACCEPTANCE_CN.md`
- `docs/tw_modular_daily_update_productization/PHASEYZ4_FINAL_CLOSURE_SUMMARY_FOR_COORDINATION_CN.md`
