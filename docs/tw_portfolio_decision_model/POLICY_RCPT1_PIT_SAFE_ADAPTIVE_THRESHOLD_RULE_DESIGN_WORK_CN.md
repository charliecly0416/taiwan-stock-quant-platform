---
created_at: 2026-06-24
status: work_order_for_rcpt1_pit_safe_adaptive_threshold_rule_design
phase: RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN
route: RCP_T_SCORE_RANK_REGIME_ADAPTIVE_THRESHOLD_DISCOVERY
parent_t0_review: docs/tw_portfolio_decision_model/POLICY_RCPT0_R_CANDIDATE_HYPOTHESIS_CONSISTENCY_REPAIR_REVIEW_CN.md
t0_artifact_root: data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery
rcp3a_artifact_root: data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate
output_root: data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design
execution_report: docs/tw_portfolio_decision_model/POLICY_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_EXECUTION_REPORT_CN.md
review_report: docs/tw_portfolio_decision_model/POLICY_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_REVIEW_CN.md
policy_replay_authorized: false
risk_control_replay_authorized: false
threshold_design_authorized: true
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

# RCPT1 PIT-safe Adaptive Threshold Rule Design 工作文档

## 1. 本轮定位

本轮执行：

```text
RCPT1: PIT-safe Adaptive Threshold Rule Design
```

目标是把 RCP-T0 的诊断发现转成下一阶段可回放的预声明自适应阈值规则合同。

本轮只做：

```text
规则设计
阈值来源合同
PIT-safe feature contract
候选数量控制
anti-overfit guardrail
cash/no-trade guardrail
T2 replay gate 设计
```

本轮不做：

```text
policy replay
risk-control replay
训练模型
strict_test
生产/default/provider/frontend/Agent/订单链路集成
```

## 2. 输入事实

T0 修复后确认：

```text
H01:
risk_off AND 0.4 <= raw_score < 0.8
sample_count = 206
mean_future_return_5d = 0.01473884
mean_future_return_20d = 0.02341612
median_future_return_20d = 0.01420901
win_rate_20d = 0.51941748
```

同时确认：

```text
H09 raw_score >= 0.8 sample_count = 9
H09 只能作为 reference-only / insufficient sample
不能写成 T1 独立硬阈值规则。
```

重要限制：

```text
T0 是 2022 downturn validation diagnostic，不是 strict OOS；
T0 的 future return label 只能用于诊断；
T1 不能把 2022 最优阈值直接写成生产策略。
```

## 3. 必须读取

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT0_R_CANDIDATE_HYPOTHESIS_CONSISTENCY_REPAIR_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT0_SCORE_RANK_REGIME_THRESHOLD_DISCOVERY_WORK_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/candidate_threshold_hypotheses.csv
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/pit_safe_candidate_filter.csv
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/score_04_08_vs_08plus_audit.csv
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/score_percentile_band_forward_return_by_regime.csv
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/rank_change_forward_return_surface.csv
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/score_delta_forward_return_surface.csv
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/anti_overfit_and_label_leakage_audit.csv
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/market_feature_by_signal_date.csv
```

必须参考合同：

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
```

## 4. 输出目录

所有本轮产物写入：

```text
data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design/
```

执行报告写入：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_EXECUTION_REPORT_CN.md
```

## 5. 必须输出文件

必须输出：

```text
manifest.json
adaptive_threshold_rule_design_manifest.json
predeclared_adaptive_threshold_rules.csv
threshold_source_contract.csv
pit_feature_contract.csv
rule_dependency_contract.csv
candidate_from_t0_mapping.csv
small_sample_exclusion_audit.csv
anti_overfit_and_no_2022_direct_fit_audit.csv
cash_no_trade_guardrail_contract.csv
t2_replay_metric_contract.csv
diagnostic_semantics_audit.json
forbidden_action_audit.csv
validator_report.json
diagnostic_findings.md
```

## 6. 规则设计要求

规则数量建议 3-6 条，不得无界 grid search。

必须至少覆盖：

```text
1. H01/H08 raw-score mid-high band in risk-off；
2. score percentile fallback，避免 raw_score 尺度不稳；
3. rank_change or score_delta trend filter；
4. participation/cash guardrail，避免 RCP3 fixed rules 的 all-cash failure。
```

建议候选：

### T1_RULE_01 Risk-off Raw-score Mid-band Buy Gate

机制：

```text
market_risk_off_ma60 = true 时，
baseline buy 只允许 raw_score 落在 [0.4, 0.8) 且 rank 足够靠前。
```

阈值来源：

```text
0.4/0.8 来自 T0 exploratory hypothesis H01；
T2 必须标记为 diagnostic-derived threshold，不可称为 strict OOS。
```

约束：

```text
不得用 raw_score >= 0.8 作为独立反向规则，因为 H09 n=9。
```

### T1_RULE_02 Risk-off Percentile Mid-high Gate

机制：

```text
market_risk_off_ma60 = true 时，
baseline buy 只允许 score_percentile_by_date 落在 top_20_40 或 top_10_40 区间。
```

目的：

```text
降低 raw_score 尺度依赖。
```

阈值来源：

```text
T0 percentile surface + fixed bounded candidate。
```

### T1_RULE_03 Risk-off Mid-band + Rank Improvement Gate

机制：

```text
risk_off 中要求 raw_score mid-band 或 percentile mid-high，
并且 rank_change_3d/5d <= 0 或 <= -10。
```

目的：

```text
避免买入静态高分但趋势恶化标的。
```

### T1_RULE_04 Adaptive Participation Cap

机制：

```text
risk_off 中不 all-cash，而是限制每日新买数量或持仓目标下限；
normal/risk_on 中回到 baseline。
```

目的：

```text
防止 RCP3 RULE_01/03/05 那类高现金失败。
```

### T1_RULE_05 Sell-side Weak Rank Deterioration

机制：

```text
只在持仓 rank 恶化且不满足 mid-band/trend 条件时提前卖出；
每日最多一支。
```

目的：

```text
结合 rank deterioration，而不是单纯 MA risk-off 卖出。
```

## 7. 每条规则字段

`predeclared_adaptive_threshold_rules.csv` 每条至少包含：

```text
rule_id
rule_name
source_hypotheses
rule_family
market_regime_condition
buy_condition
sell_condition
hold_condition
threshold_values
threshold_source
pit_safe_inputs
uses_future_return_label
uses_2022_direct_fit
uses_small_sample_hypothesis
expected_effect
cash_participation_guardrail
t2_replay_allowed
notes
```

必须保证：

```text
uses_future_return_label = false
uses_small_sample_hypothesis = false
```

如某条规则引用 H09，只能写在 notes / supporting observation，不得作为 trigger。

## 8. Threshold Source Contract

`threshold_source_contract.csv` 必须逐条记录：

```text
rule_id
threshold_name
threshold_value
source_type
source_artifact
source_hypothesis
is_2022_diagnostic_derived
requires_t2_recheck
can_be_used_in_production
notes
```

允许 source_type：

```text
T0_exploratory_diagnostic
fixed_rationale
prior_window_distribution_required_for_future
```

禁止：

```text
strict_oos_claim
production_calibrated
2022_grid_search_best
future_return_label_inference_feature
```

## 9. PIT Feature Contract

`pit_feature_contract.csv` 必须列出：

```text
feature_name
source
available_at
derivation
uses_future_data
uses_future_return_label
needed_by_rule_ids
blocks_t2_if_missing
notes
```

至少包括：

```text
raw_score
score_percentile_by_date
rank
rank_change_3d
rank_change_5d
score_delta_3d
score_delta_5d
market_risk_off_ma60
current_holdings
holding_rank
holding_days
cash
holding_count
```

## 10. Cash / Participation Guardrail

`cash_no_trade_guardrail_contract.csv` 必须继承 RCP3 gate，并针对 threshold rules 增加：

```text
min_participation_rate = 0.50
max_average_cash_rate = 0.60
max_no_position_days = 20
minimum_buy_count_relative_to_baseline
minimum_holding_count
no_all_cash
no_sell_only_policy
```

T2 规则不得仅靠高现金通过。

## 11. T2 Replay Metric Contract

`t2_replay_metric_contract.csv` 必须冻结下一阶段评价指标：

```text
net_return_after_fee_tax
max_drawdown
turnover_proxy
fee_and_tax
participation_rate
average_cash_rate
action_count
buy_count
sell_count
worst_month_return
monthly_win_rate
concentration
diagnostic_semantics
```

通过原则：

```text
不能单看收益；
不能单看回撤；
必须同时满足 cash/no-trade、fee/tax、turnover、concentration。
```

## 12. Validator

`validator_report.json` 必须包含：

```text
phase
status
pass
required_files_status
rule_count
rule_design_status
threshold_source_status
pit_feature_status
small_sample_exclusion_status
anti_overfit_status
cash_guardrail_status
t2_metric_contract_status
diagnostic_semantics_status
forbidden_actions_status
t2_authorizable
recommended_next_step
```

允许的 recommended_next_step：

```text
PASS_READY_FOR_RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY_WORK_DOC
FAIL_NEEDS_RCPT1_REPAIR
STOP_THRESHOLD_RULE_DESIGN_UNSAFE
```

## 13. 审查 Gate

审查者 verdict 只能为：

```text
PASS_READY_FOR_RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY_WORK_DOC
FAIL_NEEDS_RCPT1_REPAIR
STOP_THRESHOLD_RULE_DESIGN_UNSAFE
STOP_SCOPE_OR_LEAKAGE_VIOLATION
```

审查重点：

```text
1. 是否只做规则设计，不做 replay；
2. H01/H08 是否正确使用；
3. H09 是否仅 reference-only；
4. future return label 是否没有进入规则输入；
5. 阈值来源是否标记为 T0 diagnostic-derived，不冒充 strict OOS；
6. 是否有 cash/no-trade guardrail；
7. 是否可进入 T2 replay sanity。
```

## 14. 第一执行者指令

```text
请按 docs/tw_portfolio_decision_model/POLICY_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_WORK_CN.md 执行 RCPT1。
只做 PIT-safe adaptive threshold rule design，不运行 policy replay，不运行 risk-control replay，不训练，不 strict_test，不改生产链路，不输出订单/目标仓位/数量指令。
必须把 H01/H08 转成可回放的候选规则，同时把 H09 标为 reference-only，不得作为独立硬阈值。
完成后输出 data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design/ 下全部必需文件，并提交执行报告。
```

## 15. 第一审查者指令

```text
请按 docs/tw_portfolio_decision_model/POLICY_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_WORK_CN.md 审查 RCPT1。
重点审查是否无 replay/训练/生产越权、阈值来源是否正确、H09 是否排除、PIT feature/cash guardrail/T2 metric contract 是否完整。
通过后只授权 RCPT2 adaptive threshold replay sanity，不授权 strict_test 或生产化。
```
