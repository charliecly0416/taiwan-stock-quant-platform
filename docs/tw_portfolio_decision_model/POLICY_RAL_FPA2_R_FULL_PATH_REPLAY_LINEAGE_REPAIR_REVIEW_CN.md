---
created_at: 2026-06-23
status: fail_needs_fpa2_metric_reconciliation_repair
phase_reviewed: RAL_FPA2_R_FULL_PATH_REPLAY_LINEAGE_REPAIR
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FULL_PATH_BASELINE_PLUS_ACTION_DIAGNOSTIC_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RAL_FPA2_R_FULL_PATH_REPLAY_LINEAGE_REPAIR_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RAL_FPA2_R_FULL_PATH_REPLAY_LINEAGE_REPAIR_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/full_path_action_diagnostic/fpa2_r_full_path_replay_lineage_repair
reviewer_role: independent_reviewer
fpa2_repair_work_allowed: true
fpa3_authorized: false
fpa4_authorized: false
strict_test_authorized: false
rule_selection_authorized: false
threshold_selection_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# RAL-FPA2-R Full-path Replay Lineage Repair 审查意见

## 1. Verdict

审查结论：

```text
FAIL_NEEDS_FPA2_METRIC_RECONCILIATION_REPAIR
```

本轮修复相较 FPA2 初版有实质进展：

```text
sell_timing / hold_continuation 已补充 pre/post lineage；
pending order lineage 覆盖 replacement_buy / sell_timing / hold_continuation；
未跑 FPA3/FPA4、strict_test、规则选择、阈值选择、训练或生产链路。
```

但仍不能进入 FPA3。当前 `train_validation_direction_audit_repaired.csv`、`transaction_cost_marginal_audit_repaired.csv`、`symbol_date_concentration_audit_repaired.csv` 仍基于事件级 oracle delta 累加，而不是基于 action-space full-path replay 的 `final_equity / net_return_after_fee_tax` 相对 baseline 的同口径差分。

因此，FPA2-R 的 lineage repair 部分可以接受，但 pass gate / metric reconciliation 仍需 repair。

## 2. Findings

### Critical

1. `train_validation_direction_audit_repaired.csv` 仍使用事件级 `net_delta_after_fee_tax` 累加作为 train/validation 方向判断。

脚本证据：

```text
direction_audit(rows_by_space)
```

其中 `rows_by_space` 来自 `upper_rows`，而 sell/hold 的 `upper_rows` 仍在单个 action 处写入：

```text
delta = (delay_close - base_open) * qty
delta = (cont_close - base_open) * qty
net_delta_after_fee_tax = delta
```

这不是 action-space full-path final equity 相对 baseline 的差分。

2. `transaction_cost_marginal_audit_repaired.csv` 仍把 sell_timing / hold_continuation 的 `fee_tax_delta = 0.0`、`turnover_delta = 0.0`、`cash_opportunity_delta = 0.0` 作为 repaired cost audit。虽然完整路径 summary 里已有 `fee_and_tax`、`turnover_proxy`、`final_equity`，但当前 cost audit 没有用这些 summary 与 baseline 做差。

3. validator 没有检查：

```text
action_space_final_equity_excess_vs_baseline
action_space_fee_tax_delta_vs_baseline
action_space_turnover_delta_vs_baseline
direction_audit_uses_full_path_summary
```

因此 `PASS_FPA2_R_FULL_PATH_REPLAY_LINEAGE_REPAIR_READY_FOR_REVIEW` 仍然过宽。

### High

1. `action_space_summary_repaired.csv` 实际已经包含可用于正确判定的 full-path summary：

```text
baseline proxy = regime_participation:
  train net_return_after_fee_tax = 2.41885797
  validation net_return_after_fee_tax = 0.95376753

sell_timing:
  train net_return_after_fee_tax = 8.00302092
  validation net_return_after_fee_tax = 1.20099561

hold_continuation:
  train net_return_after_fee_tax = 6.59814848
  validation net_return_after_fee_tax = 1.52631428

replacement_buy:
  train net_return_after_fee_tax = 27.97338297
  validation net_return_after_fee_tax = 3.76251338
```

这说明 full-path summary 可能支持正上界，但当前正式 pass gate 没有使用该同口径证据。

2. `symbol_date_concentration_audit_repaired.csv` 仍基于事件级 positive delta 贡献率，而不是 full-path excess attribution。它可以作为辅助诊断，但不能单独证明 full-path positive excess 不来自集中贡献。

### Medium

1. lineage 覆盖已明显修复：

```text
full_path_pre_post_state_lineage_repaired.csv:
  replacement_buy = 1308
  sell_timing = 1389
  hold_continuation = 1403
  regime_participation = 1366

pending_order_state_lineage_repaired.csv:
  replacement_buy = 1308
  sell_timing = 1389
  hold_continuation = 1403
  regime_participation = 1366
```

该部分不再是主要 blocker。

2. `oracle_leakage_boundary_audit_repaired.csv` 保持了 oracle-only / not-rule-candidate / not-tradable-strategy / strict_test_used=false，未发现越权。

### Low

1. `regime_participation` 在 repaired summary 中等同 baseline，不提供正上界。后续 FPA3 不应围绕 regime_participation 展开，除非另有归因证据。

## 3. Mainline Compliance

| Requirement | Review |
|---|---|
| 只执行 FPA2-R repair | pass |
| 不跑 FPA3/FPA4 | pass |
| 不使用 strict_test | pass |
| 不做规则选择/阈值选择 | pass |
| 不训练模型 | pass |
| 不输出 OrderIntent / target / quantity / broker | pass |
| sell/hold lineage 覆盖 | pass |
| action-space full-path replay summary 输出 | pass |
| direction audit 使用 full-path summary 差分 | fail |
| transaction cost audit 使用 full-path summary 差分 | fail |
| concentration audit 支持 full-path excess gate | fail / insufficient |
| validator 检查 metric reconciliation | fail |
| 是否可进入 FPA3 | fail, 不允许 |

## 4. Evidence Checked

审查了执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA2_R_FULL_PATH_REPLAY_LINEAGE_REPAIR_EXECUTION_REPORT_CN.md
```

审查了 artifact root：

```text
data_tw/experiments/full_path_action_diagnostic/fpa2_r_full_path_replay_lineage_repair/
```

审查了修复脚本：

```text
scripts/build_tw_policy_ral_fpa2_r_full_path_replay_lineage_repair.py
```

脚本语法检查：

```text
python -m py_compile scripts/build_tw_policy_ral_fpa2_r_full_path_replay_lineage_repair.py
```

结果：通过。

## 5. Missing Evidence Or Open Questions

必须补一轮 metric reconciliation repair：

```text
1. 以 action_space_summary_repaired.csv 为主表，计算每个 action_space 的 full_path_excess_vs_baseline；
2. 重新生成 train_validation_direction_audit，必须使用 net_return_after_fee_tax / final_equity 相对 baseline 的差分；
3. 重新生成 transaction_cost_marginal_audit，必须使用 fee_and_tax / turnover_proxy 相对 baseline 的差分；
4. 重新生成 concentration audit，明确它是 event attribution 辅助项，还是能够支持 full-path excess concentration gate；
5. validator 必须检查 direction/cost/concentration 是否来自 full-path summary，而不是事件级 delta 累加。
```

## 6. Forbidden Actions Audit

`forbidden_consumer_audit.csv` 显示：

```text
FPA3 = not present
FPA4 = not present
strict_test = not present
rule_selection = not present
threshold_selection = not present
model_training = not present
OrderIntent_output = not present
target_weight = not present
target_position = not present
quantity = not present as output
broker_order = not present
provider/latest/monitor/frontend/Agent/production = not present
```

审查未发现越权。

## 7. Next Work Document

下一步仍是 FPA2 repair，不是 FPA3：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA2_R_FULL_PATH_METRIC_RECONCILIATION_REPAIR_WORK_CN.md
```

该 repair 只修正 FPA2-R 的 full-path metric reconciliation / validator 口径，不授权 FPA3、FPA4、strict_test、规则选择、阈值选择、模型训练或生产链路。
