# DNG6 Daily Auto Catalog / Readiness Dashboard 集成执行报告

生成日期：2026-06-29

## 1. 结论

DNG6 已完成静态 dashboard builder、validator，以及 daily auto 的可选观测集成。

当前 dashboard 结论：

```text
dashboard_status=BLOCKED_OR_PARTIAL_NOT_PRODUCTION_READY
production_ready=false
route_dependency_all_gate_pass=false
forbidden_actions_all_false=true
```

本轮未运行真实 daily auto 日更，未触发真实抓数、provider refresh/publish、accepted latest switch、readonly/Agent latest publish、模型训练、模型推理、模型 score 生成、策略收益回放、ReplayResult/NAV、broker/order/quick-trade、target_position 或 target_weight。

## 2. 新增/更新文件

脚本：

```text
scripts/build_tw_daily_readiness_dashboard.py
scripts/validate_tw_daily_readiness_dashboard.py
scripts/run_daily_tw_stock_auto_update.py
```

产物：

```text
data_tw/catalog/daily_readiness_dashboard.json
data_tw/catalog/dng6_daily_readiness_dashboard_validation.json
docs/tw_data_governance/DNG6_DAILY_AUTO_CATALOG_INTEGRATION_EXECUTION_REPORT_CN.md
```

## 3. Dashboard 字段和来源

`data_tw/catalog/daily_readiness_dashboard.json` 由静态本地文件聚合生成：

| Dashboard 字段 | 来源 |
| --- | --- |
| `provider_raw_latest_by_dataset` | `data_tw/catalog/data_catalog.json` 中 `latest_concept=provider_raw_latest` 条目 |
| `normalized_latest_by_dataset` | `data_tw/catalog/data_catalog.json` 中 `latest_concept=normalized_latest` 条目 |
| `price_store_latest` | `data_tw/catalog/latest_status.json` 的 `price_store_latest` |
| `feature_store_latest` | `data_tw/catalog/latest_status.json` 的 `feature_store_latest` |
| `qlib_accepted_latest` | `data_tw/catalog/latest_status.json` 的 `qlib_accepted_latest` |
| `model_signal_latest_by_model` | `data_tw/catalog/data_catalog.json` 与 `latest_status.json` 的 model signal 条目 |
| `readonly_snapshot_latest` | `data_tw/catalog/latest_status.json` 的 `readonly_snapshot_latest` |
| `agent_prompt_latest` | `data_tw/catalog/latest_status.json` 的 `agent_prompt_latest` |
| `pending_asof` | `data_tw/ops/daily_auto_update/pending_asof.json`，当前不存在 |
| `provider_quota_status` | 最近 `data_tw/ops/daily_auto_update/*/job.json` 的 FinMind/quota 字段 |
| `holiday_status` | 最近 `job.json` 与 accounting evidence |
| `readiness_by_layer.price/market` | `data_tw/catalog/readiness_matrix/2026-06-25/price_market_calendar.json` |
| `readiness_by_layer.orthogonal` | `data_tw/catalog/readiness_matrix/2026-06-25/orthogonal_feature_store.json` |
| `readiness_by_layer.bundle` | `data_tw/catalog/dng4_input_bundle_validation.json` |
| `readiness_by_layer.route_dependency` | `data_tw/catalog/dng5_route_dependency_validation.json` |

当前关键状态：

```text
asof=2026-06-29
provider_raw_latest=2026-06-25
normalized_latest=2026-06-25
price_store_latest=2026-06-17, PARTIAL_READY, bridge only
feature_store_latest=2026-06-25, RESEARCH_ONLY
qlib_accepted_latest=2026-06-17
model_signal_latest=2026-06-17
readonly_snapshot_latest=2026-06-18
agent_prompt_latest=MISSING
```

## 4. Daily auto 集成方式

`scripts/run_daily_tw_stock_auto_update.py` 新增以下只读/静态观测集成：

```text
TW_DAILY_AUTO_ENABLE_DATA_CATALOG_DASHBOARD=true
--enable-data-catalog-dashboard
```

集成位置为 `finalize_job()`：

```text
write daily_source_inventory
write daily_full_capture_accounting
write job.json
optional build daily_readiness_dashboard
optional validate daily_readiness_dashboard
write job.json with dashboard/validation status
```

默认仍保持关闭：

```text
data_catalog_dashboard_enabled=false
provider_publish=false
accepted_latest_switch=false
model_signal_gate=false
publish_latest_gate=false
broker_order=false
```

该集成只调用：

```text
scripts/build_tw_daily_readiness_dashboard.py
scripts/validate_tw_daily_readiness_dashboard.py
```

不会调用 provider refresh/publish、accepted latest switch、模型、score、replay、broker/order 或 target position/weight 相关入口。

## 5. 是否运行 dry-run/status 验证

未运行 `scripts/run_daily_tw_stock_auto_update.py`。

原因：现有 daily auto 脚本没有独立的安全 status-only/dry-run 参数；默认流程在通过时间窗后可能进入 FinMind segmented update。按 DNG6 工作文档要求，本轮只做静态集成和 validator。

已运行的静态命令：

```bash
python -m py_compile scripts/build_tw_daily_readiness_dashboard.py scripts/validate_tw_daily_readiness_dashboard.py scripts/run_daily_tw_stock_auto_update.py
python scripts/build_tw_daily_readiness_dashboard.py --json
python scripts/validate_tw_daily_readiness_dashboard.py --dashboard data_tw/catalog/daily_readiness_dashboard.json --json
```

## 6. Validator 输出

`data_tw/catalog/dng6_daily_readiness_dashboard_validation.json`：

```text
ok=true
status=PASS
dashboard_status=BLOCKED_OR_PARTIAL_NOT_PRODUCTION_READY
production_ready=false
route_dependency_all_gate_pass=false
forbidden_actions_all_false=true
error_count=0
warning_count=0
readiness_layer_status_counts:
  BLOCK=1
  BLOCKED_FOR_MODEL_B_LTR=1
  PARTIAL_READY=3
```

Validator 检查项：

```text
required fields
latest concept completeness
readiness_by_layer includes price/market/orthogonal/bundle/route_dependency
partial/block/missing not marked production ready
forbidden action audit all false
JSON output contract
```

## 7. Forbidden Action Audit

Dashboard forbidden action audit 全部为 false：

```text
real_data_fetch_triggered=false
provider_refresh_triggered=false
provider_publish_triggered=false
qlib_accepted_latest_switched=false
readonly_latest_published=false
agent_prompt_published=false
model_training_triggered=false
model_inference_triggered=false
model_score_generation_triggered=false
strategy_replay_triggered=false
replay_result_nav_generated=false
broker_order_quick_trade_triggered=false
target_position_or_weight_generated=false
```

## 8. 当前 Blockers

Dashboard 保守暴露以下主要 blocker，不解释为生产就绪：

1. `provider_raw_latest/normalized_latest=2026-06-25`，但 `qlib_accepted_latest=2026-06-17`。
2. `price_store_latest=2026-06-17`，且只是 execution readiness bridge，不是 canonical PriceStore latest。
3. `model_signal_latest=2026-06-17`，DNG5 的 Model B LTR route 仍为 `BLOCK`。
4. `agent_prompt_latest=MISSING`，不得从 readonly snapshot 或 strategy context 推断。
5. DNG3 orthogonal 中 `corporate_actions/monthly_revenue/valuation` 仍阻断 Model B LTR。
6. DNG4 StrategyInputBundle / ReplayInputBundle 为 `PARTIAL_READY`，replay execution remains blocked。
7. DNG5 汇总为 `pass_count=0, partial_count=2, block_count=1`，`all_gate_pass=false`。

## 9. 是否建议进入 DNG7

建议进入 DNG7，但只能按 DNG7 范围进入：

```text
ModelInferenceInput / qlib Model A ScoreJob 合同与 validator
只读 qlib Model A score pipeline
不训练
不切 qlib accepted latest
不 provider publish
不 readonly/Agent latest publish
不 replay/NAV
不 broker/order/target position/target weight
```

DNG6 的结论不是生产 ready，也不是 Model B LTR ready。DNG7 的前置条件应继续引用本 dashboard、DNG5 route dependency validation 和 readiness matrix，先把 ModelInferenceInput / ScoreJob / ModelSignalArtifact 的标准合同做出来。
