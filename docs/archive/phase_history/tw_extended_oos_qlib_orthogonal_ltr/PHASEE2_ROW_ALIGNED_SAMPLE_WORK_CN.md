# Phase E2 工作文档：宽候选 Row-aligned LTR 样本构建

生成日期：2026-06-15

## 1. 本阶段目标

本阶段只做一件事：

```text
基于 E1 frozen qlib raw OOS score 与 E1R 修订后的 candidate scope，
构建 2023-2025 LTR train 与 2026 untouched test 的宽候选 row-aligned 样本。
```

本阶段不训练 qlib、不训练 LTR、不调参、不回放。

## 2. 上游 Gate

必须满足：

```text
phase_e0_extended_oos_contract_feasible
phase_e1_frozen_qlib_oos_score_completed
phase_e1r_candidate_coverage_scope_repaired
```

必须引用：

- `docs/tw_extended_oos_qlib_orthogonal_ltr/EXTENDED_OOS_QLIB_ORTHOGONAL_LTR_MAINLINE_CN.md`
- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE0_CONTRACT_AND_FEASIBILITY_EXECUTION_REPORT_CN.md`
- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE1_FROZEN_QLIB_TRAINING_AND_OOS_SCORE_EXECUTION_REPORT_CN.md`
- `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE1R_CANDIDATE_COVERAGE_SCOPE_REPAIR_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1r_candidate_coverage_scope_repair/phasee1r_recommended_e2_candidate_contract.json`

## 3. 修订后的核心合同

E2 必须执行 E1R 修订后的口径：

```text
LTR train rows should follow old O4-style broad candidate rows, not top50-only.
Replay/treatment decision remains top50-only rerank.
```

也就是说：

- LTR 训练样本使用宽候选集合；
- 不得只取 top50 行训练；
- `qlib_rank`、`top10_flag`、`top30_flag`、`top50_flag` 可以作为训练特征；
- 未来 E4 回放时才限制 treatment 在 qlib top50 内 rerank。

## 4. 时间边界

必须保持：

```text
LTR train: 2023-01-01..2025-12-31
LTR untouched test: 2026-01-01..2026-05-07
```

硬性要求：

- train rows 只能来自 2023-2025；
- test rows 只能来自 2026；
- 2026 label 只能用于 audit / rank metric，不得用于训练、调参或模型选择；
- 所有 qlib score 必须来自同一个 E1 frozen qlib raw OOS score；
- 不得使用 qlib 2018-2022 in-sample score 训练 LTR。

## 5. Candidate Source

必须以 E1 raw OOS score 为候选源：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv
```

按 E1R 推荐合同筛选宽候选 rows：

```text
instrument in frozen option_c_150 qlib provider active range as of signal date
same-day local price/tradability available
>=60 historical price observations by signal date
E1 raw qlib score exists for date/instrument
```

禁止将训练候选过滤为：

```text
top50
top30
full_market_trailing_value_top150_intersection
```

## 6. 目标覆盖

E2 构建出的宽候选样本应接近 E1R 审计结果：

```text
LTR train 2023-2025 broad rows: 约 107408，daily 147/149/149
LTR test 2026 broad rows:      约 11822，daily 149/150/150
```

允许因 label 完整性、PIT 特征缺失 flag 或可交易性审计出现小幅差异，但不得无解释地退化为 top50-only 或 post-filter `71/86/150` 覆盖。

## 7. 特征与 Label

### 允许特征

必须沿用 O4 feature whitelist：

```text
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_feature_whitelist.csv
```

允许特征包括：

- qlib score/rank；
- qlib score percentile / zscore by date；
- rank change；
- top10 / top30 / top50 flag；
- O4 已冻结技术/市场状态特征；
- O2 PIT-safe 法人筹码与融资融券正交特征；
- missing / delay flag。

不得新增 O2/O4 之外特征。

### Label

label 必须沿用：

```text
relevance_10d_top_heavy
```

2023-2025 label 可用于训练。

2026 label 只允许用于：

```text
audit
rank metric
```

不得用于：

```text
training
tuning
model selection
candidate selection
threshold selection
replay decision
```

## 8. O2 PIT Join

必须按真实 availability 做 as-of join：

```text
available_at <= signal_asof
trade_date <= signal_asof
```

不得人工提前 `available_at`。

不得用 test 后数据修正 test 内特征。

正交特征缺失必须通过 missing / delay flag 暴露，不得因缺失正交特征删除候选股票，除非该股票不满足 E1R 的基础可交易候选条件。

## 9. E2 执行范围

执行者应完成：

1. 读取 E1R candidate contract。
2. 读取 E1 raw OOS score。
3. 按 E1R 宽候选条件生成 2023-2025 train rows 与 2026 test rows。
4. 生成 qlib 衍生特征：
   - `qlib_score_raw`
   - `qlib_rank`
   - `qlib_score_percentile_by_date`
   - `qlib_score_zscore_by_date`
   - rank change
   - top10 / top30 / top50 flag
5. 拼接 O4 技术/市场状态特征。
6. 拼接 O2 PIT-safe 正交特征。
7. 构造 `relevance_10d_top_heavy` label。
8. 输出 row alignment audit。
9. 输出 score provenance audit。
10. 输出 candidate scope audit。
11. 输出 PIT leakage audit。
12. 输出 missing report。
13. 输出 label audit。
14. 输出 feature schema / hash。
15. 输出 forbidden action audit。

## 10. 输出目录

建议输出到：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/
```

至少包含：

```text
phasee2_sample_manifest.json
phasee2_ltr_train_sample_2023_2025.csv
phasee2_ltr_test_sample_2026.csv
phasee2_feature_schema.csv
phasee2_row_alignment_audit.csv
phasee2_candidate_scope_audit.csv
phasee2_score_provenance_audit.csv
phasee2_pit_leakage_audit.csv
phasee2_missing_report.csv
phasee2_label_audit.csv
phasee2_forbidden_action_audit.json
```

## 11. 执行报告要求

必须输出：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE2_ROW_ALIGNED_SAMPLE_EXECUTION_REPORT_CN.md
```

报告必须包含：

- 做了什么；
- 使用 artifact；
- E1R candidate contract 是否执行；
- train/test 日期范围；
- train/test row count；
- 每日 rows min/median/max；
- 是否 top50-only；
- max qlib rank / median max rank；
- feature count / feature hash；
- label 可用性；
- 2026 label 是否未用于训练/调参/选择；
- score provenance；
- PIT leakage audit；
- missing report；
- 是否新增 O2/O4 之外特征；
- 是否训练、调参或回放；
- 是否触发 provider/accepted latest/monitor/交易链路；
- 是否建议进入 E3。

## 12. 停止条件

遇到以下任一情况必须停止并报告：

- 样本退化为 top50-only 训练；
- 样本退化为 E1 post-filter `71/86/150` 覆盖且无法解释；
- 无法按 E1R 宽候选合同构建样本；
- qlib score 不全来自同一个 E1 frozen qlib；
- 2026 label/future return 被用于候选选择、训练、调参或模型选择；
- O2 正交特征无法 PIT-safe join；
- 必须新增 O2/O4 之外特征；
- 必须新增 filter / market gate / turnover rule；
- 必须训练模型才能判断样本是否可用。

## 13. 禁止事项

E2 禁止：

- 训练 qlib；
- 训练 LTR；
- 调参；
- 回放；
- top50-only 训练；
- 使用 full_market_trailing_value_top150_intersection 作为 LTR 训练候选过滤；
- 使用多个 qlib 模型；
- 使用 2026 label / future return / replay PnL 做候选选择；
- 新增 O2/O4 之外特征；
- 新增 filter / market gate / turnover rule；
- 改 provider / accepted latest；
- 改前端/API；
- 触发 monitor / broker / orders / quick-trade；
- 输出真实买卖建议、目标仓位、目标权重、收益承诺、胜率或上涨概率。

## 14. Gate

E2 通过 gate：

```text
phase_e2_extended_oos_ltr_sample_passed
```

只有在以下条件全部满足时，审查者才可允许进入 E3：

- train rows only from 2023-2025；
- test rows only from 2026；
- 训练样本为宽候选集合，不是 top50-only；
- 每日候选覆盖接近 E1R 合同；
- 所有 qlib score 来自同一个 E1 frozen qlib；
- O2 join PIT-safe；
- label 可构造；
- 2026 label 未用于训练/调参/选择；
- feature whitelist 沿用 O4；
- 未训练、调参或回放；
- 未触发 provider/accepted latest/monitor/交易链路。

## 15. 给执行者的一句话

```text
请按 docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE2_ROW_ALIGNED_SAMPLE_WORK_CN.md 执行 Phase E2：基于 E1 raw OOS score 和 E1R 宽候选合同，构建 2023-2025 LTR train 与 2026 untouched test 的 row-aligned 样本；训练样本必须是旧 O4-style 宽候选集合，不得 top50-only，不得使用 full_market_trailing_value_top150_intersection 过滤；top50 只作为特征和后续回放 rerank 边界。拼接 O4 特征与 O2 PIT-safe 正交特征，构造 relevance_10d_top_heavy label，并输出 row alignment、candidate scope、score provenance、PIT、missing、label 和 forbidden action 审计；不得训练、调参、回放或使用 2026 label/future return 做任何选择。
```

## 16. 给审查者的一句话

```text
请按 docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE2_ROW_ALIGNED_SAMPLE_WORK_CN.md 审查 E2 报告，重点确认样本是否按旧 O4-style 宽候选构建而非 top50-only，candidate coverage 是否接近 E1R，score 是否来自同一个 E1 frozen qlib，2026 label 是否未用于训练/调参/选择，O2 join 是否 PIT-safe，并判断是否允许进入 E3。
```
