---
created_at: 2026-06-23
status: stop_no_predeclared_rule_sanity_pass
phase_reviewed: RAL_FPA4_PREDECLARED_FULL_PATH_RULE_SANITY
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FULL_PATH_BASELINE_PLUS_ACTION_DIAGNOSTIC_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RAL_FPA4_PREDECLARED_FULL_PATH_RULE_SANITY_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RAL_FPA4_PREDECLARED_FULL_PATH_RULE_SANITY_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/full_path_action_diagnostic/fpa4_predeclared_full_path_rule_sanity
reviewer_role: independent_reviewer
fpa4_execution_passed_contract: true
predeclared_rule_sanity_passed: false
route_should_continue_without_new_mainline: false
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# RAL-FPA4 Predeclared Full-path Rule Sanity 审查意见

## 1. Verdict

审查结论：

```text
STOP_NO_PREDECLARED_RULE_SANITY_PASS
```

FPA4 执行合同本身通过：执行者只测试了工作文档预声明的 5 个 candidate / 7 个 threshold versions，未新增候选，未做 validation mining，未使用 strict_test，未训练模型，未触碰生产链路。

但 FPA4 业务 gate 未通过：所有 candidate 的 `candidate_pass=false`。因此当前 RAL-FPA 主线应停止，不能继续调参、扩候选、进入 strict_test、切生产或输出任何策略默认变更。

## 2. Findings

### Critical

1. 没有任何 predeclared candidate 通过 FPA4 pass gate。

`candidate_pass_audit.csv` 显示 7 个 validation threshold version 全部失败：

```text
FPA4_C01 rank_lte_25: candidate_pass=false
FPA4_C01 rank_lte_50: candidate_pass=false
FPA4_C02 unrealized_gain_large: candidate_pass=false
FPA4_C03 unrealized_loss_large: candidate_pass=false
FPA4_C04 unrealized_gain_large: candidate_pass=false
FPA4_C05 holding_days_005_019: candidate_pass=false
FPA4_C05 holding_days_020_059: candidate_pass=false
```

2. 部分 candidate 有 2025 validation 正 excess，但仍未满足完整 FPA4 gate。

例如：

```text
FPA4_C01 rank_lte_25 / rank_lte_50:
  validation excess = 0.25236201
  rolling_oos_mean_excess = 0.00804079
  rolling_oos_median_excess = 0.03890537
  但 2023 window = -0.26714501，且 concentration_gate_status != pass

FPA4_C05 holding_days_020_059:
  validation excess = 0.02334573
  rolling_oos_mean_excess = -0.00552364
  concentration_gate_status != pass
```

主线要求 rolling OOS mean / median、成本换手、集中度、not baseline clone、not cash/no-trade 同时通过，因此不能只凭 validation 正收益通过。

3. `symbol_date_concentration_audit.csv` 未提供可通过的 symbol/date concentration gate。

产物标记：

```text
concentration_scope = rule_sanity_summary_no_symbol_date_pnl_attribution
symbol_date_concentration_status = not_computed_requires_trade_pnl_attribution
concentration_gate_status = review_required
```

执行脚本未将该项误判为通过，`candidate_pass` 条件要求 `concentration_status == "pass"`，因此全部 candidate 均不能通过。

### High

1. Candidate set 与 FPA4 工作文档一致：

```text
candidate_count = 5
threshold_version_count = 7
threshold_versions_per_candidate <= 2
threshold_source = fixed_rationale_from_fpa3_bucket
validation_threshold_mining_used = false
```

2. Replay 产物完整：

```text
full_path_rule_sanity_replay_summary.csv
rolling_oos_excess_audit.csv
transaction_cost_turnover_audit.csv
symbol_date_concentration_audit.csv
baseline_clone_cash_no_trade_audit.csv
candidate_pass_audit.csv
```

3. `baseline_clone_cash_no_trade_audit.csv` 显示所有 candidate 均不是 baseline clone / cash no-trade，但这只能说明没有用无效方式通过，不能抵消收益、rolling OOS 或集中度 gate 的失败。

### Medium

1. FPA4 的失败并不否定 FPA2 oracle upper-bound 或 FPA3 attribution diagnostic 的研究价值；它只说明当前 5 个预声明、可观测、低维规则 sanity 未能通过完整路径 gate。

2. 根据主线，FPA4 失败后不得继续在同一主线内扩大候选或调阈值。若要继续，必须由统筹另开新主线或明确新问题。

### Low

1. `validator_report.json` 的 `ok=true` 表示 FPA4 执行合同和产物完整，不表示 candidate 通过。最终建议已正确给出：

```text
STOP_NO_PREDECLARED_RULE_SANITY_PASS
```

## 3. Mainline Compliance

| Requirement | Review |
|---|---|
| 只有 FPA3 通过后进入 FPA4 | pass |
| candidate_count <= 5 | pass |
| threshold_versions_per_candidate <= 2 | pass |
| threshold_source 来自 train/fixed rationale | pass |
| 不使用 validation mining | pass |
| 不使用 strict_test | pass |
| 不训练模型 | pass |
| 不触碰生产链路 | pass |
| validation excess vs baseline 已计算 | pass |
| rolling OOS mean/median 已计算 | pass |
| cost/turnover audit 已输出 | pass |
| not baseline clone / not cash-no-trade 已检查 | pass |
| symbol/date concentration pass | fail / not established |
| 至少一个 candidate 通过完整 FPA4 gate | fail |
| 是否允许继续调参/扩候选 | no |

## 4. Evidence Checked

审查了执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA4_PREDECLARED_FULL_PATH_RULE_SANITY_EXECUTION_REPORT_CN.md
```

审查了产物目录：

```text
data_tw/experiments/full_path_action_diagnostic/fpa4_predeclared_full_path_rule_sanity/
```

重点核对：

```text
manifest.json
predeclared_candidate_manifest.csv
full_path_rule_sanity_replay_summary.csv
rolling_oos_excess_audit.csv
transaction_cost_turnover_audit.csv
symbol_date_concentration_audit.csv
baseline_clone_cash_no_trade_audit.csv
candidate_pass_audit.csv
oracle_leakage_boundary_audit.csv
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

审查了生成脚本：

```text
scripts/build_tw_policy_ral_fpa4_predeclared_full_path_rule_sanity.py
```

脚本语法检查：

```text
python -m py_compile scripts/build_tw_policy_ral_fpa4_predeclared_full_path_rule_sanity.py
```

结果：通过。

## 5. Missing Evidence Or Open Questions

本阶段无需 repair。当前结论不是因为产物缺失，而是因为预声明 candidate 未通过主线 gate。

不得把以下事项作为 FPA4 repair：

```text
1. 继续增加 candidate；
2. 继续调整 threshold；
3. 使用 validation mining；
4. 使用 strict_test；
5. 把 FPA2 oracle action 直接转成策略；
6. 切换生产默认策略。
```

若统筹认为还要继续研究，必须另开新主线，明确新的动作空间、证据标准和禁止事项。

## 6. Forbidden Actions Audit

审查未发现越权：

```text
strict_test_used = false
model_training_run = false
production_allowed = false
OrderIntent_output = false
target_weight_output = false
target_position_output = false
quantity_or_broker_output = false
provider_publish = false
accepted_latest_switch = false
monitor/frontend/Agent/production = false
```

## 7. Next Work Document

本轮不应给执行者新的 FPA repair 或 FPA5 工作文档。

路线控制结论：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FINAL_CLOSURE_REVIEW_CN.md
```

该 closure 文档关闭当前 RAL-FPA 主线，保留 FPA2/FPA3/FPA4 证据为研究记录，但不授权继续执行。
