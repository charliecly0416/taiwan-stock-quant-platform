# Phase E1R 工作文档：候选覆盖与训练样本口径修复审计

生成日期：2026-06-15

## 1. 本阶段目标

本阶段必须暂停原 E2，先修复一个关键口径问题：

```text
旧 O4 正交 LTR 训练不是 top50-only 训练；
它使用的是宽候选集合训练，top50-preserve 只是后续策略重排/回放边界。
```

因此本阶段只做：

```text
审计并修复 E1 产出的 2023-2026 OOS score 候选覆盖口径，
确保后续 E2 按旧 O4 正交 LTR 的训练方式构建宽候选 LTR 样本，
不得误用 top50-only 训练。
```

本阶段不训练 qlib、不训练 LTR、不回放、不调参。

## 2. 为什么需要 E1R

E1 报告显示：

```text
2023-2025 post-filter selected min/median/max = 71/85/110
2026 post-filter selected min/median/max = 115/122/150
top50 每日完整
```

但 E0 数据覆盖显示：

```text
2023-2025 active min/median/max = 148/149/150
2026 active min/median/max = 150/150/150
```

旧 O4 正交 LTR 训练报告显示：

```text
rows_used_for_training = 90301
train date_count = 625
平均每日训练 rows 约 144
```

所以，旧 O4 的 LTR 训练样本不是每日 top50-only。如果 E2 直接用 E1 top50 或被压缩后的 post-filter rows 训练，就不是“按旧 qlib + 新正交 LTR 的训练方式复刻”，而是另一个更小样本实验，会混淆“训练数据太少”的判断。

## 3. 上游状态

E0 已通过：

```text
phase_e0_extended_oos_contract_feasible
```

E1 技术训练本身可接受，但候选覆盖口径需要修复/确认：

```text
phase_e1_frozen_qlib_oos_score_completed
```

E1R 不否定 E1 的 qlib 训练，只暂停进入 E2，直到候选覆盖合同修复完成。

## 4. 核心原则

后续 E2 必须满足：

```text
LTR train rows should follow old O4-style broad candidate rows, not top50-only.
Replay/treatment decision remains top50-only rerank.
```

即：

- 训练 LTR：使用接近旧 O4 的宽候选集合；
- 回放策略：只在 qlib top50 内重排；
- top50 flag / top30 flag / rank 特征可以作为训练特征；
- 但不能只拿 top50 行训练 LTR。

## 5. E1R 执行范围

执行者应完成：

1. 对比 E1 三类 score 产物：
   - `phasee1_raw_oos_score_rank_2023_2026.csv`
   - `phasee1_post_filter_oos_score_rank_2023_2026.csv`
   - `phasee1_top50_oos_score_rank_2023_2026.csv`
2. 输出每日 coverage：
   - raw rows；
   - post-filter rows；
   - top50 rows；
   - E0 active rows。
3. 查清 post-filter selected `71/85/110` 的原因：
   - 是否由 trailing 60-day value top150 造成；
   - 是否由 active instrument range；
   - 是否由 same-day price；
   - 是否由 >=60 history；
   - 是否由实现错误或重复过滤造成。
4. 对照旧 O4 样本：
   - O4 train 平均每日约 144 rows；
   - O4 是否使用 full candidate sample；
   - O4 top50-preserve 是 score 输出/回放边界还是训练行过滤。
5. 明确后续 E2 的训练候选集合：
   - 优先选择与旧 O4 训练方式最一致的 as-of-safe broad candidate rows；
   - 不得只用 top50；
   - 不得为了凑 150 引入未来股票或非 as-of eligible 股票。
6. 证明候选 rows 全部来自同一个 E1 frozen qlib score。
7. 证明不使用 2026 label / future return 做候选选择。
8. 输出修订后的 E2 样本构建合同。

## 6. 允许与禁止的候选口径

允许：

```text
使用 E1 raw OOS score 中满足 as-of active / price / history / tradability 的宽候选 rows。
```

允许：

```text
保留 qlib_rank、top10_flag、top30_flag、top50_flag 作为特征。
```

禁止：

```text
只使用 top50 rows 训练 LTR。
```

禁止：

```text
为了扩大 coverage 引入 top150 外、无 price、无 history、非 active 或非 as-of eligible 股票。
```

禁止：

```text
使用 2026 label、future_return、future_excess_return 或 replay PnL 选择候选集合。
```

## 7. 输出目录

建议输出到：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1r_candidate_coverage_scope_repair/
```

至少包含：

```text
phasee1r_scope_manifest.json
phasee1r_raw_postfilter_top50_coverage_by_date.csv
phasee1r_filter_attrition_audit.csv
phasee1r_o4_training_scope_comparison.csv
phasee1r_recommended_e2_candidate_contract.json
phasee1r_forbidden_action_audit.json
```

## 8. 执行报告

必须输出：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE1R_CANDIDATE_COVERAGE_SCOPE_REPAIR_EXECUTION_REPORT_CN.md
```

报告必须包含：

- 做了什么；
- 为什么暂停原 E2；
- E1 raw/post-filter/top50 每日 coverage；
- post-filter selected 过少的原因；
- 与旧 O4 训练样本口径的对比；
- 后续 E2 应使用的 candidate scope；
- 是否仍保持同一个 E1 frozen qlib score；
- 是否仍保持 2023-2025 train / 2026 test；
- 是否使用 2026 label/future return 做候选选择；
- 是否新增 filter / market gate / turnover rule；
- 是否建议进入修订后的 E2。

## 9. 停止条件

遇到以下任一情况必须停止：

- 无法解释 E1 post-filter selected 过少；
- 无法构造接近旧 O4 训练方式的宽候选样本；
- 后续 E2 只能 top50-only 训练；
- 必须新增 filter / market gate / turnover rule；
- 必须使用多个 qlib 模型；
- 必须使用 2026 label/future return 做候选选择；
- 必须改 qlib/LTR 参数。

## 10. Gate

E1R 通过 gate：

```text
phase_e1r_candidate_coverage_scope_repaired
```

只有 E1R 通过后，才允许进入修订后的 E2。

## 11. 给执行者的一句话

```text
请暂停原 E2，先按 docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE1R_CANDIDATE_COVERAGE_SCOPE_REPAIR_WORK_CN.md 执行 E1R：查清 E1 post-filter selected 只有 71/85/110 的原因，并修复/冻结后续 E2 的候选样本口径，确保 LTR 训练按旧 O4 正交 LTR 的宽候选集合方式执行，而不是 top50-only；top50-only 只允许作为后续回放 rerank 边界。不得训练、调参、回放、使用 2026 label/future return、引入多模型 score 或新增规则。
```

## 12. 给审查者的一句话

```text
请按 docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE1R_CANDIDATE_COVERAGE_SCOPE_REPAIR_WORK_CN.md 审查 E1R 报告，重点确认旧 O4 训练口径是否被正确复刻、E2 是否不再 top50-only 训练、post-filter 覆盖压缩原因是否解释清楚、候选集合是否 as-of-safe 且来自同一个 E1 frozen qlib，并判断是否允许进入修订后的 E2。
```
