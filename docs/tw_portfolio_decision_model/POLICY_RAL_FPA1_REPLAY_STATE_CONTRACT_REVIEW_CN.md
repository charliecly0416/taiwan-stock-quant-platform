---
created_at: 2026-06-23
status: pass_ready_for_fpa2_work_doc
phase_reviewed: RAL_FPA1_REPLAY_STATE_CONTRACT_FREEZE
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FULL_PATH_BASELINE_PLUS_ACTION_DIAGNOSTIC_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RAL_FPA1_REPLAY_STATE_CONTRACT_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RAL_FPA1_REPLAY_STATE_CONTRACT_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract
reviewer_role: independent_reviewer
fpa2_work_doc_allowed: true
fpa2_execution_authorized_by_this_review: false
fpa3_authorized: false
fpa4_authorized: false
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# RAL-FPA1 Replay State Contract Freeze 审查意见

## 1. Verdict

审查结论：

```text
PASS_READY_FOR_FPA2_WORK_DOC
```

FPA1 执行符合新主线：本轮只冻结 full-path readonly replay state contract，未跑 FPA2 oracle、未跑规则、未做阈值选择、未使用 strict_test、未训练模型、未输出 OrderIntent / target / quantity / broker，也未触碰 provider/latest/monitor/frontend/Agent/production。

本审查只允许审查者撰写 FPA2 工作文档；不自动授权执行者直接运行 FPA2。

## 2. Findings

### Critical

无。

### High

无。

### Medium

1. Contract 覆盖了主线要求的 full-path 动作空间：

```text
replacement_buy
sell_timing_advance
sell_timing_delay
hold_continuation
regime_participation_adjustment
transaction_cost_marginal_filter
```

2. `required_state_field_audit.csv` 对时间、信号、组合、pending execution、费用税、换手、regime、流动性、缺价状态均给出了来源、PIT-safe、simulation-only 和 production boundary 标注。

3. 执行者诚实标记了 FPA2 前必须补的持久化缺口：

```text
GAP_FPA2_PRE_POST_PATH_SNAPSHOTS
GAP_ENTRY_DATE_PERSISTENCE
GAP_REPLACEMENT_CANDIDATE_LINEAGE
```

这些缺口不阻断 FPA1 contract freeze，但必须写入 FPA2 工作文档，作为 FPA2 执行前/执行中的强制输出要求。

### Low

1. FPA1 contract 是 schema/contract 级产物，不证明 FPA2 upper-bound 存在正收益。后续不得把 FPA1 pass 解读为策略有效。
2. `quantity/cash/nav/execution_price` 在 contract 中出现是合理的内部 replay accounting 字段，但 FPA2 仍必须继续审计这些字段不被输出为 OrderIntent、target、broker 或生产字段。

## 3. Mainline Compliance

| Requirement | Review |
|---|---|
| 只执行 FPA1 contract freeze | pass |
| contract 支持 replacement buy | pass |
| contract 支持 sell timing | pass |
| contract 支持 hold continuation | pass |
| contract 支持 regime participation | pass |
| transaction-cost marginal state 已覆盖 | pass |
| required state field audit 已输出 | pass |
| action space contract 已输出 | pass |
| forbidden output audit 已输出 | pass |
| validator_report.json ok=true | pass |
| 缺失字段被诚实标记 | pass |
| FPA2 oracle 未执行 | pass |
| FPA3/FPA4 未执行 | pass |
| strict_test 未使用 | pass |
| model training 未执行 | pass |
| OrderIntent / target / quantity / broker 未输出 | pass |
| provider/latest/monitor/frontend/Agent/production 未触碰 | pass |

## 4. Evidence Checked

审查了执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA1_REPLAY_STATE_CONTRACT_EXECUTION_REPORT_CN.md
```

审查了 artifact root：

```text
data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/
```

关键证据：

```text
validator_report.json:
  ok = true
  status = PASS_FPA1_REPLAY_STATE_CONTRACT_READY_FOR_REVIEW
  failed_count = 0
  final_recommendation = READY_FOR_REVIEWER_TO_CONSIDER_FPA2_WORK_DOC
  fpa2_oracle_run = false
  fpa3_attribution_run = false
  fpa4_rule_sanity_run = false
  strict_test_used = false
  model_training_run = false
  production_allowed = false
  order_intent_output = false
  target_weight_output = false
  target_position_output = false
  quantity_or_broker_output = false
```

`forbidden_output_audit.csv` 显示所有禁用项均为：

```text
allowed_in_fpa1 = false
present_in_outputs = false
```

脚本语法检查：

```text
python -m py_compile scripts/build_tw_policy_ral_fpa1_replay_state_contract.py
```

结果：通过。

## 5. Missing Evidence Or Open Questions

无阻断 FPA2 工作文档的缺口。

FPA2 工作文档必须继承以下前置要求：

```text
1. FPA2 simulator 必须持久化 pre_action_state / post_action_state / pending_order_state / cash / holdings / NAV；
2. FPA2 必须持久化 entry_date 与 exact holding_days；
3. FPA2 必须持久化 replacement candidate slate、excluded baseline candidate、selected replacement candidate 和 reason namespace；
4. 这些字段只能作为 readonly simulation diagnostics，不得成为 OrderIntent、target、quantity、broker 或 production output。
```

## 6. Next Work Document

允许撰写下一步工作文档：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA2_ORACLE_UPPER_BOUND_DIAGNOSTIC_WORK_CN.md
```

该工作文档只能授权 FPA2 oracle-style upper-bound diagnostic。

不得授权：

```text
FPA3 attribution
FPA4 rule sanity
strict_test
规则选择
阈值选择
模型训练
OrderIntent / target / quantity / broker
provider/latest/monitor/frontend/Agent/production
```

## 7. Command For Executor

建议下一步执行者命令：

```text
请严格阅读 FPA 主线、FPA1 审查意见和 FPA2 工作文档。
只执行 FPA2 Oracle-style Upper-bound Diagnostic。
不得写规则、不得选择阈值、不得 strict_test、不得训练模型、不得输出订单/target/quantity/broker、不得触碰生产链路。
```
