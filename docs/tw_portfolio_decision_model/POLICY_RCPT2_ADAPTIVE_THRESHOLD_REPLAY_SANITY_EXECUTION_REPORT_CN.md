---
created_at: 2026-06-24T09:28:47+00:00
status: rcpt2_execution_report
phase: RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY
artifact_root: data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity
recommended_next_step: PASS_READY_FOR_RCPT3_CLOSURE_REVIEW_WORK_DOC
adaptive_threshold_replay_performed: true
model_training_performed: false
strict_test_performed: false
production_or_provider_change_performed: false
---

# RCPT2 Adaptive Threshold Replay Sanity 执行报告

## 1. Scope

本轮严格按 RCPT2 工作文档执行，只做 2022 downturn validation diagnostic 的 adaptive threshold replay sanity。

已回放 RCPT1 预声明的 5 条 adaptive threshold 规则；没有新增/调规则或阈值，没有 strict_test 或训练。

## 2. Documents / Contracts Read

```text
docs/tw_portfolio_decision_model/POLICY_RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_REVIEW_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md
docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design/predeclared_adaptive_threshold_rules.csv
data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design/threshold_source_contract.csv
data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design/pit_feature_contract.csv
data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design/cash_no_trade_guardrail_contract.csv
data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design/t2_replay_metric_contract.csv
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/diagnostic_model_signal.csv
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/market_feature_by_signal_date.csv
data_tw/experiments/risk_control_policy_2022/rcp1b_diagnostic_baseline_replay_audit/baseline_summary.csv
```

## 3. Inputs

```text
signal: data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/diagnostic_model_signal.csv
market_feature: data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/market_feature_by_signal_date.csv
rule_contract: data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design/predeclared_adaptive_threshold_rules.csv
threshold_source_contract: data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design/threshold_source_contract.csv
baseline_summary: data_tw/experiments/risk_control_policy_2022/rcp1b_diagnostic_baseline_replay_audit/baseline_summary.csv
price_root: qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty
```

## 4. Outputs

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity
```

已生成工作文档要求的全部 root files 与每条规则子目录：

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
rules/{rule_id}/summary.csv
rules/{rule_id}/nav.csv
rules/{rule_id}/actions.csv
rules/{rule_id}/position_snapshots.csv
rules/{rule_id}/rule_trigger_ledger.csv
rules/{rule_id}/execution_audit.csv
```

## 5. Rule Gate Summary

```json
[
  {
    "rule_id": "RCPT1_RULE_01",
    "net_return_gate": "PASS",
    "max_drawdown_gate": "PASS",
    "turnover_gate": "PASS",
    "fee_tax_gate": "PASS",
    "cash_no_trade_gate": "FAIL",
    "participation_gate": "PASS",
    "concentration_gate": "PASS",
    "threshold_contract_gate": "PASS",
    "diagnostic_semantics_gate": "PASS",
    "overall_gate": "FAIL",
    "decision": "FAIL_CASH_OR_NO_TRADE",
    "notes": "dd_improve_pp=0.31283214; dd_improve_rel=0.73374948; net_delta=0.33581076; min_buy_count=61"
  },
  {
    "rule_id": "RCPT1_RULE_02",
    "net_return_gate": "PASS",
    "max_drawdown_gate": "PASS",
    "turnover_gate": "PASS",
    "fee_tax_gate": "PASS",
    "cash_no_trade_gate": "FAIL",
    "participation_gate": "PASS",
    "concentration_gate": "PASS",
    "threshold_contract_gate": "PASS",
    "diagnostic_semantics_gate": "PASS",
    "overall_gate": "FAIL",
    "decision": "FAIL_CASH_OR_NO_TRADE",
    "notes": "dd_improve_pp=0.31273264; dd_improve_rel=0.73351610; net_delta=0.25988420; min_buy_count=61"
  },
  {
    "rule_id": "RCPT1_RULE_03",
    "net_return_gate": "PASS",
    "max_drawdown_gate": "PASS",
    "turnover_gate": "PASS",
    "fee_tax_gate": "PASS",
    "cash_no_trade_gate": "FAIL",
    "participation_gate": "PASS",
    "concentration_gate": "PASS",
    "threshold_contract_gate": "PASS",
    "diagnostic_semantics_gate": "PASS",
    "overall_gate": "FAIL",
    "decision": "FAIL_CASH_OR_NO_TRADE",
    "notes": "dd_improve_pp=0.29081114; dd_improve_rel=0.68209911; net_delta=0.28314326; min_buy_count=61"
  },
  {
    "rule_id": "RCPT1_RULE_04",
    "net_return_gate": "PASS",
    "max_drawdown_gate": "FAIL",
    "turnover_gate": "PASS",
    "fee_tax_gate": "PASS",
    "cash_no_trade_gate": "PASS",
    "participation_gate": "PASS",
    "concentration_gate": "PASS",
    "threshold_contract_gate": "PASS",
    "diagnostic_semantics_gate": "PASS",
    "overall_gate": "FAIL",
    "decision": "FAIL_NO_RISK_REWARD_TRADEOFF",
    "notes": "dd_improve_pp=0.00000000; dd_improve_rel=0.00000000; net_delta=0.00000000; min_buy_count=61"
  },
  {
    "rule_id": "RCPT1_RULE_05",
    "net_return_gate": "PASS",
    "max_drawdown_gate": "PASS",
    "turnover_gate": "PASS",
    "fee_tax_gate": "PASS",
    "cash_no_trade_gate": "PASS",
    "participation_gate": "PASS",
    "concentration_gate": "PASS",
    "threshold_contract_gate": "PASS",
    "diagnostic_semantics_gate": "PASS",
    "overall_gate": "PASS",
    "decision": "PASS_CANDIDATE_FOR_RCPT3_CLOSURE_REVIEW",
    "notes": "dd_improve_pp=0.19727374; dd_improve_rel=0.46270663; net_delta=0.15005340; min_buy_count=61"
  }
]
```

## 6. Baseline Comparison

```json
[
  {
    "rule_id": "RCPT1_RULE_01",
    "baseline_net_return_after_fee_tax": "-0.3360922",
    "rule_net_return_after_fee_tax": -0.00028144,
    "net_delta": 0.33581076,
    "baseline_max_drawdown": "-0.42634734",
    "rule_max_drawdown": -0.1135152,
    "max_drawdown_delta": 0.31283214,
    "baseline_turnover_proxy": "48.45575343",
    "rule_turnover_proxy": 25.46586754,
    "turnover_delta": -22.98988589,
    "baseline_fee_and_tax": "112926.17",
    "rule_fee_and_tax": 72351.55,
    "fee_and_tax_delta": -40574.62,
    "decision": "FAIL_CASH_OR_NO_TRADE"
  },
  {
    "rule_id": "RCPT1_RULE_02",
    "baseline_net_return_after_fee_tax": "-0.3360922",
    "rule_net_return_after_fee_tax": -0.076208,
    "net_delta": 0.2598842,
    "baseline_max_drawdown": "-0.42634734",
    "rule_max_drawdown": -0.1136147,
    "max_drawdown_delta": 0.31273264,
    "baseline_turnover_proxy": "48.45575343",
    "rule_turnover_proxy": 13.56502697,
    "turnover_delta": -34.89072646,
    "baseline_fee_and_tax": "112926.17",
    "rule_fee_and_tax": 37017.28,
    "fee_and_tax_delta": -75908.89,
    "decision": "FAIL_CASH_OR_NO_TRADE"
  },
  {
    "rule_id": "RCPT1_RULE_03",
    "baseline_net_return_after_fee_tax": "-0.3360922",
    "rule_net_return_after_fee_tax": -0.05294894,
    "net_delta": 0.28314326,
    "baseline_max_drawdown": "-0.42634734",
    "rule_max_drawdown": -0.1355362,
    "max_drawdown_delta": 0.29081114,
    "baseline_turnover_proxy": "48.45575343",
    "rule_turnover_proxy": 25.06856338,
    "turnover_delta": -23.38719005,
    "baseline_fee_and_tax": "112926.17",
    "rule_fee_and_tax": 68380.33,
    "fee_and_tax_delta": -44545.84,
    "decision": "FAIL_CASH_OR_NO_TRADE"
  },
  {
    "rule_id": "RCPT1_RULE_04",
    "baseline_net_return_after_fee_tax": "-0.3360922",
    "rule_net_return_after_fee_tax": -0.3360922,
    "net_delta": 0.0,
    "baseline_max_drawdown": "-0.42634734",
    "rule_max_drawdown": -0.42634734,
    "max_drawdown_delta": 0.0,
    "baseline_turnover_proxy": "48.45575343",
    "rule_turnover_proxy": 48.45575343,
    "turnover_delta": 0.0,
    "baseline_fee_and_tax": "112926.17",
    "rule_fee_and_tax": 112926.17,
    "fee_and_tax_delta": 0.0,
    "decision": "FAIL_NO_RISK_REWARD_TRADEOFF"
  },
  {
    "rule_id": "RCPT1_RULE_05",
    "baseline_net_return_after_fee_tax": "-0.3360922",
    "rule_net_return_after_fee_tax": -0.1860388,
    "net_delta": 0.1500534,
    "baseline_max_drawdown": "-0.42634734",
    "rule_max_drawdown": -0.2290736,
    "max_drawdown_delta": 0.19727374,
    "baseline_turnover_proxy": "48.45575343",
    "rule_turnover_proxy": 47.89271616,
    "turnover_delta": -0.56303727,
    "baseline_fee_and_tax": "112926.17",
    "rule_fee_and_tax": 121293.38,
    "fee_and_tax_delta": 8367.21,
    "decision": "PASS_CANDIDATE_FOR_RCPT3_CLOSURE_REVIEW"
  }
]
```

## 7. Validator Result

```json
{
  "phase": "RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY",
  "status": "PASS",
  "pass": true,
  "required_files_status": "PASS",
  "t1_contract_status": "PASS",
  "replayed_rule_count": 5,
  "not_replayed_rule_count": 0,
  "any_rule_pass": true,
  "best_rule_id": "RCPT1_RULE_05",
  "threshold_contract_status": "PASS",
  "cash_no_trade_status": "PASS",
  "concentration_status": "PASS",
  "diagnostic_semantics_status": "PASS",
  "anti_overfit_status": "PASS",
  "forbidden_actions_status": "PASS",
  "repair_required": false,
  "recommended_next_step": "PASS_READY_FOR_RCPT3_CLOSURE_REVIEW_WORK_DOC"
}
```

## 8. Forbidden Actions Audit

本轮未执行：

```text
strict_test
model_training
new_rule
new_threshold
threshold_tuning
use_2022_replay_result_for_rule_selection_or_threshold_tuning
registry/default/provider/frontend/Agent/order chain changes
broker/quick-trade/real order
OrderIntent output
target_weight / target_position / quantity_instruction
```

`rules/*/actions.csv` 是 internal replay ledger，不是 OrderIntent 或真实订单建议。
