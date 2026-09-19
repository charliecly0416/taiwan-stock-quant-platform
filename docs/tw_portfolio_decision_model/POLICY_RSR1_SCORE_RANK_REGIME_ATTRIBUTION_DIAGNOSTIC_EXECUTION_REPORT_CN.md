---
created_at: 2026-06-27T14:58:58+00:00
status: executed_rsr1_score_rank_regime_attribution_diagnostic
phase: POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_WORK_CN.md
artifact_root: data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic
readonly_only: true
diagnostic_only: true
replay_rerun_performed: false
training_run: false
order_intent_generated: false
recommendation: PASS_READY_FOR_REVIEW_REPAIR_NOT_REQUIRED
---

# Execution Report

## 1. Scope
- Assigned phase: `POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC`
- Mainline document: `docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md`
- Work document: `docs/tw_portfolio_decision_model/POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_WORK_CN.md`
- Non-goals confirmed: 不训练、不 rerun replay、不调阈值、不生成 OrderIntent、不输出订单/仓位/权重/数量、不 provider publish、不 accepted latest switch、不改 production/default/frontend/daily update、不外部拉取数据。

## 2. Documents / Contracts / Skills Read

Skills read:

```text
/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md
```

Required documents and artifacts read:

```text
docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RSR0_CONTRACT_AND_DATA_READINESS_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RSR0_CONTRACT_AND_DATA_READINESS_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RSR0_CONTRACT_AND_DATA_READINESS_REVIEW_CN.md
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/manifest.json
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/input_lineage_inventory.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/feature_readiness_audit.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/pit_leakage_audit.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/forbidden_action_audit.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/rsr1_dataset_feasibility.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md
docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
```

## 3. Changes Made

新增只读 RSR1 构建脚本：

```text
scripts/build_tw_policy_rsr1_attribution_diagnostic.py
```

新增 RSR1 diagnostic artifacts 和本执行报告。未新增策略实现，未生成 `OrderIntentArtifact`，未运行 replay，未改 production/default/frontend/daily update/provider/latest。

## 4. Evidence Produced
- Artifacts:
```text
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/manifest.json
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/rsr1_diagnostic_dataset.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/portfolio_state_view.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/feature_schema.json
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/label_schema.json
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/input_lineage_links.json
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/feature_construction_audit.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/label_namespace_audit.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/consumer_forbidden_field_audit.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/pit_leakage_audit.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/diagnostic_summary.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/diagnostic_summary.md
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/forbidden_action_audit.csv
```
- Logs:
```text
python scripts/build_tw_policy_rsr1_attribution_diagnostic.py
python -m py_compile scripts/build_tw_policy_rsr1_attribution_diagnostic.py
```
- Screenshots: not applicable.
- Validator/test output: py_compile passed; artifact/audit files generated.

## 5. Compliance With Mainline

- qlib-only input set used: standard frozen qlib signal, qlib-only TEST fold lineage, full qlib rank, baseline readonly internal ledger, local stock price store, local TWII source.
- `portfolio_state_view.csv` materialized from baseline position snapshots with only `asof_date`、`instrument`、`cost_basis`、`current_holding_flag`、source path/hash. It excludes execution/accounting/PnL/cash/NAV/target/weight/quantity instruction fields.
- Feature schema and label schema are separated. Forward returns appear only as `diagnostic_label_*` columns and are excluded from feature schema.
- Rank deltas use current and historical signal observations only. Score percentile/gap uses same-day cross-section only. TWII MA/drawdown/volatility uses `merge_asof(..., direction=backward)` and TWII rows at or before `signal_date`.
- Diagnostic summary reports distributions, correlations, means, medians, hit rates, coverage, and missingness only. It does not choose a best threshold/rule/bucket or make production strategy claims.

## 6. Forbidden Actions Audit

`forbidden_action_audit.csv` reports all forbidden actions as `PASS_NOT_PERFORMED`: no training, no replay rerun, no threshold tuning, no OrderIntent, no order/position/weight/quantity output, no provider publish, no accepted latest switch, no production/default/frontend/daily update modification, and no external data pull.

## 7. Issues / Blockers / Deviations

No blocker found. Boundary risk: baseline action context is sourced from an internal readonly replay ledger, not a formal OrderIntent/ReplayResult artifact. It is used only as attribution context and not as strategy evidence.

## 8. Files Changed

```text
scripts/build_tw_policy_rsr1_attribution_diagnostic.py
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/manifest.json
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/rsr1_diagnostic_dataset.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/portfolio_state_view.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/feature_schema.json
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/label_schema.json
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/input_lineage_links.json
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/feature_construction_audit.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/label_namespace_audit.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/consumer_forbidden_field_audit.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/pit_leakage_audit.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/diagnostic_summary.csv
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/diagnostic_summary.md
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/forbidden_action_audit.csv
docs/tw_portfolio_decision_model/POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_EXECUTION_REPORT_CN.md
```

## 9. Recommendation For Reviewer

```text
PASS_READY_FOR_REVIEW_REPAIR_NOT_REQUIRED
```
