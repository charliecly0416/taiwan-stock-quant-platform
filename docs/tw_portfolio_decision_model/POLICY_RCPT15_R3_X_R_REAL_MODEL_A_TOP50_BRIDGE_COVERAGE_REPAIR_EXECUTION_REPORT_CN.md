---
created_at: 2026-06-26T06:56:36+00:00
status: execution_report
phase: RCPT15_R3_X_R_REAL_MODEL_A_TOP50_BRIDGE_COVERAGE_REPAIR
executor: RCPT15_R3_X_R
verdict: PASS_READY_FOR_R3_X_RERUN_WITH_REPAIRED_BRIDGE
production_allowed: false
provider_publish_default_allowed: false
accepted_latest_switch_allowed: false
network_used: false
order_or_target_output_allowed: false
---

# RCPT15_R3_X_R Real Model A Top50 Bridge Coverage Repair 执行报告

## 1. Scope

- Assigned phase: `RCPT15_R3_X_R_REAL_MODEL_A_TOP50_BRIDGE_COVERAGE_REPAIR`
- Work directory: `/home/chuliyang/taiwan-stock-quant-platform`
- Real asof: `2026-06-17`
- Mainline / work document: `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_X_R_REAL_MODEL_A_TOP50_BRIDGE_COVERAGE_REPAIR_WORK_CN.md`
- Output directory: `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_r_real_model_a_top50_bridge_coverage_repair`
- Verdict: `PASS_READY_FOR_R3_X_RERUN_WITH_REPAIRED_BRIDGE`

本阶段只执行隔离 bridge coverage repair：复制 R3_T `stock_price_bridge` 全量到新目录，并从本地 R1 `candidate_normalized` 补齐 real `2026-06-17` model_a top50 的 7 个缺口。

## 2. Documents / Contracts / Skills Read

- `/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_X_R_REAL_MODEL_A_TOP50_BRIDGE_COVERAGE_REPAIR_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_X_STRICT_E4_READONLY_BRIDGE_DRY_RUN_WITH_REAL_ASOF_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_X_STRICT_E4_READONLY_BRIDGE_DRY_RUN_WITH_REAL_ASOF_EXECUTION_REPORT_CN.md`

## 3. Changes Made

- 新增脚本：`scripts/build_tw_policy_rcpt15_r3_x_r_real_model_a_top50_bridge_repair.py`
- 新增隔离修复输出：`data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_r_real_model_a_top50_bridge_coverage_repair`
- 新增本执行报告：`docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_X_R_REAL_MODEL_A_TOP50_BRIDGE_COVERAGE_REPAIR_EXECUTION_REPORT_CN.md`

未修改 R3_T 原始 bridge，未修改 provider / latest / accepted latest / frontend / Agent / monitor，未运行 YZ2/YZ2R builder。

## 4. Evidence Produced

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

## 5. Key Metrics

```text
real_asof = 2026-06-17
model_a_top50_count = 50
r3_t_bridge_file_count = 99
repaired_bridge_file_count = 106
repaired_bridge_top50_present_count = 50
repaired_bridge_top50_missing_count = 0
added_symbol_count = 7
added_symbol_date_max_min = 2026-06-25
added_symbol_date_max_max = 2026-06-25
all_added_schema_match = true
all_added_required_ohlcv_present = true
forbidden_scope_pass = true
```

Added symbols:

```text
TW5439, TW2486, TW1785, TW5351, TW2485, TW6789, TW3105
```

## 6. Validation Results

```text
py_compile = PASS
script_run = PASS
coverage_gate = PASS
schema_gate = PASS
forbidden_scope_gate = PASS
```

Commands run:

```bash
python -m py_compile scripts/build_tw_policy_rcpt15_r3_x_r_real_model_a_top50_bridge_repair.py
python scripts/build_tw_policy_rcpt15_r3_x_r_real_model_a_top50_bridge_repair.py
```

## 7. Compliance With Work Doc

```text
copied_r3_t_bridge_full = true
added_7_from_local_r1_candidate_normalized = true
r3_t_source_unchanged_by_script = true
real_model_a_top50_coverage_50_of_50 = true
no_network = true
no_provider_publish = true
no_accepted_latest_switch = true
no_formal_latest_write = true
no_daily_latest_write = true
no_yz2_yz2r_builder_run = true
no_order_target_quantity_broker = true
```

## 8. Forbidden Actions Audit

未发现以下越界行为：

```text
network
provider publish
accepted latest switch
formal latest pointer write
daily latest write
YZ2/YZ2R builder run
R3_T source bridge mutation
frontend / Agent / monitor mutation
training / tuning
order / target / quantity / broker output
```

## 9. Issues / Blockers / Deviations

无阻断项。R3_X_R repaired bridge 已满足 real model_a top50 coverage gate，可供后续阶段在保持 no-network/no-publish/no-latest-write/no-builder-unless-authorized 边界下，将 price bridge 输入切换为本隔离修复目录重跑 R3_X。

## 10. Files Changed

```text
scripts/build_tw_policy_rcpt15_r3_x_r_real_model_a_top50_bridge_repair.py
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_r_real_model_a_top50_bridge_coverage_repair/
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_X_R_REAL_MODEL_A_TOP50_BRIDGE_COVERAGE_REPAIR_EXECUTION_REPORT_CN.md
```

## 11. Recommendation For Reviewer

建议审查者复核 `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_r_real_model_a_top50_bridge_coverage_repair` 下 manifest、coverage audit、source trace、schema audit、forbidden scope audit，并确认 R3_T 原始 bridge 未被修改。
