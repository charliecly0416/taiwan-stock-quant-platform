# Decision Meta Model Phase 0 审核意见与 Phase 1 下一步工作文档

## 0. 审查入口与依据

审查入口：

- `docs/tw_decision_model/PHASE0_EXECUTION_REPORT_CN.md`

审查依据：

- `prompt_investigate.md`
- `docs/TW_STOCK_DECISION_META_MODEL_DESIGN_CN.md`
- `docs/tw_decision_model/PHASE0_REVIEW_BASELINE_AND_NEXT_WORK_CN.md`
- `docs/tw_decision_model/phase0_feature_availability_report.md`
- `data_tw/experiments/decision_model/phase0_feature_coverage.csv`
- `data_tw/experiments/decision_model/phase0_data_sources.json`
- `data_tw/experiments/decision_model/phase0_point_in_time_rules.md`
- `scripts/audit_tw_decision_phase0.py`

本次同时按台股 research-only 安全边界进行审查。

## 1. 本步审核结论

结论：有条件通过。

Phase 0 的工作没有偏离主线，没有进入训练、标签生成、组合回放或前端产品化，也没有新增与 Decision Meta Model 无关的实现分支。

允许执行者进入 Phase 1，但必须按本文档限定范围执行。Phase 1 只能构建 point-in-time 训练样本和审计标签质量，不能训练 Entry Model / Exit Risk Model。

## 2. 主线一致性审查

### 2.1 未发现偏离主线

执行者完成的工作仍在 Phase 0 范围内：

- 审计 qlib historical prediction / Top50 signal，见 `PHASE0_EXECUTION_REPORT_CN.md:13` 至 `PHASE0_EXECUTION_REPORT_CN.md:25`。
- 生成 Phase 0 指定产物，见 `PHASE0_EXECUTION_REPORT_CN.md:27` 至 `PHASE0_EXECUTION_REPORT_CN.md:35`。
- 新增只读审计脚本，见 `PHASE0_EXECUTION_REPORT_CN.md:50` 至 `PHASE0_EXECUTION_REPORT_CN.md:62`。
- 明确未训练模型、未生成 Entry / Exit 标签、未生成真实交易建议，见 `PHASE0_EXECUTION_REPORT_CN.md:37` 至 `PHASE0_EXECUTION_REPORT_CN.md:48`。

### 2.2 未发现新增分支

以下口径属于 Phase 0 审计后的正常收敛，不构成新增分支：

- FinMind institutional / margin / monthly revenue / valuation 暂缓。当前归档为 0 rows 且没有 `available_at` / `announcement_date`，见 `PHASE0_EXECUTION_REPORT_CN.md:139` 至 `PHASE0_EXECUTION_REPORT_CN.md:156`。
- market breadth 由稳定股票池横截面复算。该做法仍属于总设计要求的大盘连续特征，不是新模型路线，见 `PHASE0_EXECUTION_REPORT_CN.md:129` 至 `PHASE0_EXECUTION_REPORT_CN.md:137`。
- `volume * vwap` 作为交易额 proxy。当前 normalized bars 没有正式 `trading_money`，使用 proxy 可接受，但 Phase 1 必须记录字段口径，见 `PHASE0_EXECUTION_REPORT_CN.md:99` 至 `PHASE0_EXECUTION_REPORT_CN.md:117`。
- 官方 limit-up/down flag 暂缓，仅保留 OHLCV proxy 风险说明。该处理保守，符合 Phase 0 审计结论，见 `PHASE0_EXECUTION_REPORT_CN.md:115` 至 `PHASE0_EXECUTION_REPORT_CN.md:117`。

## 3. 发现的问题

### 3.1 Medium：TWII 日期缺口必须在 Phase 1 明确处理

执行报告显示股票池 OHLCV 覆盖到 `2026-06-09`，但 TWII 只覆盖到 `2026-05-21`，见 `PHASE0_EXECUTION_REPORT_CN.md:68` 至 `PHASE0_EXECUTION_REPORT_CN.md:72`，以及 `PHASE0_EXECUTION_REPORT_CN.md:223` 至 `PHASE0_EXECUTION_REPORT_CN.md:226`。

总设计要求大盘信息是 Decision Model 的必选输入。Phase 1 不得对 `2026-05-22` 至 `2026-06-09` 的 TWII 特征做无根据 forward fill，也不得在缺失大盘特征时静默生成完整训练样本。

处理要求：

- Phase 1 主样本必须默认使用 qlib signal、OHLCV、TWII 的共同可用日期。
- 超出 TWII 覆盖范围的日期只能进入 `excluded_due_to_market_feature_gap` 审计表，不能进入训练样本。
- 如执行者认为应保留这些日期，必须先提交单独问题给审查者和用户确认。

### 3.2 Medium：`future_return_label_base` 不能作为输入特征

Phase 0 报告将 `future_return_label_base` 标为 include，见 `phase0_feature_availability_report.md:71` 至 `phase0_feature_availability_report.md:72`。

这个字段只能表示 Phase 1 标签生成所需的价格基础，不得进入 feature matrix。Phase 1 必须在 schema 中把字段分成：

- `input_features`
- `label_targets`
- `audit_only_columns`
- `excluded_columns`

其中 `future_return_label_base` 只能属于 `label_targets` 或 `audit_only_columns`，不能属于 `input_features`。

### 3.3 Low：proxy 字段必须保留口径说明，不能伪装成官方字段

`trading_value_proxy`、`suspension_proxy`、`slippage_proxy`、`market_breadth20` 都是可接受的 v1 proxy，但 Phase 1 必须保留生成规则和局限性。

依据：

- `volume * vwap` 作为交易额 proxy，见 `phase0_feature_availability_report.md:35` 至 `phase0_feature_availability_report.md:42`。
- limit-up/down 官方字段暂缓，见 `phase0_feature_availability_report.md:90`。
- market breadth 从稳定股票池复算，见 `phase0_feature_availability_report.md:48` 和 `phase0_feature_availability_report.md:98`。

### 3.4 Low：FinMind 暂缓是正确结论，但 Phase 1 不得留下隐式开关

FinMind institutional / margin / monthly revenue / valuation 当前应暂缓，见 `phase0_feature_availability_report.md:51` 至 `phase0_feature_availability_report.md:61`，以及 `phase0_feature_availability_report.md:99` 至 `phase0_feature_availability_report.md:103`。

Phase 1 代码中不得出现默认可启用这些字段的配置开关。若保留配置项，默认必须关闭，并在 schema/report 中显示 `deferred_by_phase0=true`。

## 4. 必须修复项

Phase 1 执行前或执行中必须满足：

1. 样本日期默认裁剪到 qlib signal、OHLCV、TWII 连续特征的共同可用日期。
2. 所有 TWII 缺口日期必须输出到 exclusion report，不能静默丢弃或静默填充。
3. `future_return_label_base` 不得进入模型输入特征。
4. FinMind institutional / margin / monthly revenue / valuation 不得进入 v1 样本。
5. proxy 字段必须在 schema 中标记 `is_proxy=true`，并写明计算口径。
6. qlib raw score 必须同时生成 date percentile 和 date z-score，不得写死绝对 score band。
7. market_regime 只能作为解释与分组评估字段，不得作为硬动作闸门。
8. Phase 1 必须输出 leakage audit report，证明所有输入特征只使用 `asof` 及以前数据。

## 5. 可暂缓项

以下内容可以继续暂缓，不阻塞 Phase 1：

1. FinMind institutional net buy。
2. FinMind margin balance / short balance。
3. FinMind monthly revenue yoy / mom。
4. FinMind valuation PER / PBR。
5. 官方 limit-up/down flag。
6. 正式 `trading_money` 字段。
7. Entry Model / Exit Risk Model 训练。
8. 前端产品化。

## 6. 台股只读安全边界审查

### Findings

Critical：无。

High：无。

Medium：无。

Low：关键词扫描命中 `broker`、`orders`、`quick-trade`、`accepted latest`、`publish`、`refresh` 等词，但上下文均为禁止事项、安全说明或 research-only 声明，不是真实 API 调用或动作入口。

### Network Audit

本次 Phase 0 未提供网络审计文件。执行报告说明只读取本地 CSV / JSON / 文档化归档，未触发 provider refresh / publish / accepted latest switching，见 `PHASE0_EXECUTION_REPORT_CN.md:56` 至 `PHASE0_EXECUTION_REPORT_CN.md:62`。

### Console Audit

本次 Phase 0 未提供 console audit。执行报告记录普通沙箱出现 `bwrap: loopback: Failed RTM_NEWADDR`，提权命令仍为只读本地检查和写指定审计报告，见 `PHASE0_EXECUTION_REPORT_CN.md:206` 至 `PHASE0_EXECUTION_REPORT_CN.md:209`。

### Text / Agent Semantics

未发现真实下单、目标仓位、收益承诺、上涨概率承诺、连接券商、自动买卖语义。报告中相关词均用于禁止事项或边界声明。

### Verdict

通过。

## 7. 是否需要用户确认的问题

当前没有必须停下来让用户确认的问题。

审查者接受以下 Phase 0 收敛口径：

- FinMind institutional / margin / monthly revenue / valuation 在 v1 暂缓。
- market breadth 可由稳定股票池横截面复算。
- `volume * vwap` 可作为 v1 交易额 proxy。
- 官方 limit-up/down flag 暂缓，仅保留 OHLCV proxy 风险说明。
- 在 FinMind 补充特征暂缓的前提下进入 Phase 1。

但如果执行者在 Phase 1 想改变以上任一口径，必须停止并提交需要用户确认的问题。

## 8. 下一步工作文档：Phase 1 构建 point-in-time 训练样本

### 8.1 目标

构建 Decision Model v1 的 `date-symbol` point-in-time 样本面板，为后续 Entry Model 和 Exit Risk Model 训练做准备。

Phase 1 只负责样本、特征、标签、schema、质量报告和泄漏审计，不训练模型。

### 8.2 范围

允许：

- 新增只读样本构建脚本。
- 读取 Phase 0 include 特征来源。
- 生成 `date-symbol` 面板样本。
- 生成 Candidate Generator 审计字段。
- 生成动态标签、连续目标、排序目标。
- 输出 schema、label quality report、leakage audit report、exclusion report。

禁止：

- 不训练 LightGBM 或任何模型。
- 不生成真实交易建议。
- 不接前端。
- 不写 broker / orders / quick-trade / target position。
- 不触发 provider refresh / publish / accepted latest switching。
- 不修改 monitor config / alerts / 模拟账户。
- 不启用 Phase 0 暂缓的 FinMind 特征。
- 不使用固定 qlib score 绝对区间作为准入规则。
- 不在测试集上调标签阈值。

### 8.3 输入

只能使用以下输入：

1. qlib historical prediction / Top50 signal。
2. stable universe 150。
3. adjusted OHLCV 150。
4. TWII 连续特征，且默认只使用共同可用日期。
5. 从稳定股票池复算的 market breadth。
6. Phase 0 include 的技术趋势与流动性 proxy。

不得使用：

1. FinMind institutional / margin / monthly revenue / valuation。
2. period-only 财务/月营收 join。
3. 官方 limit-up/down flag，除非另有稳定归档证明。
4. 缺失 TWII 日期上的伪造 market feature。

### 8.4 输出

必须生成：

1. `scripts/build_tw_decision_phase1_samples.py`
2. `data_tw/experiments/decision_model/phase1_samples.parquet`
3. `data_tw/experiments/decision_model/phase1_samples_preview.csv`
4. `data_tw/experiments/decision_model/phase1_schema.json`
5. `data_tw/experiments/decision_model/phase1_label_quality_report.md`
6. `data_tw/experiments/decision_model/phase1_leakage_audit_report.md`
7. `data_tw/experiments/decision_model/phase1_exclusion_report.csv`
8. `docs/tw_decision_model/PHASE1_EXECUTION_REPORT_CN.md`

如果 parquet 依赖不可用，可以输出 csv，但必须在执行报告说明原因。

### 8.5 样本要求

每一行必须是一个 `date-symbol`。

基础键：

- `asof`
- `symbol`
- `is_in_stable_universe`

qlib 特征：

- `qlib_score_raw`
- `qlib_rank`
- `qlib_score_percentile_by_date`
- `qlib_score_zscore_by_date`
- `top10_flag`
- `top30_flag`
- `top50_flag`
- `rank_change_1d`
- `rank_change_3d`
- `rank_change_5d`
- `top30_streak`
- `top50_streak`
- `newly_entered_top30`
- `dropped_from_top30`

技术趋势特征：

- `ma5_slope`
- `ma10_slope`
- `ma20_slope`
- `ma60_slope`
- `distance_to_ma20_pct`
- `rsi14`
- `macd_hist`
- `bollinger_position`
- `ret20`
- `volatility20`
- `volume_ratio20`
- `trend_score`

流动性与风险 proxy：

- `avg_trading_value_20d`
- `liquidity_percentile_by_date`
- `volume_stability20`
- `missing_rate20`
- `suspension_proxy`
- `slippage_proxy`
- `position_risk_status`

大盘特征：

- `twii_ret20`
- `twii_ret60`
- `twii_close_vs_ma60`
- `twii_close_vs_ma120`
- `market_volatility20`
- `market_drawdown60`
- `market_breadth_ma20`
- `market_breadth_ret20_positive`
- `market_regime`，仅解释与分组评估

Candidate Generator 审计字段：

- `candidate_from_top50`
- `candidate_from_score_percentile`
- `candidate_from_rank_improvement`
- `candidate_from_trend_strength`
- `passes_liquidity_filter`
- `liquidity_penalty`
- `candidate_in_expanded_pool`
- `candidate_reason_flags`

### 8.6 标签要求

Phase 1 必须同时生成或审计以下目标，不能只生成单一固定阈值 binary label。

Entry 相关：

- `future_20d_return_after_fee`
- `future_20d_twii_return`
- `future_20d_excess_return_after_fee`
- `future_20d_max_drawdown`
- `entry_label_dynamic`
- `entry_target_regression`
- `entry_rank_target`

Exit Risk 预备字段：

- `future_3d_drawdown`
- `future_3d_excess_return_after_fee`
- `future_10d_drawdown`
- `future_10d_excess_return_after_fee`
- `exit_label_3d`
- `exit_label_10d`
- `exit_volatility_target`

标签只能使用未来窗口作为 target，不得回流到输入特征。

### 8.7 日期切分与缺口处理

必须输出以下日期范围：

- qlib signal range
- OHLCV range
- TWII range
- common sample range
- excluded market-feature-gap range
- excluded label-horizon-incomplete range

默认主样本日期必须落在 common sample range 内。

若某个 `asof` 的未来 20d label 不完整，该行可以保留为 inference-only / unlabeled audit row，但不能进入 training-labeled rows。

### 8.8 验收标准

Phase 1 只有满足以下条件才可进入 Phase 2：

1. 样本粒度为 `date-symbol`，不是全市场宽表。
2. 覆盖稳定股票池或明确的 expanded candidate pool，不只覆盖 Top50。
3. 所有输入特征只使用 `asof` 及以前数据。
4. 标签字段与输入特征字段在 schema 中明确分离。
5. `future_return_label_base` 不在 `input_features`。
6. qlib score 同时保留 raw、date percentile、date z-score。
7. 没有固定绝对 qlib score 区间规则。
8. Candidate Generator 包含流动性过滤和滑点 proxy。
9. 大盘状态以连续特征为主，`market_regime` 仅用于解释和分组评估。
10. FinMind 暂缓字段没有进入样本。
11. 每个训练区间输出 label imbalance。
12. 输出 leakage audit report，且无未来函数证据。
13. 输出 exclusion report，说明 TWII 缺口、label horizon 不完整、流动性过滤失败等原因。
14. 未触碰 broker、orders、quick-trade、target position、provider publish/refresh、accepted latest switching、monitor config、alerts。

### 8.9 执行报告模板

执行者完成后必须提交：

```markdown
# Phase 1 Point-in-Time 样本构建执行报告

## 1. 执行摘要

- 执行日期：
- 代码变更：
- 生成文件：
- 是否训练模型：
- 是否触碰只读边界：

## 2. 输入数据范围

| 数据源 | start_date | end_date | rows/symbols | 状态 |
|---|---|---|---:|---|

## 3. 样本范围

- qlib signal range：
- OHLCV range：
- TWII range：
- common sample range：
- labeled sample range：
- inference-only / unlabeled rows：
- excluded rows：

## 4. Schema 摘要

- input_features 数量：
- label_targets 数量：
- audit_only_columns 数量：
- excluded_columns 数量：
- proxy_features：

## 5. Candidate Generator 审计

| source_flag | rows | unique_dates | unique_symbols |
|---|---:|---:|---:|

## 6. Label Quality Report 摘要

| split_or_year | rows | positive_rate_dynamic | target_mean | target_std | notes |
|---|---:|---:|---:|---:|---|

## 7. Leakage Audit

- asof join 检查：
- rolling window 检查：
- future label 隔离检查：
- TWII 缺口处理：
- FinMind 暂缓字段检查：

## 8. 安全边界

- broker/orders/quick-trade：
- provider publish/refresh：
- accepted latest switching：
- monitor config/alerts：
- 真实交易建议语义：

## 9. 风险与待审查问题

- 必须修复：
- 需要用户确认：
- 可暂缓：

## 10. Phase 2 准入建议

- 是否建议进入 Phase 2：
- 若建议，限制条件：
```

## 9. 审查者最终意见

Phase 0 有条件通过。

执行者可以进入 Phase 1，但必须严格按本文档构建 point-in-time 样本。Phase 1 完成后，审查者将重点检查样本泄漏、标签设计、label imbalance、Candidate Generator 流动性过滤、TWII 缺口处理、FinMind 暂缓边界，以及是否仍保持 research-only。
