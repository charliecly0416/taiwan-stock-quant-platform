---
created_at: 2026-06-23
status: fail_needs_fpa2_repair
phase_reviewed: RAL_FPA2_ORACLE_UPPER_BOUND_DIAGNOSTIC
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FULL_PATH_BASELINE_PLUS_ACTION_DIAGNOSTIC_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RAL_FPA2_ORACLE_UPPER_BOUND_DIAGNOSTIC_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RAL_FPA2_ORACLE_UPPER_BOUND_DIAGNOSTIC_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/full_path_action_diagnostic/fpa2_oracle_upper_bound
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

# RAL-FPA2 Oracle Upper-bound Diagnostic 审查意见

## 1. Verdict

审查结论：

```text
FAIL_NEEDS_FPA2_REPAIR
```

FPA2 执行没有越权：未跑 FPA3/FPA4、未使用 strict_test、未做规则选择/阈值选择、未训练模型、未输出 OrderIntent / target / quantity / broker，也未触碰生产链路。

但本轮不能按执行报告建议进入 FPA3。原因是：

```text
sell_timing 和 hold_continuation 的 upper-bound 不是 full-path replay；
它们是 baseline event scan 上的局部未来价差估算。
```

这违反 FPA2 工作文档的核心要求：

```text
必须使用 full-path replay，不得只算单笔 local delta；
必须持久化被改动 sell / hold 的 pre_action_state / post_action_state / pending_order_state / cash / holdings / NAV path。
```

## 2. Findings

### Critical

1. `sell_timing_upper_bound.csv` 与 `hold_continuation_upper_bound.csv` 不满足 full-path replay 要求。

脚本 `scripts/build_tw_policy_ral_fpa2_oracle_upper_bound_diagnostic.py` 中，`baseline_event_rows()` 对 sell/hold 只是：

```text
sell_timing: (delay_close - base_open) * qty
hold_continuation: (cont_close - base_open) * qty
```

并没有重放后续 cash、holding_count、pending orders、replacement capacity、fee/tax timing、NAV path。因此当前 sell/hold positive upper-bound 不能作为进入 FPA3 的合格证据。

2. `full_path_pre_post_state_lineage.csv` 与 `pending_order_state_lineage.csv` 只覆盖 `replacement_buy`。

审查命令显示：

```text
full_path_pre_post_state_lineage.csv:
  replacement_buy = 1308 rows
  sell_timing = 0 rows
  hold_continuation = 0 rows

pending_order_state_lineage.csv:
  replacement_buy = 1308 rows
  sell_timing = 0 rows
  hold_continuation = 0 rows
```

这说明 FPA1 审查要求的 sell/hold pre/post state lineage 没有被持久化。

### High

1. `transaction_cost_marginal_audit.csv` 中 sell_timing 与 hold_continuation 的 `fee_tax_delta = 0.0`、`turnover_delta = 0.0`，当前没有证明这是完整路径下的真实成本差异。对于卖出延后或继续持有，费用税时点、现金可用性、后续买入机会和最终 NAV 都会变化，不能用 0 直接代表成本无变化。

2. `validator_report.json` 的 `full_path_replay_used=true` 说明写得过宽。实际只有 replacement oracle 使用了 portfolio cash/holdings/pending replay path；sell_timing 和 hold_continuation 没有同等 full-path replay。

### Medium

1. `replacement_buy` 部分有较完整的组合路径循环、replacement_candidate_lineage 和 pending_order_state_lineage，可作为 FPA2-R 的可保留 partial evidence，但仍应在 repair 中重新和 sell/hold 同口径汇总。

2. `oracle_leakage_boundary_audit.csv` 合规标记了 oracle-only / not-rule-candidate / not-tradable-strategy，未发现 strict_test 或规则候选越权。

### Low

1. `regime_participation` 为 0 且 `fail_no_stable_positive_upper_bound`，不构成本轮失败原因；它只是没有提供进入 FPA3 的正证据。

## 3. Mainline Compliance

| Requirement | Review |
|---|---|
| 只执行 FPA2 oracle diagnostic | pass |
| 不写规则 | pass |
| 不做 threshold selection | pass |
| 不使用 strict_test | pass |
| 不训练模型 | pass |
| 不触碰生产链路 | pass |
| forbidden consumer audit | pass |
| oracle leakage boundary audit | pass |
| replacement_buy full-path evidence | pass with review |
| sell_timing full-path replay | fail |
| hold_continuation full-path replay | fail |
| pre/post state lineage for sell_timing | fail |
| pre/post state lineage for hold_continuation | fail |
| transaction cost path audit for sell/hold | fail |
| 是否可进入 FPA3 | fail, 不允许 |

## 4. Evidence Checked

审查了执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA2_ORACLE_UPPER_BOUND_DIAGNOSTIC_EXECUTION_REPORT_CN.md
```

审查了 artifact root：

```text
data_tw/experiments/full_path_action_diagnostic/fpa2_oracle_upper_bound/
```

关键证据：

```text
validator_report.json:
  ok = true
  final_recommendation = READY_FOR_REVIEWER_TO_CONSIDER_FPA3_WORK_DOC
```

审查不接受该 final_recommendation，因为 validator 没有区分各 action_space 是否都满足 full-path replay。

`train_validation_direction_audit.csv` 显示：

```text
replacement_buy: train positive, validation positive
sell_timing: train positive, validation positive
hold_continuation: train positive, validation positive
regime_participation: no stable positive upper-bound
```

但 sell/hold 的正值来自局部事件价差，不满足 full-path gate。

脚本语法检查：

```text
python -m py_compile scripts/build_tw_policy_ral_fpa2_oracle_upper_bound_diagnostic.py
```

结果：通过。

## 5. Missing Evidence Or Open Questions

必须修复后重审：

```text
1. sell_timing 必须做 full-path replay；
2. hold_continuation 必须做 full-path replay；
3. sell/hold 必须输出 pre_action_state / post_action_state / pending_order_state lineage；
4. sell/hold 必须重新计算 fee_tax_delta / turnover_delta / cash opportunity / NAV path delta；
5. validator 必须按 action_space 分别检查 full_path_replay_used，而不是全局通过。
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

下一步应执行 FPA2 repair，而不是进入 FPA3：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA2_R_FULL_PATH_REPLAY_LINEAGE_REPAIR_WORK_CN.md
```

FPA2-R 只修复 FPA2 的 full-path replay / lineage / validator 口径，不授权 FPA3、FPA4、strict_test、规则选择、阈值选择、模型训练或生产链路。
