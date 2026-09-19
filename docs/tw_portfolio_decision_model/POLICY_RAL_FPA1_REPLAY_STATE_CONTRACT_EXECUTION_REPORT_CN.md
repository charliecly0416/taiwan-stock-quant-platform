---
created_at: 2026-06-23T10:20:34+00:00
status: pass_ready_for_review
phase: RAL_FPA1_REPLAY_STATE_CONTRACT_FREEZE
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FULL_PATH_BASELINE_PLUS_ACTION_DIAGNOSTIC_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RAL_FPA1_REPLAY_STATE_CONTRACT_WORK_CN.md
artifact_root: data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract
readonly_only: true
simulation_only: true
production_allowed: false
---

# RAL-FPA1 Replay State Contract Freeze 执行报告

## 1. Scope

本轮严格执行 FPA1：冻结 full-path readonly replay state contract，并审计字段可用性、动作空间契约和禁用输出边界。

FPA2 oracle run = false
FPA3 attribution run = false
FPA4 rule sanity run = false
strict_test_used = false
model_training_run = false
production_allowed = false
OrderIntent_output = false
target_weight_output = false
target_position_output = false
quantity_or_broker_output = false

## 2. Documents / Contracts Read

- `docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FULL_PATH_BASELINE_PLUS_ACTION_DIAGNOSTIC_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RAL_FPA1_REPLAY_STATE_CONTRACT_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RAL_ED2_A_BASELINE_REPLAY_ACCOUNTING_AUDIT_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RAL_ED2_A_COORDINATOR_POST_AUDIT_OPINION_CN.md`
- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`

## 3. Source Code and Artifacts Inspected

- `scripts/run_tw_policy_action_model_pa1.py`
- `data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit/manifest.json`
- `data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit/baseline_replay_source_manifest.json`
- `data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit/baseline_summary_recomputed.json`
- `data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit/baseline_nav_recomputed.csv`
- `data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit/baseline_actions_recomputed.csv`
- `data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit/validator_report.json`

## 4. Outputs Produced

- `data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/manifest.json`
- `data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/full_path_replay_state_contract.md`
- `data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/required_state_field_audit.csv`
- `data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/action_space_contract.csv`
- `data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/forbidden_output_audit.csv`
- `data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/validator_report.json`
- `data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/source_artifact_manifest.json`
- `data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/pa1_replay_field_inventory.csv`
- `data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/contract_gap_audit.csv`
- `data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/diagnostic_findings.md`

## 5. State Fields Covered

已覆盖 time/identity、PIT signal slate、portfolio state、pending execution state、cost/turnover state、regime/liquidity state、missing price status。

动作空间覆盖：

- replacement_buy
- sell_timing_advance
- sell_timing_delay
- hold_continuation
- regime_participation_adjustment
- transaction_cost_marginal_filter

## 6. Missing Fields or Blockers

本轮没有 full-path replay 根本性字段 blocker。需要在 FPA2 执行前修复/持久化的缺口有 1 项：

- `post_intervention_path_state_snapshot`: Not a blocker for FPA1 contract, but FPA2 must persist altered path pre/post snapshots.

Contract gap audit 另列出：

- `GAP_FPA2_PRE_POST_PATH_SNAPSHOTS`: FPA2 simulator must persist pre_action_state, post_action_state, pending_order_state, cash/holdings/NAV after each intervention.
- `GAP_ENTRY_DATE_PERSISTENCE`: Persist entry_date and exact holding_days in FPA2 state snapshots.
- `GAP_REPLACEMENT_CANDIDATE_LINEAGE`: Persist candidate slate, excluded baseline candidate, selected replacement candidate, and reason namespace in FPA2 diagnostics.


这些缺口不授权 FPA2 执行；只说明审查者如撰写 FPA2 工作文档，应要求 FPA2 simulator 持久化相应 lineage。

## 7. Forbidden Action Audit Summary

禁用项全部为 `allowed_in_fpa1=false` 且 `present_in_outputs=false`。其中 `quantity/cash/nav/execution_price` 仅可作为内部 replay accounting 字段被契约描述，不得作为策略、OrderIntent、target、broker 或生产输出。

## 8. Validator Summary

```json
{
  "ok": true,
  "status": "PASS_FPA1_REPLAY_STATE_CONTRACT_READY_FOR_REVIEW",
  "phase": "RAL_FPA1_REPLAY_STATE_CONTRACT_FREEZE",
  "failed_count": 0,
  "final_recommendation": "READY_FOR_REVIEWER_TO_CONSIDER_FPA2_WORK_DOC"
}
```

## 9. Final Recommendation

```text
READY_FOR_REVIEWER_TO_CONSIDER_FPA2_WORK_DOC
```

该建议只表示 FPA1 contract freeze 可交给审查者评估是否撰写 FPA2 工作文档；不表示已授权或执行 FPA2 oracle。
