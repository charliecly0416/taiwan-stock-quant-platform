---
created_at: 2026-06-24T15:42:14+00:00
status: rcpt5a_option_a_execution_report
phase: RCPT5A_OPTION_A_2021_PIT_FEATURE_REPAIR_DIAGNOSTIC
artifact_root: data_tw/experiments/risk_control_policy_2022/rcpt5a_option_a_2021_pit_feature_repair_diagnostic
verdict: PASS_READY_FOR_OPTION_B_QLIB_ONLY_STRICT_OOS_WORK_DOC
diagnostic_only: true
strict_oos: false
model_training_performed: false
strict_test_performed: false
production_or_provider_change_performed: false
---

# RCPT5A Option A 2021 PIT Feature Repair + Pre-2022 Diagnostic 执行报告

## 1. Scope

本轮执行 `RCPT5A Option A`：

```text
补齐 2021 PIT market feature
冻结 RCPT1_RULE_05
做 2021 pre-2022 sanity diagnostic
```

2021 结果只写作 `pre-2022 sanity diagnostic`。本轮没有训练模型、没有 strict_test、没有新增/调整规则阈值、没有修改 production/default/provider/frontend/Agent/monitor/order 链路，也没有输出 OrderIntent、target_weight、target_position 或 quantity_instruction。

## 2. 2021 PIT Feature Repair

- 本地 TWII source: `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv`
- MA60 contract: `current TWII close + previous 59 available TWII rows`
- uses_future_price: `false`
- feature file: `data_tw/experiments/risk_control_policy_2022/rcpt5a_option_a_2021_pit_feature_repair_diagnostic/market_feature_2021_by_signal_date.csv`
- coverage audit: `data_tw/experiments/risk_control_policy_2022/rcpt5a_option_a_2021_pit_feature_repair_diagnostic/market_feature_coverage_audit.csv`

## 3. Frozen RULE_05

冻结条件：

```text
risk_off
len(holdings) > 1
rank_change_5d > 0 或 rank_change_3d > 0
not pass_rule03_combined_support
max_early_sell_per_day = 1
```

## 4. Key Results

| metric | RULE_05 | baseline |
| --- | ---: | ---: |
| net_return_after_fee_tax | 0.47696307 | 0.54760487 |
| gross_return | 0.65191367 | 0.73416806 |
| max_drawdown | -0.20594562 | -0.31695465 |
| participation_rate | 0.99588477 | 0.99588477 |
| average_cash_rate | 0.49247449 | 0.21546045 |
| max_cash_rate | 1.15007883 | 1.0 |
| cash_gt_80_day_share | 0.22633745 | 0.02469136 |
| cash_gt_90_day_share | 0.1399177 | 0.00823045 |
| average_holding_count | 6.01646091 | 8.25925926 |
| buy_count / sell_count / action_count | 242 / 234 / 476 | 241 / 232 / 473 |
| fee_and_tax / commission / tax | 174950.6 / 85621.68 / 89328.96 | 186563.19 / 91371.15 / 95192.01 |
| turnover_proxy | 47.89053261 | 47.81979264 |
| accelerated_sell_count | 36 | 0 |

## 5. Validator

```json
{
  "phase": "RCPT5A_OPTION_A_2021_PIT_FEATURE_REPAIR_DIAGNOSTIC",
  "status": "PASS",
  "pass": true,
  "required_files_status": "PASS",
  "market_feature_coverage_status": "PASS",
  "pit_ma60_status": "PASS",
  "rule05_frozen_contract_status": "PASS",
  "diagnostic_semantics_status": "PASS",
  "forbidden_actions_status": "PASS",
  "forbidden_root_output_fields_status": "PASS",
  "strict_oos_claim_status": "PASS_NOT_CLAIMED",
  "model_training_status": "PASS_NOT_PERFORMED",
  "strict_test_status": "PASS_NOT_PERFORMED",
  "production_chain_status": "PASS_NOT_CHANGED",
  "rule05_net_return_after_fee_tax": 0.47696307,
  "baseline_net_return_after_fee_tax": 0.54760487,
  "rule05_max_drawdown": -0.20594562,
  "baseline_max_drawdown": -0.31695465,
  "rule05_average_cash_rate": 0.49247449,
  "rule05_cash_gt_90_day_share": 0.1399177,
  "rule05_accelerated_sell_count": 36,
  "recommended_verdict": "PASS_READY_FOR_OPTION_B_QLIB_ONLY_STRICT_OOS_WORK_DOC",
  "missing_required_files": []
}
```

## 6. Verdict

建议进入审查的 verdict：

```text
PASS_READY_FOR_OPTION_B_QLIB_ONLY_STRICT_OOS_WORK_DOC
```

该 verdict 只表示 2021 pre-2022 sanity diagnostic 未提前暴露明显失败；它不是 strict OOS、final OOS 或 independent test 结论。
