---
created_at: 2026-06-23
status: pass_ready_for_fpa3_work_doc
phase_reviewed: RAL_FPA2_R_FULL_PATH_METRIC_RECONCILIATION_REPAIR
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FULL_PATH_BASELINE_PLUS_ACTION_DIAGNOSTIC_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RAL_FPA2_R_FULL_PATH_METRIC_RECONCILIATION_REPAIR_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RAL_FPA2_R_FULL_PATH_METRIC_RECONCILIATION_REPAIR_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/full_path_action_diagnostic/fpa2_r_full_path_metric_reconciliation_repair
reviewer_role: independent_reviewer
fpa2_passed: true
fpa3_work_doc_authorized: true
fpa4_authorized: false
strict_test_authorized: false
rule_selection_authorized: false
threshold_selection_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# RAL-FPA2-R Full-path Metric Reconciliation Repair 审查意见

## 1. Verdict

审查结论：

```text
PASS_READY_FOR_FPA3_WORK_DOC
```

本轮修复解决了上一轮 blocker：direction / cost / concentration 的主 pass gate 已从事件级 oracle delta 累加，切换为 `action_space_summary_repaired.csv` 派生的 full-path summary 相对 baseline/no-op path 差分。

因此，FPA2 oracle-style upper-bound diagnostic 可以视为通过，并允许 reviewer 给出 FPA3 工作文档。

注意：本结论只授权进入 FPA3 pre-rule attribution diagnostic，不授权 FPA4、规则 sanity、阈值选择、strict_test、模型训练或生产链路。

## 2. Findings

### Critical

无 blocking finding。

### High

1. `full_path_metric_reconciliation.csv` 已按每个 action_space、每个 split 计算 baseline 与 action-space 的 full-path 差分：

```text
baseline_final_equity
action_space_final_equity
excess_final_equity
baseline_net_return_after_fee_tax
action_space_net_return_after_fee_tax
excess_net_return_after_fee_tax
baseline_fee_and_tax
action_space_fee_and_tax
fee_tax_delta
baseline_turnover_proxy
action_space_turnover_proxy
turnover_delta
action_count_delta
skip_count_delta
```

2. `regime_participation` 已明确声明为 FPA2-R baseline/no-op path。其 own excess 为 0，不应作为后续 positive action-space 展开。

3. direction audit 已使用 `full_path_metric_reconciliation.csv`：

```text
replacement_buy:
  train excess_net_return_after_fee_tax = 25.554525
  validation excess_net_return_after_fee_tax = 2.80874585

sell_timing:
  train excess_net_return_after_fee_tax = 5.58416295
  validation excess_net_return_after_fee_tax = 0.24722808

hold_continuation:
  train excess_net_return_after_fee_tax = 4.17929051
  validation excess_net_return_after_fee_tax = 0.57254675
```

三类 action-space 均满足 train / validation full-path positive excess。`regime_participation` 不满足。

4. cost audit 已使用 full-path fee/tax 与 turnover 差分，不再把 sell/hold 的成本项固定为 0。

5. concentration audit 已正确降级为：

```text
concentration_scope = event_attribution_auxiliary
not_primary_full_path_gate = true
primary_gate_source = full_path_metric_reconciliation.csv
```

这符合上一轮 repair 要求。

### Medium

1. FPA2 的 positive upper-bound 仍是 oracle diagnostic，不是可交易规则。后续 FPA3 必须只做可观测低维特征归因，不得直接把 oracle action 当规则。

2. FPA3 应优先围绕 `replacement_buy`、`sell_timing`、`hold_continuation` 展开。`regime_participation` 在本轮没有 positive excess，只能作为上下文特征或 negative/control evidence。

### Low

1. `sample_count_train` / `sample_count_validation` 在 direction audit 中为空。由于本轮主目标是 metric reconciliation，且 full-path split summary 已完整，该项不阻塞 FPA2 通过；但 FPA3 归因表必须补足 bucket/sample/action counts。

## 3. Mainline Compliance

| Requirement | Review |
|---|---|
| 仍属于 FPA2 repair | pass |
| 使用 full-path summary 作为主 gate | pass |
| 不再使用 event delta 作为 primary gate | pass |
| baseline/no-op path 声明 | pass |
| direction audit 使用 excess final equity / net return | pass |
| cost audit 使用 fee/tax 与 turnover 差分 | pass |
| concentration scope 明确 | pass |
| 至少一个 action-space train/validation 正上界 | pass |
| 不跑 FPA3/FPA4 | pass |
| 不使用 strict_test | pass |
| 不做规则选择/阈值选择 | pass |
| 不训练模型 | pass |
| 不输出 OrderIntent / target / quantity / broker | pass |
| 是否允许写 FPA3 工作文档 | pass |

## 4. Evidence Checked

审查了执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA2_R_FULL_PATH_METRIC_RECONCILIATION_REPAIR_EXECUTION_REPORT_CN.md
```

审查了工作文档：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA2_R_FULL_PATH_METRIC_RECONCILIATION_REPAIR_WORK_CN.md
```

审查了产物目录：

```text
data_tw/experiments/full_path_action_diagnostic/fpa2_r_full_path_metric_reconciliation_repair/
```

重点核对：

```text
manifest.json
source_fpa2_r_manifest.json
full_path_metric_reconciliation.csv
train_validation_direction_audit_metric_reconciled.csv
transaction_cost_marginal_audit_metric_reconciled.csv
symbol_date_concentration_audit_metric_reconciled.csv
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

审查了生成脚本：

```text
scripts/build_tw_policy_ral_fpa2_r_metric_reconciliation_repair.py
```

脚本语法检查：

```text
python -m py_compile scripts/build_tw_policy_ral_fpa2_r_metric_reconciliation_repair.py
```

结果：通过。

## 5. Missing Evidence Or Open Questions

FPA2 无需继续 repair。

FPA3 需要补充的新证据不是 FPA2 缺陷，而是下一阶段目标：

```text
1. positive upper-bound 是否可归因到低维可观测特征；
2. 归因是否不是 baseline clone、不是 cash/no-trade、不是 oracle-only；
3. 每个候选 hypothesis 是否有 train/validation 同向证据；
4. 是否能形成少量预声明 hypothesis，供 FPA4 之后再审查是否允许规则 sanity。
```

## 6. Forbidden Actions Audit

`forbidden_consumer_audit.csv` 与 manifest / validator 均显示：

```text
FPA3 = not run
FPA4 = not run
strict_test = false
rule_selection = false
threshold_selection = false
model_training = false
OrderIntent_output = false
target_weight_output = false
target_position_output = false
quantity_or_broker_output = false
production_allowed = false
provider/frontend/Agent/production = not performed
```

审查未发现越权。

## 7. Next Work Document

下一步进入 FPA3：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA3_PRE_RULE_ATTRIBUTION_DIAGNOSTIC_WORK_CN.md
```

FPA3 只允许 pre-rule attribution diagnostic。不得进入 FPA4，不得写可执行规则，不得选择阈值，不得使用 strict_test，不得训练模型，不得输出订单或生产字段。
