# Phase O5 审查结论：Controlled Replay Evaluation

生成日期：2026-06-15

审查对象：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEO5_CONTROLLED_REPLAY_EVALUATION_WORK_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEO5_CONTROLLED_REPLAY_EVALUATION_EXECUTION_REPORT_CN.md
scripts/evaluate_orthogonal_ltr_phase_o5_controlled_replay.py
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/
```

## 1. 结论

O5 暂不建议放行进入下一阶段。

本轮未发现执行者重训模型、改训练窗口、改 label、换特征、改 Phase1C anchor、触发 provider/accepted latest/monitor/前端/交易链路，也未发现新增 market gate、stop loss、take profit、turnover rule 或额外阈值。

但是，O5 的 common universe 结果存在证据链缺口：

```text
full universe metrics == o5 pairwise common universe metrics
o5_pairwise_common_key_count = 10110
full_universe_key_count = 30475
```

报告没有解释为什么 common key 大幅减少后，Phase1C 与 O4 treatment 的收益、回撤、action_count、turnover、fee/tax 全部完全相同；也没有输出 common replay 的 action/nav 明细供复核。因此 O5 的 common universe 对照目前不能作为已闭环证据。

## 2. 与主线一致的部分

O5 窗口符合工作文档：

```text
2025-07-01..2026-05-07
```

回放口径符合工作文档：

```text
next-day execution
fee_rate = 0.001425
tax_rate = 0.003
target_position_count = 10
preserve_scope = top50_only
```

Control 固定为 Phase1C anchor：

```text
score_head10_all_l31_alpha0.7_top50_only
```

Treatment 固定为 O4 输出：

```text
phaseo4_treatment_ltr_score
```

脚本中生成：

```text
phaseo4_treatment_ltr_score_top50_preserve
```

其逻辑为按 `qlib_rank <= 50` 落实 `preserve_scope=top50_only`。这是 O5 工作文档允许的 preserve scope 实现，不属于新增未授权 alpha/filter。

## 3. 主要问题

### 3.1 Common universe 口径未充分证明

O5 报告定义 pairwise common universe 为：

```text
Phase1C anchor score non-null
AND O4 treatment top50-preserve score non-null
on same date/instrument
```

该定义得到：

```text
o5_pairwise_common_key_count = 10110
```

但 full 与 common 的核心回放指标完全一致：

```text
Phase1C full return = 0.721631
Phase1C common return = 0.721631
O4 full return = 0.800329
O4 common return = 0.800329
```

只读复核显示，O5 common key 并非显然完全无约束：

```text
Phase1C active actions = 405
Phase1C active action signal keys missing from O5 common = 84
其中 historical_add missing = 0
其中 historical_risk_reduce missing = 84

Phase1C daily top50 keys = 10250
removed by common = 140
affected days = 110
```

这些 missing action 全部是卖出触发信号，可能不会改变最终实际持仓路径，也可能被 replay engine 的持仓状态和 pending order 逻辑抵消。但 O5 报告没有提供 common action audit、common nav 或 selected-key removed audit，无法证明相同指标是合理结果而不是 common replay 输出/审计不完整。

### 3.2 Common action/nav 未输出

`phaseo5_action_audit.csv` 与 `phaseo5_daily_nav.csv` 只收集了 full universe 的 replay 结果：

```text
for result in full_results.values():
    nav_rows.extend(result["curve"])
    action_rows.extend(result["actions"])
```

O5 虽然计算了 `common_results`，但没有把 common replay 的 action/nav 写入对应产物。因此审查者无法逐笔比较：

```text
full vs common selected candidates
full vs common pending orders
full vs common active actions
full vs common daily NAV
full vs common removed selected/action-driving rows
```

这不满足 O5 工作文档中 common universe 必须输出 key count、excluded reason、不得只用 full universe 得出结论的要求。

## 4. 当前可读结果

在 full universe 下，O4 treatment 相对 Phase1C anchor：

```text
Phase1C return = 0.721631
O4 treatment return = 0.800329
relative return = +0.078698

Phase1C max_drawdown = -0.050830
O4 treatment max_drawdown = -0.074962
drawdown worse by = -0.024132

Phase1C actions = 405
O4 treatment actions = 403
```

Ranking 辅助指标显示 treatment 有改善：

```text
Phase1C rank_ic_10d full = 0.025736746681
O4 treatment rank_ic_10d full = 0.068649444085
```

PnL 集中度未显示单一极端来源：

```text
O4 treatment top_symbol_abs_share = 0.102661
O4 treatment top_day_abs_share = 0.069842
```

低覆盖股票有少量参与，报告已输出审计文件；但正文没有汇总关键贡献，需要 O5R 一并补充。

## 5. 禁止错误解释

在 O5R 完成前，不得把以下说法作为正式结论：

```text
O4 treatment 已在 full/common universe 双口径稳定胜出；
common universe 结果已闭环；
O4 treatment 可以进入默认化、前端展示或产品链路；
O4 treatment 优于 Phase1C 的证据已经完全充分。
```

当前只可表述为：

```text
O4 treatment 在 full universe 同窗口回放中收益更高，但回撤更深；
common universe 对照需要补审计后才能放行。
```

## 6. Gate

本审查给出的 gate：

```text
phase_o5_needs_common_universe_audit_repair
```

下一步应执行 O5R，只补 common universe 审计与报告，不允许重训、不允许改策略、不允许引入新过滤。
