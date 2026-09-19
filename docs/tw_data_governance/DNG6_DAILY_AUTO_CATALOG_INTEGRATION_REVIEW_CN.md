# DNG6 Daily Auto Catalog / Readiness Dashboard 集成审查报告

生成日期：2026-06-29

## 1. 结论

```text
PASS_WITH_CONDITIONS_GO_DNG7
```

DNG6 dashboard builder、dashboard validator 与 daily auto 可选观测集成基本满足 DNG6 范围：required fields 完整，partial/block/missing 未被标为 production ready，dashboard forbidden action audit 全 false，daily auto 默认没有打开 provider publish、accepted latest switch、model signal gate、publish latest gate 或 broker/order。

但建议命令 `python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json` 当前返回失败。失败点是静态审计器命中 `broker_order` 字符串模式；本审查核对后判断它来自 forbidden-action audit 字段名 `broker_order_quick_trade_triggered=false`，未发现实际 broker/order 调用。但因为该建议审计命令失败，DNG7 只能带条件进入，且 DNG7 前必须修复或豁免该静态审计误报。

## 2. 审查范围

已阅读：

```text
docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md
docs/tw_data_governance/DNG6_DAILY_AUTO_CATALOG_INTEGRATION_WORK_CN.md
docs/tw_data_governance/DNG6_DAILY_AUTO_CATALOG_INTEGRATION_REVIEW_WORK_CN.md
docs/tw_data_governance/DNG6_DAILY_AUTO_CATALOG_INTEGRATION_EXECUTION_REPORT_CN.md
scripts/build_tw_daily_readiness_dashboard.py
scripts/validate_tw_daily_readiness_dashboard.py
scripts/run_daily_tw_stock_auto_update.py
data_tw/catalog/daily_readiness_dashboard.json
data_tw/catalog/dng6_daily_readiness_dashboard_validation.json
```

本审查未抓数、未运行 daily auto、未训练、未推理、未 score、未回放、未 publish、未切 latest。

## 3. Validator / Static Checks

运行结果：

```text
python -m py_compile scripts/build_tw_daily_readiness_dashboard.py scripts/validate_tw_daily_readiness_dashboard.py scripts/run_daily_tw_stock_auto_update.py
PASS

python scripts/validate_tw_daily_readiness_dashboard.py --dashboard data_tw/catalog/daily_readiness_dashboard.json --json
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

python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
ok=false
status=failed
error:
  script_broker_order_pattern: script contains broker/order runtime pattern
warnings:
  legacy_provider_publish_path_present
  legacy_accepted_latest_path_present
```

M3 audit 同时报告：

```text
legacy_provider_gate_default_disabled=true
default_provider_refresh_reachable=false
default_provider_publish_reachable=false
default_accepted_latest_reachable=false
provider_refresh_guarded=true
provider_publish_guarded=true
accepted_latest_call_guarded=true
has_readonly_snapshot_dry_run_default=true
```

因此 M3 失败不等于本轮实际触发 forbidden action，但它仍是进入 DNG7 前需要处理的审计条件。

## 4. Dashboard Required Fields

`scripts/validate_tw_daily_readiness_dashboard.py` 明确检查 DNG6 required fields：

```text
schema_version
generated_at
asof
provider_raw_latest_by_dataset
normalized_latest_by_dataset
price_store_latest
feature_store_latest
qlib_accepted_latest
model_signal_latest_by_model
readonly_snapshot_latest
agent_prompt_latest
pending_asof
provider_quota_status
holiday_status
next_retry_hint
readiness_by_layer
route_dependency_summary
known_blockers
allowed_next_steps
forbidden_actions_audit
```

当前 validator `error_count=0`，字段完整性通过。

## 5. Production Ready 边界

Dashboard 当前状态：

```text
dashboard_status=BLOCKED_OR_PARTIAL_NOT_PRODUCTION_READY
production_ready=false
route_dependency_all_gate_pass=false
```

`readiness_by_layer` 保守标记如下：

```text
price: PARTIAL_READY, production_ready=false
market: PARTIAL_READY, production_ready=false
orthogonal: BLOCKED_FOR_MODEL_B_LTR, production_ready=false
bundle: PARTIAL_READY, production_ready=false
route_dependency: BLOCK, production_ready=false
```

这满足 DNG6 条件：partial/block/missing 没有被解释为 Model B LTR ready、replay ready、publish ready 或 production ready。

## 6. Daily Auto Gate 审查

`scripts/run_daily_tw_stock_auto_update.py` 中 DNG6 dashboard 集成位于 `finalize_job()` 的可选观测步骤：

```text
TW_DAILY_AUTO_ENABLE_DATA_CATALOG_DASHBOARD=true
--enable-data-catalog-dashboard
default_enabled=false
safe_static_only=true
```

默认安全边界核对：

```text
data_catalog_dashboard_enabled=false
legacy_provider_publish_enabled=false
legacy_provider_refresh_default_reachable=false
legacy_provider_publish_default_reachable=false
legacy_accepted_latest_default_reachable=false
provider_publish_triggered=false
latest_signal_updated=false
trading.orders_enabled=false
trading.connects_to_broker=false
```

脚本中确实保留 legacy provider refresh/publish、accepted latest、readonly snapshot latest 等非默认路径；但 provider refresh/publish 与 accepted latest 位于 `--enable-legacy-provider-publish` 显式 gate 后，readonly snapshot latest 默认 `ENABLE_TW_READONLY_STRATEGY_SNAPSHOT_PUBLISH=false` 且 dry-run 默认 true。DNG6 本轮未运行 daily auto，因此未触发这些路径。

## 7. Forbidden Action Audit

`data_tw/catalog/daily_readiness_dashboard.json` 中：

```text
forbidden_actions_audit.all_false=true
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

本审查运行的命令均为 py_compile、dashboard validator、orchestrator static audit，未执行真实日更或任何 forbidden action。

## 8. 当前 Blockers

DNG6 dashboard 明确暴露而未掩盖的 blocker：

```text
provider_raw_latest/normalized_latest=2026-06-25, qlib_accepted_latest=2026-06-17
price_store_latest=2026-06-17 且仅为 execution readiness bridge，不是 canonical PriceStore
model_signal_latest=2026-06-17
readonly_snapshot_latest=2026-06-18，但 source signal/data asof=2026-06-17
agent_prompt_latest=MISSING
orthogonal corporate_actions/monthly_revenue/valuation 阻断 Model B LTR
DNG4 bundle 为 PARTIAL_READY，replay execution remains blocked
DNG5 route_dependency all_gate_pass=false，block_count=1，partial_count=2
```

这些 blocker 不阻止进入 DNG7 的合同与 validator 设计，但阻止任何 production ready、Model B LTR ready、replay ready、publish ready 声明。

## 9. 进入 DNG7 条件

允许进入 DNG7 的范围仅限：

```text
ModelInferenceInput / qlib Model A ScoreJob 合同与 validator
只读 qlib Model A score pipeline 设计或静态验证
继续引用 DNG6 dashboard、DNG5 route dependency validation 和 readiness matrix
```

进入条件：

1. DNG7 不得训练、不切 qlib accepted latest、不 provider publish、不 readonly/Agent latest publish、不 replay/NAV、不 broker/order/target position/target weight。
2. DNG7 必须把 DNG6 dashboard 当前 `production_ready=false` 作为前置事实。
3. DNG7 前或 DNG7 首项必须处理 `validate_tw_daily_orchestrator_m3.py` 的 `script_broker_order_pattern` 静态审计失败：要么修复审计器误报规则，要么重命名 DNG6 audit 字段并保持合同兼容，要么由 coordinator 明确批准豁免。

## 10. Verdict

```text
PASS_WITH_CONDITIONS_GO_DNG7
```
