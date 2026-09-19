---
created_at: 2026-06-23T05:33:02+00:00
status: executed_ral2_existing_pba_action_attribution
phase: RAL2_EXISTING_PBA_ACTION_ATTRIBUTION
artifact_root: data_tw/experiments/rule_attribution_ledger/ral2_existing_pba_action_attribution
strict_test_used: false
training_run: false
production_allowed: false
overall_status: stop_return_to_coordinator_no_ral3_hypothesis
---

# RAL2 Existing PBA Action Attribution 执行报告

本轮只使用 existing PBA evidence：PBA2/PBA3/PBA3-R/PBA-RC artifacts 和 RAL1-R baseline anchor。未训练、未 strict_test、未新增规则、未 RAL3 sanity、未输出 OrderIntent / target_weight / target_position / quantity。

## Documents Read

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ACTION_LEDGER_RULE_ATTRIBUTION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL1_R_BASELINE_REPLAY_DATA_CONTRACT_REPAIR_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL1_R_BASELINE_REPLAY_DATA_CONTRACT_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL1_BASELINE_ACTION_LEDGER_BUILD_AND_PARITY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL0_LEDGER_CONTRACT_MAPPING_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA2_RULE_CALIBRATED_ACTIVE_OVERLAY_SANITY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA3_R_FOLD_STABILITY_CONSTRAINED_REPAIR_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA_RC_REGIME_CONDITIONED_ACTIVE_POLICY_DIAGNOSTIC_REVIEW_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
```

## Key Findings

- PBA2 `score_gap_buy_filter` validation excess 来自 `block_buy` opportunity attribution，但 train/validation 方向不一致。
- PBA3 `shallow_mlp_active_policy_seed_23` validation edge 仍是模型依赖且存在 train 方向反转风险。
- PBA3-R contextual bandit `+0.07789642` 有 validation summary edge，但不足以形成稳定、可解释、非模型化 rule hypothesis。
- PBA-RC `mid_vol no_extra_action` 是 baseline clone/no-extra-action，不是 active edge。
- `buy_filter` 有局部 validation 信号；`delay_sell` validation 负；`no_extra_action` 已单独审计为 clone/no-active contribution。
- 成本主要来自 baseline/allow buy-sell 行；no-extra-action 不产生实际交易成本。

## Recommendation

```text
overall_status = stop_return_to_coordinator_no_ral3_hypothesis
ral3_authorized_by_executor = false
```
