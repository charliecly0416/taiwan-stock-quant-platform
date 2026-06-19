# Phase E5 工作文档：Extended OOS 决策审查

生成日期：2026-06-15

## 1. 本阶段目标

本阶段只做结论审查，不训练、不回放、不改策略：

```text
基于 E0-E4 的审计与 2026 untouched replay 结果，
判断“延长 LTR 训练样本后，orthogonal LTR 是否在 frozen qlib 上形成增益”。
```

本阶段不得把本支线结果直接升级为默认策略或产品化策略。

## 2. 上游 Gate

必须满足：

```text
phase_e0_extended_oos_contract_feasible
phase_e1_frozen_qlib_oos_score_completed
phase_e1r_candidate_coverage_scope_repaired
phase_e2_extended_oos_ltr_sample_passed
phase_e3_extended_oos_ltr_trained
phase_e4_extended_oos_2026_replay_completed
```

必须引用：

- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE1R_CANDIDATE_COVERAGE_SCOPE_REPAIR_EXECUTION_REPORT_CN.md`
- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE2_ROW_ALIGNED_SAMPLE_EXECUTION_REPORT_CN.md`
- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE3_ORTHOGONAL_LTR_TRAINING_EXECUTION_REPORT_CN.md`
- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE4_2026_REPLAY_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_control_vs_treatment_2026_summary.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_coverage_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_next_day_accounting_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_pnl_concentration.csv`

## 3. 必须回答的问题

E5 必须回答：

1. E4 是否严格使用 2026 untouched test？
2. Control 与 treatment 是否同窗口、同回放引擎、同 fee/tax、同持仓数、同 candidate_k？
3. Treatment 是否只在 frozen qlib top50 内 rerank？
4. E1R/E2 是否已修复候选覆盖压缩，LTR 训练是否确认为宽候选？
5. 是否存在 2026 label/future return/realized PnL 被用于决策？
6. treatment 相对 control 的净收益提升是多少？
7. treatment 的最大回撤是否恶化，恶化幅度是多少？
8. 换手、动作数、费用税费是否有明显风险？
9. 收益是否集中在少数个股或少数交易日？
10. 该结果能否回答“训练样本太少是否是前一支线无增益的重要原因”？
11. 该结果不能推出哪些结论？

## 4. 固定事实口径

E5 必须基于以下事实，不得重新解释为其他实验：

```text
qlib train: 2018-01-01..2022-12-31
qlib frozen OOS score: 2023-01-01..2026-05-07
LTR train: 2023-01-01..2025-12-31
LTR test/replay: 2026-01-01..2026-05-07
LTR training scope: broad candidate rows, daily near 150
Replay boundary: frozen qlib top50 rerank only
Replay target_position_count: 10
Replay candidate_k: 50
```

不得把本支线描述为：

- fresh qlib 默认策略替代实验；
- Orthogonal Fresh Qlib 实验；
- 每日产品化链路实验；
- LTR 参数搜索实验；
- full-market 150 只直接交易实验。

## 5. 决策分层

E5 结论必须分三层写清楚：

### 5.1 支线内结论

判断 extended frozen qlib + orthogonal LTR 是否在 2026 上跑赢 extended frozen qlib baseline。

### 5.2 对前一 clean stacking 失败原因的解释

判断是否支持：

```text
前一支线的“fresh qlib + orthogonal LTR 无明显增益”
可能受到 LTR 训练样本不足或 top50-only 训练偏离的影响。
```

必须避免过度声称“已经完全证明唯一原因就是样本量”。

### 5.3 对后续主线的建议

给出后续是否值得做：

- fresh qlib + 宽候选正交 LTR 重新训练；
- 或继续保持 fresh qlib 默认策略，只把 LTR 作为候选研究；
- 或做更长窗口、多年份 untouched test 的稳健性验证。

## 6. 指标要求

E5 报告必须列出：

- control net return；
- treatment net return；
- net return diff；
- control max drawdown；
- treatment max drawdown；
- max drawdown diff；
- action_count diff；
- turnover proxy diff；
- fee/tax diff；
- coverage daily min/median/max；
- next-day accounting 是否通过；
- top50 rerank boundary 是否通过；
- PnL concentration 风险摘要。

## 7. 禁止事项

E5 禁止：

- 新训练 qlib；
- 新训练 LTR；
- 新回放；
- 改参数、改窗口、改 label、改特征；
- 用 E4 结果反向选择模型；
- 把 2026 结果用于调参；
- 宣布默认策略切换；
- 触发 provider/accepted latest/frontend/monitor/交易链路；
- 给出交易执行指令。

## 8. 输出报告

必须输出：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE5_DECISION_REVIEW_CN.md
```

报告必须包含：

- 总结论；
- 合同合规性；
- E4 指标表；
- 覆盖与 next-day accounting 审查；
- 风险与限制；
- 对前一支线偏离的反思；
- 是否建议收尾；
- 是否建议开启后续新主线。

## 9. 停止条件

若发现以下任一情况，必须停止并报告：

- E4 并非 2026 untouched replay；
- treatment 不只是在 qlib top50 内 rerank；
- control/treatment coverage 或回放口径不一致；
- 使用了 2026 label/future return 做决策；
- E4 指标与 artifact 不一致；
- 试图把本支线直接升级为默认策略。

## 10. Gate

若 E5 完成且未触发停止条件，gate 为：

```text
phase_e5_extended_oos_decision_review_completed
```

E5 是本支线的收口阶段。是否开启下一条主线，由用户确认。
