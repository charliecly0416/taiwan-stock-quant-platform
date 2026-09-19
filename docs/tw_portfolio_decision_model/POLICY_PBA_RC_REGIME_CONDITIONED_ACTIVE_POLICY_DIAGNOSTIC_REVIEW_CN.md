---
created_at: 2026-06-22
status: review_stop_return_to_coordinator
phase_reviewed: PBA_RC_REGIME_CONDITIONED_ACTIVE_POLICY_DIAGNOSTIC
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_PBA_RC_REGIME_CONDITIONED_ACTIVE_POLICY_DIAGNOSTIC_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_PBA_RC_REGIME_CONDITIONED_ACTIVE_POLICY_DIAGNOSTIC_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba_rc_regime_conditioned_diagnostic
verdict: STOP_RETURN_TO_COORDINATOR_NO_PBA_RC_MODEL_WORK_AUTHORIZATION
diagnostic_artifacts_complete: true
strict_test_authorized: false
strict_test_used: false
training_authorized: false
training_run: false
pba5_authorized: false
pba4_offline_rl_authorized: false
qlib_ltr_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity: true
---

# PBA-RC Regime-conditioned Active Policy Diagnostic 审查报告

## 1. 审查结论

结论：

```text
STOP_RETURN_TO_COORDINATOR_NO_PBA_RC_MODEL_WORK_AUTHORIZATION
```

执行者完成了 PBA-RC regime diagnostic 的主要产物，且边界控制基本合规：

```text
strict_test_used = false
training_run = false
no_pba5_request = true
no_pba4_offline_rl = true
no_qlib_ltr = true
no_order_intent_output = true
no_target_weight = true
no_target_position = true
no_quantity = true
no_provider_monitor_frontend_agent_production = true
```

但是执行报告给出的：

```text
PASS_READY_FOR_REVIEWER_TO_CONSIDER_PBA_RC_MODEL_WORK
```

证据不足，不应由审查者直接授权进入 PBA-RC 模型工作。

本轮诊断更合理的结论是：

```text
PBA-RC 证明 active overlay 的收益确实 regime-specific；
但当前还没有足够强的、非 baseline-clone 的、跨 PBA2/PBA3/PBA3-R 一致正收益 regime gate；
因此应回到统筹，由统筹决定是否开新主线、缩小问题，或关闭 PBA。
```

## 2. 合同完成情况

工作文档要求的 artifact root 已生成：

```text
data_tw/experiments/baseline_anchored_active_policy/pba_rc_regime_conditioned_diagnostic/
```

文件齐全：

```text
manifest.json
regime_definition_manifest.json
pba2_regime_replay_metrics.csv
pba3_regime_replay_metrics.csv
pba3_r_regime_replay_metrics.csv
regime_excess_return_summary.csv
regime_failure_attribution.csv
regime_gate_candidate_audit.csv
active_decision_change_rate_by_regime.csv
participation_gate_by_regime.csv
cash_dominance_gate_by_regime.csv
risk_asset_exposure_by_regime.csv
cost_turnover_by_regime.csv
baseline_clone_by_regime.csv
feature_available_at_audit.csv
forbidden_feature_and_consumer_audit.csv
validator_report.json
golden_samples_report.json
```

`regime_definition_manifest.json` 覆盖：

```text
market_regime
volatility_regime
score_dispersion_regime
baseline_state
action_context
```

并声明：

```text
uses_future_return = false
uses_validation_metric = false
uses_strict_test = false
pit_safe = true
```

评价：

```text
PASS_AS_DIAGNOSTIC_ARTIFACT_COMPLETION
```

## 3. 关键发现

### 3.1 执行边界合规

`validator_report.json` 显示：

```text
strict_test_not_used = true
no_training_run = true
no_pba5_request = true
no_pba4_offline_rl = true
no_qlib_ltr = true
no_order_intent_output = true
no_target_weight = true
no_target_position = true
no_quantity = true
no_broker_order = true
no_provider_monitor_frontend_agent_production = true
feature_available_at_audit_pass = true
forbidden_feature_and_consumer_audit_pass = true
```

评价：

```text
PASS
```

本轮没有越权进入 strict_test、PBA5、PBA4、qlib+LTR、生产链路或订单链路。

### 3.2 Regime-specific 现象成立，但方向不支持直接开模型子线

`regime_excess_return_summary.csv` 显示多数 market regime 并不稳定：

```text
market_regime caution buy_filter:
  positive_source_count = 0
  negative_source_count = 2
  mean_excess_return = -0.00383175
  status = fail

market_regime normal buy_filter:
  positive_source_count = 1
  negative_source_count = 2
  mean_excess_return = -0.08799341
  status = fail

market_regime normal no_extra_action:
  positive_source_count = 1
  negative_source_count = 2
  mean_excess_return = -0.48466494
  status = fail
```

只有一个跨 PBA2/PBA3/PBA3-R 一致正 excess 的条目：

```text
volatility_regime mid_vol no_extra_action:
  consistent_positive_across_pba2_pba3_pba3r = true
  mean_excess_return = 0.03396951
  positive_sources = PBA2;PBA3;PBA3_R
  negative_source_count = 0
  status = pass
```

但该条目是 `no_extra_action`，不是明确的 active overlay 决策。结合 `baseline_clone_by_regime.csv`，PBA3-R 的 `no_extra_action` 多数为 baseline clone：

```text
PBA3_R market_regime normal no_extra_action baseline_clone_flag = True
PBA3_R market_regime caution no_extra_action baseline_clone_flag = True
PBA3_R volatility_regime mid_vol no_extra_action baseline_clone_flag = True
```

评价：

```text
PASS_FOR_DIAGNOSIS
FAIL_FOR_MODEL_WORK_AUTHORIZATION
```

这说明诊断捕捉到了 regime 依赖，但不能把 `no_extra_action` 的正收益直接解释成“可训练 active policy edge”。

### 3.3 Gate candidate 不满足进入模型工作的条件

`regime_gate_candidate_audit.csv` 中唯一 `status=pass` 的 gate 是：

```text
gate_id = pba3_normal_caution_risk_off_baseline
baseline_net_return_after_fee_tax = 0.95376772
gated_overlay_net_return_after_fee_tax = 1.11566342
excess_return_after_fee_tax = 0.16189570
active_decision_change_rate = 0.00553586
baseline_clone_flag = False
status = pass
```

但这个 gate 来自 PBA3 的 `shallow_mlp_active_policy_seed_23` 方向，而 PBA3 既有审查已经判定：

```text
fold_stability_pass = false
FAIL_STOP_NO_STRICT_TEST_NO_PBA5
```

PBA3-R 对应 gate：

```text
gate_id = pba3r_normal_caution_risk_off_baseline
excess_return_after_fee_tax = 0.11438211
active_decision_change_rate = 0.00217774
baseline_clone_flag = True
status = fail
```

评价：

```text
FAIL_FOR_NEXT_MODEL_AUTHORIZATION
```

一个来自已失败 PBA3 模型的 gate，不能单独支撑新模型工作；而修复后 PBA3-R 的 gate 又退化为 baseline clone / active rate 过低。

### 3.4 Risk-off 诊断有价值，但没有形成稳定处理规则

执行报告指出 PBA3-R contextual bandit 在 `risk_off` 下失败：

```text
PBA3_R market_regime risk_off no_extra_action:
  baseline_net_return_after_fee_tax = -0.04035368
  active_overlay_net_return_after_fee_tax = -0.05728356
  excess_return_after_fee_tax = -0.01692988
  baseline_clone_flag = True
  status = fail
```

但 PBA2 / PBA3 在 `risk_off` 上反而有部分正 excess：

```text
PBA2 risk_off buy_filter excess = +0.01086479
PBA2 risk_off no_extra_action excess = +0.05272460
PBA3 risk_off buy_filter excess = +0.01078515
PBA3 risk_off no_extra_action excess = +0.00835745
```

评价：

```text
MIXED
```

这说明 `risk_off 一律 fallback baseline` 还不是充分证明的规则。当前更像是：

```text
不同 active overlay 机制在 risk_off 的行为差异很大；
PBA3-R contextual bandit 的失败不能直接推广成所有 overlay 的 risk_off 失败。
```

### 3.5 成本与换手为 proxy，不能用于强结论

执行报告承认：

```text
部分 by-regime turnover / cost_drag 为 split-level readonly summary 按日期占比分摊的 diagnostic proxy，
因为既有 ledger 不含逐日费用。
```

评价：

```text
PASS_WITH_LIMITATION
```

这在诊断阶段可以接受，但不允许把该 proxy 当成进入 strict_test 或模型工作的强成本证据。

## 4. 对工作文档进入条件的逐项判断

工作文档要求“可建议统筹考虑 PBA-RC 模型工作文档”的条件包括：

```text
1. 至少一个预定义 regime 中，PBA2/PBA3/PBA3-R active overlay 对 baseline 有一致正 excess。
2. risk_off 或失败 regime 的损害来源可解释。
3. 简单 regime gate 能降低负 regime 伤害，同时不把策略退化成 baseline clone。
4. participation / risk exposure / cash dominance 仍不过度退化。
5. active decision change rate 高于最低阈值。
6. 所有分析不使用 strict_test，不使用 future feature，不用 validation 反复调参。
```

本轮判断：

```text
1. FAIL_AS_ACTIVE_OVERLAY_EDGE
   只有 mid_vol no_extra_action 一致正 excess，但 no_extra_action / baseline clone 不能证明 active overlay edge。

2. PARTIAL
   PBA3-R risk_off 失败可解释，但 PBA2/PBA3 risk_off 并非一致失败。

3. FAIL
   PBA3 gate pass 来自既有 fold-stability failed 模型；PBA3-R gate baseline_clone_flag=True 且 active_decision_change_rate 不足。

4. PASS
   participation / risk exposure / cash dominance 没有 cash/no-trade 退化。

5. MIXED_FAIL
   PBA3 gate 勉强超过阈值，但来源模型已失败；PBA3-R gate active_decision_change_rate=0.00217774 且 status=fail。

6. PASS
   未见 strict_test、future feature 或生产链路越权。
```

综合：

```text
NOT_READY_FOR_PBA_RC_MODEL_WORK
```

## 5. 审查意见

### S1: 执行报告的推荐结论过度

严重级别：

```text
S1_BLOCKER_FOR_NEXT_PHASE
```

执行报告建议：

```text
PASS_READY_FOR_REVIEWER_TO_CONSIDER_PBA_RC_MODEL_WORK
```

但产物本身显示：

```text
跨 PBA2/PBA3/PBA3-R 一致正 excess 的有效 active regime 不充分；
唯一稳定正项偏向 no_extra_action / baseline clone；
可用 gate 依赖已失败的 PBA3 模型或退化为 PBA3-R baseline clone。
```

因此审查者不能据此开 PBA-RC 模型工作文档。

### S2: 诊断报告过短，关键问题主要依赖 artifact 反推

严重级别：

```text
S2_EVIDENCE_PRESENT_BUT_UNDER_EXPLAINED
```

执行报告没有逐条展开工作文档要求的 8 个问题，尤其是：

```text
normal/caution 是否启用 overlay；
score dispersion 高/低差异；
baseline strong/weak/drawdown 差异；
持仓年龄、趋势、波动对 delay_sell / block_buy 的影响；
简单 gate 是否非 baseline-clone。
```

由于 artifact 中有对应信息，本项不要求 repair，但未来同类执行报告必须把 artifact 结论写进正文，不能只列文件。

## 6. 最终裁定

最终裁定：

```text
STOP_RETURN_TO_COORDINATOR_NO_PBA_RC_MODEL_WORK_AUTHORIZATION
```

允许保留本轮诊断产物作为统筹参考。

不得进入：

```text
PBA-RC model work
PBA5 strict-test final replay
strict_test
PBA4 offline RL
qlib+LTR
production/default
OrderIntent / target_weight / target_position / quantity
provider/latest/monitor/frontend/Agent/broker
```

建议统筹下一步只在以下选项中选择：

```text
1. 关闭 PBA 路线，归档为“有局部 validation signal，但不足以继续模型化”。
2. 另开新的、更窄的诊断主线，只研究 mid_vol / no_extra_action 是否是 baseline replay artifact，而不是 active policy edge。
3. 另开新的数据合同工作，补齐逐日费用/turnover ledger 后再判断 regime gate。
```

审查者本轮不撰写下一步执行文档，因为当前结论是 STOP_RETURN_TO_COORDINATOR，且 PBA 主线没有授权审查者擅自开启新的模型子线或拆分新步骤。
