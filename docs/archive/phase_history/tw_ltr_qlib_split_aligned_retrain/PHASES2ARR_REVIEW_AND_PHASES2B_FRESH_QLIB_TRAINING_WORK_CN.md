# Phase S2ARR 审查意见与 Phase S2B Fresh Qlib Training 工作文档

生成日期：2026-06-14

审查入口：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES2ARR_INSTRUMENT_CONTRACT_REPAIR_EXECUTION_REPORT_CN.md
```

主线依据：

```text
docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md
docs/tw_ltr_qlib_split_aligned_retrain/PHASES2AR_REVIEW_AND_PHASES2ARR_INSTRUMENT_CONTRACT_REPAIR_WORK_CN.md
```

---

## 1. 审查结论

结论：`S2ARR 通过，允许进入 Phase S2B fresh qlib training。`

通过理由：

- S2ARR 已确认 canonical provider 内只有 `instruments/all.txt`，没有 `instruments/tw_liquid_dyn.txt`；
- qlib loading layer 已冻结为 `instruments = all`，避免 S2B 训练阶段出现 unresolved `tw_liquid_dyn` alias；
- `tw_liquid_dyn` 已独立冻结为 score 后置 as-of universe filter，而不是训练加载层 instruments；
- 后置 filter 使用现有 `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt`，没有新增数据源；
- provider path、handler end、split、线程阶梯均沿用 S2AR/S2ARR 修复后的合同；
- 未训练、未回放、未调参、未改前端/API、未触发 provider refresh/publish、未切换 accepted latest、未触发 monitor 或交易链路。

允许进入：

```text
Phase S2B fresh qlib training
```

不允许跳到：

```text
fresh LTR training
portfolio replay
default strategy decision
frontend/API integration
provider refresh/publish
accepted latest switching
monitor
trading chain
```

---

## 2. Findings

### Low 1：S2ARR 采用 `all + post-score filter` 是正确修复

本地核查：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt 存在
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/tw_liquid_dyn.txt 不存在
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt 存在
```

因此 S2ARR 选择：

```text
qlib loading layer: all
score post-filter layer: tw_liquid_dyn as-of active universe filter
```

该选择避免了 provider mutation，也避免了把不存在的 alias 写进 S2B yaml。

### Low 2：S2B 必须对 score 覆盖做强审计

S2ARR 只冻结合同，没有实际训练和预测。S2B 训练完成后必须检查：

- raw qlib score 覆盖 train / validation / test；
- post-filter 后每日 selected count；
- missing score / rank；
- duplicate date-instrument；
- test end 附近是否因 label 或 handler end 产生尾部缺口；
- post-filter 是否仍覆盖完整 frozen test：`2025-07-01..2026-05-07`。

如果 S2B 发现 fresh test 无法完整覆盖，不得继续 LTR 训练，必须提交 coverage/blocker 报告。

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

## 3. Gate

S2ARR gate 接受：

```text
s2arr_instrument_contract_repair_pass_request_s2b_fresh_qlib_training
```

下一轮执行：

```text
Phase S2B fresh qlib training
```

---

## 4. Phase S2B 工作目标

S2B 只回答一个问题：

```text
在 S2 fresh split 和已修复合同下，fresh qlib baseline 是否能完成训练，并生成可供后续 LTR fresh sample 使用的 qlib score/rank？
```

S2B 不是策略比较轮，也不是产品化轮。

---

## 5. Phase S2B 固定合同

### 5.1 qlib provider / instruments

必须使用：

```text
provider_uri = qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin
handler instruments = all
```

不得写成：

```text
handler instruments = tw_liquid_dyn
```

score 生成后再使用：

```text
score_universe_filter_file = qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt
score_filter_policy = as-of active + same-day price + >=60 history + trailing 60-day value top150
```

### 5.2 split

必须保持：

```text
train = 2017-01-10..2024-12-31
validation = 2025-01-01..2025-06-30
test = 2025-07-01..2026-05-07
```

不得缩短、移动或合并 split。

### 5.3 handler / fit window

必须保持：

```text
handler start_time = 2015-05-04
handler end_time = 2026-05-07
fit_start_time = 2015-05-04
fit_end_time = 2024-12-31
```

若最后若干 test 日期因 qlib label 或 handler end 无法输出 score，必须报告缺口，不得静默延长 handler end 或使用 post-test 数据。

### 5.4 model / resource

model family：

```text
qlib.contrib.model.gbdt.LGBModel
```

参数沿用 Option C / S2A/S2ARR 修复合同，不做搜索。

线程阶梯：

```text
4 -> 2 -> 1
```

如果 4 线程 OOM 或 exit code 137，允许降到 2；如果 2 仍失败，允许降到 1。若 1 线程仍失败，必须停止并提交资源失败报告，不得缩 universe、缩 split、删 feature、换模型或改数据。

---

## 6. Phase S2B 执行范围

执行者必须完成：

1. 生成 fresh qlib yaml：
   - 路径：`qlib_pipeline/configs/tw_yahoo_primary_alpha158_s2_fresh_retrain.yaml`；
   - `qlib_init.provider_uri` 与 S2ARR 合同一致；
   - `handler.kwargs.instruments = all`；
   - split / handler / fit window 与本文件一致；
   - `num_threads` 从 4 开始。

2. 训练 fresh qlib model：
   - 只训练 qlib fresh baseline；
   - 不训练 LTR；
   - 不做参数搜索；
   - 记录 recorder id、model path、config hash、训练日志摘要、实际线程数。

3. 生成 qlib raw score / rank：
   - 至少覆盖 validation 与 test；
   - 如后续 LTR sample 需要 train score，也应按合同生成 train/validation/test 三段 score；
   - raw score 生成后不得直接拿来做策略结论。

4. 执行 post-score universe filter：
   - 使用现有 `tw_liquid_dyn.txt`；
   - 使用 S1 已冻结的 as-of active + same-day price + >=60 history + trailing 60-day value top150；
   - 输出过滤后每日 selected count、missing score、missing rank、duplicate 检查。

5. 输出 coverage / leakage / safety 审计：
   - train / validation / test 分段覆盖；
   - frozen test `2025-07-01..2026-05-07` 覆盖；
   - post-filter 每日股票数；
   - 是否使用 test 反馈；
   - 是否使用 post-test 数据；
   - 是否触发 provider / accepted latest / frontend/API / monitor / trading chain。

---

## 7. Phase S2B 禁止事项

本轮禁止：

- 训练 LTR；
- 构建 LTR 样本；
- 跑 portfolio replay；
- 比较策略收益；
- 调参或参数搜索；
- 改 split；
- 改 feature / label；
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

## 8. Phase S2B 交付物

建议输出目录：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/
```

必须产物：

```text
phase_s2b_generated_qlib_config.yaml
phase_s2b_training_manifest.json
phase_s2b_recorder_manifest.json
phase_s2b_raw_score_rank.parquet 或 .csv
phase_s2b_post_filter_score_rank.parquet 或 .csv
phase_s2b_score_coverage_by_date.csv
phase_s2b_score_coverage_by_split.csv
phase_s2b_leakage_audit.json
phase_s2b_resource_audit.json
phase_s2b_forbidden_action_audit.json
phase_s2b_gate_summary.json
```

执行报告：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES2B_FRESH_QLIB_TRAINING_EXECUTION_REPORT_CN.md
```

---

## 9. Phase S2B 通过条件

只有全部满足时，才允许下一轮进入 fresh LTR sample/training：

```text
fresh_qlib_training_completed = true
generated_yaml_matches_s2arr_contract = true
handler_instruments = all
provider_uri_matches_contract = true
thread_policy_respected = true
parameter_search_performed = false
split_contract_unchanged = true
fit_end_time = 2024-12-31
handler_end_time = 2026-05-07
post_score_filter_uses_existing_tw_liquid_dyn = true
validation_score_coverage_complete_or_explained = true
test_score_coverage_complete_or_explained = true
no_test_feedback_for_tuning = true
no_post_test_data_used = true
no_provider_refresh_publish = true
no_accepted_latest_switching = true
no_frontend_or_api = true
no_monitor_or_trading_chain = true
```

通过 gate：

```text
s2b_fresh_qlib_training_pass_request_s2c_fresh_ltr_sample_and_training
```

失败 gate：

```text
s2b_blocked_by_training_failure
s2b_blocked_by_score_coverage_gap
s2b_blocked_by_resource_limit
s2b_blocked_by_contract_drift
s2b_blocked_by_scope_violation
```

---

## 10. 给执行者的一句话

请执行 Phase S2B：按 S2ARR 合同生成 fresh qlib yaml 并只训练 fresh qlib baseline，`handler instruments=all`、score 后置使用现有 `tw_liquid_dyn` as-of filter、线程按 `4->2->1`，输出 raw/post-filter score rank 与覆盖/泄漏/资源/安全审计；不得训练 LTR、回放、调参、改 split/feature/label 或触发 provider/accepted latest/前端/API/monitor/交易链路。
