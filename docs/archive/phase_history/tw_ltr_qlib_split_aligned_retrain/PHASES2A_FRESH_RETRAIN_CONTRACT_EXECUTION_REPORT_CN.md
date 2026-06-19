# Phase S2A 执行报告：Fresh Retrain Contract Freeze

生成日期：2026-06-14

## 1. 执行范围

本轮严格按 `docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B6R_REVIEW_AND_PHASES2A_FRESH_RETRAIN_CONTRACT_WORK_CN.md` 执行，只冻结 S2 fresh qlib + fresh LTR 重训验证合同。

已执行：

- 冻结 fresh split；
- 冻结 qlib / LTR 的模型、feature / label、候选策略和资源策略；
- 冻结 S1B6R accounting 回放口径与 S2 指标口径；
- 基于本地现有证据盘点 fresh test 覆盖是否足以进入 S2B。

未执行：

- 未训练 qlib；
- 未训练 LTR；
- 未跑组合回放；
- 未调参；
- 未改 feature / label / split / universe 的既有主线边界；
- 未改前端/API；
- 未联网；
- 未触发 provider refresh / publish；
- 未切换 accepted latest；
- 未触发 monitor / trading chain；
- 未输出收益结论、买卖、持有、仓位、胜率或上涨概率语义。

## 2. Fresh 覆盖结论

本轮使用的本地证据：

- `docs/tw_ltr_qlib_split_aligned_retrain/PHASES1A_SCORE_RANK_COVERAGE_REPORT_CN.md`
- `docs/tw_ltr_qlib_split_aligned_retrain/PHASES0_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_ltr_samples.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv`
- `qlib_pipeline/data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260610_20260610T183814Z/run_metadata.json`

只读盘点结果：

| 项目 | 结论 |
| --- | --- |
| 本地 normalized price 日期范围 | `2015-01-02..2026-06-01` |
| 当前 LTR 样本 fresh 尾部 | `2025-07-01..2026-06-12`，`231` 个交易日，`150` 个股票，`34650` 行 |
| 当前完整 score fresh 尾部 | `2025-07-01..2026-05-07`，`205` 个交易日，`150` 个股票，`30475` 行 |
| 已接受 qlib daily signal asof | `2026-06-10` |

结论：

- raw fresh 数据已经延伸到 `2026-06`；
- 但当前“共同完整、可直接作为 untouched fresh test 合同证据”的更保守终点是 `2026-05-07`；
- 该 fresh test 仍有 `205` 个交易日、`150` 个股票，长度足以进入 S2B；
- 因此本轮不需要回到用户做“更长 train vs 更长 untouched test”的取舍。

## 3. 冻结 Split

本轮冻结的 S2 split：

| split | 日期区间 | 用途 |
| --- | --- | --- |
| train | `2017-01-10..2024-12-31` | 仅供 fresh qlib / fresh LTR 训练 |
| validation | `2025-01-01..2025-06-30` | 固定诊断、固定候选比较 |
| test | `2025-07-01..2026-05-07` | 唯一 untouched fresh holdout |

冻结理由：

- 遵循审查文档推荐的 fresh retrain 顺序；
- 保留完整独立的 `2025-07-01` 之后测试期；
- `2026-05-07` 是当前本地已证实的共同完整 fresh test 终点；
- 不把 `2026-05-08..2026-06-12` 的 raw 尾部直接塞进 final test，避免 score/label 完整性歧义。

## 4. 模型与特征/标签合同

### 4.1 qlib fresh retrain

- 待生成配置路径：`qlib_pipeline/configs/tw_yahoo_primary_alpha158_s2_fresh_retrain.yaml`
- 配置模板来源：`phase_s1b0_qlib_config_freeze.json`
- model family：`qlib.contrib.model.gbdt.LGBModel`
- 参数：沿用 frozen Option C 参数，不做搜索
- dataset / handler：沿用 `DatasetH + Alpha158`
- universe：`tw_liquid_dyn`
- benchmark：`TWII`
- provider 合同：`data_tw/experiments/yahoo_adjusted_primary/qlib_bin`

### 4.2 LTR fresh retrain

- sample build 模板：`phase_s1b2_sample_schema.json`
- feature 合同：沿用 `phase_s1b3_feature_label_contract.json` 的 34 个输入列
- label：继续使用 `ltr_relevance_label`
- label 来源：`topk_forward_bucket`
- base future window：`10 trading days`
- bucket policy：固定分位阈值 `0.2/0.4/0.6/0.8`
- model family：`LightGBM.LGBMRanker`
- 参数：沿用 `phase_s1b3_training_policy.json`，不做参数搜索

### 4.3 turnover-controlled usage layer

本轮冻结为：继续沿用已有 frozen config，不在 S2A 或 S2 test 上重选。

冻结 config：

```text
k30_a3_gap0.0_buf0.0_holdw2_budget0.2
```

## 5. 候选策略冻结

S2 后续至少保留：

- `fresh_qlib_top50_adaptive_baseline`
- `fresh_rank_rotate_top50`
- `fresh_confirmed_exit`
- `fresh_ltr_simple`
- `fresh_ltr_turnover_controlled`

关于 rank baseline：

- `rank_rotate_top30` 在此前 `position_count_target=10` 口径下已退化为与 `top50` 同一路径；
- 本轮为避免重复证据，只把 `fresh_rank_rotate_top50` 冻结为主 rank baseline；
- 不把退化后的 `top30` 当成独立 primary candidate。

## 6. 资源策略冻结

考虑此前 `WF-VAL` 本地 OOM / exit code `137`，S2B/S2C 必须先采用低线程阶梯：

```text
4 -> 2 -> 1
```

边界：

- 低线程只用于资源控制，不得借机改 split / universe / feature / label / model family；
- 若本地在冻结阶梯下仍重复 OOM，才允许远程服务器承担繁重训练；
- 远程只承担计算，不得改变实验合同；
- 远程产物回传后必须先审查，再进入下一步。

## 7. 回放与指标合同

S2 后续回放必须沿用 S1B6R 已修复的 accounting：

```text
signal_date/asof -> pending orders
execution_date -> next trading day close
effective_nav_date == execution_date
signal_date 不影响 same-day NAV
```

必须保留指标：

- `fee_tax_adjusted_net_return`
- `max_drawdown`
- `action_count`
- `buy_count`
- `sell_count`
- `fee_and_tax`
- `turnover_proxy_by_notional_over_avg_equity`
- `relative_return_vs_fresh_top50_adaptive`
- `relative_drawdown_vs_fresh_top50_adaptive`
- `relative_actions_vs_fresh_top50_adaptive`

测试区间口径：

- full test：`2025-07-01..2026-05-07`
- 分段：`2025H2`、`2026YTD_to_2026-05-07`
- rolling：只允许 `6m` 且窗口必须完全落在 test 内
- `12m rolling` 暂不冻结，因为当前 untouched test 仅 `205` 个交易日，强行保留会形成零窗口或越界解释

## 8. 禁止事项执行结果

- 未训练 qlib / LTR；
- 未跑回放；
- 未调参；
- 未新增数据源；
- 未联网；
- 未改前端/API；
- 未触发 provider / accepted latest / monitor / trading chain；
- 未做默认策略切换；
- 未输出真实交易语义。

## 9. 产物

- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2a_fresh_retrain_contract/phase_s2a_data_coverage_audit.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2a_fresh_retrain_contract/phase_s2a_split_contract.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2a_fresh_retrain_contract/phase_s2a_model_policy.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2a_fresh_retrain_contract/phase_s2a_strategy_policy.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2a_fresh_retrain_contract/phase_s2a_resource_policy.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2a_fresh_retrain_contract/phase_s2a_replay_accounting_policy.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2a_fresh_retrain_contract/phase_s2a_forbidden_action_audit.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2a_fresh_retrain_contract/phase_s2a_gate_summary.json`

## 10. Gate 建议

推荐 gate：

```text
s2a_fresh_retrain_contract_pass_request_s2b_fresh_qlib_training
```

理由：

- S1 已通过方法层验证，允许进入 fresh retrain；
- 本轮 fresh split、模型、策略、资源和 accounting 合同已冻结；
- 当前本地证据支持一个保守但完整的 untouched fresh test：`2025-07-01..2026-05-07`；
- 不需要用户先做 split tradeoff。
