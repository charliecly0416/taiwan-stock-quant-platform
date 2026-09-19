---
created_at: 2026-06-22T17:32:42+00:00
status: executed_policy_model_research_route_closure
phase: POLICY_MODEL_RESEARCH_ROUTE_CLOSURE
artifact_root: data_tw/experiments/policy_model_research_route_closure
strict_test_used: false
training_run: false
production_allowed: false
recommendation: PASS_READY_FOR_REVIEWER_TO_CLOSE_POLICY_MODEL_RESEARCH_ROUTE
---

# Policy Model Research Route Closure 执行报告

## 1. Scope

本轮只做 policy model research route closure：汇总既有 PAL / PBA / PBA-RC review、execution report 和 artifacts。未训练模型，未运行或读取 strict_test，未进入 PBA5 / PAL3 / PBA4，未扩展 qlib+LTR，未输出 OrderIntent / target_weight / target_position / quantity / broker_order，未触碰 provider/latest/monitor/frontend/Agent/broker/production/default。

## 2. Documents Read

```text
docs/tw_portfolio_decision_model/POLICY_PAL_PAPER_ALIGNED_PORTFOLIO_ALLOCATION_RL_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PAL2_MINIMAL_EIIE_CNN_TRAINING_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PAL2_R_COST_AWARE_CONCENTRATION_CONSTRAINED_EIIE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA2_RULE_CALIBRATED_ACTIVE_OVERLAY_SANITY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA3_R_FOLD_STABILITY_CONSTRAINED_REPAIR_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA_RC_REGIME_CONDITIONED_ACTIVE_POLICY_DIAGNOSTIC_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA3_R_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
```

## 3. Route Evidence Summary

### PAL Free Allocation / EIIE

PAL2 minimal EIIE-CNN：validation baseline = `0.95376753`，best selected net after fee/tax = `0.66673752`。虽然 gross return 可高，但 cost drag 高、concentration fail、seed stability fail。

PAL2-R cost/concentration repair：selected mean validation net after fee/tax = `0.02833287`，baseline = `0.95376753`。repair 降低 turnover/cost，但退化为 cash/no-trade dominant，seed stability fail。

结论：free allocation action space 在当前项目设置下不稳定；无约束时高成本/高集中，加强约束后 cash/no-trade。关闭 PAL free allocation / EIIE 子线，不授权 PAL3、strict_test 或 full GPU training。

### PBA Baseline-anchored Active Policy

PBA2 selected rule `score_gap_buy_filter`：validation = `0.97910586`，baseline = `0.95376753`，excess = `+0.02533833`，但 train/validation 方向不一致。

PBA3 selected `shallow_mlp_active_policy_seed_23`：validation = `1.20247421`，baseline = `0.95376753`，excess = `+0.24870668`；participation / cash / OOD / clone gates pass，但 fold stability fail，train excess = `-0.92621018`。

PBA3-R：stability-constrained selected model 退化为 baseline clone，validation = `0.95376753`，excess = `0.0`，active decision change rate fail。contextual bandit 仍有 `+0.07789642` validation excess，但 fold stability fail / risk_off fail / active rate below minimum。

结论：PBA action space 比 PAL 更合理，并产生过局部 validation signal；但 model edge 未能同时满足收益、fold stability、非 clone active change。关闭 PBA active policy 模型子线，不授权 PBA5 strict_test。

### PBA-RC Regime Diagnostic

PBA-RC 证明 active overlay 收益存在 regime-specific 现象，但没有足够强的、跨 PBA2/PBA3/PBA3-R 一致正收益的非 baseline-clone active regime。

唯一一致正项：`volatility_regime mid_vol no_extra_action`，mean_excess_return = `+0.03396951`，但 `no_extra_action` / baseline clone 不能证明 active policy edge。

唯一 gate pass：`pba3_normal_caution_risk_off_baseline`，excess = `+0.16189570`，active_decision_change_rate = `0.00553586`，baseline_clone_flag = false；但来源是 fold-stability failed 的 PBA3 model。PBA-RC review 已给出 `STOP_RETURN_TO_COORDINATOR_NO_PBA_RC_MODEL_WORK_AUTHORIZATION`。

结论：regime 诊断有研究价值，但不足以授权 PBA-RC model work。

## 4. Failure Taxonomy

已输出 `route_failure_taxonomy.csv`，覆盖：

```text
high turnover cost drag
concentration
cash/no-trade degeneration
fold instability
baseline clone
regime-specific non-transferable edge
insufficient active decision change rate
```

## 5. Final Closure Decision

```text
PAL free allocation / EIIE 子线关闭。
PBA baseline-anchored active policy 模型子线关闭。
PBA-RC regime-conditioned model work 不授权。
PBA2/PBA3/PBA-RC 的局部 validation signal 保留为 readonly research evidence。
当前不再继续同线 policy/RL/active overlay 模型训练。
当前不授权 strict_test / qlib+LTR / production / OrderIntent。
```

核心解释：当前强 qlib baseline 已经吃掉主要 ranking alpha；policy 层只能做二阶微调。二阶微调在当前数据窗口下表现为信号弱、样本少、regime 依赖强、交易成本敏感。因此训练独立 policy model 的边际收益目前不稳定，不足以进入 strict_test 或生产化。

这不是 policy 理论上永远无效，而是在当前数据、合同、action space、baseline 条件下，继续同线训练 policy model 的短期性价比不高。

## 6. Retained Research Value

见 `retained_research_value.md`。保留价值包括：PAL 排除了当前 free allocation 路线，PBA 找到更合理 action space，PBA2/PBA3 证明局部 validation signal，PBA3-R/PBA-RC 证明稳定性不足，并形成未来重启所需 artifact / gate / failure taxonomy。

## 7. Future Restart Requirements

见 `future_restart_requirements.md`。重启前必须补齐 action-level / symbol-level / daily ledger，扩大 rolling walk-forward 数据窗口，等待新 signal/OOS 边界更清楚，并重新写 coordinator mainline。

## 8. Forbidden Actions Audit

`forbidden_action_closure_audit.csv` 全部 pass：未训练、未 strict_test、未进入 PBA5/PAL3/PBA4、未 qlib+LTR、未输出 OrderIntent/target fields/quantity/broker order、未触碰 production/default/provider/latest/monitor/frontend/Agent/broker。

## 9. Recommendation for Reviewer

```text
PASS_READY_FOR_REVIEWER_TO_CLOSE_POLICY_MODEL_RESEARCH_ROUTE
```
