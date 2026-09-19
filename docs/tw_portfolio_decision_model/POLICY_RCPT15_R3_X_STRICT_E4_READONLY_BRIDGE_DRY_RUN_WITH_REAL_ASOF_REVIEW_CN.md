---
created_at: 2026-06-26
status: review
phase: RCPT15_R3_X_STRICT_E4_READONLY_BRIDGE_DRY_RUN_WITH_REAL_ASOF
reviewer: RCPT15_R3_X_INDEPENDENT_REVIEWER
verdict: PASS_STOP_ACCEPTED
production_allowed: false
provider_publish_default_allowed: false
accepted_latest_switch_allowed: false
network_used: false
order_or_target_output_allowed: false
recommended_next_phase: RCPT15_R3_X_R_REPAIR_R3_T_BRIDGE_TOP50_COVERAGE_OR_COORDINATOR_ROUTE_DECISION
---

# RCPT15_R3_X Strict E4 Readonly Bridge Dry Run With Real Asof 审查报告

## 1. Verdict

```text
PASS_STOP_ACCEPTED
```

本审查接受执行者的 `STOP_BLOCKED_BEFORE_BUILDER`。这不是 R3_X pass gate 通过；相反，真实 `2026-06-17` model_a top50 对 R3_T `stock_price_bridge` 覆盖不足，命中工作文档 Stop Condition #2：

```text
R3_T bridge 缺失或覆盖不足
```

执行者在 builder 前停止是正确行为。不得把本阶段推进到 shadow acceptance contract，也不得把 validator FAIL 视为需绕过的技术失败。

## 2. Findings

### Critical

无。

### High

1. `2026-06-17` real model_a top50 的 R3_T bridge 覆盖不足，R3_X 不能运行 YZ2/YZ2R builder。

独立复算结果：

```text
top50_count = 50
present_count = 43
missing_count = 7
bridge_file_count = 99
missing = TW5439@24 TW2486@30 TW1785@39 TW5351@41 TW2485@43 TW6789@47 TW3105@50
```

缺口符号与执行报告一致：

```text
TW5439, TW2486, TW1785, TW5351, TW2485, TW6789, TW3105
```

2. R3_X pass gate 未满足。

以下 gate 因正确 STOP 而未满足：

```text
yz2_command_ok = false / not executed
yz2r_command_ok = false / not executed
yz2_manifest_exists = false in isolated out-root
yz2_source_trace_exists = false in isolated out-root
yz2_source_freshness_audit_exists = false in isolated out-root
model_b_yz2_manifest_exists = false in isolated out-root
yz2r_manifest_exists = false in isolated out-root
yz2r_source_trace_exists = false in isolated out-root
bridge_validator_ok = false
```

该结果不构成执行者违规；它是 Stop Condition 的预期后果。

### Medium

1. 正式 `data_tw/artifacts/phase_yz` 中已存在 `2026-06-17` 的 YZ2/YZ2R 文件，但这些文件时间为 `2026-06-18`，早于本 R3_X 证据生成时间 `2026-06-26 06:44`。

审查结论限定如下：

```text
R3_X 未在 isolated_phase_yz 生成 builder 产物。
R3_X 执行报告未把正式 phase_yz 既有产物当成本阶段通过证据。
不能据此声称正式 phase_yz 下不存在 2026-06-17 YZ2/YZ2R 文件。
```

2. 工作树存在大量无关 modified / untracked 文件；本审查仅对 R3_X 指定文档与证据目录作结论。

### Low

无。

## 3. Mainline Compliance

```text
required skills/docs read = PASS
real_asof_2026_06_17_used = PASS
model_a_manifest_exists = PASS
model_a_row_count_150 = PASS
preflight_before_builder = PASS
stop_condition_2_triggered = PASS
yz2_builder_not_run = PASS
yz2r_builder_not_run = PASS
isolated_phase_yz_empty = PASS
no_fallback_to_formal_or_stale_source = PASS_BY_EVIDENCE
no_new_isolated_yz2_yz2r_outputs = PASS
bridge_validator_fail_reasonable = PASS
no_provider_publish = PASS_BY_EVIDENCE
no_accepted_latest_switch = PASS_BY_EVIDENCE
no_formal_latest_write = PASS_BY_EVIDENCE
no_daily_latest_write = PASS_BY_EVIDENCE
no_frontend_agent_monitor_mutation = PASS_BY_EVIDENCE
no_training_or_tuning = PASS_BY_EVIDENCE
no_order_target_quantity_broker = PASS_BY_EVIDENCE
```

R3_X 工作文档要求的理想链路是：

```text
real model_a asof + R3_T isolated price/TWII bridge
  -> isolated YZ2/YZ2R outputs
  -> validator PASS
```

当前实际链路是：

```text
real model_a asof + R3_T isolated price/TWII bridge preflight
  -> top50 bridge coverage insufficient
  -> STOP before builder
  -> validator FAIL because bridge-used records do not exist
```

这符合工作文档 Stop Conditions。

## 4. Evidence Checked

已读取的必读文档：

```text
/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md
/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md
/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-data-freshness-diagnosis/references/data-source-boundary.md
/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-data-freshness-diagnosis/references/freshness-status-fields.md
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_X_STRICT_E4_READONLY_BRIDGE_DRY_RUN_WITH_REAL_ASOF_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_X_STRICT_E4_READONLY_BRIDGE_DRY_RUN_WITH_REAL_ASOF_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_W_SCOPE_ISOLATION_REPAIR_REVIEW_CN.md
```

已读取的 R3_X 证据：

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/manifest.json
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/real_asof_dry_run_job.json
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/strict_e4_readonly_bridge_validator_report.json
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/diagnostic_findings.md
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/forbidden_scope_audit.csv
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/yz2_command_stdout.json
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/yz2r_command_stdout.json
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/real_asof_yz2_source_trace_review.json
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/real_asof_yz2r_source_trace_review.json
```

已独立检查的输入与目录：

```text
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a/manifest.json
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a/signals.csv
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/manifest.json
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/stock_price_bridge/
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/twii_bridge.csv
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_x_strict_e4_readonly_bridge_dry_run_with_real_asof/isolated_phase_yz/
```

关键证据：

```text
R3_X isolated_phase_yz file count = 0
R3_X evidence files timestamp = 2026-06-26 06:44
formal phase_yz existing YZ2/YZ2R 2026-06-17 files timestamp = 2026-06-18 09:14 / 09:29
validator result = FAIL, 10/14 PASS
validator failed checks = yz2_payload_records_bridge_used, yz2_chain_records_bridge_used, yz2r_payload_records_bridge_used, yz2r_chain_records_bridge_used
```

Builder guardrail code inspection supports executor's stop rationale:

```text
scripts/build_phase_yz2_orthogonal_package.py requires readonly stock bridge files when readonly_price_bridge_dir is provided.
scripts/build_phase_yz2_orthogonal_package.py requires readonly TWII bridge when readonly_twii_bridge is provided.
scripts/build_phase_yz2r_execution_price_readiness.py requires readonly price bridge files when readonly_price_bridge_dir is provided.
```

## 5. Validator FAIL Interpretation

Validator FAIL is reasonable and expected in this STOP state.

The validator requires YZ2/YZ2R payload and chain fields to record bridge usage. Because builder execution was correctly blocked before YZ2/YZ2R ran, these records cannot exist:

```text
readonly_price_bridge_used_by_yz2 = false
readonly_twii_bridge_used_by_yz2 = false
readonly_price_bridge_used_by_yz2r = false
```

The validator still passed the relevant forbidden-action checks:

```text
no_provider_publish = PASS
no_accepted_latest_switch = PASS
no_formal_latest_write = PASS
no_order_target_quantity_broker = PASS
no_fallback_to_stale_formal_source_when_bridge_requested = PASS
job_not_production_publish = PASS
```

Therefore the correct interpretation is:

```text
contract validator did not pass because required builder evidence was intentionally absent after STOP.
```

不是：

```text
builder evidence exists but validator is wrong.
```

## 6. Missing Evidence Or Open Questions

无阻断性审查缺口。

限制说明：

```text
本审查没有联网。
本审查没有运行 YZ2/YZ2R builder。
本审查没有运行 provider refresh/publish。
本审查没有切换 accepted latest。
本审查没有写 latest pointer。
本审查没有修改执行脚本。
```

由于未在 R3_X 执行前建立完整 mtime baseline，关于“没有写正式 latest/provider/accepted latest”的结论以 R3_X job JSON、forbidden_scope_audit、执行报告、隔离目录产物和已观察文件时间为依据；未对仓库中所有历史 latest/provider 文件作全量时间线归因。

## 7. Forbidden Actions Audit

本审查未发现 R3_X 证据显示以下行为：

```text
network
provider publish
accepted latest switch
formal latest pointer write
daily latest write
production default switch
frontend / Agent / monitor mutation
training / tuning
order / target / quantity / broker output
fallback to stale formal price/TWII source
```

执行者没有运行 YZ2/YZ2R builder，也没有 fallback 到 formal/stale source。R3_X 目录下仅有 11 个顶层证据文件，`isolated_phase_yz` 下无 builder 文件。

## 8. Next Work Document

推荐下一阶段：

```text
RCPT15_R3_X_R_REPAIR_R3_T_BRIDGE_TOP50_COVERAGE_OR_COORDINATOR_ROUTE_DECISION
```

优先路线：

```text
补齐 R3_T bridge 对 2026-06-17 real model_a top50 的 7 个缺口：
TW5439, TW2486, TW1785, TW5351, TW2485, TW6789, TW3105
```

修复边界必须由协调者明确授权。若只是继续当前 R3_X 审查路线，则仍应保持：

```text
network_allowed = false
provider_publish_allowed = false
accepted_latest_switch_allowed = false
formal_latest_pointer_write_allowed = false
daily_latest_write_allowed = false
production_default_switch_allowed = false
frontend_agent_monitor_mutation_allowed = false
training_tuning_allowed = false
execution_semantics_output_allowed = false
```

协调者可选路线：

1. `preferred`: 新开隔离 repair 阶段，补齐上述 7 个 R3_T bridge CSV，并复核 date_max / schema / forbidden scope 后，重跑 R3_X。
2. `alternative`: 选择另一个 real asof，但必须先证明该 asof 的 model_a top50 被 R3_T 或新授权 bridge 完整覆盖，并由协调者修改 R3_X asof 合同。
3. `contract_change`: 修改 strict E4 readonly bridge 合同，允许部分覆盖或其他 source，但这会改变当前 safety contract，必须由协调者显式重开合同阶段；当前审查不建议这样做。

不得采取的路线：

```text
不得用正式 data_tw/artifacts/phase_yz 既有 YZ2/YZ2R 产物替代 R3_X isolated builder evidence。
不得 fallback 到 stale formal price/TWII source。
不得写 provider/latest/accepted latest。
不得在未补齐 bridge 覆盖前强行运行 builder 来制造失败产物。
```

## 9. Command For Coordinator

```text
R3_X STOP accepted. Do not proceed to shadow acceptance. Open a narrow repair/route-decision phase to either complete R3_T bridge coverage for 2026-06-17 model_a top50 missing symbols (TW5439, TW2486, TW1785, TW5351, TW2485, TW6789, TW3105), select a coordinator-approved alternative real asof with complete bridge coverage, or explicitly revise the strict E4 readonly bridge contract.
```
