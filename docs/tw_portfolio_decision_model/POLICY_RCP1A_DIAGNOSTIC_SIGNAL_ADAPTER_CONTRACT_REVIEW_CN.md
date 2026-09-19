---
created_at: 2026-06-24
status: rcp1a_review
phase: RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT
work_doc: docs/tw_portfolio_decision_model/POLICY_RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract
verdict: PASS_READY_FOR_RCP1B_DIAGNOSTIC_BASELINE_REPLAY_AUDIT_WORK_DOC
---

# RCP1A Diagnostic Signal Adapter / Contract 审查报告

## 1. Verdict

`PASS_READY_FOR_RCP1B_DIAGNOSTIC_BASELINE_REPLAY_AUDIT_WORK_DOC`

RCP1A 执行满足工作文档要求：已把 RCP0 选中的 `C03_S1B1_WF_VAL_2021_2022` 转为 diagnostic-only replay input，schema、coverage、rank/score、lineage、diagnostic semantics 与 forbidden audit 均通过。

## 2. Findings

### Critical

无。

### High

无。

### Medium

无阻塞。需要在 RCP1B 继续保持口径：2022 只能称为 `downturn validation diagnostic`，不得称为 strict OOS / final OOS / independent test。

### Low

执行报告说明了 `semantic_label` 与 forbidden `label` 字段的审计差异。该解释合理：`semantic_label` 是 RCP1A 工作文档要求的语义字段，不是训练标签或 future label。

## 3. Mainline Compliance

已符合主线边界：

```text
不做 baseline replay
不做 risk-control replay
不训练模型
不做 strict_test
不修改 registry/default/provider/frontend/Agent/订单链路
不输出 OrderIntent / target_weight / target_position / quantity_instruction
```

RCP1A 只完成 signal adapter / contract / validation，未越权。

## 4. Evidence Checked

已审查：

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
```

validator 摘要：

```text
status = PASS
row_count = 73078
date_min = 2021-01-04
date_max = 2022-12-30
trading_days = 489
schema_status = PASS
coverage_status = PASS
rank_score_status = PASS
lineage_status = PASS
diagnostic_semantics_status = PASS
forbidden_actions_status = PASS
rcp1b_authorizable = true
```

## 5. Missing Evidence Or Open Questions

RCP1A 无缺失证据。

RCP1B 仍需单独审计：

```text
1. baseline replay 是否严格消费 RCP1A adapter；
2. 2022 signal/price/execution_date 对齐是否可信；
3. next_open 缺失是否 skip 或 audit，不得 fallback；
4. fee/tax/turnover 是否可审计；
5. 输出是否仍为 diagnostic-only，不进入生产链路。
```

## 6. Forbidden Actions Audit

RCP1A forbidden audit clean：

```text
baseline replay = not performed
risk-control replay = not performed
model training = not performed
strict_test = not performed
registry/default/provider/frontend/Agent/order chain = not touched
OrderIntent / target_weight / target_position / quantity_instruction = not output
```

## 7. Next Work Document

审查通过后，授权进入：

```text
RCP1B: 2022 Diagnostic Baseline Replay Audit
```

RCP1B 只允许：

```text
1. 读取 RCP1A diagnostic_model_signal.csv；
2. 使用既有 readonly replay accounting 口径回放 baseline rule；
3. 输出 2022 baseline summary / NAV / actions / positions / coverage / accounting audits；
4. 明确 2022 是 downturn validation diagnostic；
5. 为 RCP2 risk-control rule design 提供对照基线。
```

RCP1B 不允许：

```text
risk-control replay
规则设计或阈值选择
模型训练
strict_test
production/default/provider/frontend/Agent/订单链路集成
OrderIntent artifact 输出
target_weight / target_position / quantity_instruction
把 2022 写成 strict OOS
```

## 8. Command For Executor

```text
请按 docs/tw_portfolio_decision_model/POLICY_RCP1B_DIAGNOSTIC_BASELINE_REPLAY_AUDIT_WORK_CN.md 执行 RCP1B。只做 2022 diagnostic baseline replay audit，不做 risk-control policy，不训练，不 strict_test，不修改生产链路。完成后输出 data_tw/experiments/risk_control_policy_2022/rcp1b_diagnostic_baseline_replay_audit/ 下全部必需文件，并提交执行报告。
```
