---
created_at: 2026-06-24T16:07:52+00:00
status: rcpt5b_option_b_execution_report
phase: RCPT5B_OPTION_B_QLIB_ONLY_STRICT_OOS
artifact_root: data_tw/experiments/risk_control_policy_2022/rcpt5b_option_b_qlib_only_strict_oos
verdict: FAIL_RULE05_DOES_NOT_PASS_QLIB_ONLY_STRICT_OOS
qlib_only: true
strict_oos_candidate: true
model_training_performed: false
production_or_provider_change_performed: false
---

# RCPT5B Option B 2023-2025 Qlib-only Strict OOS Candidate 执行报告

## 1. Scope

本轮只使用 `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/TEST.csv` 的 `qlib_score_raw` 与 `qlib_rank`，并读取审计 `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/TEST.manifest.json`。

本轮未训练模型、未读取 LTR/orthogonal LTR/stacking score、未调阈值、未新增规则、未修改 production/default/provider/frontend/Agent/monitor/order 链路，未输出 OrderIntent、target_weight、target_position 或 quantity_instruction。

## 2. Frozen Contracts

RULE_05 冻结条件：

```text
risk_off
len(holdings) > 1
rank_change_5d > 0 OR rank_change_3d > 0
not pass_rule03_combined_support
max_early_sell_per_day = 1
```

现金 gate 主口径冻结为 `cash / equity`。`cash / initial_cash` 只作为 auxiliary 输出，不用于 gate 主口径。

## 3. Key Results

| metric | RULE_05 | baseline |
| --- | ---: | ---: |
| net_return_after_fee_tax | 0.31759959 | 0.4121439 |
| net_return_delta | -0.09454431 |  |
| max_drawdown | -0.35800856 | -0.5590545 |
| max_drawdown_delta | 0.20104594 |  |
| participation_rate | 0.99832496 | 0.99832496 |
| primary_average_cash_rate | 0.30471485 | 0.09005068 |
| cash_gt_90pct_equity_day_share | 0.01340034 | 0.00167504 |
| average_holding_count | 6.94304858 | 9.09045226 |
| buy_count / sell_count / action_count | 576 / 569 / 1145 | 558 / 549 / 1107 |
| fee_and_tax / commission / tax | 439097.66 / 214036.85 / 225060.7 | 509542.18 / 248489.47 / 261052.76 |
| accelerated_sell_count | 111 | 0 |

## 4. Gate

- gate failures: `fee_tax_delta_abs`
- validator status: `PASS`
- reviewer verdict 建议：`FAIL_RULE05_DOES_NOT_PASS_QLIB_ONLY_STRICT_OOS`

Gate 明细见 `data_tw/experiments/risk_control_policy_2022/rcpt5b_option_b_qlib_only_strict_oos/rule05_2023_2025_gate_decision.csv`。

## 5. Required Artifacts

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt5b_option_b_qlib_only_strict_oos
```

`manifest.json`、contamination、signal lineage、market/price coverage、rule05 freeze、strict_oos_gate_freeze、summary/comparison/gate/monthly/cash/fee/concentration/trigger attribution、diagnostic/forbidden audits、validator、diagnostic_findings 均已落盘。

## 6. Validator

```json
{
  "phase": "RCPT5B_OPTION_B_QLIB_ONLY_STRICT_OOS",
  "status": "PASS",
  "pass": true,
  "required_files_status": "PASS",
  "contamination_audit_status": "PASS",
  "signal_lineage_status": "PASS",
  "market_feature_coverage_status": "PASS",
  "price_coverage_status": "PASS",
  "rule05_freeze_status": "PASS",
  "strict_oos_gate_freeze_status": "PASS",
  "cash_primary_denominator_status": "PASS_CASH_OVER_EQUITY",
  "forbidden_actions_status": "PASS",
  "forbidden_root_output_fields_status": "PASS",
  "model_training_status": "PASS_NOT_PERFORMED",
  "ltr_score_status": "PASS_NOT_READ",
  "production_chain_status": "PASS_NOT_CHANGED",
  "rule05_net_return_after_fee_tax": 0.31759959,
  "baseline_net_return_after_fee_tax": 0.4121439,
  "net_return_delta": -0.09454431,
  "rule05_max_drawdown": -0.35800856,
  "baseline_max_drawdown": -0.5590545,
  "max_drawdown_delta": 0.20104594,
  "rule05_primary_average_cash_rate": 0.30471485,
  "rule05_cash_gt_90pct_equity_day_share": 0.01340034,
  "rule05_accelerated_sell_count": 111,
  "recommended_verdict": "FAIL_RULE05_DOES_NOT_PASS_QLIB_ONLY_STRICT_OOS",
  "missing_required_files": [],
  "gate_decision_status": "PASS_REVIEWABLE"
}
```
