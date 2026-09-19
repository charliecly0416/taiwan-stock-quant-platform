---
created_at: 2026-06-22
status: coordinator_work_document
phase: POLICY_MODEL_RESEARCH_ROUTE_CLOSURE
scope: close_pal_pba_policy_model_research_after_regime_diagnostic
mainline_docs:
  - docs/tw_portfolio_decision_model/POLICY_PAL_PAPER_ALIGNED_PORTFOLIO_ALLOCATION_RL_MAINLINE_CN.md
  - docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
latest_reviews:
  - docs/tw_portfolio_decision_model/POLICY_PAL2_R_COST_AWARE_CONCENTRATION_CONSTRAINED_EIIE_REVIEW_CN.md
  - docs/tw_portfolio_decision_model/POLICY_PBA3_R_FOLD_STABILITY_CONSTRAINED_REPAIR_REVIEW_CN.md
  - docs/tw_portfolio_decision_model/POLICY_PBA_RC_REGIME_CONDITIONED_ACTIVE_POLICY_DIAGNOSTIC_REVIEW_CN.md
strict_test_authorized: false
training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity: true
---

# Policy Model Research Route Closure 工作文档

## 1. 本轮目标

你是执行者。请对当前 policy model research 路线做收尾，形成 closure。

本轮不是新实验，不是 repair，不是训练，也不是 strict_test。

目标是把已经完成的 PAL / PBA / PBA-RC 证据整理成一份可审查的路线收尾报告，回答：

```text
在当前 qlib-only 信号、当前 2023-2025 policy 数据窗口、当前 action space 与合同边界下，
训练独立 policy / RL / active overlay model 是否已经显示出稳定可用的收益提升？
为什么不继续投入同线模型化？
未来如重启，需要先补什么数据或合同？
```

## 2. 必须读取

执行前必须读取：

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

如需引用早期证据，也可读取：

```text
docs/tw_portfolio_decision_model/POLICY_PRL1_R1_R_PARTICIPATION_CONSTRAINED_REPAIR_STAGE_SUMMARY_CN.md
docs/tw_portfolio_decision_model/POLICY_PAV2_ACTION_VALUE_RANKER_REPAIR_REVIEW_AND_ROUTE_CLOSURE_CN.md
docs/tw_portfolio_decision_model/POLICY_PE1_REPAIR_QLIB_ONLY_ACTIVE_POLICY_SEARCH_REVIEW_CN.md
```

## 3. 授权范围

本轮只允许：

```text
1. 汇总既有 review / execution report / artifact 指标。
2. 读取既有 CSV / JSON artifact 做表格摘录。
3. 写 closure execution report。
4. 形成路线状态、失败模式、保留价值、未来重启条件。
```

本轮禁止：

```text
1. 训练任何模型。
2. 运行或读取 strict_test。
3. 进入 PBA5 / PAL3 / PBA4 offline RL。
4. 扩展 qlib+LTR。
5. 新增策略、规则、模型、action space 或调参。
6. 输出 OrderIntent。
7. 输出 target_weight / target_position / quantity / broker_order。
8. provider publish / accepted latest switch。
9. monitor write / frontend default / Agent recommendation。
10. broker / quick-trade / real order。
11. 修改 production/default 策略。
```

## 4. 必须形成的 Closure 判断

执行报告必须明确写出以下统筹判断，但可以用证据支持、补充或细化：

```text
1. PAL free allocation / EIIE 子线关闭。
2. PBA baseline-anchored active policy 模型子线关闭。
3. PBA-RC regime-conditioned model work 不授权。
4. PBA2/PBA3/PBA-RC 的局部 validation signal 保留为 readonly research evidence。
5. 当前不再继续同线 policy/RL/active overlay 模型训练。
6. 当前不授权 strict_test / qlib+LTR / production / OrderIntent。
```

Closure 的核心解释应是：

```text
当前强 qlib baseline 已经吃掉主要 ranking alpha；
policy 层只能做二阶微调；
二阶微调在当前数据窗口下表现为信号弱、样本少、regime 依赖强、交易成本敏感；
因此训练独立 policy model 的边际收益目前不稳定，不足以进入 strict_test 或生产化。
```

不要写成：

```text
policy 理论上永远无效。
```

应写成：

```text
在当前数据、合同、action space、baseline 条件下，继续同线训练 policy model 的短期性价比不高。
```

## 5. 必须汇总的路线证据

### 5.1 PAL Free Allocation / EIIE

必须汇总：

```text
PAL2 minimal EIIE-CNN:
  validation baseline = 0.95376753
  best selected net after fee/tax = 0.66673752
  gross high but cost drag high
  concentration fail
  seed stability fail

PAL2-R cost/concentration repair:
  selected mean validation net after fee/tax = 0.02833287
  baseline = 0.95376753
  repair 降低 turnover/cost，但退化为 cash/no-trade dominant
  seed stability fail
```

结论：

```text
free allocation action space 在本项目当前设置下不稳定；
无约束时高成本/高集中；
加强约束后 cash/no-trade；
不得继续 PAL3 / strict_test / full GPU training。
```

### 5.2 PBA Baseline-anchored Active Policy

必须汇总：

```text
PBA2 rule selected:
  score_gap_buy_filter
  validation = 0.97910586
  baseline = 0.95376753
  excess = +0.02533833
  但 train/validation 方向不一致。

PBA3 selected:
  shallow_mlp_active_policy_seed_23
  validation = 1.20247421
  baseline = 0.95376753
  excess = +0.24870668
  participation / cash / OOD / clone gates pass
  但 fold stability fail，train excess = -0.92621018。

PBA3-R:
  stability-constrained selected = baseline clone
  validation = 0.95376753
  excess = 0.0
  active decision change rate fail
  contextual bandit still has +0.07789642 validation excess but fold stability fail / risk_off fail / active rate below minimum。
```

结论：

```text
PBA action space 比 PAL 更合理，并产生过局部 validation signal；
但模型 edge 未能同时满足收益、fold stability、非 clone active change。
不得进入 PBA5 strict_test。
```

### 5.3 PBA-RC Regime Diagnostic

必须汇总：

```text
PBA-RC 证明 active overlay 收益存在 regime-specific 现象；
但没有足够强的、跨 PBA2/PBA3/PBA3-R 一致正收益的非 baseline-clone active regime。

唯一一致正项:
  volatility_regime mid_vol no_extra_action
  mean_excess_return = +0.03396951
  但 no_extra_action / baseline clone 不能证明 active policy edge。

唯一 gate pass:
  pba3_normal_caution_risk_off_baseline
  excess = +0.16189570
  active_decision_change_rate = 0.00553586
  baseline_clone_flag = false
  但来源是 fold-stability failed 的 PBA3 模型。
```

结论：

```text
regime 诊断有研究价值；
但不足以授权 PBA-RC model work。
```

## 6. 必须列出的保留价值

Closure 不应只写失败，也要写保留价值：

```text
1. PAL 证明 free allocation 不适合当前强 baseline / 日频台湾股票 / 成本结构。
2. PBA 证明 baseline-anchored action space 比 free allocation 更接近正确问题。
3. PBA2/PBA3 证明局部 validation active overlay signal 存在。
4. PBA3-R/PBA-RC 证明该 signal 目前不具备足够稳定性。
5. 所有路线都保持 readonly / simulation-only / no production 边界。
6. 形成了未来重启 policy 所需的 artifact / gate / failure taxonomy。
```

## 7. 未来重启条件

执行报告必须列出未来如要重启 policy，需要先满足的条件：

```text
1. 补齐 action-level / symbol-level / daily ledger：
   daily fee
   sell tax
   turnover
   realized and unrealized PnL by symbol
   action contribution by decision type

2. 重新规划更合理的 policy train/validation/test：
   更多年份或 rolling walk-forward
   不只依赖 2023-2025 一个短窗口

3. 等新的 signal 版本或 qlib+LTR OOS 边界更清楚后再评估：
   但不得把 LTR 训练窗口当 strict OOS。

4. 若重启模型，优先从小而明确的 action 问题开始：
   score threshold
   buy filter
   sell delay
   regime fallback
   不直接回到 free allocation RL。

5. 任何重启都必须重新写 coordinator mainline，不得在本 closure 后直接续跑。
```

## 8. 输出产物

必须输出 artifact root：

```text
data_tw/experiments/policy_model_research_route_closure/
```

建议文件：

```text
manifest.json
route_evidence_summary.csv
route_failure_taxonomy.csv
retained_research_value.md
future_restart_requirements.md
forbidden_action_closure_audit.csv
closure_decision.md
```

必须写执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MODEL_RESEARCH_ROUTE_CLOSURE_EXECUTION_REPORT_CN.md
```

## 9. 执行报告结构

执行报告必须包括：

```text
1. Scope：确认只做 closure，不训练、不 strict_test。
2. Documents read。
3. Route evidence summary：
   PAL / PBA / PBA-RC 分别列核心指标和结论。
4. Failure taxonomy：
   high turnover cost drag
   concentration
   cash/no-trade degeneration
   fold instability
   baseline clone
   regime-specific non-transferable edge
   insufficient active decision change rate
5. Final closure decision。
6. Retained research value。
7. Future restart requirements。
8. Forbidden actions audit。
9. Recommendation for reviewer。
```

推荐结论应为：

```text
PASS_READY_FOR_REVIEWER_TO_CLOSE_POLICY_MODEL_RESEARCH_ROUTE
```

除非发现既有证据矛盾、合同越权或 artifact 缺失，则写：

```text
STOP_RETURN_TO_COORDINATOR
```

## 10. 审查者下一轮重点

审查者应检查：

```text
1. Closure 是否完整覆盖 PAL / PBA / PBA-RC。
2. 是否正确区分“当前场景下收益边际有限”和“policy 永远无效”。
3. 是否没有擅自授权 strict_test / PBA5 / PBA4 / qlib+LTR。
4. 是否没有把 PBA3 的 2025 validation 强信号当成可生产结论。
5. 是否没有把 PBA-RC 的 no_extra_action / baseline clone 当成 active edge。
6. 是否列出未来重启前的 ledger / 数据窗口 / 合同条件。
7. forbidden actions audit 是否明确通过。
```

审查输出建议：

```text
docs/tw_portfolio_decision_model/POLICY_MODEL_RESEARCH_ROUTE_CLOSURE_REVIEW_CN.md
```
