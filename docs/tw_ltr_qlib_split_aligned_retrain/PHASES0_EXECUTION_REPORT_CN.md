# Phase S0 证据冻结与实验合同执行报告

生成日期：2026-06-14

## 1. 执行范围

本轮严格按 `docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md` 执行 Phase S0，只做证据冻结与 S1/S2 实验合同冻结。

已执行：

- 盘点 qlib Option C frozen baseline 的 recorder、config、model、split、universe、handler/feature/label 证据；
- 盘点当前 LTR Phase1C 的样本、split、feature、label、score 产物和 forbidden feature 审计；
- 冻结后续 S1 旧窗口 split-aligned 公平验证合同；
- 冻结后续 S2 新鲜窗口 qlib + LTR 重训验证合同；
- 冻结候选策略、比较口径和指标。

未执行：

- 未训练 qlib；
- 未训练 LTR；
- 未调参；
- 未跑新回放；
- 未改前端/API；
- 未联网；
- 未触发 provider refresh/publish；
- 未切换 accepted latest；
- 未触发 monitor、broker、orders、quick-trade 或任何交易链路。

## 2. qlib Option C Frozen Baseline 证据冻结

### 2.1 Frozen recorder / config / model

| 项目 | 冻结值 |
| --- | --- |
| recorder id | `950741cfd5f14ee5a05464fec3e12e0a` |
| experiment id | `607910013167647574` |
| recorder 路径 | `qlib_pipeline/mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a` |
| model 路径 | `qlib_pipeline/mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a/artifacts/params.pkl` |
| pred 路径 | `qlib_pipeline/mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a/artifacts/pred.pkl` |
| task artifact | `qlib_pipeline/mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a/artifacts/task` |
| config 路径 | `qlib_pipeline/configs/tw_yahoo_primary_alpha158.yaml` |
| daily signal metadata | `qlib_pipeline/data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260610_20260610T183814Z/run_metadata.json` |
| 既有审查证据 | `docs/tw_ltr_baseline_conservative_tuning/QLIB_OPTION_C_TRAINING_WINDOW_EVIDENCE_REVIEW_CN.md` |

`run_metadata.json` 明确记录：

- `model_retraining_performed: false`
- `model_tuning_performed: false`
- `refresh_triggered: false`
- `publish_triggered: false`
- `provider_mutation_triggered: false`
- `paper_trading_started: false`
- `live_trading_started: false`
- `target_trades_generated: false`
- `executable_orders_generated: false`

### 2.2 qlib split

来自 `qlib_pipeline/configs/tw_yahoo_primary_alpha158.yaml`：

| split | 日期区间 | S0 解释 |
| --- | --- | --- |
| train | `2015-05-04..2020-12-31` | 训练期，不可作为样本外证据 |
| valid | `2021-01-01..2022-12-31` | 验证期，只能用于选择/观察 |
| test / research backtest | `2023-01-01..2025-06-30` | frozen qlib baseline 的测试/研究回放区间 |

backtest 配置：

- `start_time: 2023-01-01`
- `end_time: 2025-06-30`
- `strategy: TopkDropoutStrategy`
- `topk: 30`
- `n_drop: 1`
- `deal_price: close`
- `open_cost: 0.001425`
- `close_cost: 0.004425`
- `min_cost: 20`

### 2.3 qlib universe / handler / feature / label

| 项目 | 冻结值 |
| --- | --- |
| market | `tw_liquid_dyn` |
| benchmark | `TWII` |
| provider_uri | `data_tw/experiments/yahoo_adjusted_primary/qlib_bin` |
| 当前 daily metadata provider_uri | `data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin` |
| universe 路径 | `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt` |
| universe 行数 | `3126` |
| handler | `qlib.contrib.data.handler.Alpha158` |
| model | `qlib.contrib.model.gbdt.LGBModel` |
| dataset | `qlib.data.dataset.DatasetH` |

handler 配置：

- `start_time: 2015-05-04`
- `end_time: 2025-06-30`
- `fit_start_time: 2015-05-04`
- `fit_end_time: 2020-12-31`
- `instruments: tw_liquid_dyn`

feature 冻结：qlib baseline 使用 `Alpha158` handler 的标准特征配置；S0 不展开改写 Alpha158 特征，不新增特征。

label 冻结：以 frozen recorder/config 中 `Alpha158` / `DatasetH` 保存的任务配置为准。S0 不改 label，不重建 dataset。

## 3. 当前 LTR Phase1C 证据冻结

### 3.1 样本与 score 产物

| 项目 | 路径 / 值 |
| --- | --- |
| LTR 样本 | `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_ltr_samples.csv` |
| LTR 样本行数 | `159994` 含表头 |
| input feature list | `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_input_feature_list.json` |
| label audit | `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_label_audit_summary.json` |
| split summary | `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_split_summary.json` |
| forbidden feature audit | `data_tw/experiments/ltr_rerank_regime_turnover/phase0_forbidden_feature_audit.csv` |
| frozen Phase1C score | `data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv` |
| frozen score 行数 | `152250` 含表头 |
| score schema | `data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_score_schema.json` |
| score gate | `data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_gate_summary.json` |

### 3.2 当前 LTR split

从 `phase1_ltr_samples.csv` 只读统计：

| split | 日期区间 | 行数 | 说明 |
| --- | --- | ---: | --- |
| train | `2022-01-10..2024-08-09` | `92717` | 当前 LTR 训练期 |
| validation | `2024-08-12..2025-06-24` | `31296` | 当前 LTR 验证期 |
| independent_test | `2025-06-25..2026-05-07` | `31350` | 当前 LTR 独立测试期 |
| out_of_split_or_incomplete | `2022-01-03..2026-06-12` | `4630` | 不完整或范围外行，不进入 frozen Phase1C score 主表 |

从 `phase3a0_frozen_phase1c_row_scores.csv` 只读统计：

| split | 日期区间 | 行数 | 说明 |
| --- | --- | ---: | --- |
| train | `2022-01-10..2024-08-09` | `90301` | 完整特征/标签行 |
| validation | `2024-08-12..2025-06-24` | `30877` | 完整特征/标签行 |
| independent_test | `2025-06-25..2026-05-07` | `31071` | 完整特征/标签行 |

结论：当前 LTR 与 qlib Option C frozen baseline 的训练窗口不一致。当前 LTR 在 2025/2026 的表现不能直接证明 LTR 方法在 qlib 同一训练假设下优于 qlib。

### 3.3 当前 LTR input features

当前 LTR feature 列来自 `phase1_input_feature_list.json`：

| 类别 | feature |
| --- | --- |
| qlib score/rank | `qlib_score_raw`, `qlib_rank`, `qlib_score_percentile_by_date`, `qlib_score_zscore_by_date` |
| qlib rank 变化/成员 | `rank_change_1d`, `rank_change_3d`, `rank_change_5d`, `top10_flag`, `top30_flag`, `top50_flag`, `top30_streak`, `top50_streak` |
| 个股技术/流动性 | `MA5`, `MA10`, `MA20`, `MA60`, `RSI14`, `MACD`, `Bollinger_position`, `ret20`, `volatility20`, `volume_ratio20`, `avg_trading_value_20d`, `volume_stability20`, `missing_rate20`, `suspension_proxy`, `slippage_proxy` |
| 市场状态 | `TWII_ret20`, `TWII_ret60`, `TWII_close_vs_MA60`, `TWII_close_vs_MA120`, `market_volatility20`, `market_drawdown60`, `market_breadth20` |

是否使用 qlib score/rank 作为输入：是。当前 LTR 是在 qlib score/rank 与本地技术/市场特征基础上的 rerank。

### 3.4 当前 LTR label

来自 `phase1_label_audit_summary.json`：

| label / audit 字段 | 定义 |
| --- | --- |
| `future_excess_return_rank_5d` | 未来 5 个交易日个股收益减 TWII 收益后，同日截面排名 |
| `future_excess_return_rank_10d` | 未来 10 个交易日个股收益减 TWII 收益后，同日截面排名 |
| `future_excess_return_rank_20d` | 未来 20 个交易日个股收益减 TWII 收益后，同日截面排名 |
| `topk_forward_bucket` | 基于 10d future excess return rank 的 5 桶 relevance label |
| `ltr_relevance_label` | 等同于 `topk_forward_bucket`，作为 LambdaMART relevance |

边界：future 字段只允许作为 label/audit，不允许进入 input features。

### 3.5 当前 Phase1C frozen score 配置

来自 `phase3a0_score_schema.json`：

| 项目 | 冻结值 |
| --- | --- |
| score column | `score_head10_all_l31_alpha0.7_top50_only` |
| candidate id | `head10_all_l31_alpha0.7_top50_only` |
| model id | `head10_all_l31` |
| blend alpha | `0.7` |
| preserve scope | `top50_only` |
| label col | `relevance_10d_top_heavy` |
| feature mode | `all_whitelist_without_trend_score` |
| num_leaves | `31` |
| learning_rate | `0.03` |
| n_estimators | `120` |
| random_state | `42` |

score schema 同时记录：

- `forbidden_feature_hits: []`
- `outside_top50_preserve_ok: true`
- `daily_outside_score_not_above_top50_ok: true`

`phase3a0_gate_summary.json` 记录：

- `row_level_score_materialized: true`
- `metrics_reproduced_within_tolerance: true`
- `no_ltr_retraining: true`
- `no_phase1c_score_rebuild: true`
- `no_provider_refresh_or_publish: true`
- `no_accepted_latest_switching: true`
- `no_frontend_or_api: true`
- `no_monitor_database_or_trading: true`

### 3.6 forbidden future / PIT-unsafe features

`phase0_forbidden_feature_audit.csv` 记录以下字段均未进入 Phase0 input features：

- `institutional_net_buy`
- `margin_balance`
- `short_balance`
- `monthly_revenue_yoy_mom`
- `valuation_PER_PBR`
- `any_field_without_available_at_or_announcement_date`

S0 冻结结论：当前 LTR 产物未发现 forbidden feature hits，但 S1/S2 若重建样本，仍必须重新输出 feature leakage / forbidden feature scan，不能沿用本轮结论替代新实验审计。

## 4. 当前比较口径证据冻结

### 4.1 已有完整日频回放口径

主要证据：

- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_method_comparison.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_period_comparison.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_gate_summary.json`
- `data_tw/experiments/ltr_baseline_conservative_tuning/phaseb1_conservative_replay/phaseb1_period_comparison.csv`
- `data_tw/experiments/ltr_baseline_conservative_tuning/phaseb1_conservative_replay/phaseb1_method_summary.csv`

冻结回放口径：

- 使用完整日频 replay；
- 费用后指标以 `fee_tax_adjusted_net_return` 为主；
- `gross_return` 在当前引擎中为 `not_available_in_current_engine`；
- turnover proxy 为 `sum_abs_quantity_price_over_average_equity`；
- 价格执行审计已有 `missing_price_count`、`trading_days_used`、`price_execution_audit`；
- 不在 S0 改 replay 逻辑。

### 4.2 冻结候选策略

后续 S1/S2 比较策略冻结为已有策略族，不新增主线外候选：

| 策略 | 角色 |
| --- | --- |
| `rank_rotate_top50_adaptive_score` | qlib / Top50 adaptive 主 baseline |
| `rank_rotate_top50` | Top50 规则 baseline |
| `rank_rotate_top30` | Top30 规则 baseline |
| `confirmed_exit` | 已有低动作退出参考 |
| `phase1c_ltr_simple_daily` | 当前 LTR simple 参考 |
| `phase1c_ltr_turnover_controlled_daily` | 当前 LTR turnover controlled 参考 |
| `phase1c_ltr_conservative_top30_2day_confirm_daily` | 已有保守 LTR 参考 |
| `phase1c_ltr_conservative_top20_entry_2day_exit_daily` | 已有保守 LTR 参考 |

S1/S2 不允许临时新增新策略族；如必须删减候选，应由审查者在下一阶段工作文档中明确。

### 4.3 冻结指标

后续 S1/S2 必须至少输出以下指标：

- `fee_tax_adjusted_net_return`
- `max_drawdown`
- `action_count`
- `buy_count`
- `sell_count`
- `fee_and_tax`
- `turnover_proxy_by_notional_over_avg_equity`
- `relative_return_vs_top50_adaptive`
- `relative_drawdown_vs_top50_adaptive`
- `relative_actions_vs_top50_adaptive`

建议保留已有辅助审计字段：

- `missing_price_count`
- `trading_days_used`
- `turnover_notional`
- `final_equity`
- `comparison_status`

## 5. Phase S1 实验合同冻结：旧窗口 Split-Aligned 公平验证

### 5.1 S1 要回答的问题

在 qlib Option C 同样旧训练窗口下，LTR rerank 方法本身是否相对 qlib / Top50 baseline 有增益？

### 5.2 S1 split

冻结优先 split：

| split | 日期区间 |
| --- | --- |
| train | `2015-05-04..2020-12-31` |
| validation | `2021-01-01..2022-12-31` |
| test | `2023-01-01..2025-06-30` |

若 LTR feature、label、qlib score/rank 在早期数据不足，S1 执行者必须报告：

- 缺失日期；
- 缺失字段；
- 缺失股票/样本规模；
- 是否影响训练可行性；
- 是否需要缩短为最早共同窗口。

不得静默缩短窗口。

### 5.3 S1 feature / label 合同

S1 feature 只能从当前 LTR whitelist 出发，不新增正交数据源，不新增法人、融资融券、月营收、估值等未 PIT 验证字段。

S1 label 以当前 LTR 10d future excess return relevance 体系为优先冻结候选：

- `future_excess_return_rank_10d`
- `topk_forward_bucket`
- `ltr_relevance_label`

若审查者要求与 qlib label 完全对齐，需在 S1 工作文档中明确，不得由执行者临时改 label。

### 5.4 S1 选择规则

- 模型训练允许仅在 S1 授权后执行；
- 模型选择只能使用 train / validation；
- test 只能最终评估；
- 不得在 test 上调参；
- 若需要轻量参数搜索，参数表必须在 S1 开始前冻结；
- S1 不得改 provider、accepted latest、monitor、前端/API 或交易链路。

### 5.5 S1 输出要求

S1 至少输出：

- full test：`2023-01-01..2025-06-30`；
- 分年：2023、2024、2025 H1；
- rolling 6m / 12m；
- bear / normal / bull 或现有等价 regime；
- feature leakage / forbidden feature scan；
- 数据覆盖与缺口诊断；
- 与 qlib / Top50 adaptive 的相对指标。

### 5.6 S1 gate

S1 只能给以下 gate 之一：

```text
split_aligned_ltr_method_supported
split_aligned_ltr_method_not_supported
split_aligned_data_insufficient
```

## 6. Phase S2 实验合同冻结：新鲜窗口 qlib + LTR 重训验证

### 6.1 进入条件

只有 S1 得到 `split_aligned_ltr_method_supported`，S2 才能自动进入。

若 S1 未支持 LTR 方法但用户仍要求继续，必须先生成用户确认文档，不能自动推进。

### 6.2 S2 要回答的问题

在真实使用场景下，qlib 与 LTR 都使用较新训练窗口时，哪个策略更适合后续默认只读展示？

### 6.3 S2 split 原则

具体日期需在 S1 后根据数据新鲜度冻结，但原则先冻结：

- train 尽可能覆盖到较近日期，但不能触碰 test；
- validation 位于 train 之后，用于模型选择；
- test 位于 validation 之后，必须保持 untouched；
- qlib 与 LTR 使用同一个新鲜 split 原则；
- LTR 若使用 qlib score/rank，必须使用同一 S2 新鲜 qlib 模型输出，不得混用旧 frozen qlib score。

主线文档示例 split 仅作为候选，不在 S0 直接定稿：

| split | 示例日期 |
| --- | --- |
| train | `2015-05-04..2024-12-31` |
| validation | `2025-01-01..2025-06-30` |
| test | `2025-07-01..latest available` |

### 6.4 S2 比较要求

S2 必须同时重训并比较：

- 新鲜窗口 qlib baseline；
- 新鲜窗口 LTR rerank；
- Top50 adaptive / rank rotation 规则 baseline；
- S1/S0 冻结的可解释保守参考。

不得只重训 LTR 后与旧 qlib 比较。

### 6.5 S2 禁止事项

- 不得把 S2 test 反复用于调参；
- 不得把 S2 结果直接写成前端默认；
- 不得自动改 provider 或 accepted latest；
- 不得触发 monitor、broker、orders、quick-trade；
- 不得输出买卖、持有、仓位、收益承诺、胜率或上涨概率语义。

### 6.6 S2 gate

S2 只能给以下 gate 之一：

```text
fresh_retrain_ltr_default_candidate_supported
fresh_retrain_qlib_or_top50_default_supported
fresh_retrain_inconclusive
fresh_retrain_data_or_leakage_blocked
```

## 7. S0 发现的问题与边界

1. 当前 LTR 和 frozen qlib 的训练窗口不一致。LTR train 为 `2022-01-10..2024-08-09`，qlib train 为 `2015-05-04..2020-12-31`，不能直接宣称当前 LTR 方法在同一训练假设下优于 qlib。
2. 当前 LTR 依赖 qlib score/rank，因此 S1 若要对齐旧窗口，需要确认旧窗口每个训练/验证/test 日期均存在可用 qlib score/rank 或可重建同口径 score。
3. S1 若因早期数据不足需要缩短共同窗口，必须显式上报，不得静默缩短。
4. S2 必须 qlib 和 LTR 都新鲜重训；只重训 LTR 会再次形成不公平比较。
5. S0 没有做任何训练或回放，因此本报告不提供新的优劣结论。

## 8. Gate 建议

建议提交审查，进入：

```text
request_phase_s1_split_aligned_work_doc
```

理由：S0 已冻结 qlib Option C 与当前 LTR 的训练窗口、feature、label、universe、score 产物、比较候选、指标和 S1/S2 合同；同时明确当前 LTR 与 qlib 训练假设不一致，下一步必须先做旧窗口 split-aligned 公平验证。
