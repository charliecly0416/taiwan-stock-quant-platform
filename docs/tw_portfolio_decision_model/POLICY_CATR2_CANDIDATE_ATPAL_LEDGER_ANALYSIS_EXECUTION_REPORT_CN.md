---
created_at: 2026-06-23T17:27:28+00:00
status: ready_for_review
phase: CATR2_CANDIDATE_ATPAL_LEDGER_ANALYSIS
artifact_root: data_tw/experiments/candidate_atpal_replay_feasibility/catr2_candidate_atpal_ledger_analysis
analysis_only: true
candidate_pass_fail_judgement: false
strict_test_used: false
model_training_run: false
production_allowed: false
---

# CATR2 Candidate ATPAL Ledger Analysis 执行报告

## 1. Scope

本轮严格执行 CATR2：只分析 CATR1 生成的 candidate ATPAL ledgers，解释既有 FPA4 candidates 的收益/亏损来源、集中度、train/validation 不稳定原因。

确认未执行：

```text
candidate pass/fail judgement
FPA4 repair
改变 FPA4 原始失败结论
新增候选
调阈值
validation mining
strict_test
模型训练
生产/default/order/provider/frontend/Agent 集成
OrderIntent output
target_weight / target_position / quantity_instruction / broker_order
```

## 2. Documents / Artifacts Read

```text
docs/tw_portfolio_decision_model/POLICY_CATR_CANDIDATE_ATPAL_REPLAY_FEASIBILITY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_CATR1_CANDIDATE_ATPAL_REPLAY_BUILDER_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_CATR1_CANDIDATE_ATPAL_REPLAY_BUILDER_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_CATR2_CANDIDATE_ATPAL_LEDGER_ANALYSIS_WORK_CN.md
data_tw/experiments/candidate_atpal_replay_feasibility/catr1_candidate_atpal_replay_builder/
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit/
data_tw/experiments/full_path_action_diagnostic/fpa4_predeclared_full_path_rule_sanity/
```

## 3. Outputs

输出目录：

```text
data_tw/experiments/candidate_atpal_replay_feasibility/catr2_candidate_atpal_ledger_analysis
```

输出文件：

```text
manifest.json
source_artifact_manifest.json
candidate_delta_component_analysis.csv
candidate_symbol_date_concentration_analysis.csv
candidate_trade_pnl_distribution_analysis.csv
candidate_lifecycle_pnl_distribution_analysis.csv
candidate_train_validation_failure_attribution.csv
candidate_year_regime_stability_analysis.csv
candidate_research_recommendation_audit.csv
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

## 4. Key Findings

Validation delta 为正的条目数：

```text
3
```

Validation delta 非正的条目数：

```text
4
```

主要解释：

```text
C01 validation 为正但 train 为负，且费用/换手上升，方向不稳定。
C02/C03/C04 validation 非正，candidate path 未形成稳定收益改善。
C05 validation 有正 delta，但 train 证据弱，不能直接作为策略结论。
candidate concentration 普遍高于 baseline reference，需要统筹决定是否只作为负面证据关闭，或另开新主线讨论。
```

## 5. Validator Summary

```json
{
  "ok": true,
  "status": "CATR2_ANALYSIS_READY_FOR_REVIEW",
  "phase": "CATR2_CANDIDATE_ATPAL_LEDGER_ANALYSIS",
  "final_recommendation": "READY_FOR_REVIEWER_TO_AUDIT_CATR2_ANALYSIS",
  "source_catr1_validator_ok": true,
  "candidate_scope_matches_fpa4": true,
  "analysis_only": true,
  "candidate_pass_fail_judgement": false,
  "new_candidate_added": false,
  "threshold_adjustment": false,
  "strict_test_used": false,
  "model_training_run": false,
  "production_allowed": false,
  "order_intent_output": false,
  "target_weight_output": false,
  "target_position_output": false,
  "quantity_instruction_output": false,
  "broker_order_output": false,
  "failed_count": 0,
  "checks": [
    {
      "check": "source_catr1_validator_ok",
      "ok_flag": true
    },
    {
      "check": "candidate_scope_matches_fpa4",
      "ok_flag": true
    },
    {
      "check": "analysis_only",
      "ok_flag": true
    },
    {
      "check": "recommendations_allowed",
      "ok_flag": true
    },
    {
      "check": "forbidden_terms_absent",
      "ok_flag": true
    }
  ]
}
```

## 6. Final Recommendation

```text
READY_FOR_REVIEWER_TO_AUDIT_CATR2_ANALYSIS
```
