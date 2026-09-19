---
created_at: 2026-06-24T05:19:35+00:00
status: rcp3_execution_report
phase: RCP3_RISK_CONTROL_REPLAY_SANITY
artifact_root: data_tw/experiments/risk_control_policy_2022/rcp3_risk_control_replay_sanity
recommended_next_step: STOP_NO_RULE_HAS_RISK_REWARD_TRADEOFF
risk_control_replay_performed: true
model_training_performed: false
strict_test_performed: false
production_or_provider_change_performed: false
---

# RCP3 Risk-control Replay Sanity 执行报告

## 1. Scope

本轮严格按 RCP3 工作文档执行，只做 2022 downturn validation diagnostic 的 risk-control replay sanity。

已回放 RCP2 预声明的 6 条规则，使用 RCP3A 已通过的 `TWII MA60` market feature gate。

## 2. Documents / Contracts Read

```text
docs/tw_portfolio_decision_model/POLICY_RCP3_RISK_CONTROL_REPLAY_SANITY_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP3A_MARKET_FEATURE_COVERAGE_PIT_GATE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP2_RISK_CONTROL_RULE_DESIGN_CONTRACT_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
```

## 3. Inputs

```text
signal: data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/diagnostic_model_signal.csv
market_feature: data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/market_feature_by_signal_date.csv
rule_contract: data_tw/experiments/risk_control_policy_2022/rcp2_risk_control_rule_design_contract/predeclared_rule_candidates.csv
baseline_summary: data_tw/experiments/risk_control_policy_2022/rcp1b_diagnostic_baseline_replay_audit/baseline_summary.csv
price_root: qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty
```

## 4. Outputs

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcp3_risk_control_replay_sanity
```

已生成工作文档要求的全部 root files 与每条规则子目录：

```text
manifest.json
replay_source_manifest.json
rule_replay_summary.csv
rule_baseline_comparison.csv
rule_gate_decision.csv
risk_metric_summary_by_rule.csv
cash_no_trade_audit_by_rule.csv
turnover_fee_tax_audit_by_rule.csv
action_count_audit_by_rule.csv
concentration_audit_by_rule.csv
diagnostic_semantics_audit.json
anti_overfit_and_no_2022_mining_audit.csv
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
    "rule_id": "RCP2_RULE_01",
    "net_return_gate": "PASS",
    "max_drawdown_gate": "PASS",
    "turnover_gate": "PASS",
    "fee_tax_gate": "PASS",
    "cash_no_trade_gate": "FAIL",
    "participation_gate": "FAIL",
    "concentration_gate": "PASS",
    "diagnostic_semantics_gate": "PASS",
    "overall_gate": "FAIL",
    "decision": "FAIL_CASH_OR_NO_TRADE",
    "notes": "dd_improve_pp=0.31228613; dd_improve_rel=0.73246881; net_delta=0.25009012"
  },
  {
    "rule_id": "RCP2_RULE_02",
    "net_return_gate": "PASS",
    "max_drawdown_gate": "FAIL",
    "turnover_gate": "PASS",
    "fee_tax_gate": "PASS",
    "cash_no_trade_gate": "PASS",
    "participation_gate": "PASS",
    "concentration_gate": "PASS",
    "diagnostic_semantics_gate": "PASS",
    "overall_gate": "FAIL",
    "decision": "FAIL_NO_RISK_REWARD_TRADEOFF",
    "notes": "dd_improve_pp=0.00000000; dd_improve_rel=0.00000000; net_delta=0.00000000"
  },
  {
    "rule_id": "RCP2_RULE_03",
    "net_return_gate": "PASS",
    "max_drawdown_gate": "PASS",
    "turnover_gate": "PASS",
    "fee_tax_gate": "PASS",
    "cash_no_trade_gate": "FAIL",
    "participation_gate": "FAIL",
    "concentration_gate": "PASS",
    "diagnostic_semantics_gate": "PASS",
    "overall_gate": "FAIL",
    "decision": "FAIL_CASH_OR_NO_TRADE",
    "notes": "dd_improve_pp=0.29421897; dd_improve_rel=0.69009219; net_delta=0.21916254"
  },
  {
    "rule_id": "RCP2_RULE_04",
    "net_return_gate": "PASS",
    "max_drawdown_gate": "FAIL",
    "turnover_gate": "PASS",
    "fee_tax_gate": "PASS",
    "cash_no_trade_gate": "PASS",
    "participation_gate": "PASS",
    "concentration_gate": "PASS",
    "diagnostic_semantics_gate": "PASS",
    "overall_gate": "FAIL",
    "decision": "FAIL_NO_RISK_REWARD_TRADEOFF",
    "notes": "dd_improve_pp=0.00000000; dd_improve_rel=0.00000000; net_delta=0.00000000"
  },
  {
    "rule_id": "RCP2_RULE_05",
    "net_return_gate": "PASS",
    "max_drawdown_gate": "PASS",
    "turnover_gate": "PASS",
    "fee_tax_gate": "PASS",
    "cash_no_trade_gate": "FAIL",
    "participation_gate": "FAIL",
    "concentration_gate": "PASS",
    "diagnostic_semantics_gate": "PASS",
    "overall_gate": "FAIL",
    "decision": "FAIL_CASH_OR_NO_TRADE",
    "notes": "dd_improve_pp=0.31223588; dd_improve_rel=0.73235095; net_delta=0.24963581"
  },
  {
    "rule_id": "RCP2_RULE_06",
    "net_return_gate": "PASS",
    "max_drawdown_gate": "FAIL",
    "turnover_gate": "PASS",
    "fee_tax_gate": "PASS",
    "cash_no_trade_gate": "PASS",
    "participation_gate": "PASS",
    "concentration_gate": "PASS",
    "diagnostic_semantics_gate": "PASS",
    "overall_gate": "FAIL",
    "decision": "FAIL_NO_RISK_REWARD_TRADEOFF",
    "notes": "dd_improve_pp=-0.00010531; dd_improve_rel=-0.00024701; net_delta=-0.00467718"
  }
]
```

## 6. Baseline Comparison

```json
[
  {
    "rule_id": "RCP2_RULE_01",
    "baseline_net_return_after_fee_tax": "-0.3360922",
    "rule_net_return_after_fee_tax": -0.08600208,
    "net_delta": 0.25009012,
    "baseline_max_drawdown": "-0.42634734",
    "rule_max_drawdown": -0.11406121,
    "max_drawdown_delta": 0.31228613,
    "baseline_turnover_proxy": "48.45575343",
    "rule_turnover_proxy": 13.49958659,
    "turnover_delta": -34.95616684,
    "baseline_fee_and_tax": "112926.17",
    "rule_fee_and_tax": 36753.14,
    "fee_and_tax_delta": -76173.03,
    "decision": "FAIL_CASH_OR_NO_TRADE"
  },
  {
    "rule_id": "RCP2_RULE_02",
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
    "rule_id": "RCP2_RULE_03",
    "baseline_net_return_after_fee_tax": "-0.3360922",
    "rule_net_return_after_fee_tax": -0.11692966,
    "net_delta": 0.21916254,
    "baseline_max_drawdown": "-0.42634734",
    "rule_max_drawdown": -0.13212837,
    "max_drawdown_delta": 0.29421897,
    "baseline_turnover_proxy": "48.45575343",
    "rule_turnover_proxy": 9.75652242,
    "turnover_delta": -38.69923101,
    "baseline_fee_and_tax": "112926.17",
    "rule_fee_and_tax": 25561.05,
    "fee_and_tax_delta": -87365.12,
    "decision": "FAIL_CASH_OR_NO_TRADE"
  },
  {
    "rule_id": "RCP2_RULE_04",
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
    "rule_id": "RCP2_RULE_05",
    "baseline_net_return_after_fee_tax": "-0.3360922",
    "rule_net_return_after_fee_tax": -0.08645639,
    "net_delta": 0.24963581,
    "baseline_max_drawdown": "-0.42634734",
    "rule_max_drawdown": -0.11411146,
    "max_drawdown_delta": 0.31223588,
    "baseline_turnover_proxy": "48.45575343",
    "rule_turnover_proxy": 13.49229851,
    "turnover_delta": -34.96345492,
    "baseline_fee_and_tax": "112926.17",
    "rule_fee_and_tax": 36715.71,
    "fee_and_tax_delta": -76210.46,
    "decision": "FAIL_CASH_OR_NO_TRADE"
  },
  {
    "rule_id": "RCP2_RULE_06",
    "baseline_net_return_after_fee_tax": "-0.3360922",
    "rule_net_return_after_fee_tax": -0.34076938,
    "net_delta": -0.00467718,
    "baseline_max_drawdown": "-0.42634734",
    "rule_max_drawdown": -0.42645265,
    "max_drawdown_delta": -0.00010531,
    "baseline_turnover_proxy": "48.45575343",
    "rule_turnover_proxy": 46.08656781,
    "turnover_delta": -2.36918562,
    "baseline_fee_and_tax": "112926.17",
    "rule_fee_and_tax": 108930.76,
    "fee_and_tax_delta": -3995.41,
    "decision": "FAIL_NO_RISK_REWARD_TRADEOFF"
  }
]
```

## 7. Validator Result

```json
{
  "phase": "RCP3_RISK_CONTROL_REPLAY_SANITY",
  "status": "PASS",
  "pass": true,
  "required_files_status": "PASS",
  "rcp3a_gate_status": "PASS",
  "replayed_rule_count": 6,
  "not_replayed_rule_count": 0,
  "best_gate_decision": "NO_RULE_PASS",
  "any_rule_pass": false,
  "cash_no_trade_status": "FAIL",
  "concentration_status": "PASS",
  "diagnostic_semantics_status": "PASS",
  "anti_overfit_status": "PASS",
  "forbidden_actions_status": "PASS",
  "rcp4_authorizable": false,
  "repair_required": false,
  "recommended_next_step": "STOP_NO_RULE_HAS_RISK_REWARD_TRADEOFF"
}
```

## 8. Forbidden Actions Audit

本轮未执行：

```text
strict_test
model training
新增规则或阈值
2022 结果调参/换特征/筛选规则
registry/default/provider/frontend/Agent/订单链路修改
OrderIntent 输出
target_weight / target_position / quantity_instruction 输出
```

说明：`rules/*/actions.csv` 是内部 replay ledger，不是订单建议。

## 9. Recommendation

```text
STOP_NO_RULE_HAS_RISK_REWARD_TRADEOFF
```
