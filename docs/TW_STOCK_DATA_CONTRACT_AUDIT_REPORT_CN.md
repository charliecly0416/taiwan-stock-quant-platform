# 台股数据口径与 Universe 审计报告

生成日期：2026-06-15

## 1. 结论摘要

当前项目的数据主链路已经比较清楚，但 `full/common universe` 的混乱并不是单一问题，而是两个问题叠在一起：

1. `historical asof` 上，静态 `accepted 150` 与按日期生效的 `asof-aware universe` 没有严格对齐。
2. fresh qlib 日频分数在后置过滤阶段被额外缩窄，导致 `raw 150 -> replay-ready 88/109/150`，从而把 coverage 差异混进了策略收益比较。

因此，现阶段不能把 `full universe` 下的回测差异简单解释为“模型优劣”，也不能把 `common universe` 视为唯一正确答案。更准确的说法是：

- 主数据来源合同基本明确；
- 历史与增量数据的 schema/来源已经可持续拼接；
- 但“研究 universe / provider universe / replay-ready universe / common comparison universe”四层口径还没有完全统一。

## 2. 当前主链路审计结果

### 2.1 qlib 主链路

qlib 当前主链路是 Yahoo/Scrapling 复权日频数据，不混 FinMind 价格。

证据：

- [docs/DAILY_AUTO_UPDATE_CN.md](/home/chuliyang/taiwan-stock-quant-platform/docs/DAILY_AUTO_UPDATE_CN.md:77)
- [data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260611_20260611T103001Z/job.json](/home/chuliyang/taiwan-stock-quant-platform/data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260611_20260611T103001Z/job.json:122)

明确约束：

- `source_policy = Yahoo-only; no yfinance; no FinMind fallback; no mixed provider`
- FinMind raw 不会 silently mixed into qlib provider

### 2.2 FinMind 链路

FinMind 当前用于 QuantDinger raw 库、趋势/K 线/交叉分析/展示补充，不是 qlib 训练/预测的主价格源。

证据：

- [docs/DAILY_AUTO_UPDATE_CN.md](/home/chuliyang/taiwan-stock-quant-platform/docs/DAILY_AUTO_UPDATE_CN.md:78)
- [scripts/run_daily_tw_stock_auto_update.py](/home/chuliyang/taiwan-stock-quant-platform/scripts/run_daily_tw_stock_auto_update.py:4)

### 2.3 每日自动更新链路

当前每日脚本已经把历史与增量更新串成了同一条主链：

1. 先更新 FinMind raw；
2. 再跑 Yahoo/Scrapling Option C 150；
3. 重建 staged provider；
4. 发布 formal Option C 150 provider；
5. 更新 accepted latest。

证据：

- [scripts/run_daily_tw_stock_auto_update.py](/home/chuliyang/taiwan-stock-quant-platform/scripts/run_daily_tw_stock_auto_update.py:14)
- [data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260611_20260611T103001Z/job.json](/home/chuliyang/taiwan-stock-quant-platform/data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260611_20260611T103001Z/job.json:628)

补充确认：

- 本次 job 使用的 Python 是 miniconda 环境：
  [job.json](/home/chuliyang/taiwan-stock-quant-platform/data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260611_20260611T103001Z/job.json:11)
- staged refresh 成功抓到 150/150 symbols：
  [job.json](/home/chuliyang/taiwan-stock-quant-platform/data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260611_20260611T103001Z/job.json:120)

## 3. 历史与增量数据是否同口径

结论：从当前可见证据看，qlib 主价格链路的历史与增量数据已经是同一 schema、同一来源策略、同一字段合同，可以持续拼接。

直接证据：

- 历史 normalized 文件：
  [qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW1301.csv](/home/chuliyang/taiwan-stock-quant-platform/qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TW1301.csv:1)
- 当日 staged candidate normalized 文件：
  [qlib_pipeline/data_tw/experiments/option_c_ops/option_c_yahoo_scrapling_refresh_20260611_20260611T103146Z_daily_auto/candidate_normalized/TW1301.csv](/home/chuliyang/taiwan-stock-quant-platform/qlib_pipeline/data_tw/experiments/option_c_ops/option_c_yahoo_scrapling_refresh_20260611_20260611T103146Z_daily_auto/candidate_normalized/TW1301.csv:1)

两者字段一致：

```text
symbol,date,open,high,low,close,volume,vwap,factor
```

同时，正式 provider 的 instrument 合同也体现出连续日历拼接：

- [qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt](/home/chuliyang/taiwan-stock-quant-platform/qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt:1)
- [staged_qlib_bin/instruments/all.txt](/home/chuliyang/taiwan-stock-quant-platform/qlib_pipeline/data_tw/experiments/option_c_ops/option_c_yahoo_scrapling_refresh_20260611_20260611T103146Z_daily_auto/staged_qlib_bin/instruments/all.txt:1)

这说明现在真正需要修的不是“历史和增量来自不同口径”，而是 “哪些 symbol/日期应当进入某个策略或回放口径”的定义问题。

## 4. Universe 层次审计

### 4.1 动态研究 universe：`tw_liquid_dyn`

`tw_liquid_dyn.txt` 不是静态股票列表，而是按时间片段生效的动态 universe。

证据：

- [qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt](/home/chuliyang/taiwan-stock-quant-platform/qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt:1)

该文件是多段区间格式，例如同一股票会出现多行不同起止区间。这代表它描述的是“某股票在某时间段属于研究 universe”，不是“永远固定在池子里”。

### 4.2 静态 accepted prediction universe：`accepted 150`

当前 daily auto update 与 Option C provider 使用的是静态 150 档 accepted list。

证据：

- [qlib_pipeline/data_tw/experiments/option_c_forward_validation/timed_data_availability_retry_20260601T101323Z/symbols_accepted_prediction_universe.txt](/home/chuliyang/taiwan-stock-quant-platform/qlib_pipeline/data_tw/experiments/option_c_forward_validation/timed_data_availability_retry_20260601T101323Z/symbols_accepted_prediction_universe.txt:1)
- [data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260611_20260611T103001Z/job.json](/home/chuliyang/taiwan-stock-quant-platform/data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260611_20260611T103001Z/job.json:98)

这个列表是“当前 accepted 150 研究池”，而不是历史上每个 asof 都成立的动态 universe。

### 4.3 Formal provider universe：Option C 150 provider

正式 qlib provider 的 `instruments/all.txt` 表明当前 formal provider 是静态 150-symbol provider，但每个 symbol 自身有可用起止日。

证据：

- [qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt](/home/chuliyang/taiwan-stock-quant-platform/qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt:1)
- 例如 `TW7769`：
  [all.txt:138](/home/chuliyang/taiwan-stock-quant-platform/qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt:138)

`TW7769` 的 provider 起始日是 `2024-11-01`，这意味着它出现在静态 150 档里并不等于它在 2023/2024 年初也应该参与 historical validation。

## 5. full/common universe 问题的真实来源

### 5.1 问题 A：historical asof 与静态 150 未对齐

这已经在正交数据主线里被明确诊断过。

结论证据：

- [docs/tw_decision_model_orthogonal/PHASE1B_FORMAL_SOURCE_DIAGNOSIS_REPORT_CN.md](/home/chuliyang/taiwan-stock-quant-platform/docs/tw_decision_model_orthogonal/PHASE1B_FORMAL_SOURCE_DIAGNOSIS_REPORT_CN.md:1)

关键事实：

- formal validation 失败不是 provider 缺字段、缺 calendar、缺文件；
- 根因是 static accepted universe 包含了历史 asof 上尚未进入 source 覆盖期的 symbol；
- `TW7769` 就是最直接证据。

因此，`historical asof` 上应当引入 `asof-aware universe`，而不是直接把静态 150 生搬进去。

### 5.2 问题 B：fresh replay-ready 产物被后置过滤缩窄

这部分是最近 full/common 争议的直接根因。

证据：

- [docs/tw_fresh_top50_coverage_repair/PHASEC0_COVERAGE_AUDIT_EXECUTION_REPORT_CN.md](/home/chuliyang/taiwan-stock-quant-platform/docs/tw_fresh_top50_coverage_repair/PHASEC0_COVERAGE_AUDIT_EXECUTION_REPORT_CN.md:1)
- [data_tw/experiments/fresh_top50_coverage_repair/phasec0_summary.json](/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/fresh_top50_coverage_repair/phasec0_summary.json:1)
- [data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2f_old_vs_fresh_same_window_recheck/phase_s2f_same_window_coverage_audit.json](/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2f_old_vs_fresh_same_window_recheck/phase_s2f_same_window_coverage_audit.json:1)

关键数字：

```text
window: 2025-07-01..2026-05-07

fresh raw qlib score rows:      30750  (daily 150/150/150)
fresh post-filter score rows:   22613  (daily 88/109/150)
fresh replay-ready rows:        22613  (daily 88/109/150)
old Phase1C frozen rows:        30475  (daily 147/149/150)

old - fresh_top50 keys:          7952
missing_fresh_raw_qlib_score:       0
raw_top150_missing_local_price:     0
filtered_by_s2b_post_score_universe_policy: 7952
```

这说明：

1. fresh qlib 原始分数并没有缺；
2. 本地价格也没有缺；
3. 缺口几乎全部来自 `S2B post-score universe filter`；
4. 所以这不是“源数据天生不完整”，而是“回放准备口径把本来可用的数据过滤掉了”。

## 6. 当前可以下的判断

### 6.1 已经基本确认的事

1. qlib 历史与增量价格主链路是同口径的 Yahoo/Scrapling adjusted 数据。
2. FinMind 目前主要是展示/趋势/交叉分析辅助链路，不是 qlib 主价格源。
3. `full/common universe` 争议里，至少一部分并不是模型能力问题，而是 universe/filter 口径问题。
4. 当前最该优先修的是 universe/filter 合同，不是继续盲目训练新模型。

### 6.2 还没有完全确认的事

1. `2015-2026` 全历史上 150 支股票是否都能做到“上市后 + 可交易区间内”的稳定 raw full coverage 分类表。
2. `tw_liquid_dyn` 与 `accepted 150` 之间是否应冻结一个新的、专门给回测/比较使用的 `model-ready universe contract`。
3. fresh top50 coverage 修复后，full universe 下 old Phase1C vs fresh adaptive vs simple LTR 的相对优势会变化多少。

## 7. 推荐后续动作顺序

建议按这个顺序推进，避免再混口径：

1. 先冻结 universe 合同：
   - `raw full universe`
   - `asof-aware provider universe`
   - `model-ready replay universe`
2. 修掉 fresh top50 的 `post-score universe filter` 缩窄问题。
3. 再做 full universe 对比。
4. 最后才讨论 strict LTR extension 或新的 stacking / decision layer。

如果要做“补强版 simple LTR”，必须额外满足：

1. frozen qlib score 在 `2021-2025` 连续、同口径生成；
2. 不混入静态 150 与 historical asof 冲突的 symbol；
3. 不再依赖 `common universe` 临时修补解释收益。

## 8. 给当前主线的直接建议

对正在处理 `full vs common universe` 的执行/审查主线，我的建议是：

1. 不要再把“源数据缺失”和“post-filter 缩窄”混成一个问题。
2. 不要把 `common universe` 当成最终产品口径，它只能用来做审计辅助。
3. 如果 fresh top50 coverage 修复后能恢复到接近 daily 150，再比较 full universe 才有意义。
4. 如果后续要验证 strict LTR extension，必须统一：
   - 数据来源口径；
   - qlib score provenance；
   - replay-ready universe；
   - historical asof symbol eligibility。

## 9. 一句话结论

当前项目的主数据来源合同并没有失控，真正的问题是 universe/filter 合同还没完全冻结；因此下一步最有价值的工作不是继续加模型，而是先把 `asof-aware universe + replay-ready coverage` 这层修干净。
