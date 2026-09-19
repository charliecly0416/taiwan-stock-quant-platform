---
created_at: 2026-06-23
status: executed_ral_ed2_predeclared_block_buy_rule_sanity
phase: RAL_ED2_PREDECLARED_BLOCK_BUY_RULE_SANITY
work_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ED2_PREDECLARED_BLOCK_BUY_RULE_SANITY_WORK_CN.md
artifact_root: data_tw/experiments/explicit_rule_discovery/ral_ed2_predeclared_block_buy_rule_sanity
final_recommendation: STOP_NO_PREDECLARED_RULE_BEATS_BASELINE
strict_test_used: false
model_training_run: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# RAL-ED2 Predeclared Block-buy Rule Sanity 执行报告

## 1. Scope

本轮只测试工作文档预声明的 6 个 block-buy candidates，每个 candidate 2 个 threshold versions。未执行 strict_test、模型训练、grid search、validation threshold selection、生产集成或订单输出。

## 2. Evidence Produced

```text
manifest.json
source_artifact_manifest.json
predeclared_rule_candidate_manifest.csv
threshold_source_audit.csv
readonly_rule_replay_result.csv
baseline_vs_rule_replay_comparison.csv
rolling_oos_result.csv
participation_cash_dominance_audit.csv
turnover_cost_gate_audit.csv
active_decision_change_audit.csv
symbol_date_pnl_concentration_audit.csv
baseline_clone_no_trade_audit.csv
forbidden_consumer_audit.csv
strict_test_boundary_audit.csv
diagnostic_findings.md
validator_report.json
```

## 3. Main Result

```text
candidate_count = 6
threshold_versions_per_candidate_max = 2
validation_positive_rule_version_count = 0
rolling_positive_rule_version_count = 0
validator_ok = true
failed_count = 0
final_recommendation = STOP_NO_PREDECLARED_RULE_BEATS_BASELINE
```

## 4. Boundary

```text
strict_test_used = false
model_training_run = false
rule_grid_search = false
validation_threshold_selection = false
OrderIntent output = false
target_weight / target_position / quantity / broker_order = false
provider/latest/monitor/frontend/Agent/production = not_performed
```

## 5. Recommendation For Reviewer

```text
STOP_NO_PREDECLARED_RULE_BEATS_BASELINE
```

若为 READY，也只表示统筹可考虑 ED3 final-only strict_test 工作文档，不自动使用 strict_test。
