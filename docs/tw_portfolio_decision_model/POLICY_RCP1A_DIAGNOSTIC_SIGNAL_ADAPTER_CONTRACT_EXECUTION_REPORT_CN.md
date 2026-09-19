---
created_at: 2026-06-24
status: rcp1a_execution_report
phase: RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT
work_doc: docs/tw_portfolio_decision_model/POLICY_RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT_WORK_CN.md
output_root: data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract
recommended_next_step: PASS_READY_FOR_RCP1B_DIAGNOSTIC_BASELINE_REPLAY_AUDIT_WORK_DOC
baseline_replay_performed: false
risk_control_replay_performed: false
model_training_performed: false
strict_test_performed: false
production_or_provider_change_performed: false
---

# RCP1A Diagnostic Signal Adapter / Contract 执行报告

## 1. Scope

本轮执行范围：

```text
RCP1A: Diagnostic Signal Adapter / Contract
```

目标是把 RCP0 选中的 `C03_S1B1_WF_VAL_2021_2022` 合同化为后续 RCP1B baseline replay 可读取的只读诊断信号输入。

已确认非目标：

```text
不做 baseline replay
不做 risk-control replay
不训练模型
不做 strict_test
不修改 registry/default/provider/frontend/Agent/订单链路
不输出 OrderIntent / target_weight / target_position / quantity_instruction
```

## 2. Documents / Contracts / Skills Read

已读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP0_COORDINATOR_DECISION_ACCEPT_2022_DIAGNOSTIC_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP0_2015_2020_QLIB_ARTIFACT_DISCOVERY_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP0_2015_2020_QLIB_ARTIFACT_DISCOVERY_REVIEW_CN.md
data_tw/experiments/risk_control_policy_2022/rcp0_artifact_discovery/selected_signal_artifact_contract.json
data_tw/experiments/risk_control_policy_2022/rcp0_artifact_discovery/field_availability_audit.csv
data_tw/experiments/risk_control_policy_2022/rcp0_artifact_discovery/oos_window_audit.csv
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
```

使用 workflow 标准：

```text
coordinator-executor-reviewer-workflow
```

## 3. Changes Made

生成 RCP1A 只读诊断 adapter 产物，输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/
```

核心转换：

```text
date = source.date
signal_date = source.date
instrument = source.instrument
rank = source.qlib_rank
score = source.qlib_score_raw
raw_score = source.qlib_score_raw
source_rank = source.qlib_rank
source_score = source.qlib_score_raw
model_id = rcp_qllib_20150504_20201231_wf_val_2021_2022_diagnostic
model_family = qlib_lightgbm_alpha158
signal_type = qlib_score_rank
strict_oos = false
diagnostic_only = true
semantic_label = downturn_validation_diagnostic_only
```

## 4. Evidence Produced

已生成工作文档要求的全部文件：

```text
manifest.json
diagnostic_signal_adapter_manifest.json
diagnostic_model_signal.csv
schema_mapping.csv
coverage_validation.csv
rank_score_validation.csv
lineage_audit.json
diagnostic_semantics_audit.json
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

核心统计：

```text
row_count = 73078
date_range = 2021-01-04..2022-12-30
trading_days = 489
years = 2021, 2022
```

## 5. Validation Result

`validator_report.json` 结论：

```json
{
  "phase": "RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT",
  "status": "PASS",
  "pass": true,
  "input_exists": true,
  "output_exists": true,
  "schema_status": "PASS",
  "coverage_status": "PASS",
  "rank_score_status": "PASS",
  "lineage_status": "PASS",
  "diagnostic_semantics_status": "PASS",
  "forbidden_actions_status": "PASS",
  "rcp1b_authorizable": true,
  "recommended_next_step": "PASS_READY_FOR_RCP1B_DIAGNOSTIC_BASELINE_REPLAY_AUDIT_WORK_DOC",
  "row_count": 73078,
  "date_min": "2021-01-04",
  "date_max": "2022-12-30",
  "trading_days": 489,
  "years": [
    2021,
    2022
  ],
  "notes": "RCP1A only contracts diagnostic signal input. It authorizes only RCP1B diagnostic baseline replay audit after reviewer pass, not risk-control replay."
}
```

验证摘要：

```text
schema_status = PASS
coverage_status = PASS
rank_score_status = PASS
lineage_status = PASS
diagnostic_semantics_status = PASS
forbidden_actions_status = PASS
```

## 6. Diagnostic Semantics

本轮明确：

```text
strict_oos_2022 = false
diagnostic_only = true
threshold_mining_on_2022_allowed = false
baseline_replay_allowed_after_pass = true
risk_control_replay_allowed_after_pass = false
```

允许语言：

```text
2022 downturn validation diagnostic
non-train downturn diagnostic
```

禁止语言：

```text
strict OOS
final OOS
independent test
```

## 7. Forbidden Actions Audit

本轮未执行：

```text
baseline replay
risk-control replay
model training
strict_test
registry/default 修改
provider publish
accepted latest switch
monitor/frontend/Agent integration
broker/order/quick-trade
OrderIntent 输出
target_weight / target_position / quantity_instruction 输出
```

`forbidden_consumer_audit.csv` 已检查 adapter 输出不含成交、现金、仓位、订单、future return、forward return、label 或 `label_*` 训练标签字段。

说明：`semantic_label` 是工作文档要求的诊断语义字段，不是 future label / label_ 训练标签，因此不构成 forbidden field。

## 8. Issues / Blockers / Deviations

无阻塞。

有一个审计口径说明：初版 forbidden audit 曾按子串把 `semantic_label` 误判为 `label` 风险；已修正为精确字段 `label` 与前缀 `label_*` 检查，避免把 RCP1A 必需语义字段误伤。

## 9. Files Changed

```text
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/manifest.json
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/diagnostic_signal_adapter_manifest.json
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/diagnostic_model_signal.csv
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/schema_mapping.csv
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/coverage_validation.csv
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/rank_score_validation.csv
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/lineage_audit.json
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/diagnostic_semantics_audit.json
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/forbidden_consumer_audit.csv
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/validator_report.json
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/diagnostic_findings.md
docs/tw_portfolio_decision_model/POLICY_RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT_EXECUTION_REPORT_CN.md
```

## 10. Recommendation For Reviewer

建议审查者结论：

```text
PASS_READY_FOR_RCP1B_DIAGNOSTIC_BASELINE_REPLAY_AUDIT_WORK_DOC
```

若审查通过，只授权进入 RCP1B diagnostic baseline replay audit 工作文档；不得直接授权 risk-control replay、strict_test 或生产链路集成。
