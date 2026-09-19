---
created_at: 2026-06-28
status: review
phase: MTRC2_T_R_PRICESTORE_BRIDGE_OR_READINESS_REPAIR
reviewer: MTRC2_T_R_independent_reviewer
readonly_only: true
research_only: true
production_allowed: false
---

# POLICY_MTRC2_T_R_PRICESTORE_BRIDGE_OR_READINESS_REPAIR_REVIEW_CN

## Verdict

```text
PASS_READY_FOR_MTRC2_T_GATE_RERUN
```

MTRC2_T_R 产物满足 research-only PriceStore-like bridge/readiness 修复目标。审查接受该阶段输出作为重新运行 MTRC2_T gate 的输入候选。

本 verdict 不放行直接进入 MTRC2_U replay。下一步只能重新运行 MTRC2_T gate，让 gate 消费本 research-only price bridge/readiness；只有 gate rerun 再次 PASS 后，才可由后续授权决定是否进入 MTRC2_U。

## Findings

### Critical

无。

### High

无。

### Medium

无。

### Low

1. `mtrc2_t_rerun_gate_recommendation.md` 表述为 "MTRC2_U replay still requires separate authorization"，边界方向正确；为避免流程误读，本审查明确收窄下一步为 MTRC2_T gate rerun，不能绕过 gate 直接进入 MTRC2_U。

## Evidence Checked

已读取并核对必读工作文档、执行报告和合同：

- `docs/tw_portfolio_decision_model/POLICY_MTRC2_T_R_PRICESTORE_BRIDGE_OR_READINESS_REPAIR_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC2_T_R_PRICESTORE_BRIDGE_OR_READINESS_REPAIR_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC2_T_SAME_SIGNAL_REPLAY_INPUT_BUILD_CONTRACT_REVIEW_CN.md`
- `docs/tw_modular_contracts/PRICE_STORE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`

已审查 builder：

- `scripts/build_tw_policy_mtrc2_t_r_pricestore_bridge_or_readiness_repair.py`

已审查 MTRC2_T_R 输出目录全部 17 个产物：

- `manifest.json`
- `prices.csv`
- `schema.json`
- `source_inventory.csv`
- `source_selection_audit.csv`
- `coverage_audit.csv`
- `execution_availability_audit.csv`
- `adjustment_audit.json`
- `order_intent_price_join_audit.csv`
- `missing_price_audit.csv`
- `missing_next_open_audit.csv`
- `invalid_source_audit.csv`
- `forbidden_field_audit.csv`
- `forbidden_action_audit.json`
- `validator_report.json`
- `diagnostic_findings.md`
- `mtrc2_t_rerun_gate_recommendation.md`

已审查 staged source manifest / forbidden audit：

- `data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/manifest.json`
- `data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/forbidden_scope_audit.csv`

## Independent Recompute/Audit 摘要

输出目录文件集复核通过。目录下仅有授权的 price bridge/readiness/audit/validator/recommendation 产物；未发现 `summary.csv`、`actions.csv`、`daily_nav.csv`、`position_snapshots.csv`、`ledger.csv`、`trade_ledger.csv`、`action_ledger.csv` 或 ReplayResult 产物。

`prices.csv` schema 复核通过：

```text
row_count = 2378
required_fields_missing = []
forbidden_price_fields = []
open_close_not_positive = 0
price_date_range = 2017-01-11..2026-05-08
instrument_count = 142
```

必需字段存在：

```text
price_date, instrument, open, close, adj_factor, tradable_flag, halt_flag,
next_day_execution_availability, price_source, adjustment_policy, source_file
```

独立复算 MTRC2_S `order_intents.csv` join 通过：

```text
order_intent_rows = 2378
join_audit_rows = 2378
prices_rows = 2378
order_join_row_mismatch = 0
join_status_not_pass = 0
execution_date_not_after_signal_date = 0
next_open_not_positive = 0
fallback_used_not_false = 0
demo_source_used_in_join = 0
price_join_key_delta = 0
```

源文件级复算通过。审查逐行打开 `selected_source_file`，按 `signal_date` 后第一条可用正 open/close 价格重算 execution date/open/close：

```text
source_file_level_recomputed_rows = 2378
source_file_cache_entries = 142
bad_count = 0
```

覆盖与缺失审计一致：

```text
coverage_audit rows = 5, pass = 5
execution_availability_audit rows = 3, pass = 3
missing_price_audit data_rows = 0
missing_next_open_audit data_rows = 0
order_intent_next_open_coverage = 2378/2378
```

来源选择复核通过：

```text
stock_price_bridge selected_order_intent_count = 1615
staged_candidate_normalized selected_order_intent_count = 763
secondary stock_price_bridge selected_order_intent_count = 0
self_contained_demo_normalized selected_order_intent_count = 0
```

`source_inventory.csv` 显示 staged `candidate_normalized` 是既有本地 staged source，路径为：

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/option_c_ops/rcpt15_r1_option_c_yahoo_scrapling_refresh_20260625/candidate_normalized
```

其样本 schema 为 `symbol|date|open|high|low|close|volume|vwap|factor`，覆盖 MTRC2_S 所需 142/142 instruments。staged source manifest 指向既有 `stage_job_dir`，`forbidden_scope_audit.csv` 明确：

```text
provider_publish = PASS_NOT_PERFORMED
accepted_latest_switch = PASS_NOT_PERFORMED
latest_pointer_write = PASS_NOT_PERFORMED
production_default_latest_write = PASS_NOT_PERFORMED
frontend_agent_monitor_order = PASS_NOT_PERFORMED
target_weight_target_position_broker = PASS_NOT_PERFORMED
```

`data_tw/self_contained_demo/normalized` 已 inventory 为 invalid demo source，并在 selection audit 中 `excluded`、`selected_order_intent_count=0`；join audit 中未出现 demo selected source。

## Forbidden Actions Audit

`forbidden_action_audit.json` status 为 `pass`，所有禁止动作均 `performed=false`。独立审查未发现以下行为：

- provider refresh/download/publish。
- accepted latest switch、latest/default/provider pointer 写入。
- 正式 PriceStore 写入；`data_tw/artifacts/price_store` 当前不存在。
- `configs/price_store_registry.yaml` 或 `configs/tw_modular_registry.yaml` 写入。
- frontend/API/Agent/daily/production 写入。
- ReplayResult、ledger、summary/actions/daily_nav/position snapshots 生成。
- 收益 replay、收益、回撤、集中度、rolling window、risk-off 诊断。
- broker、quick-trade、真实 order。
- target weight、target position、quantity instruction。
- close fallback 或 same-day open fallback。

关键词审查中的 broker/order/target/quantity/replay/return/provider/latest 命中均位于 deny-list、schema、validator 或审计说明上下文，未构成真实动作或产物字段。

## Next Work Document

下一步只能执行：

```text
重新运行 MTRC2_T gate，让它消费本阶段 research-only price bridge/readiness。
```

不得直接进入 `MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD`。只有 MTRC2_T gate rerun 再次 PASS 后，才可由后续工作文档授权 MTRC2_U replay。
