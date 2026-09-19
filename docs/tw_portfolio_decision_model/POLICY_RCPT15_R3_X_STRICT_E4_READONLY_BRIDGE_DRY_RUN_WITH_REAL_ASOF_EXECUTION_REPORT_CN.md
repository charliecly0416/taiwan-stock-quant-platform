---
created_at: 2026-06-26
status: execution_report
phase: RCPT15_R3_X_STRICT_E4_READONLY_BRIDGE_DRY_RUN_WITH_REAL_ASOF
executor: RCPT15_R3_X
verdict: STOP_BLOCKED_BEFORE_BUILDER
production_allowed: false
provider_publish_default_allowed: false
accepted_latest_switch_allowed: false
network_used: false
order_or_target_output_allowed: false
---

# RCPT15_R3_X Strict E4 Readonly Bridge Dry Run With Real Asof 执行报告

## 1. Scope

- Assigned phase: `RCPT15_R3_X_STRICT_E4_READONLY_BRIDGE_DRY_RUN_WITH_REAL_ASOF`
- Work directory: `/home/chuliyang/taiwan-stock-quant-platform`
- Real asof: `2026-06-17`
- Intended YZ2 out-root: `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/isolated_phase_yz/`
- Intended YZ2R out-root: `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/isolated_phase_yz/yz2r_execution_price_readiness/`
- Verdict: `STOP_BLOCKED_BEFORE_BUILDER`

本阶段按工作文档要求先做 real asof 与 R3_T bridge 覆盖预检。预检发现 R3_T `stock_price_bridge` 对真实 `2026-06-17` model_a top50 覆盖不足，触发工作文档 Stop Condition #2，因此没有执行 YZ2/YZ2R builder，避免产生不完整或 fallback 风险产物。

## 2. Documents / Contracts / Skills Read

- `/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`
- `/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md`
- `/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-data-freshness-diagnosis/references/data-source-boundary.md`
- `/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-data-freshness-diagnosis/references/freshness-status-fields.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_X_STRICT_E4_READONLY_BRIDGE_DRY_RUN_WITH_REAL_ASOF_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_W_SCOPE_ISOLATION_REPAIR_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_W_COORDINATOR_CLOSURE_AND_R3X_ENTRY_CONDITIONS_CN.md`

## 3. Changes Made

只新增/更新 R3_X 隔离证据与本执行报告：

- `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/`
- `docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_X_STRICT_E4_READONLY_BRIDGE_DRY_RUN_WITH_REAL_ASOF_EXECUTION_REPORT_CN.md`

没有修改 production builder 代码、frontend、Agent、monitor、provider、latest pointer 或正式 `data_tw/artifacts/phase_yz` 产物。

## 4. Evidence Produced

隔离输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/
```

已生成要求文件：

```text
real_asof_dry_run_job.json
yz2_command_stdout.json
yz2_command_stderr.txt
yz2r_command_stdout.json
yz2r_command_stderr.txt
real_asof_yz2_source_trace_review.json
real_asof_yz2r_source_trace_review.json
strict_e4_readonly_bridge_validator_report.json
forbidden_scope_audit.csv
diagnostic_findings.md
manifest.json
```

## 5. Key Metrics

```text
real_asof = 2026-06-17
model_a_manifest_exists = true
model_a_row_count = 150
model_a_top50_count = 50
stock_price_bridge_file_count = 99
top50_price_bridge_present_count = 43
top50_price_bridge_missing_count = 7
missing_symbols = TW5439, TW2486, TW1785, TW5351, TW2485, TW6789, TW3105
present_top50_price_date_max_min = 2026-06-25
present_top50_price_date_max_max = 2026-06-25
twii_bridge_exists = true
twii_bridge_date_max = 2026-06-25
```

Missing top50 ranks:

```text
TW5439 rank 24
TW2486 rank 30
TW1785 rank 39
TW5351 rank 41
TW2485 rank 43
TW6789 rank 47
TW3105 rank 50
```

## 6. Builder Execution

YZ2 command was not executed:

```text
blocked_before_execution = true
reason = R3_T stock_price_bridge missing real model_a top50 symbols
```

YZ2R command was not executed:

```text
blocked_before_execution = true
reason = R3_T stock_price_bridge missing real model_a top50 symbols
```

Reasoning: `scripts/build_phase_yz2_orthogonal_package.py` and `scripts/build_phase_yz2r_execution_price_readiness.py` enforce readonly bridge file existence for required symbols when bridge args are provided. Running them with the current bridge would fail on missing top50 price files. Allowing fallback would violate the R3_X work doc stop conditions.

## 7. Bridge Validator

Command executed:

```bash
python scripts/validate_tw_daily_strict_e4_readonly_bridge_contract.py \
  --job-json data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/real_asof_dry_run_job.json \
  --json
```

Result:

```text
ok = false
verdict = FAIL
checks = 10/14 PASS
```

Failed checks:

```text
yz2_payload_records_bridge_used
yz2_chain_records_bridge_used
yz2r_payload_records_bridge_used
yz2r_chain_records_bridge_used
```

This FAIL is expected for the STOP state: the validator was run against `real_asof_dry_run_job.json`, but YZ2/YZ2R were not executed because bridge coverage was insufficient.

## 8. Compliance With Mainline

```text
real_asof = PASS
model_a_manifest_exists = PASS
isolated_out_root_created = PASS
yz2_command_ok = FAIL / not executed due STOP
yz2r_command_ok = FAIL / not executed due STOP
yz2_manifest_exists = FAIL / not generated due STOP
yz2_source_trace_exists = FAIL / not generated due STOP
yz2_source_freshness_audit_exists = FAIL / not generated due STOP
model_b_yz2_manifest_exists = FAIL / not generated due STOP
yz2r_manifest_exists = FAIL / not generated due STOP
yz2r_source_trace_exists = FAIL / not generated due STOP
bridge_validator_ok = FAIL
bridge_validator_checks = 10/14 PASS
```

## 9. Forbidden Actions Audit

```text
no_network = true
no_provider_publish = true
no_accepted_latest_switch = true
no_formal_latest_write = true
no_daily_latest_write = true
no_production_default_write = true
no_frontend_agent_monitor_mutation = true
no_training_or_tuning = true
no_order_target_quantity_broker = true
no_formal_phase_yz_write = true
```

## 10. Issues / Blockers / Deviations

### Blocker

R3_T bridge coverage is insufficient for the real `2026-06-17` model_a top50. This triggers the R3_X stop condition:

```text
R3_T bridge 缺失或覆盖不足
```

The R3_T manifest states `stock_price_bridge_symbols = 99`, but that 99-symbol set does not fully cover the real model_a top50 used by this phase. The missing symbols are exactly the blocker.

### Deviation From Desired Pass Gate

The requested pass gate cannot be satisfied in this state because builder dry-run would need all top50 price bridge CSVs under the R3_T bridge directory.

## 11. Files Changed

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/real_asof_dry_run_job.json
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/yz2_command_stdout.json
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/yz2_command_stderr.txt
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/yz2r_command_stdout.json
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/yz2r_command_stderr.txt
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/real_asof_yz2_source_trace_review.json
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/real_asof_yz2r_source_trace_review.json
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/strict_e4_readonly_bridge_validator_report.json
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/forbidden_scope_audit.csv
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/diagnostic_findings.md
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/manifest.json
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_X_STRICT_E4_READONLY_BRIDGE_DRY_RUN_WITH_REAL_ASOF_EXECUTION_REPORT_CN.md
```

## 12. Recommendation For Reviewer

Verdict should be `STOP` or `FAIL_NEEDS_REPAIR` rather than PASS.

Recommended repair route: produce an isolated bridge repair for the missing real model_a top50 symbols, then rerun RCPT15_R3_X with the same no-network/no-publish/no-latest-write/no-production/no-training/no-trading boundary unless the coordinator explicitly authorizes a separate data repair stage.
