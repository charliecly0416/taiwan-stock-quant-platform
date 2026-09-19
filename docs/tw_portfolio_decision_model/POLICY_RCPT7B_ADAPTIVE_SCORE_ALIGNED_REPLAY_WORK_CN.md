---
created_at: 2026-06-24
status: work_doc
phase: RCPT7B_ADAPTIVE_SCORE_ALIGNED_REPLAY
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT7A_ADAPTIVE_SCORE_CONTRACT_AND_DATA_READINESS_REVIEW_CN.md
mainline: docs/tw_portfolio_decision_model/POLICY_RCPT7_ADAPTIVE_SCORE_ALIGNED_RISK_CONTROL_REPAIR_MAINLINE_CN.md
production_allowed: false
order_or_target_output_allowed: false
model_training_authorized: false
ltr_allowed: false
---

# RCPT7B Adaptive-score-aligned Predeclared Replay 工作文档

## 1. 目标

执行 RCPT7A 已冻结的三个候选：

```text
Candidate A: RULE_05 + Adaptive Buy Filter
Candidate B: Top50 Adaptive Score + RULE_05 Sell Overlay
Candidate C: Adaptive Score Conservative Variant
```

目标是判断是否存在候选能在旧版 adaptive score 逻辑对齐后，同时满足：

```text
1. 2022 下跌年接近或优于 rank_rotate_top50_adaptive_score；
2. 2023-2025 qlib-only strict OOS candidate 中 return_capture >= 0.85；
3. 不靠 all-cash/no-trade、费用漏算、集中度伪改善或阈值调参。
```

## 2. 固定 Signal Lineage / Window

RCPT7B 必须明确分三类窗口，不得混淆：

### 2.1 2021 Pre-2022 Sanity Diagnostic

语义：

```text
pre-2022 sanity diagnostic
not strict OOS
```

信号来源：

```text
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/diagnostic_model_signal.csv
```

窗口：

```text
2021-01-04..2021-12-30
```

### 2.2 2022 Downturn Diagnostic

语义：

```text
downturn validation diagnostic
not strict OOS
```

信号来源：

```text
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/diagnostic_model_signal.csv
```

窗口：

```text
2022-01-03..2022-12-30
```

### 2.3 2023-2025 Qlib-only Strict OOS Candidate

语义：

```text
qlib-only strict OOS candidate
```

唯一授权信号来源：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/TEST.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/TEST.manifest.json
```

固定窗口：

```text
2023-01-03..2025-06-30
```

不得把该结果写成完整 2025 自然年，也不得混入覆盖到 2025-12-31 或 2026 的其他 artifact。

## 3. Adaptive Score Formula

必须严格使用 RCPT7A 公式：

```text
adaptive_score_baseline =
    0.70 * qlib_score_zscore_by_date
  + 0.15 * ret20
  - 0.10 * volatility20
  + 0.05 * TWII_ret20
```

字段 PIT 合同：

```text
qlib_score_zscore_by_date = same signal_date cross-section z-score
ret20 = adjusted close at signal_date / adjusted close 20 prior rows - 1
volatility20 = std of historical daily returns ending at signal_date
TWII_ret20 = TWII close at signal_date / TWII close 20 prior rows - 1
```

Null policy：

```text
ret20、volatility20、TWII_ret20 缺失按历史公式 fill 0.0；
qlib score 缺失不得填补，应排除或 fail audit。
```

## 4. 必须比较的 Baseline

每个窗口必须同口径回放：

```text
rank_rotate_top50_adaptive_score
rank_rotate_top50
RCPT1_RULE_05
qlib_only_baseline
Candidate A
Candidate B
Candidate C
```

主 baseline：

```text
rank_rotate_top50_adaptive_score
```

说明：

```text
RCPT7B 的 adaptive baseline 应在同一 signal lineage/window 内重新构造；
不得直接拿历史不同 lineage 的收益表拼接比较。
```

## 5. 候选冻结定义

候选定义必须完全来自：

```text
data_tw/experiments/risk_control_policy_2022/rcpt7a_adaptive_score_contract_and_data_readiness/candidate_rule_contract.csv
```

不得新增候选或调阈值。

Candidate C 的阈值固定为：

```text
risk_off_min_adaptive_score = same_date_top50_median
max_risk_off_replacement_buys_per_day = 1
```

该阈值是同日分布规则，不是 replay 后调参。

## 6. 输出要求

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt7b_adaptive_score_aligned_replay/
```

必须生成：

```text
manifest.json
signal_lineage_freeze.json
adaptive_feature_build_audit.csv
baseline_and_candidate_replay_summary.csv
window_metric_summary.csv
gate_decision_by_candidate.csv
candidate_vs_adaptive_baseline.csv
return_capture_audit.csv
cash_exposure_audit.csv
fee_tax_reconciliation.csv
concentration_audit.csv
rule_trigger_attribution.csv
forbidden_action_audit.csv
diagnostic_semantics_audit.json
validator_report.json
diagnostic_findings.md
```

可以生成：

```text
internal_replay_ledgers_not_order_intent/
```

但该目录只能存 readonly accounting ledger，不得是 OrderIntent 或真实订单。

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT7B_ADAPTIVE_SCORE_ALIGNED_REPLAY_EXECUTION_REPORT_CN.md
```

## 7. Gate

### 7.1 2022 Gate

候选对 `rank_rotate_top50_adaptive_score`：

```text
net_return_after_fee_tax >= adaptive_baseline_net_return - 0.03
max_drawdown_severity <= adaptive_baseline_drawdown_severity + 0.03
```

### 7.2 2023-2025 Strict OOS Candidate Gate

候选对 `rank_rotate_top50_adaptive_score`：

```text
return_capture >= 0.85
max_drawdown not worse than adaptive baseline by more than 3pp
primary_average_cash_rate <= 0.65
cash_gt_90pct_equity_day_share <= 0.25
fee/tax not worse without return compensation
top_month / top_symbol / top_trigger concentration PASS
```

### 7.3 Fail Conditions

失败条件：

```text
1. 无候选满足 2022 gate；
2. 无候选满足 2023-2025 return_capture >= 0.85；
3. 候选靠 all-cash/no-trade 通过；
4. 费用、换手、集中度或 cash/equity 失控；
5. 出现 future leakage 或 replay 后调参。
```

## 8. 禁区

本阶段禁止：

```text
model training
LTR / orthogonal LTR / stacking score
new candidate
threshold tuning
production/default/provider change
frontend/Agent/monitor/order integration
broker / quick-trade / real order
OrderIntent
target_weight
target_position
quantity_instruction
```

## 9. 审查者职责

审查者必须判断：

```text
1. 是否只回放 Candidate A/B/C；
2. strict-OOS signal lineage/window 是否固定为 TEST.csv 2023-01-03..2025-06-30；
3. adaptive_score_baseline 是否 PIT-safe 构造；
4. 是否同口径比较 rank_rotate_top50_adaptive_score；
5. gate 是否严格执行；
6. 是否没有训练、LTR、调参、生产或订单越权。
```

审查结论只能是：

```text
PASS_RCPT7_CANDIDATE_READY_FOR_CLOSURE
FAIL_NO_CANDIDATE_BEATS_ADAPTIVE_BASELINE_TRADEOFF
FAIL_NEEDS_RCPT7B_REPAIR
STOP_SCOPE_OR_DATA_CONTRACT_VIOLATION
```
