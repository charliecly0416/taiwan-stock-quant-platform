# Phase S2B 审查意见与 Phase S2C Fresh LTR Sample/Training 工作文档

生成日期：2026-06-14

审查入口：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES2B_FRESH_QLIB_TRAINING_EXECUTION_REPORT_CN.md
```

主线依据：

```text
docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md
docs/tw_ltr_qlib_split_aligned_retrain/PHASES2ARR_REVIEW_AND_PHASES2B_FRESH_QLIB_TRAINING_WORK_CN.md
```

---

## 1. 审查结论

结论：`S2B 通过，允许进入 Phase S2C fresh LTR sample and training。`

通过理由：

- fresh qlib baseline 已完成训练；
- generated yaml 与 S2ARR 合同一致：
  - `provider_uri = qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin`
  - `handler instruments = all`
  - `fit_end_time = 2024-12-31`
  - `handler_end_time = 2026-05-07`
  - `num_threads = 4`
- 训练使用 4 线程完成，未触发 OOM fallback；
- raw score/rank 覆盖 train / validation / test；
- post-filter score/rank 覆盖 validation/test，且 frozen test `2025-07-01..2026-05-07` 覆盖 205 个交易日；
- 未发现 duplicate date-instrument；
- 未发现 missing score / rank；
- 未训练 LTR、未构建 LTR 样本、未回放、未调参、未改前端/API、未触发 provider refresh/publish、未切换 accepted latest、未触发 monitor 或交易链路。

允许进入：

```text
Phase S2C fresh LTR sample and training
```

不允许跳到：

```text
portfolio replay
strategy return comparison
default strategy decision
frontend/API integration
provider refresh/publish
accepted latest switching
monitor
trading chain
```

---

## 2. 关键证据

### 2.1 qlib config 合同

S2B generated config：

```text
qlib_init.provider_uri = qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin
handler instruments = all
train = 2017-01-10..2024-12-31
valid = 2025-01-01..2025-06-30
test = 2025-07-01..2026-05-07
fit_end_time = 2024-12-31
handler_end_time = 2026-05-07
num_threads = 4
```

这符合 S2ARR 审查要求。

### 2.2 raw score 覆盖

只读核查：

| split | rows | instruments | dates |
| --- | ---: | ---: | ---: |
| train | 278765 | 150 | 1939 |
| validation | 17400 | 150 | 116 |
| test | 30750 | 150 | 205 |

raw score：

```text
missing qlib_score_raw = 0
missing qlib_rank_raw_by_split = 0
duplicate date-instrument = 0
```

### 2.3 post-filter score 覆盖

只读核查：

| split | rows | unique instruments | dates |
| --- | ---: | ---: | ---: |
| train | 136685 | 139 | 1939 |
| validation | 10068 | 101 | 116 |
| test | 22613 | 150 | 205 |

post-filter score：

```text
duplicate date-instrument = 0
test date range = 2025-07-01..2026-05-07
test date count = 205
```

coverage by split：

```text
test selected_count_min = 88
test selected_count_median = 109
test selected_count_max = 150
validation selected_count_min = 84
validation selected_count_median = 87
validation selected_count_max = 89
train selected_count_min = 51
train selected_count_median = 69
train selected_count_max = 89
```

解释：

- raw score 在 qlib loading layer 为 150 档；
- post-filter 数量小于 150 是 S2ARR 冻结的 `tw_liquid_dyn as-of active + same-day price + >=60 history + trailing 60-day value top150` 后置过滤结果；
- S2C 不得把 post-filter 数量不足 150 解释成数据缺失，除非后续发现具体日期缺 score / 缺 rank / 重复键。

### 2.4 字段命名注意

raw score rank 字段为：

```text
qlib_rank_raw_by_split
```

post-filter score rank 字段为：

```text
qlib_rank
```

这不是阻塞，但 S2C 构建 LTR 样本时必须明确使用 post-filter 后的 `qlib_rank` 与 `qlib_score_raw`，不得把 raw split rank 当成后置 universe rank。

---

## 3. Findings

### Low 1：S2B 报告正文偏短，但产物支撑 gate

执行报告正文没有展开 coverage 数字，但必需 JSON/CSV 产物齐全，审查已直接核查：

- generated config；
- training manifest；
- resource audit；
- leakage audit；
- forbidden action audit；
- raw/post-filter score files；
- coverage by date/split。

因此不要求重写 S2B 报告。

### Low 2：S2C 必须加入 label horizon / split purity 审计

S2C 将进入 LTR 样本构建与训练，必须额外审计：

- forward label 的 `label_end_date`；
- train rows 的 label window 是否越过 train end；
- validation rows 的 label window 是否越过 validation end；
- test labels 是否被用于训练、选参或 usage layer 选择。

如发现 train label window 使用 validation 未来结果并污染训练/验证边界，必须采取 purge/embargo 或停止报告，不得静默训练。

### Low 3：安全边界通过

未发现以下越权：

- frontend/API 修改；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 真实买卖建议、收益承诺、胜率承诺或上涨概率承诺；
- 新数据源或联网。

---

## 4. Gate

S2B gate 接受：

```text
s2b_fresh_qlib_training_pass_request_s2c_fresh_ltr_sample_and_training
```

下一轮执行：

```text
Phase S2C fresh LTR sample and training
```

---

## 5. Phase S2C 工作目标

S2C 只回答一个问题：

```text
基于 S2B fresh qlib score/rank，能否按已冻结 feature/label/split 合同构建 fresh LTR 样本，并训练 fresh_ltr_simple 与 fresh_ltr_turnover_controlled 所需的 LTR 模型/score？
```

S2C 不是组合回放轮，不比较收益，不决定默认策略。

---

## 6. Phase S2C 固定输入

必须使用 S2B 产物：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv
```

必须使用 post-filter 后字段：

```text
date
instrument
qlib_score_raw
qlib_rank
split
```

不得直接使用 raw `qlib_rank_raw_by_split` 作为 LTR universe 内 rank。

split 必须保持：

```text
train = 2017-01-10..2024-12-31
validation = 2025-01-01..2025-06-30
test = 2025-07-01..2026-05-07
```

feature / label 合同必须沿用 S1B3 / S2A 冻结内容：

```text
feature columns = S1B3 frozen 34 columns
label = ltr_relevance_label
label source = topk_forward_bucket
base future window = 10 trading days
bucket thresholds = 0.2 / 0.4 / 0.6 / 0.8
model family = LightGBM.LGBMRanker
parameter search = false
```

turnover-controlled usage layer：

```text
reuse frozen config k30_a3_gap0.0_buf0.0_holdw2_budget0.2
no S2 validation/test reselection
```

---

## 7. Phase S2C 执行范围

执行者必须完成：

1. 构建 fresh LTR 样本：
   - 使用 S2B post-filter score/rank；
   - 拼接既有技术/市场特征；
   - 不新增特征；
   - 不新增数据源；
   - 不改 label 定义；
   - 输出 train / validation / test 样本覆盖。

2. 做 label horizon / split purity 审计：
   - 输出每行或每 split 的 `label_start_date` / `label_end_date` 规则；
   - train 用于模型拟合的样本不得把 validation/test 结果作为训练标签；
   - validation 可用于诊断，但不得用于参数搜索；
   - test label 不得用于训练、选参、usage layer 选择；
   - 如需要 purge/embargo，必须明确规则和被剔除行数。

3. 训练 fresh LTR：
   - 训练 `fresh_ltr_simple` 所需 ranker；
   - 生成 train / validation / test 的 LTR score；
   - turnover-controlled 只复用已冻结 usage config，不得重选；
   - 不做参数搜索。

4. 输出 score 覆盖审计：
   - LTR score by date；
   - missing feature / missing label；
   - duplicate date-instrument；
   - train / validation / test coverage；
   - test score 覆盖必须覆盖 `2025-07-01..2026-05-07`，若不能覆盖必须解释。

5. 输出安全与边界审计：
   - no replay；
   - no strategy return comparison；
   - no frontend/API；
   - no provider refresh/publish；
   - no accepted latest switching；
   - no monitor/trading chain。

---

## 8. Phase S2C 禁止事项

本轮禁止：

- 跑 portfolio replay；
- 比较策略收益、回撤、换手或费用；
- 决定默认策略；
- 调参或参数搜索；
- 使用 test 反馈改变 feature / label / usage config；
- 新增 feature；
- 新增数据源；
- 联网；
- provider refresh / publish；
- accepted latest switching；
- 改前端/API；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 买卖建议、收益承诺、胜率承诺、上涨概率承诺。

---

## 9. Phase S2C 交付物

建议输出目录：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/
```

必须产物：

```text
phase_s2c_ltr_sample_schema.json
phase_s2c_ltr_samples.csv 或 .parquet
phase_s2c_sample_coverage_by_split.csv
phase_s2c_label_horizon_split_purity_audit.json
phase_s2c_training_manifest.json
phase_s2c_ltr_model_manifest.json
phase_s2c_ltr_score_rank.csv 或 .parquet
phase_s2c_ltr_score_coverage_by_date.csv
phase_s2c_ltr_score_coverage_by_split.csv
phase_s2c_missing_feature_label_audit.json
phase_s2c_forbidden_action_audit.json
phase_s2c_gate_summary.json
```

执行报告：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES2C_FRESH_LTR_SAMPLE_TRAINING_EXECUTION_REPORT_CN.md
```

---

## 10. Phase S2C 通过条件

只有全部满足时，才允许下一轮进入 S2D full daily replay：

```text
fresh_ltr_sample_built = true
uses_s2b_post_filter_score_rank = true
uses_post_filter_qlib_rank_not_raw_split_rank = true
feature_contract_unchanged = true
label_contract_unchanged = true
label_horizon_split_purity_pass = true
parameter_search_performed = false
fresh_ltr_training_completed = true
fresh_ltr_score_generated = true
test_ltr_score_coverage_complete_or_explained = true
turnover_controlled_usage_config_reused_without_reselection = true
no_replay_in_s2c = true
no_strategy_return_comparison = true
no_test_feedback_for_tuning = true
no_provider_refresh_publish = true
no_accepted_latest_switching = true
no_frontend_or_api = true
no_monitor_or_trading_chain = true
```

通过 gate：

```text
s2c_fresh_ltr_training_pass_request_s2d_full_daily_replay
```

失败 gate：

```text
s2c_blocked_by_sample_coverage_gap
s2c_blocked_by_label_split_leakage
s2c_blocked_by_training_failure
s2c_blocked_by_contract_drift
s2c_blocked_by_scope_violation
```

---

## 11. 给执行者的一句话

请执行 Phase S2C：只基于 S2B post-filter qlib score/rank 构建 fresh LTR 样本并训练 fresh LTR，严格沿用冻结的 34 个 feature、label、split 和 turnover-controlled usage config，必须做 label horizon/split purity 审计；不得回放、比较收益、调参、改 feature/label/split 或触发 provider/accepted latest/前端/API/monitor/交易链路。
