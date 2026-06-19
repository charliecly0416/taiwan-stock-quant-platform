# Phase E5 工作文档：E4 合理性与公平性审计

生成日期：2026-06-16

## 1. 本阶段目标

本阶段只做一件事：

```text
对 frozen qlib + orthogonal LTR / E4 的 2026 回放结果做独立合理性与公平性审计，
确认其高收益不是由未来函数、未来标签、窗口污染、回放不公平或统计口径偏差造成。
```

本阶段不是默认策略切换，不训练 qlib，不训练 LTR，不改规则。

## 2. 必须审查的对象

必须审查并引用：

- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE4_2026_REPLAY_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_replay_manifest.json`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_control_vs_treatment_2026_summary.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_coverage_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_next_day_accounting_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_pnl_concentration.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_rank_metrics_summary.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_feature_importance_summary.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_forbidden_action_audit.json`

## 3. 必须回答的问题

E5 必须逐项回答：

1. E4 是否严格使用 `2026-01-01..2026-05-07` untouched test？
2. control / treatment 是否使用同一 replay engine、同一 next-day execution、同一 fee/tax、同一持仓数、同一 candidate_k？
3. treatment 是否只在 frozen qlib top50 内重排？
4. 是否存在 2026 label、future return、realized PnL 被用于选择、排序或调参？
5. 是否存在 qlib 训练或 LTR 训练泄漏进回放决策？
6. 是否存在 coverage 不公平，尤其是 score 缺失、top50 缺失、candidate 数不等？
7. 是否存在 next-day accounting 违规、同日成交、未来价格倒灌、最后一日成交未到账？
8. 收益是否集中在少数日期或少数股票？
9. feature importance 是否与回放结果自洽，而不是靠单一异常特征驱动？
10. 与 repaired fresh qlib 比较时，公平性是否成立？
11. E4 能否作为“默认候选”继续讨论，而不是直接默认切换？

## 4. 审计重点

必须重点核验以下事实：

- E3 训练样本为宽候选，不是 top50-only；
- E4 replay-ready 表中 qlib_rank 只在 `1..50`；
- E4 `top50_flag` 全为真；
- control/treatment 的日覆盖一致；
- 2026 只作 audit，不进入训练或选择；
- O4 / E4 的收益提升不能由窗口切片错误解释；
- E4 的收益提升不能由费用税费或持仓数差异解释；
- E4 的收益提升不能由新增 filter、market gate、turnover rule 解释；
- E4 的收益提升不能由 price/source 缺失修补差异解释；
- E4 的收益提升不能由 payout/accounting 口径错误解释。

## 5. 需要输出的结论格式

结论必须分三层：

### 5.1 合规性

是否通过：

- 未来函数审计
- 未来标签审计
- coverage 审计
- next-day accounting 审计
- 规则边界审计

### 5.2 公平性

是否可以说：

```text
E4 与 repaired fresh qlib 的 2026 同窗口 replay 是公平比较。
```

并明确说明公平性成立的理由与残留 caveat。

### 5.3 可解释性

是否能够说明：

- 为什么收益高；
- 哪些股票 / 日期贡献最大；
- 是否有集中风险；
- 是否足以支持进入默认候选讨论。

## 6. 停止条件

发现以下任一情况，必须停止并报告：

- 2026 窗口不是 untouched test；
- treatment 不是 top50 内重排；
- 使用了 2026 label / future return / realized PnL 做决策；
- control/treatment replay 口径不一致；
- coverage 不公平无法解释；
- next-day accounting 失败；
- 收益主要由少数异常日期或少数异常股票驱动且无法解释；
- 发现任何 provider / accepted latest / frontend / monitor / trading 链路越权。

## 7. 输出报告

必须输出：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE5_E4_FAIRNESS_AUDIT_EXECUTION_REPORT_CN.md
```

报告必须明确：

- 是否建议 E4 进入默认候选讨论；
- 是否需要回滚或重跑；
- 是否需要额外桥接实验。

## 8. Gate

若审计通过，gate 为：

```text
phase_e5_e4_fairness_audit_passed
```

