---
created_at: 2026-06-22
status: coordinator_opinion_for_reviewer
scope: after_pba3_r_fold_stability_constrained_repair_review
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
review_doc: docs/tw_portfolio_decision_model/POLICY_PBA3_R_FOLD_STABILITY_CONSTRAINED_REPAIR_REVIEW_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_PBA3_R_FOLD_STABILITY_CONSTRAINED_REPAIR_EXECUTION_REPORT_CN.md
recommended_next: PBA_RC_REGIME_CONDITIONED_ACTIVE_POLICY_DIAGNOSTIC
pba5_authorized: false
strict_test_authorized: false
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

# PBA3-R 统筹意见：关闭同线模型修复，转 Regime-conditioned Active Policy 诊断

## 1. 统筹结论

本轮 `PBA3-R Fold-stability Constrained Repair` 的审查结论成立：

```text
FAIL_STOP_NO_STRICT_TEST_NO_PBA5
```

不得授权：

```text
PBA5 strict-test final replay
strict_test
PBA4 offline RL
qlib+LTR adapter
OrderIntent / target_weight / target_position / quantity
provider/latest/monitor/frontend/Agent/broker/production
```

同时，不建议继续做：

```text
PBA3 / PBA3-R 同线小模型无界 repair。
```

统筹建议下一步转向：

```text
PBA-RC = Regime-conditioned Active Policy Diagnostic
```

目标不是马上训练新模型，而是先验证：

```text
PBA2/PBA3 的 active overlay 收益是否只存在于特定 market regime / score regime / baseline state。
```

如果诊断证明 edge 是 regime-specific，再由统筹决定是否写新的 PBA-RC 模型工作文档。

## 2. 当前证据复盘

PBA3 原始模型曾出现强 validation signal：

```text
selected_model_id = shallow_mlp_active_policy_seed_23
validation_baseline_net_return_after_fee_tax = 0.95376753
selected_validation_net_return_after_fee_tax = 1.20247421
selected_excess_return_after_fee_tax = +0.24870668
```

且当时没有出现 PAL 路线的典型退化：

```text
cash/no-trade dominant = false
OOD action = false
baseline clone = false
forbidden consumer = false
```

但 PBA3 的硬伤是：

```text
train_excess_return = -0.92621018
validation_excess_return = +0.24870668
fold_stability_pass = false
```

PBA3-R 尝试修复 fold stability 后，结果变成：

```text
fold-stable candidates -> baseline clone / active decision change rate = 0
non-clone-ish candidate -> fold stability fail / risk_off fail / active decision change rate below minimum
```

关键证据：

```text
selected_model_id = supervised_utility_logistic_or_tree_stability_constrained
selected_validation_net_return_after_fee_tax = 0.95376753
selected_excess_return_after_fee_tax = 0.0
not_baseline_clone = false
active_decision_change_rate_pass = false
```

唯一仍有 validation excess 的候选：

```text
contextual_bandit_conservative_stability_constrained
validation_net_return_after_fee_tax = 1.03166395
excess = +0.07789642
positive_excess_fold_count = 2
negative_excess_fold_count = 2
fold_stability_pass = false
risk_off regime = fail
active_decision_change_rate = 0.00367377 < 0.005
```

## 3. 底层失败原因判断

### 3.1 不是 PBA action space 彻底无效

PBA2 rule 和 PBA3 supervised/bandit 都曾在 2025 validation 上超过 baseline：

```text
PBA2 score_gap_buy_filter excess = +0.02533833
PBA3 shallow_mlp seed_23 excess = +0.24870668
PBA3-R contextual_bandit excess = +0.07789642
```

这说明 baseline-anchored active overlay 方向仍有实验价值。

### 3.2 当前问题是 edge 不具备全局稳定性

PBA3/PBA3-R 的共同现象：

```text
有收益的候选无法跨 fold / regime 稳定；
稳定的候选退化为不改 baseline。
```

这说明 active overlay 可能不是全市场、全时段通用规则，而是：

```text
只在某些 regime 下有效；
在 risk_off 或其它 regime 下可能损害 baseline；
如果强迫全局稳定，模型只能退回 baseline clone。
```

### 3.3 继续原地修 PBA3 小模型收益不高

继续做同线 repair 会在两种失败之间摆动：

```text
放松约束 -> validation edge 强，但 fold/regime 不稳；
加强约束 -> 稳定，但 active decision change rate 接近 0，退回 baseline clone。
```

因此当前不应继续追求一个全局 active policy，而应先回答：

```text
哪些 regime 允许 active overlay？
哪些 regime 必须退回 baseline？
```

## 4. 下一步授权：PBA-RC 诊断，不是训练

授权审查者撰写下一步工作文档：

```text
docs/tw_portfolio_decision_model/POLICY_PBA_RC_REGIME_CONDITIONED_ACTIVE_POLICY_DIAGNOSTIC_WORK_CN.md
```

本阶段只做诊断和合同设计，不训练新模型，不 strict_test。

目标：

```text
把 PBA2/PBA3/PBA3-R 的 active overlay 行为按 regime 拆开，
判断收益来自哪些市场状态、score 状态、baseline 状态、持仓状态。
```

## 5. PBA-RC 诊断应回答的问题

执行者必须至少回答：

```text
1. PBA2 selected rule 在哪些 regime 赢 baseline，哪些 regime 输 baseline？
2. PBA3 selected model 在哪些 regime 赢 baseline，哪些 regime 输 baseline？
3. PBA3-R contextual bandit 在 risk_off 为什么失败？
4. active overlay 的收益是否主要来自 normal regime？
5. score dispersion 高/低时，active overlay 是否效果不同？
6. baseline 自身强/弱时，active overlay 是否效果不同？
7. 当前持仓年龄、趋势、波动状态是否影响 delay_sell / block_buy 的收益？
8. 是否存在一个简单的 regime gate：
   normal/caution 启用 active overlay；
   risk_off 退回 baseline 或只允许保守规则。
```

## 6. 建议 regime 切分

PBA-RC 诊断至少覆盖：

```text
market_regime:
  normal
  caution
  risk_off

volatility_regime:
  low_vol
  mid_vol
  high_vol

score_dispersion_regime:
  low_dispersion
  mid_dispersion
  high_dispersion

baseline_state:
  baseline_recent_strong
  baseline_recent_weak
  baseline_drawdown

action_context:
  buy_filter
  sell_delay
  no_extra_action
  top_rank_tilt_diagnostic
```

所有 regime 定义必须 PIT-safe，不得使用 future return 或 validation 结果倒推。

## 7. 通过条件建议

PBA-RC 诊断不以“策略通过”为目标，而以“是否值得开 PBA-RC 模型子线”为目标。

可进入下一步 PBA-RC 模型工作文档的条件：

```text
1. 至少一个预定义 regime 中，PBA2/PBA3/PBA3-R active overlay 对 baseline 有一致正 excess。
2. risk_off 或失败 regime 的损害来源可解释。
3. 简单 regime gate 能降低负 regime 伤害，同时不把策略退化成 baseline clone。
4. participation / risk exposure / cash dominance 仍不过度退化。
5. active decision change rate 高于最低阈值。
6. 所有分析不使用 strict_test，不使用 future feature，不用 validation 反复调参。
```

如果诊断结果显示：

```text
没有任何 regime 存在稳定 active edge；
或启用 regime gate 后只是 baseline clone；
```

则应回到统筹，考虑：

```text
1. 暂停 qlib-only PBA 模型子线；
2. 只保留 PBA2 rule-based overlay 为 readonly research artifact；
3. 重新规划 policy 数据窗口；
4. 等 qlib/LTR 信号更新后再评估 policy。
```

## 8. 禁止事项

PBA-RC 诊断仍禁止：

```text
strict_test
PBA5
PBA4 offline RL
qlib+LTR
训练新模型
无界调参
free allocation vector
target_weight
target_position
quantity
OrderIntent
broker / quick-trade / real order
provider publish / accepted latest switch
monitor write
frontend default
Agent recommendation
production/default 策略切换
```

## 9. 建议产物

建议审查者要求执行者输出：

```text
data_tw/experiments/baseline_anchored_active_policy/pba_rc_regime_conditioned_diagnostic/
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

docs/tw_portfolio_decision_model/POLICY_PBA_RC_REGIME_CONDITIONED_ACTIVE_POLICY_DIAGNOSTIC_EXECUTION_REPORT_CN.md
```

## 10. 给审查者的下一步指令

请审查者基于本意见文档撰写：

```text
docs/tw_portfolio_decision_model/POLICY_PBA_RC_REGIME_CONDITIONED_ACTIVE_POLICY_DIAGNOSTIC_WORK_CN.md
```

工作文档应要求执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA3_R_FOLD_STABILITY_CONSTRAINED_REPAIR_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA3_R_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
```

不得写：

```text
PBA5 strict-test 工作文档
PBA4 offline RL 工作文档
qlib+LTR adapter 工作文档
production integration 工作文档
```

## 11. 最终控制

当前最终控制是：

```text
PBA3/PBA3-R 同线模型 repair: stop
PBA-RC regime diagnostic: authorized
PBA5 strict_test: not authorized
PBA4 offline RL: not authorized
qlib+LTR: not authorized
production/default/order: not authorized
```

这不是关闭 PBA 方向，而是把问题从：

```text
训练一个全局 active policy
```

收敛到更符合证据的：

```text
识别哪些 regime 下 active overlay 才有正收益。
```
