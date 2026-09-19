---
created_at: 2026-06-23
status: coordinator_route_decision
route: CATR_CANDIDATE_ATPAL_REPLAY_FEASIBILITY
previous_review: docs/tw_portfolio_decision_model/POLICY_CATR2_CANDIDATE_ATPAL_LEDGER_ANALYSIS_REVIEW_CN.md
catr0_status: pass_ready_for_catr1_work_doc
catr1_status: pass_candidate_atpal_ledgers_ready_for_analysis
catr2_status: pass_ready_for_coordinator_route_decision
recommended_next: CATR3_NARROW_ROBUSTNESS_DIAGNOSTIC
candidate_pass_fail_authorized: false
new_candidate_authorized: false
threshold_selection_authorized: false
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# CATR Final Route Decision：关闭多数候选，仅保留窄范围 Robustness Diagnostic

## 1. 统筹结论

CATR0 / CATR1 / CATR2 已完成：

```text
CATR0: 证明既有 FPA4 candidates 可被合同化回放；
CATR1: 生成 candidate ATPAL ledgers；
CATR2: 分析 candidate delta、concentration、train/validation 不稳定原因。
```

CATR2 审查结论为：

```text
PASS_READY_FOR_COORDINATOR_ROUTE_DECISION
```

当前路线决策：

```text
1. 关闭 C02 / C03 / C04 / C05 holding_days_005_019 为 negative evidence。
2. 不恢复 FPA4。
3. 不进入 strict_test。
4. 不训练模型。
5. 不新增候选或调阈值。
6. 仅允许对 C01 与 C05 holding_days_020_059 做一次极窄 robustness diagnostic。
```

## 2. 候选处理

### 2.1 关闭为 negative evidence

以下候选关闭：

```text
FPA4_C02 / unrealized_gain_large
FPA4_C03 / unrealized_loss_large
FPA4_C04 / unrealized_gain_large
FPA4_C05 / holding_days_005_019
```

原因：

```text
validation delta 非正；
或 train 强 validation 弱；
或 full-path candidate ledger 下路径收益不足。
```

### 2.2 仅保留为统筹讨论对象

以下候选不关闭，但也不通过：

```text
FPA4_C01 / rank_lte_25
FPA4_C01 / rank_lte_50
FPA4_C05 / holding_days_020_059
```

保留原因：

```text
C01 validation delta = +0.25236201，但 train delta = -0.03672023；
C05 holding_days_020_059 validation delta = +0.02334573，train delta = +0.31916291。
```

风险：

```text
C01 方向反转、费用和换手更高；
C05 validation 边际很薄；
两者均存在 symbol-date / lifecycle / trade 集中风险。
```

因此它们只能进入 robustness diagnostic，不得直接进入策略重审。

## 3. CATR3 授权范围

下一步授权：

```text
CATR3_NARROW_ROBUSTNESS_DIAGNOSTIC
```

CATR3 只做：

```text
1. C01 rank_lte_25 / rank_lte_50 的集中度与窗口稳健性分析；
2. C05 holding_days_020_059 的集中度与窗口稳健性分析；
3. 判断这些正 delta 是否主要由少数 symbol/date/lifecycle/trade 驱动；
4. 判断是否值得另开新主线讨论。
```

CATR3 不做：

```text
candidate pass/fail；
FPA4 repair；
新候选；
阈值调整；
validation mining；
strict_test；
模型训练；
生产或订单集成。
```

## 4. CATR3 之后的可能结论

CATR3 只能给出路线建议：

```text
close_all_candidate_policy_route
eligible_for_new_mainline_discussion_only
needs_external_closure
```

不得给出：

```text
pass
selected
approved
strict_test_ready
production_ready
```

## 5. 一句话

```text
CATR2 后没有任何候选可以直接推进；
CATR3 只是对 C01 和 C05 holding_days_020_059 做最后一次窄范围稳健性审查，
决定是彻底关闭 policy route，还是仅保留为未来新主线讨论材料。
```
