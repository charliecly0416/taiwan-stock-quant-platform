# Phase 1 执行报告：最小 LTR Baseline

生成时间：2026-06-13T15:34:39+00:00

## 1. 本轮目标

按审查者 Phase 1 步骤文档，构建真实样本、生成列级 schema、训练最小 LambdaMART LTR baseline，并报告 rank quality、TopK、baseline 对照、年度 / 分段结果。

## 2. 实际完成内容

- 新增样本构建脚本：`scripts/build_tw_ltr_phase1_samples.py`。
- 新增训练评估脚本：`scripts/train_tw_ltr_phase1_lambdamart.py`。
- 使用本地 qlib prediction / top30 / top50、OHLCV、TWII 派生样本。
- 默认排除 `trend_score`，未引入新数据源。
- 使用 LightGBM `LGBMRanker(objective=lambdarank)` 训练最小树模型 LTR。

## 3. 改动文件清单

- `scripts/build_tw_ltr_phase1_samples.py`
- `scripts/train_tw_ltr_phase1_lambdamart.py`
- `docs/tw_ltr_rerank_regime_turnover/PHASE1_LTR_BASELINE_EXECUTION_REPORT_CN.md`

## 4. 新增产物清单

- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_ltr_samples.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_sample_schema.json`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_sample_coverage.json`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_input_feature_list.json`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_label_audit_summary.json`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_split_summary.json`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_ltr_metrics.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_topk_metrics.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_year_segment_metrics.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_baseline_comparison.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_gate_summary.json`

## 5. 样本覆盖与切分

- 完整样本行数：152249。
- 完整样本日期数：1043。
- split 计数：`{'train': 90301, 'independent_test': 31071, 'validation': 30877}`。
- LTR group：同一交易日横截面；group size min/median/max = 110 / 148.0 / 150。

## 6. input / label / audit / grouping schema

- input features：34 个，全部来自 Phase 0 白名单且排除 `trend_score`。
- label columns：`['future_return_5d', 'future_return_10d', 'future_return_20d', 'future_excess_return_5d', 'future_excess_return_10d', 'future_excess_return_20d', 'future_excess_return_rank_5d', 'future_excess_return_rank_10d', 'future_excess_return_rank_20d', 'topk_forward_bucket', 'ltr_relevance_label']`。
- audit columns：`['label_complete_5d', 'label_complete_10d', 'label_complete_20d', 'feature_complete', 'sample_complete']`。
- grouping columns：`['date', 'instrument', 'year', 'split', 'regime_segment']`。
- forbidden hits：`[]`。
- label/input overlap：`[]`。

## 7. 模型类型与训练口径

- 模型：LightGBM `LGBMRanker`。
- objective：`lambdarank`。
- 模型族：LambdaMART / GBDT LTR。
- 不是 Transformer、deep reranker 或 decision-focused 主模型。
- primary label：`ltr_relevance_label`，来自 10 日未来相对横截面分桶标签；该标签不进入 input features。

## 8. 评估指标与结果

独立测试集核心结果：

```text
           split                           method            score_column  date_count  row_count  mean_daily_spearman_rank_ic_10d  ndcg_at_10  ndcg_at_30  ndcg_at_50
independent_test                   ltr_lambdamart               ltr_score         209      31071                         0.054690    0.514995    0.517182    0.560571
independent_test                rank_rotate_top30     qlib_baseline_score         209      31071                         0.026642    0.539438    0.532858    0.561234
independent_test                rank_rotate_top50     qlib_baseline_score         209      31071                         0.026642    0.539438    0.532858    0.561234
independent_test rank_rotate_top50_adaptive_score adaptive_score_baseline         209      31071                         0.027657    0.541562    0.533366    0.561163
independent_test                   confirmed_exit confirmed_exit_baseline         209      31071                         0.026509    0.539524    0.532913    0.561325
```

TopK 指标已写入 `phase1_topk_metrics.csv`，年度 / regime 分段结果已写入 `phase1_year_segment_metrics.csv`。

## 9. baseline 对照

已覆盖：

- `rank_rotate_top30`
- `rank_rotate_top50`
- `rank_rotate_top50_adaptive_score`
- `confirmed_exit`

说明：本轮只做 rank quality / TopK 层面对照；真实组合净值、换手、动作次数、成本等需要后续 replay 阶段，未在本轮伪造。

## 10. 是否达到本轮门槛

- 样本构建成功：`True`。
- input features 全部来自白名单：`True`。
- `trend_score` 已排除：`True`。
- 禁止特征命中为 0：`True`。
- label / input / audit / grouping 隔离通过：`True`。
- train / validation / independent test 成立：`True`。
- LTR 训练成功且模型类型合规：`True`。
- 推荐 gate：`phase1_ltr_baseline_needs_repair`。
- gate 原因：LTR did not clear independent_test qlib baseline on both rank_ic and ndcg_at_30。

## 11. 风险 / 异常 / 未解决问题

- 本轮 LTR 只完成最小 baseline，不包含 regime gating、turnover layer、前端/API 或真实 replay。
- 若推荐 gate 为 `phase1_ltr_baseline_needs_repair`，说明独立测试对照未达到进入 Phase 2 的最低证据要求。
- Baseline 中 `rank_rotate_top50_adaptive_score` 和 `confirmed_exit` 是 Phase1 rank/TopK 层面的代理对照，不是旧 replay 收益复用。

## 12. 需要审查者重点检查的点

- `phase1_sample_schema.json` 中 input / label / audit / grouping 是否隔离。
- `phase1_input_feature_list.json` 是否严格排除 `trend_score` 和禁止特征。
- `phase1_baseline_comparison.csv` 是否足以支持当前 gate。
- 本轮是否仍保持无前端/API/provider/monitor/trading 越界。

## 13. 禁止事项遵守情况

本轮未改后端 API、未改前端、未接 provider、未接 accepted latest、未接 monitor、未做 turnover portfolio layer、未做 regime gating 动作实现、未联网、未使用 token、未写数据库、未接 broker / quick-trade / orders，未输出买入/卖出/持有、仓位、收益率承诺、上涨概率或胜率语义。
