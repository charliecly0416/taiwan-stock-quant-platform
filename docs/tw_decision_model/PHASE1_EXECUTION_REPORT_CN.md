# Phase 1B 样本 schema 修复执行报告

## 1. 执行摘要

- 执行日期：`2026-06-10T14:54:35+00:00`
- 修改文件：`scripts/build_tw_decision_phase1_samples.py`。
- 重新生成文件：`phase1_samples.parquet`、`phase1_samples_preview.csv`、`phase1_schema.json`、`phase1_label_quality_report.md`、`phase1_leakage_audit_report.md`、`phase1_exclusion_report.csv`、`phase1_date_coverage_report.csv`、`PHASE1_EXECUTION_REPORT_CN.md`。
- 是否训练模型：否。
- 是否触碰只读边界：否。未触发 broker/orders/quick-trade/target position/provider refresh/provider publish/accepted latest/monitor config/alerts。

## 2. 修复项对照

| 修复项 | 状态 | 证据 |
|---|---|---|
| market_regime 移出 input_features | pass | grouping_columns=['market_regime'] |
| candidate_reason_flags 移出 input_features | pass | audit_only_columns contains candidate_reason_flags=True |
| grouping_columns/audit_only_columns 更新 | pass | schema includes grouping_columns and expanded audit_only_columns |
| 日期覆盖报告生成 | pass | `phase1_date_coverage_report.csv` |
| leakage audit 更新 | pass | schema policy checks added |

## 3. Schema 检查

- input_features 数量：`48`
- label_targets 数量：`14`
- audit_only_columns 数量：`13`
- grouping_columns 数量：`1`
- excluded_columns 数量：`1`
- input/label overlap：`[]`
- input/audit overlap：`[]`
- future inputs：`[]`
- deferred FinMind columns：`[]`

## 4. 日期覆盖

- 2022 rows：`36231`
- 2023 rows：`18426`
- 2024 rows：`0`
- 2025 rows：`36300`
- 2026 rows：`13350`
- 2024 缺口说明：`2024_missing_from_phase1_artifacts; reason=unknown_from_phase1_artifacts; Phase2_must_not_assume_2024_available`。

## 5. 样本 diff

- 修复前 sample rows：`104307`
- 修复后 sample rows：`104307`
- 修复前 labeled rows：`101249`
- 修复后 labeled rows：`101249`
- 是否有非预期变化：否。样本行数与标签行数保持一致；schema 分组和覆盖报告变化属于预期修复。

## 6. Leakage Audit

- market_regime_not_in_input_features：`pass`
- candidate_reason_flags_not_in_input_features：`pass`
- future_columns_not_in_input_features：`pass`
- label_targets_no_overlap_with_input_features：`pass`
- audit_only_no_overlap_with_input_features：`pass`
- deferred_by_phase0_absent_from_sample_columns：`pass`

## 7. 安全边界

- broker/orders/quick-trade：未触碰。
- provider publish/refresh：未触碰。
- accepted latest switching：未触碰。
- monitor config/alerts：未触碰。
- 真实交易建议语义：未生成。

## 8. 风险与待审查问题

- 必须修复：暂无执行者自行认定的剩余必须修复项，待审查者复核。
- 需要用户确认：暂无。
- 可暂缓：FinMind institutional/margin/monthly revenue/valuation、官方 limit-up/down flag、正式 trading_money。

## 9. Phase 2 准入建议

- 是否建议进入 Phase 2：建议在审查者确认 Phase 1B schema、date coverage、leakage audit 后再进入。
- 若建议，限制条件：Phase 2 只能使用 `phase1_schema.json` 中的 `input_features`；不得使用 `market_regime` 和 `candidate_reason_flags` 作为模型输入；不得假设 2024 可用。

## 10. Candidate Generator 审计补充

| source_flag | rows | unique_dates | unique_symbols |
|---|---:|---:|---:|
| candidate_from_top50 | 40800 | 816 | 150 |
| candidate_from_score_percentile | 26523 | 816 | 150 |
| candidate_from_rank_improvement | 33185 | 811 | 150 |
| candidate_from_trend_strength | 46408 | 813 | 150 |
| candidate_in_expanded_pool | 66194 | 816 | 150 |
