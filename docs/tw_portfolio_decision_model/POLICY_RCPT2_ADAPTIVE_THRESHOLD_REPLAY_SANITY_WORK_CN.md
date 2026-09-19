---
created_at: 2026-06-24
status: work_order_for_rcpt2_adaptive_threshold_replay_sanity
phase: RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY
route: RCP_T_SCORE_RANK_REGIME_ADAPTIVE_THRESHOLD_DISCOVERY
parent_t1_review: docs/tw_portfolio_decision_model/POLICY_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_REVIEW_CN.md
t1_artifact_root: data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design
signal_artifact_root: data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract
market_feature_artifact_root: data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate
baseline_artifact_root: data_tw/experiments/risk_control_policy_2022/rcp1b_diagnostic_baseline_replay_audit
output_root: data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity
execution_report: docs/tw_portfolio_decision_model/POLICY_RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY_EXECUTION_REPORT_CN.md
review_report: docs/tw_portfolio_decision_model/POLICY_RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY_REVIEW_CN.md
adaptive_threshold_replay_authorized: true
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity_instruction: true
---

# RCPT2 Adaptive Threshold Replay Sanity 工作文档

## 1. 本轮定位

本轮执行：

```text
RCPT2: Adaptive Threshold Replay Sanity
```

目标是在 2022 downturn validation diagnostic 窗口中，只读回放 RCPT1 冻结的 5 条 adaptive threshold 规则，判断是否存在可接受的风险收益 tradeoff。

本轮允许：

```text
simulation-only replay of predeclared RCPT1 rules
baseline comparison
cash/no-trade gate
turnover/fee/tax gate
concentration audit
diagnostic-only conclusion
```

本轮不允许：

```text
strict_test
训练模型
新增规则
调阈值
用 2022 replay 结果选择/扩展规则
生产/default/provider/frontend/Agent/订单链路集成
OrderIntent / target_weight / target_position / quantity_instruction
```

## 2. 必须读取

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_REVIEW_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design/predeclared_adaptive_threshold_rules.csv
data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design/threshold_source_contract.csv
data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design/pit_feature_contract.csv
data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design/cash_no_trade_guardrail_contract.csv
data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design/t2_replay_metric_contract.csv
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/diagnostic_model_signal.csv
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/market_feature_by_signal_date.csv
data_tw/experiments/risk_control_policy_2022/rcp1b_diagnostic_baseline_replay_audit/baseline_summary.csv
```

可复用：

```text
scripts/run_tw_policy_action_model_pa1.py
scripts/run_tw_policy_rcp3_risk_control_replay_sanity.py
```

但必须明确：

```text
复用 replay accounting engine 不代表训练 policy；
actions.csv 是 internal replay ledger，不是 OrderIntent 或真实订单建议。
```

## 3. 允许回放的规则

只能回放 RCPT1 冻结规则：

```text
RCPT1_RULE_01
RCPT1_RULE_02
RCPT1_RULE_03
RCPT1_RULE_04
RCPT1_RULE_05
```

规则解释必须以 RCPT1 已冻结的 `threshold_values` / `threshold_source_contract.csv` 为准。

特别注意：

```text
RCPT1_RULE_02 只能按已冻结的 score_percentile_floor=0.10 / score_percentile_ceiling=0.40 / primary_band=top_20_40_percent 回放。
不得因为 H03 表述，把规则临时扩展到未声明的 top_40_60_percent。
```

H09：

```text
只能 reference-only；
不得作为 rule trigger；
不得反向写成 avoid raw_score >= 0.8 的硬规则。
```

## 4. 输出目录

所有产物写入：

```text
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/
```

执行报告写入：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY_EXECUTION_REPORT_CN.md
```

## 5. 必须输出文件

必须输出：

```text
manifest.json
replay_source_manifest.json
adaptive_rule_replay_summary.csv
adaptive_rule_baseline_comparison.csv
adaptive_rule_gate_decision.csv
risk_metric_summary_by_rule.csv
cash_no_trade_audit_by_rule.csv
turnover_fee_tax_audit_by_rule.csv
action_count_audit_by_rule.csv
concentration_audit_by_rule.csv
threshold_contract_compliance_audit.csv
diagnostic_semantics_audit.json
anti_overfit_and_no_2022_replay_tuning_audit.csv
forbidden_action_audit.csv
validator_report.json
diagnostic_findings.md
```

每条 replayed rule 必须输出：

```text
rules/{rule_id}/summary.csv
rules/{rule_id}/nav.csv
rules/{rule_id}/actions.csv
rules/{rule_id}/position_snapshots.csv
rules/{rule_id}/rule_trigger_ledger.csv
rules/{rule_id}/execution_audit.csv
```

## 6. Replay 行为合同

### RCPT1_RULE_01

```text
if market_risk_off_ma60:
  allow baseline buy only when 0.4 <= raw_score < 0.8 and rank <= 5
else:
  baseline behavior
sells:
  baseline sell logic unchanged
```

### RCPT1_RULE_02

```text
if market_risk_off_ma60:
  allow baseline buy only when 0.10 <= score_percentile_by_date <= 0.40
else:
  baseline behavior
```

说明：

```text
score_percentile_by_date 的方向必须由 RCPT0/RCPT1 产物确认；
如果 percentile 定义为 rank percentile，执行者必须在 threshold_contract_compliance_audit.csv 中说明方向。
不得临时改成 top_40_60_percent。
```

### RCPT1_RULE_03

```text
if market_risk_off_ma60:
  allow baseline buy only when:
    (RCPT1_RULE_01 mid-band condition OR RCPT1_RULE_02 percentile condition)
    AND (rank_change_5d <= -10 OR rank_change_3d <= -10 OR score_delta_5d > 0)
else:
  baseline behavior
```

### RCPT1_RULE_04

```text
cash/participation guardrail:
  no all-cash
  no sell-only policy
  min participation / average cash gates are evaluated after replay
  if no qualifying replacement exists and blocking buy would violate minimum holding guardrail,
    preserve current holding rather than force sell-only / all-cash.
```

RCPT1_RULE_04 可作为独立 diagnostic guardrail replay，也可作为 acceptance gate applied to all candidates；执行者必须在 source manifest 说明采用方式。

### RCPT1_RULE_05

```text
if market_risk_off_ma60:
  allow at most one early sell per day when:
    holding no longer satisfies mid-band/trend support
    AND rank_change_5d > 0 OR rank_change_3d > 0
    AND sell does not violate participation guardrail
buy side:
  governed by RCPT1_RULE_01/02/03 if combined, otherwise baseline buy path
```

如果独立回放 RCPT1_RULE_05 的语义不清，执行者必须标记 `NOT_REPLAYED_REQUIRES_REPAIR`，不得临时改规则。

## 7. Gate 与判定

`adaptive_rule_gate_decision.csv` 必须逐条输出：

```text
rule_id
net_return_gate
max_drawdown_gate
turnover_gate
fee_tax_gate
cash_no_trade_gate
participation_gate
concentration_gate
threshold_contract_gate
diagnostic_semantics_gate
overall_gate
decision
notes
```

最低要求：

```text
max_drawdown improvement >= 5 percentage points OR relative improvement >= 15%
net_return_after_fee_tax deterioration <= 5 percentage points vs baseline
participation_rate >= 0.50
average_cash_rate <= 0.60
turnover_proxy / fee_and_tax not worse unless net and drawdown both materially improve
no all-cash / no no-trade
concentration pass
threshold contract compliance pass
diagnostic semantics preserved
```

允许 decision：

```text
PASS_CANDIDATE_FOR_RCPT3_CLOSURE_REVIEW
FAIL_NO_RISK_REWARD_TRADEOFF
FAIL_CASH_OR_NO_TRADE
FAIL_COST_OR_TURNOVER
FAIL_THRESHOLD_CONTRACT_VIOLATION
FAIL_IMPLEMENTATION_OR_DATA
NOT_REPLAYED_REQUIRES_REPAIR
```

## 8. validator_report.json

必须包含：

```text
phase
status
pass
required_files_status
t1_contract_status
replayed_rule_count
not_replayed_rule_count
any_rule_pass
best_rule_id
threshold_contract_status
cash_no_trade_status
concentration_status
diagnostic_semantics_status
anti_overfit_status
forbidden_actions_status
repair_required
recommended_next_step
```

允许 recommended_next_step：

```text
PASS_READY_FOR_RCPT3_CLOSURE_REVIEW_WORK_DOC
FAIL_NEEDS_RCPT2_REPAIR
STOP_NO_ADAPTIVE_THRESHOLD_RULE_HAS_RISK_REWARD_TRADEOFF
```

## 9. 禁止事项

本轮禁止：

```text
strict_test
训练
新增规则或阈值
用 2022 replay 结果选择/调阈值
把 H09 写成硬触发
provider publish / accepted latest switch
frontend / Agent / monitor 集成
broker / quick-trade / real order
OrderIntentArtifact
target_weight
target_position
quantity_instruction
```

## 10. 审查 Gate

审查者 verdict 只能为：

```text
PASS_READY_FOR_RCPT3_CLOSURE_REVIEW_WORK_DOC
FAIL_NEEDS_RCPT2_REPAIR
STOP_NO_ADAPTIVE_THRESHOLD_RULE_HAS_RISK_REWARD_TRADEOFF
STOP_REPLAY_SCOPE_OR_THRESHOLD_CONTRACT_VIOLATION
```

审查重点：

```text
1. 是否只回放 RCPT1 冻结规则；
2. RCPT1_RULE_02 是否未被 H03 噪音扩展；
3. H09 是否未作为 trigger；
4. replay accounting 是否与 RCP1B baseline 可比；
5. cash/no-trade、turnover/fee/tax、concentration 是否通过；
6. 是否没有 replay 后调参或新增规则；
7. 是否没有生产或订单链路越权。
```

## 11. 第一执行者指令

```text
请按 docs/tw_portfolio_decision_model/POLICY_RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY_WORK_CN.md 执行 RCPT2。
只回放 RCPT1 预声明 adaptive threshold rules，不训练，不 strict_test，不新增或调规则，不用 2022 replay 结果筛选/改阈值，不改生产链路，不输出订单/目标仓位/数量指令。
特别注意 RCPT1_RULE_02 必须按冻结 threshold_values 回放，不能因 H03 表述扩展到未声明区间；H09 只能 reference-only。
完成后输出 data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/ 下全部必需文件，并提交执行报告。
```

## 12. 第一审查者指令

```text
请按 docs/tw_portfolio_decision_model/POLICY_RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY_WORK_CN.md 审查 RCPT2 产物。
重点审查 replay scope、threshold contract compliance、H09 排除、cash/no-trade、fee/tax、turnover、concentration、diagnostic-only 语义和 forbidden actions。
通过后只授权 RCPT3 closure review，不授权 strict_test 或生产化。
```
