---
created_at: 2026-06-23
status: pass_ready_for_fpa4_work_doc
phase_reviewed: RAL_FPA3_PRE_RULE_ATTRIBUTION_DIAGNOSTIC
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FULL_PATH_BASELINE_PLUS_ACTION_DIAGNOSTIC_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RAL_FPA3_PRE_RULE_ATTRIBUTION_DIAGNOSTIC_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RAL_FPA3_PRE_RULE_ATTRIBUTION_DIAGNOSTIC_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/full_path_action_diagnostic/fpa3_pre_rule_attribution_diagnostic
reviewer_role: independent_reviewer
fpa3_passed: true
fpa4_work_doc_authorized: true
fpa4_execution_authorized_by_this_review: false
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# RAL-FPA3 Pre-rule Attribution Diagnostic 审查意见

## 1. Verdict

审查结论：

```text
PASS_READY_FOR_FPA4_WORK_DOC
```

FPA3 已完成 pre-rule attribution diagnostic：只分析了 FPA2 通过的 `replacement_buy`、`sell_timing`、`hold_continuation`，未把 `regime_participation` 作为 positive candidate，且未执行 FPA4、rule sanity、strict_test、规则选择、阈值选择、模型训练或生产链路。

本结论允许 reviewer 写 FPA4 工作文档；不等于执行者可自由扩展候选、自由选阈值或进入 strict_test。

## 2. Findings

### Critical

无 blocking finding。

### High

1. FPA3 产物满足主线输出要求：

```text
feature_bucket_action_delta_attribution.csv
train_validation_direction_audit.csv
candidate_predeclared_rule_hypothesis_audit.csv
oracle_leakage_boundary_audit.csv
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

2. 至少一个 hypothesis 满足 FPA3 通过条件。实际产物中共有 18 个 eligible hypothesis，均标记：

```text
observable_before_action = true
low_dimensional = true
not_oracle_only = true
not_baseline_clone = true
not_cash_only = true
validation_threshold_mining_used = false
```

3. 特征构造来自 action 前可观测字段：

```text
candidate_replacement_rank
holding_days
holding_unrealized_return_bucket
```

`oracle_delta` 仅作为 attribution label 使用，不作为 rule condition。

4. `oracle_leakage_boundary_audit.csv` 显示：

```text
future_return_used_as_feature = false
future_price_used_as_feature = false
post_action_nav_used_as_feature = false
oracle_label_used_as_rule_condition = false
validation_threshold_mining_used = false
strict_test_used = false
```

5. `forbidden_consumer_audit.csv` 显示 FPA4、rule_sanity、executable_rule、strict_test、训练、OrderIntent、target、quantity、broker、provider/frontend/Agent/production 均未出现。

### Medium

1. FPA3 产出了 18 个 eligible hypothesis，但 FPA4 主线限制：

```text
candidate_count <= 5
threshold_versions_per_candidate <= 2
threshold_source 只能来自 train 或 fixed rationale
不得使用 validation mining
不得使用 strict_test
```

因此 FPA4 工作文档必须由 reviewer 预先收敛候选，不能让执行者在 FPA4 自行从 18 个 hypothesis 中筛选。

2. 当前 FPA3 hypothesis 仍是 diagnostic hypothesis，不是 executable rule。FPA4 才允许做少量 predeclared full-path rule sanity，但仍必须 readonly、simulation-only。

### Low

1. `sell_timing + holding_days_060_plus` 在 direction audit 中因样本数不足失败，未进入 candidate hypothesis，处理合理。

## 3. Mainline Compliance

| Requirement | Review |
|---|---|
| 只有 FPA2 通过后进入 FPA3 | pass |
| 只做 pre-rule attribution diagnostic | pass |
| 归因到低维可观测特征 | pass |
| 至少一个 hypothesis 非 oracle-only / 非 baseline clone / 非 cash-only | pass |
| 不分析 regime_participation 作为 positive candidate | pass |
| 不跑 FPA4 | pass |
| 不做 rule sanity | pass |
| 不写 executable rule | pass |
| 不选择阈值 | pass |
| 不使用 strict_test | pass |
| 不训练模型 | pass |
| 不输出 OrderIntent / target / quantity / broker | pass |
| 是否允许写 FPA4 工作文档 | pass |

## 4. Evidence Checked

审查了执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA3_PRE_RULE_ATTRIBUTION_DIAGNOSTIC_EXECUTION_REPORT_CN.md
```

审查了产物目录：

```text
data_tw/experiments/full_path_action_diagnostic/fpa3_pre_rule_attribution_diagnostic/
```

重点核对：

```text
manifest.json
source_fpa2_metric_manifest.json
feature_bucket_action_delta_attribution.csv
train_validation_direction_audit.csv
candidate_predeclared_rule_hypothesis_audit.csv
oracle_leakage_boundary_audit.csv
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

审查了生成脚本：

```text
scripts/build_tw_policy_ral_fpa3_pre_rule_attribution_diagnostic.py
```

脚本语法检查：

```text
python -m py_compile scripts/build_tw_policy_ral_fpa3_pre_rule_attribution_diagnostic.py
```

结果：通过。

## 5. Missing Evidence Or Open Questions

FPA3 无需 repair。

进入 FPA4 前必须明确：

```text
1. FPA4 候选数不得超过 5；
2. 候选和阈值必须在工作文档中预声明；
3. threshold_source 只能来自 train 或 fixed rationale；
4. 不得使用 validation mining；
5. 不得使用 strict_test；
6. FPA4 只做 readonly full-path rule sanity，不做生产集成。
```

## 6. Forbidden Actions Audit

审查未发现越权：

```text
FPA4 run = false
rule_sanity_run = false
executable_rule = false
strict_test_used = false
rule_selection_run = false
threshold_selection_run = false
model_training_run = false
OrderIntent_output = false
target_weight_output = false
target_position_output = false
quantity_or_broker_output = false
production_allowed = false
```

## 7. Next Work Document

下一步进入 FPA4：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA4_PREDECLARED_FULL_PATH_RULE_SANITY_WORK_CN.md
```

FPA4 只能测试少量预声明 full-path baseline-plus rules。不得增加候选，不得做 validation mining，不得 strict_test，不得训练模型，不得输出订单或生产字段。
