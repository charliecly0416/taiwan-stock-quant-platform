---
created_at: 2026-06-24
status: work_order_for_rcpt0_score_rank_regime_threshold_discovery
phase: RCPT0_SCORE_RANK_REGIME_THRESHOLD_DISCOVERY
route: RCP_T_SCORE_RANK_REGIME_ADAPTIVE_THRESHOLD_DISCOVERY
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RCP_RISK_CONTROL_POLICY_2022_DOWNTURN_MAINLINE_CN.md
rcp3_review: docs/tw_portfolio_decision_model/POLICY_RCP3_RISK_CONTROL_REPLAY_SANITY_REVIEW_CN.md
rcp3a_artifact_root: data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate
signal_artifact_root: data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract
output_root: data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery
execution_report: docs/tw_portfolio_decision_model/POLICY_RCPT0_SCORE_RANK_REGIME_THRESHOLD_DISCOVERY_EXECUTION_REPORT_CN.md
review_report: docs/tw_portfolio_decision_model/POLICY_RCPT0_SCORE_RANK_REGIME_THRESHOLD_DISCOVERY_REVIEW_CN.md
policy_replay_authorized: false
risk_control_replay_authorized: false
threshold_discovery_authorized: true
future_return_label_diagnostic_authorized: true
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

# RCP-T0 Score / Rank / Regime Threshold Discovery 工作文档

## 1. 本轮定位

本轮开启新支线：

```text
RCP-T: Score / Rank / Regime Adaptive Threshold Discovery
```

本轮阶段：

```text
RCP-T0: threshold discovery diagnostic
```

目标是验证一个关键现象是否真实存在：

```text
在大盘下跌 / risk-off 时，
qlib score 的最高区间未必对应最好未来收益；
中高 score 区间，例如 0.4-0.8，可能优于 0.8+。
```

同时诊断：

```text
score raw band
score percentile band
rank band
rank_change_1d/3d/5d
score_delta_1d/3d/5d
market regime
```

与未来收益之间的关系。

本轮只做 exploratory diagnostic，不做 policy replay，不做策略通过判定。

## 2. 为什么需要本支线

RCP3 固定规则失败的底层原因：

```text
1. 粗 risk-off gate 可改善亏损和回撤，但把 participation / cash 拉得过低；
2. 保守 gate 保住参与度，但几乎 no-op；
3. 二值大盘规则无法捕捉 qlib score/rank 在不同市场状态下的非线性。
```

因此下一步应分析：

```text
在 risk-off 中，哪些 score/rank/trend 区间的未来收益更好；
是否存在“不要买最高 score，而买中高 score / rank 改善”的结构；
是否可形成下一阶段 PIT-safe 自适应阈值规则。
```

## 3. 本轮允许与禁止

允许：

```text
1. 构建 diagnostic forward-return label；
2. 计算 score/rank/trend/regime 分桶统计；
3. 画 threshold surface / heatmap 数据表；
4. 输出候选阈值 hypothesis；
5. 标记哪些 hypothesis 只是 2022 exploratory，哪些可能进入 PIT-safe T1。
```

禁止：

```text
1. policy replay；
2. risk-control replay；
3. strict_test；
4. 训练模型；
5. 用 2022 最优阈值直接宣称通过；
6. 修改生产/default/provider/frontend/Agent/订单链路；
7. 输出 OrderIntent / target_weight / target_position / quantity_instruction；
8. 把 future return label 放进 inference feature 或策略输入。
```

## 4. 必须读取

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT0_SCORE_RANK_REGIME_THRESHOLD_DISCOVERY_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP3_RISK_CONTROL_REPLAY_SANITY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP3A_MARKET_FEATURE_COVERAGE_PIT_GATE_REVIEW_CN.md
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/diagnostic_model_signal.csv
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/market_feature_by_signal_date.csv
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv
```

必须参考合同：

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
```

可参考价格读取实现：

```text
scripts/run_tw_policy_action_model_pa1.py
```

## 5. 输入与窗口

输入信号：

```text
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/diagnostic_model_signal.csv
```

市场状态：

```text
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/market_feature_by_signal_date.csv
```

诊断窗口：

```text
2022-01-03..2022-12-30
```

语义：

```text
2022 downturn validation diagnostic
strict_oos_2022 = false
```

## 6. 输出目录

所有本轮产物写入：

```text
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/
```

执行报告写入：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT0_SCORE_RANK_REGIME_THRESHOLD_DISCOVERY_EXECUTION_REPORT_CN.md
```

## 7. 必须输出文件

必须输出：

```text
manifest.json
threshold_discovery_source_manifest.json
diagnostic_forward_return_dataset.csv
forward_return_label_audit.csv
score_distribution_audit.csv
score_raw_band_forward_return_by_regime.csv
score_percentile_band_forward_return_by_regime.csv
score_04_08_vs_08plus_audit.csv
rank_band_forward_return_by_regime.csv
rank_change_forward_return_surface.csv
score_delta_forward_return_surface.csv
score_rank_joint_threshold_surface.csv
regime_conditional_threshold_surface.csv
candidate_threshold_hypotheses.csv
pit_safe_candidate_filter.csv
anti_overfit_and_label_leakage_audit.csv
diagnostic_semantics_audit.json
forbidden_action_audit.csv
validator_report.json
diagnostic_findings.md
```

## 8. Diagnostic Forward-return Dataset 合同

`diagnostic_forward_return_dataset.csv` 必须包含每个 2022 signal row 的诊断标签，至少字段：

```text
signal_date
instrument
rank
score
raw_score
score_percentile_by_date
score_zscore_by_date
rank_change_1d
rank_change_3d
rank_change_5d
score_delta_1d
score_delta_3d
score_delta_5d
market_risk_off_ma60
market_index_close
market_index_ma60
future_return_1d
future_return_5d
future_return_10d
future_return_20d
future_return_label_available_1d
future_return_label_available_5d
future_return_label_available_10d
future_return_label_available_20d
label_only_not_feature
strict_oos
diagnostic_only
semantic_label
```

未来收益标签口径必须写入 `forward_return_label_audit.csv`。建议：

```text
entry_price = next available open after signal_date
exit_price_horizon_h = close on or after h-th future trading row for that instrument
future_return_h = exit_price / entry_price - 1
```

如果执行者采用不同但等价的 PIT diagnostic label 口径，必须说明。

未来收益标签只能用于本轮分桶分析，不得作为策略输入。

## 9. Score 区间重点

必须专门输出：

```text
score_04_08_vs_08plus_audit.csv
```

比较：

```text
0.4 <= raw_score < 0.8
raw_score >= 0.8
```

并按市场状态拆分：

```text
risk_off
normal_or_risk_on
all
```

如果 `raw_score >= 0.8` 样本过少，必须报告：

```text
sample_count
insufficient_sample_status
not_comparable_reason
```

同时必须使用 percentile band 补充，因为不同 qlib 模型 raw score 尺度可能不稳定：

```text
top_0_5_percent
top_5_10_percent
top_10_20_percent
top_20_40_percent
top_40_60_percent
bottom_40_percent
```

## 10. Rank / Trend Surface

必须输出：

```text
rank_change_forward_return_surface.csv
score_delta_forward_return_surface.csv
score_rank_joint_threshold_surface.csv
```

至少覆盖：

```text
rank <= 5 / 10 / 20 / 30 / 50
rank_change_1d <= -10, -5, 0, >=5, >=10
rank_change_3d <= -20, -10, 0, >=10, >=20
score_delta_1d / 3d / 5d quantile bins
```

说明：

```text
rank 越小越好；
rank_change = current_rank - prior_rank；
rank_change < 0 表示排名提升；
rank_change > 0 表示排名恶化。
```

必须按 `market_risk_off_ma60` 拆分。

## 11. Candidate Threshold Hypotheses

`candidate_threshold_hypotheses.csv` 输出少量候选，不超过 10 条。

每条至少包含：

```text
hypothesis_id
source_surface
condition
market_regime
expected_effect
sample_count
mean_future_return_5d
mean_future_return_20d
median_future_return_20d
win_rate_20d
why_interesting
overfit_risk
pit_safe_t1_possible
allowed_next_phase
notes
```

候选只能作为 T1 规则设计输入，不能直接进入生产或 strict_test。

## 12. Anti-overfit / Label Leakage Audit

`anti_overfit_and_label_leakage_audit.csv` 必须逐项确认：

```text
future_return_labels_used_only_for_diagnostic
future_return_labels_not_in_feature_columns
2022_threshold_surface_is_exploratory_only
no_policy_replay
no_rule_selection_for_production
no_strict_oos_claim
no_model_training
```

T0 的结论只能是：

```text
有/没有可研究的 threshold hypothesis。
```

不能是：

```text
策略通过。
```

## 13. validator_report.json

必须包含：

```text
phase
status
pass
required_files_status
forward_return_dataset_status
score_band_status
score_04_08_vs_08plus_status
rank_change_surface_status
score_delta_surface_status
candidate_hypothesis_status
anti_overfit_status
diagnostic_semantics_status
forbidden_actions_status
t1_authorizable
repair_required
recommended_next_step
```

允许的 `recommended_next_step`：

```text
PASS_READY_FOR_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_WORK_DOC
FAIL_NEEDS_RCPT0_REPAIR
STOP_NO_THRESHOLD_SIGNAL_FOUND
```

## 14. 审查 Gate

审查者 verdict 只能为：

```text
PASS_READY_FOR_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_WORK_DOC
FAIL_NEEDS_RCPT0_REPAIR
STOP_NO_THRESHOLD_SIGNAL_FOUND
STOP_SCOPE_OR_LEAKAGE_VIOLATION
```

审查重点：

```text
1. 是否只是 diagnostic threshold discovery；
2. future return label 是否只用于标签分析；
3. 是否没有 policy/risk-control replay；
4. 是否重点审计 raw score 0.4-0.8 vs 0.8+；
5. 是否同时用 percentile band 处理 raw score 尺度问题；
6. rank_change / score_delta 是否按 PIT 历史计算；
7. 是否按 market risk-off 拆分；
8. 是否有足够证据支持 T1，而不是直接把 2022 最优阈值当策略。
```

## 15. 第一执行者指令

```text
请按 docs/tw_portfolio_decision_model/POLICY_RCPT0_SCORE_RANK_REGIME_THRESHOLD_DISCOVERY_WORK_CN.md 执行 RCP-T0。
只做 score/rank/regime threshold diagnostic discovery，不运行 policy replay 或 risk-control replay，不训练，不 strict_test，不改生产链路，不输出订单/目标仓位/数量指令。
必须重点审计 risk-off 中 raw_score 0.4-0.8 是否优于 raw_score >= 0.8，并同时用 score percentile、rank_change、score_delta 做稳健分桶。
完成后输出 data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/ 下全部必需文件，并提交执行报告。
```

## 16. 第一审查者指令

```text
请按 docs/tw_portfolio_decision_model/POLICY_RCPT0_SCORE_RANK_REGIME_THRESHOLD_DISCOVERY_WORK_CN.md 审查 RCP-T0 产物。
重点审查 threshold surface 是否完整、future return label 是否未泄漏到 feature/策略、raw score 0.4-0.8 vs 0.8+ 是否有足够样本与证据、rank/score trend 是否 PIT-safe、是否没有 replay/训练/生产链路越权。
通过后只授权写 RCP-T1 PIT-safe adaptive threshold rule design 工作文档，不授权 strict_test 或生产化。
```
