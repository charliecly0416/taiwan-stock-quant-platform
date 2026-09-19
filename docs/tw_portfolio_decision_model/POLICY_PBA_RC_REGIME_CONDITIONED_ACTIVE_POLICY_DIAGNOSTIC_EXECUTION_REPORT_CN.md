---
created_at: 2026-06-22T17:02:51+00:00
status: executed_pba_rc_regime_conditioned_diagnostic
phase: PBA_RC_REGIME_CONDITIONED_ACTIVE_POLICY_DIAGNOSTIC
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_PBA_RC_REGIME_CONDITIONED_ACTIVE_POLICY_DIAGNOSTIC_WORK_CN.md
artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba_rc_regime_conditioned_diagnostic
strict_test_used: false
training_run: false
production_allowed: false
recommendation: PASS_READY_FOR_REVIEWER_TO_CONSIDER_PBA_RC_MODEL_WORK
---

# PBA-RC Regime-conditioned Active Policy Diagnostic 执行报告

## 1. Scope

本轮只做 PBA-RC regime diagnostic，不训练新模型，不运行或读取 strict_test，不进入 PBA5/PBA4，不接 production / OrderIntent / target fields。

## 2. Documents Read

```text
docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA3_R_FOLD_STABILITY_CONSTRAINED_REPAIR_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA3_R_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
```

## 3. Regime Definitions

Regime definitions 已写入 `regime_definition_manifest.json`，覆盖 market_regime、volatility_regime、score_dispersion_regime、baseline_state、action_context；全部为 PIT-safe，未使用 future return、validation-derived threshold 或 strict_test。

## 4. PBA2/PBA3/PBA3-R Regime Metrics

输出：

```text
pba2_regime_replay_metrics.csv
pba3_regime_replay_metrics.csv
pba3_r_regime_replay_metrics.csv
```

## 5. Key Diagnostic Answers

PBA2/PBA3/PBA3-R 的 active overlay edge 呈 regime-specific，而不是全局稳定。PBA3-R contextual bandit 在 risk_off 的失败证据：

```text
[{'source_stage': 'PBA3_R', 'policy_or_rule_id': 'contextual_bandit_conservative_stability_constrained', 'regime_family': 'market_regime', 'regime_name': 'risk_off', 'action_context': 'buy_filter', 'date_count': 1, 'baseline_net_return_after_fee_tax': -0.08915072, 'active_overlay_net_return_after_fee_tax': -0.08915072, 'excess_return_after_fee_tax': 0.0, 'turnover': 0.17374228, 'cost_drag': 0.00060439, 'participation_rate': 0.98669623, 'risk_asset_exposure': 0.99586777, 'cash_dominance_rate': 0.00413223, 'active_decision_change_rate': 0.1, 'baseline_clone_flag': False, 'status': 'fail'}, {'source_stage': 'PBA3_R', 'policy_or_rule_id': 'contextual_bandit_conservative_stability_constrained', 'regime_family': 'market_regime', 'regime_name': 'risk_off', 'action_context': 'no_extra_action', 'date_count': 23, 'baseline_net_return_after_fee_tax': -0.04035368, 'active_overlay_net_return_after_fee_tax': -0.05728356, 'excess_return_after_fee_tax': -0.01692988, 'turnover': 3.99607254, 'cost_drag': 0.01390105, 'participation_rate': 0.98669623, 'risk_asset_exposure': 0.99586777, 'cash_dominance_rate': 0.00413223, 'active_decision_change_rate': 0.0, 'baseline_clone_flag': True, 'status': 'fail'}]
```

PBA2 risk_off evidence：

```text
[{'source_stage': 'PBA2', 'policy_or_rule_id': 'score_gap_buy_filter', 'regime_family': 'market_regime', 'regime_name': 'risk_off', 'action_context': 'buy_filter', 'date_count': 11, 'baseline_net_return_after_fee_tax': -0.03308285, 'active_overlay_net_return_after_fee_tax': -0.02221806, 'excess_return_after_fee_tax': 0.01086479, 'turnover': 0.56596432, 'cost_drag': 0.00198904, 'participation_rate': 0.90023202, 'risk_asset_exposure': 0.99173554, 'cash_dominance_rate': 0.00826446, 'active_decision_change_rate': 0.09834711, 'baseline_clone_flag': False, 'status': 'pass'}, {'source_stage': 'PBA2', 'policy_or_rule_id': 'score_gap_buy_filter', 'regime_family': 'market_regime', 'regime_name': 'risk_off', 'action_context': 'no_extra_action', 'date_count': 27, 'baseline_net_return_after_fee_tax': -0.10447802, 'active_overlay_net_return_after_fee_tax': -0.05175342, 'excess_return_after_fee_tax': 0.0527246, 'turnover': 1.38918516, 'cost_drag': 0.0048822, 'participation_rate': 0.90023202, 'risk_asset_exposure': 0.99173554, 'cash_dominance_rate': 0.00826446, 'active_decision_change_rate': 0.0, 'baseline_clone_flag': True, 'status': 'pass'}]
```

PBA3 risk_off evidence：

```text
[{'source_stage': 'PBA3', 'policy_or_rule_id': 'shallow_mlp_active_policy_seed_23', 'regime_family': 'market_regime', 'regime_name': 'risk_off', 'action_context': 'buy_filter', 'date_count': 4, 'baseline_net_return_after_fee_tax': -0.11344471, 'active_overlay_net_return_after_fee_tax': -0.10265956, 'excess_return_after_fee_tax': 0.01078515, 'turnover': 0.22901879, 'cost_drag': 0.00085815, 'participation_rate': 0.98013245, 'risk_asset_exposure': 0.99173554, 'cash_dominance_rate': 0.00826446, 'active_decision_change_rate': 0.1, 'baseline_clone_flag': False, 'status': 'pass'}, {'source_stage': 'PBA3', 'policy_or_rule_id': 'shallow_mlp_active_policy_seed_23', 'regime_family': 'market_regime', 'regime_name': 'risk_off', 'action_context': 'no_extra_action', 'date_count': 34, 'baseline_net_return_after_fee_tax': -0.02330338, 'active_overlay_net_return_after_fee_tax': -0.01494593, 'excess_return_after_fee_tax': 0.00835745, 'turnover': 1.94665974, 'cost_drag': 0.00729427, 'participation_rate': 0.98013245, 'risk_asset_exposure': 0.99173554, 'cash_dominance_rate': 0.00826446, 'active_decision_change_rate': 0.0, 'baseline_clone_flag': True, 'status': 'pass'}]
```

## 6. Regime Gate Candidate Audit

简单 gate candidate 已写入 `regime_gate_candidate_audit.csv`。本轮只做 audit，不声明进入 PBA5。

## 7. Participation / Cash / Risk / Change-rate By Regime

输出：

```text
participation_gate_by_regime.csv
cash_dominance_gate_by_regime.csv
risk_asset_exposure_by_regime.csv
active_decision_change_rate_by_regime.csv
baseline_clone_by_regime.csv
```

## 8. Issues / Blockers / Deviations

部分 by-regime turnover / cost_drag 为 split-level readonly summary 按日期占比分摊的 diagnostic proxy，因为既有 ledger 不含逐日费用。该限制已保留在诊断语义内，未用于生产。

## 9. Recommendation

```text
PASS_READY_FOR_REVIEWER_TO_CONSIDER_PBA_RC_MODEL_WORK
```
