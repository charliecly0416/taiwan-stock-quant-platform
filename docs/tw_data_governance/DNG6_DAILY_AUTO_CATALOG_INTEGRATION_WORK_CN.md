# DNG6 Daily Auto Catalog / Readiness Dashboard 集成工作文档

生成日期：2026-06-29

## 1. 背景

DNG5 审查结论：

```text
PASS_WITH_CONDITIONS_GO_DNG6
```

条件：

- DNG6 只能进入 daily auto catalog/readiness/dashboard integration；
- 不能把 partial/block 解释为 Model B LTR、replay、publish 或生产就绪。

## 2. 目标

把 DNG1-DNG5 的 DataCatalog、latest_status、readiness matrix 和 route dependency validation 接入日更观测层，让 daily auto 每次运行都能输出统一 dashboard，说明每层数据状态。

## 3. 必须生成/更新

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

如果运行 daily auto，只能使用不会触发真实抓数/publish/latest 的 dry-run/status 模式；若现有脚本没有安全 dry-run 模式，DNG6 只能做静态集成和 validator，不得强行运行真实日更。

## 4. Dashboard 必须字段

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

## 5. Daily auto 集成要求

`scripts/run_daily_tw_stock_auto_update.py` 只能新增或接入：

```text
DataCatalog scanner command reference
daily_readiness_dashboard builder
dashboard validator
job.json dashboard path/status fields
```

不得新增默认 provider refresh/publish、accepted latest switch、score generation、replay 或 production publish。

建议环境变量 / 参数：

```text
TW_DAILY_AUTO_ENABLE_DATA_CATALOG_DASHBOARD=true
--enable-data-catalog-dashboard
```

默认行为必须保持安全：

```text
provider_publish=false
accepted_latest_switch=false
model_signal_gate=false
publish_latest_gate=false
broker_order=false
```

## 6. Validator 要求

`scripts/validate_tw_daily_readiness_dashboard.py` 必须支持：

```text
python scripts/validate_tw_daily_readiness_dashboard.py --dashboard data_tw/catalog/daily_readiness_dashboard.json --json
```

检查：

- required fields；
- latest concepts 完整；
- readiness_by_layer 包含 price/market/orthogonal/bundle/route_dependency；
- partial/block 不得标 production ready；
- forbidden action audit 全 false；
- 输出 JSON。

## 7. 禁止动作

不得执行：

```text
真实抓数
provider refresh / publish
qlib accepted latest switch
readonly latest publish
Agent prompt latest publish
模型训练
模型推理
模型 score 生成
策略收益回放
ReplayResult/NAV 生成
broker/order/quick-trade
target_position / target_weight
```

## 8. 执行报告

报告必须说明：

1. dashboard 字段和来源。
2. daily auto 集成方式。
3. 是否运行 dry-run/status 验证。
4. validator 输出。
5. forbidden action audit。
6. 是否建议进入 DNG7 ModelInferenceInput / qlib Model A score pipeline。
