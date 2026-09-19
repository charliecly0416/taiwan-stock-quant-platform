---
created_at: 2026-06-26
status: work
phase: RCPT15_R3_X_R_REAL_MODEL_A_TOP50_BRIDGE_COVERAGE_REPAIR
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_X_STRICT_E4_READONLY_BRIDGE_DRY_RUN_WITH_REAL_ASOF_REVIEW_CN.md
production_allowed: false
provider_publish_default_allowed: false
accepted_latest_switch_allowed: false
network_allowed: false
order_or_target_output_allowed: false
---

# RCPT15_R3_X_R Real Model A Top50 Bridge Coverage Repair 工作文档

## 1. 目标

修复 R3_X real asof dry-run 的唯一 blocker：R3_T `stock_price_bridge` 不覆盖 `2026-06-17` real `model_a` top50 中 7 个股票。

本阶段只允许做隔离 bridge coverage repair：

```text
R3_T stock_price_bridge + 7 missing symbols from local R1 candidate_normalized
  -> R3_X_R repaired stock_price_bridge
  -> coverage audit PASS for real model_a top50
```

不联网，不写正式 provider，不切换 accepted latest，不写 formal/latest pointer，不运行 YZ2/YZ2R builder。

## 2. 缺口

R3_X 审查确认缺失：

```text
TW5439 rank 24
TW2486 rank 30
TW1785 rank 39
TW5351 rank 41
TW2485 rank 43
TW6789 rank 47
TW3105 rank 50
```

R3_X preflight：

```text
model_a_top50_count = 50
top50_price_bridge_present_count = 43
top50_price_bridge_missing_count = 7
```

## 3. 本地可用来源

优先使用本地 R1 candidate normalized：

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/option_c_ops/rcpt15_r1_option_c_yahoo_scrapling_refresh_20260625/candidate_normalized/
```

该来源对 7 个缺口的覆盖：

```text
TW5439: 2015-01-05 .. 2026-06-25
TW2486: 2015-01-05 .. 2026-06-25
TW1785: 2015-01-05 .. 2026-06-25
TW5351: 2015-01-05 .. 2026-06-25
TW2485: 2015-01-05 .. 2026-06-25
TW6789: 2021-04-07 .. 2026-06-25
TW3105: 2015-01-05 .. 2026-06-25
```

字段 schema 与 R3_T bridge 一致：

```text
symbol,date,open,high,low,close,volume,vwap,factor
```

## 4. 输出目录

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_r_real_model_a_top50_bridge_coverage_repair/
```

必须输出：

```text
manifest.json
stock_price_bridge/
repaired_bridge_inventory.csv
real_model_a_top50_coverage_audit.csv
added_symbol_source_trace.csv
price_schema_audit.csv
forbidden_scope_audit.csv
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_X_R_REAL_MODEL_A_TOP50_BRIDGE_COVERAGE_REPAIR_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_X_R_REAL_MODEL_A_TOP50_BRIDGE_COVERAGE_REPAIR_REVIEW_CN.md
```

建议脚本：

```text
scripts/build_tw_policy_rcpt15_r3_x_r_real_model_a_top50_bridge_repair.py
```

## 5. 修复方式

1. 复制 R3_T `stock_price_bridge/` 全量内容到 X_R repaired bridge。
2. 从 R1 candidate normalized 复制 7 个缺口 symbol 的 CSV 到 repaired bridge。
3. 不改 R3_T 原始目录。
4. 不从 stale formal `normalized_nonempty` 取数据，除非仅做 comparison audit。
5. 不联网。
6. 生成 source trace，记录每个新增 symbol 的来源路径、date_min/date_max、row_count、sha256。

## 6. 必须验证

验证 real `2026-06-17` model_a top50：

```text
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a/manifest.json
```

Pass gate：

```text
real_asof = 2026-06-17
model_a_top50_count = 50
repaired_bridge_top50_present_count = 50
repaired_bridge_top50_missing_count = 0
added_symbol_count = 7
added_symbol_date_max_min >= 2026-06-25
all_added_schema_match = true
all_added_required_ohlcv_present = true
no_network = true
no_provider_publish = true
no_accepted_latest_switch = true
no_formal_latest_write = true
no_daily_latest_write = true
no_yz2_yz2r_builder_run = true
no_order_target_quantity_broker = true
```

## 7. Stop Conditions

必须 STOP：

1. R1 candidate normalized 缺任一缺口 symbol；
2. 任一新增 symbol date_max < 2026-06-25；
3. schema 不匹配；
4. 需要联网才能补齐；
5. 需要写 R3_T 原始目录或正式 provider；
6. 需要运行 YZ2/YZ2R builder；
7. 发现任何 latest/provider/accepted latest/order/target/broker 越界。

## 8. Executor Command

```text
请执行 RCPT15_R3_X_R_REAL_MODEL_A_TOP50_BRIDGE_COVERAGE_REPAIR。
```

## 9. Reviewer Audit Brief

审查者必须确认：

1. repaired bridge 是隔离新目录；
2. R3_T 原始 bridge 未被修改；
3. 7 个缺口全部来自本地 R1 candidate normalized；
4. real model_a top50 覆盖从 43/50 变为 50/50；
5. 不联网、不 publish、不写 latest、不运行 builder；
6. 是否可以重跑 `RCPT15_R3_X`，并将 price bridge 输入改为 X_R repaired bridge。
