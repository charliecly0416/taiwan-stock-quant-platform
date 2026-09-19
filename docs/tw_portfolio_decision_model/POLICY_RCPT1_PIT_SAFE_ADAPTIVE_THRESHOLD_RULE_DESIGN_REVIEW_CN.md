---
created_at: 2026-06-24
status: rcpt1_independent_review_completed
phase: RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN
work_doc: docs/tw_portfolio_decision_model/POLICY_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_EXECUTION_REPORT_CN.md
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT0_R_CANDIDATE_HYPOTHESIS_CONSISTENCY_REPAIR_REVIEW_CN.md
artifact_root: data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design
verdict: PASS_READY_FOR_RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY_WORK_DOC
readonly_review: true
policy_replay_performed_by_reviewer: false
risk_control_replay_performed_by_reviewer: false
model_training_performed_by_reviewer: false
strict_test_performed_by_reviewer: false
production_or_order_chain_change_performed_by_reviewer: false
---

# RCPT1 PIT-safe Adaptive Threshold Rule Design 独立审查报告

## 1. Verdict

`PASS_READY_FOR_RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY_WORK_DOC`

RCPT1 执行产物满足本轮 gate：已完成 PIT-safe adaptive threshold rule design 所需合同冻结，未发现 replay / training / strict_test / 生产链路 / 订单链路越权，也未发现 future return label 进入规则输入或 H09 被误写成独立硬阈值。

本次通过只授权进入：

```text
RCPT2 adaptive threshold replay sanity
```

不授权：

```text
strict_test
production calibrated claim
production/default/provider/frontend/Agent/订单链路接入
```

## 2. Findings

### Critical

无。

### High

无。

### Medium

无。

### Low

1. percentile fallback 的来源映射存在轻微合同表述不一致，但不构成当前 gate 阻塞。
`RCPT1_RULE_02` 的冻结阈值写为：

```text
top_20_40_percent primary; bounded top_10_40_percent family
```

但 `source_hypotheses` / `candidate_from_t0_mapping.csv` / `diagnostic_findings.md` 同时把 H03 也映射到该规则，而 H03 在 T0 中对应的是：

```text
risk_off AND top_40_60_percent
```

证据：

```text
predeclared_adaptive_threshold_rules.csv:3
threshold_source_contract.csv:4
candidate_from_t0_mapping.csv:3-4
diagnostic_findings.md:9
candidate_threshold_hypotheses.csv:3-4
```

该问题当前不阻塞通过，因为：

```text
规则冻结值本身是显式的；
未引入未来标签、未越过只读边界、未触发 replay；
H03 只造成 traceability/表述噪音，不改变当前已冻结的 rule contract。
```

RCPT2 应以已冻结的 `threshold_value` / `threshold_values` 为准，不应据 H03 推导出未声明的 `top_40_60_percent` 回放路径。

## 3. Required Checks Review

### 3.1 必需文件是否齐全

通过。

工作文档要求的 15 个文件均已存在于：

```text
data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design/
```

证据包括：

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

同时 `validator_report.json` 记录：

```text
required_files_status = PASS
```

### 3.2 是否只做规则设计，没有 policy replay / risk-control replay

通过。

脚本只生成 CSV/JSON/MD 合同与执行报告，不调用任何 replay、training 或 strict_test 逻辑。
执行报告、manifest、forbidden audit、validator 均一致声明：

```text
policy_replay_performed = false
risk_control_replay_performed = false
model_training_performed = false
strict_test_performed = false
```

证据：

```text
scripts/run_tw_policy_rcpt1_pit_safe_adaptive_threshold_rule_design.py:18-48
scripts/run_tw_policy_rcpt1_pit_safe_adaptive_threshold_rule_design.py:412-420
scripts/run_tw_policy_rcpt1_pit_safe_adaptive_threshold_rule_design.py:458-470
data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design/manifest.json
data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design/forbidden_action_audit.csv:2-5
data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design/validator_report.json
docs/tw_portfolio_decision_model/POLICY_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_EXECUTION_REPORT_CN.md
```

结论：本轮是 rule design only，没有 replay 泄漏。

### 3.3 预声明 adaptive threshold rules 是否 3-6 条、可解释、T2 可回放

通过。

规则数为 5，落在要求的 3-6 条区间内：

```text
RCPT1_RULE_01
RCPT1_RULE_02
RCPT1_RULE_03
RCPT1_RULE_04
RCPT1_RULE_05
```

每条规则都包含：

```text
rule_id
rule_name
source_hypotheses
threshold_values
pit_safe_inputs
cash_participation_guardrail
t2_replay_allowed
```

且 `t2_replay_allowed=True`，并附解释性 notes。

证据：

```text
predeclared_adaptive_threshold_rules.csv:2-6
adaptive_threshold_rule_design_manifest.json
validator_report.json
```

结论：满足“预声明、可解释、T2 可回放”的设计要求。

### 3.4 H01/H08 是否正确使用，H09 是否仅 reference-only

通过。

H01/H08 已用于 risk-off mid-band 与 rank refinement：

```text
H01 -> raw_score 0.4 <= x < 0.8
H08 -> rank <= 5 refinement
```

证据：

```text
predeclared_adaptive_threshold_rules.csv:2,4
threshold_source_contract.csv:2-3
candidate_from_t0_mapping.csv:2,9
candidate_threshold_hypotheses.csv:2,9
```

H09 保持 reference-only，未进入独立 trigger：

```text
threshold_source_contract.csv:9 -> rule_id = REFERENCE_ONLY
candidate_from_t0_mapping.csv:10 -> REFERENCE_ONLY_NOT_A_TRIGGER
small_sample_exclusion_audit.csv:10 -> allowed_in_predeclared_rule_trigger = False
forbidden_action_audit.csv:12 -> h09_independent_hard_threshold = False
```

且 H09 的 n=9 与 RCPT0-R 结论一致，没有被提升为硬阈值。

### 3.5 future_return label 是否没有进入规则输入

通过。

所有预声明规则均记录：

```text
uses_future_return_label = False
```

PIT feature contract 中全部特征也记录：

```text
uses_future_return_label = False
uses_future_data = False
```

rule dependency contract 进一步把以下字段列入 forbidden：

```text
future_return_*
future_excess_return_*
forward_return_*
label_*
realized_pnl
replay_return
```

证据：

```text
predeclared_adaptive_threshold_rules.csv:2-6
pit_feature_contract.csv:2-14
rule_dependency_contract.csv:2-6
anti_overfit_and_no_2022_direct_fit_audit.csv:7
forbidden_action_audit.csv:11
```

结论：future_return label 仅保留为 T0 诊断语义，不是规则输入。

### 3.6 threshold_source_contract 是否把 T0 发现标记为 diagnostic-derived，不冒充 strict OOS/production calibrated

通过。

`threshold_source_contract.csv` 中来自 T0 的条目全部写明：

```text
is_2022_diagnostic_derived = True
requires_t2_recheck = True
can_be_used_in_production = False
```

并在 notes 中明确：

```text
not strict OOS
not production calibrated
```

`diagnostic_semantics_audit.json` 与 `adaptive_threshold_rule_design_manifest.json` 也同步冻结：

```text
strict_oos_2022 = false
diagnostic_only = true
forbidden_language includes strict OOS / production calibrated / 2022 grid-search best
```

证据：

```text
threshold_source_contract.csv:2-9
diagnostic_semantics_audit.json
adaptive_threshold_rule_design_manifest.json
```

结论：没有冒充 strict OOS 或 production calibrated。

### 3.7 pit_feature_contract / cash guardrail / T2 metric contract 是否完整

通过。

`pit_feature_contract.csv` 覆盖了工作文档要求的全部核心字段：

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

证据：

```text
pit_feature_contract.csv:2-14
validator_report.json -> pit_feature_status = PASS
```

`cash_no_trade_guardrail_contract.csv` 覆盖了要求的全部 guardrail：

```text
min_participation_rate >= 0.50
max_average_cash_rate <= 0.60
max_no_position_days <= 20
minimum_buy_count_relative_to_baseline
minimum_holding_count
no_all_cash
no_sell_only_policy
```

证据：

```text
cash_no_trade_guardrail_contract.csv:2-8
```

`t2_replay_metric_contract.csv` 覆盖了工作文档要求的全部 T2 metric：

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

并明确：

```text
T2 cannot pass using a single metric.
```

证据：

```text
t2_replay_metric_contract.csv:2-14
validator_report.json -> cash_guardrail_status = PASS / t2_metric_contract_status = PASS
```

### 3.8 是否未训练、未 strict_test、未修改生产链路或订单链路

通过。

未发现：

```text
training
strict_test
provider/default/registry/frontend/Agent chain modification
order / target_weight / target_position / quantity_instruction output
```

证据：

```text
scripts/run_tw_policy_rcpt1_pit_safe_adaptive_threshold_rule_design.py:36-48
scripts/run_tw_policy_rcpt1_pit_safe_adaptive_threshold_rule_design.py:458-470
manifest.json
forbidden_action_audit.csv:6-10
validator_report.json
```

此外 `rule_dependency_contract.csv` 也显式把相关 forbidden actions 冻结为不可执行。

### 3.9 verdict 是否可以进入 RCPT2

可以进入 RCPT2。

理由：

```text
必需文件齐全；
本轮仅做规则设计，没有 replay / training / strict_test；
规则数、字段、PIT 输入、cash guardrail、T2 metric contract 完整；
H01/H08 使用正确；
H09 维持 reference-only；
future_return label 未进入规则输入；
threshold source 已标为 diagnostic-derived / not production calibrated；
未触碰生产或订单链路。
```

授权边界仍然必须保持：

```text
只授权 RCPT2 adaptive threshold replay sanity；
不授权 strict_test；
不授权 production 化；
不授权把 2022 诊断语义表述成 strict OOS 或 production calibrated。
```

## 4. Evidence Checked

已读取并核查用户要求材料：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT0_R_CANDIDATE_HYPOTHESIS_CONSISTENCY_REPAIR_REVIEW_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design/ 下全部必需产物
scripts/run_tw_policy_rcpt1_pit_safe_adaptive_threshold_rule_design.py
```

并为交叉核对补读：

```text
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/candidate_threshold_hypotheses.csv
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/pit_safe_candidate_filter.csv
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/score_percentile_band_forward_return_by_regime.csv
```

## 5. Final Authorization Statement

最终审查结论：

```text
PASS_READY_FOR_RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY_WORK_DOC
```
