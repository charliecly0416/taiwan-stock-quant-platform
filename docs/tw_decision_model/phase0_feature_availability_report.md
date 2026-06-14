# Phase 0 Feature Availability Report

## 1. 执行摘要

- 审计日期：`2026-06-10T14:15:49+00:00`
- 范围：只读审计 qlib signal、adjusted OHLCV、技术/流动性可复算性、TWII 连续特征、FinMind 归档可用性。
- 代码变更：新增只读审计脚本 `scripts/audit_tw_decision_phase0.py`；生成 Phase 0 报告文件。
- 是否触碰只读边界：否。未训练模型、未刷新 provider、未发布、未切换 accepted latest、未写 broker/orders/quick-trade/monitor config/alerts。
- v1 特征准入：include `31`，defer `6`，reject `0`。

## 2. 数据源清单

| 数据源 | 路径/表名 | 日期范围 | symbol 覆盖 | 状态 |
|---|---|---:|---:|---|
| qlib historical prediction | `qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill` + `qlib_pipeline/data_tw/experiments/option_c_daily_signal` | 2022-01-03 ~ 2026-06-09 | 每日 146~150 rows | include |
| qlib Top50 signals | `qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill` | 2022-01-03 ~ 2026-06-09 | Top50 observed dates 829 | include |
| adjusted OHLCV 150 | `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized` | 2015-01-05 ~ 2026-06-09 | 150 | include |
| stable universe | `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt` | instrument-level ranges | 150 | include |
| TWII index | `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv` | 2015-01-05 ~ 2026-05-21 | 1 index | include |
| FinMind archive summary | `qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill/option_c_historical_backfill_20260101_20260531/finmind_archive_apply_summary.json` | 2025-07-01 ~ 2026-06-02 | archive symbols 150 | partial/defer |

## 3. qlib Score 分布审计

- prediction 文件数：`891`；Top50 文件数：`875`。
- 覆盖交易日：`829`，范围 `2022-01-03` ~ `2026-06-09`。
- 每日候选数量：min `146`，median `150`，max `150`。
- raw score 范围：`-0.06571911267422426` ~ `0.14159364654664783`，均值 `0.0016438985013703888`。
- date percentile 可计算日期：`829` / `829`。
- date z-score 可计算日期：`829` / `829`。
- Top50 完整日期：`829` / `829`。
- 是否发现 score 量级漂移：每日均值范围 `-0.01774911994373552` ~ `0.037442992901409934`，每日 std 范围 `0.00973547604918829` ~ `0.048710807793741616`；Phase 1 必须使用日期内 percentile/z-score，不得写死绝对 score 区间。

## 4. OHLCV / 技术 / 流动性审计

- OHLCV symbol 数：`150`；日历范围 `2015-01-05` ~ `2026-06-09`。
- adjusted close 完整可用 symbol：`150`。
- volume 完整可用 symbol：`150`。
- `volume * vwap` 可作为成交额 proxy 的 symbol：`150`。
- 缺失交易日比例中位数：`0.00%`。
- 技术指标 MA5/10/20/60、RSI14、MACD、Bollinger、20d return、20d volatility、volume ratio 均可从 adjusted OHLCV 复算，进入 v1。
- 流动性字段 20d average trading value、volume stability、missing rate、suspension proxy、slippage proxy 可复算，进入 v1。
- 涨跌停风险仅能用 OHLCV proxy，官方涨跌停 flag 未归档，v1 暂缓作为正式字段。

## 5. TWII / 大盘状态审计

- TWII close 覆盖：`100.00%`，范围 `2015-01-05` ~ `2026-05-21`。
- ret20/ret60、MA60/MA120、20d volatility、60d drawdown 可用：`True` / `True` / `True` / `True` / `True` / `True`。
- market breadth 未单独归档，但可用稳定股票池同日横截面复算，例如站上 MA20 比例或 20d return 为正比例。
- `market_regime` 只能作为解释摘要和分组评估，不作为唯一硬规则。

## 6. FinMind Point-in-Time 审计

| feature_group | has_available_at | proposed_lag_rule | safe_forward_fill | v1_status |
|---|---|---|---|---|
| daily OHLCV archive | false | 若使用需至少 T+1；当前 price v1 优先使用 adjusted OHLCV | 不需要 | defer for price v1 |
| institutional trades | false | 必须证明交易日后可见时间，保守 T+1 后 join | 仅 daily rolling，不 forward fill | defer |
| margin trading | false | 必须证明 available_at，保守 T+1 后 join | 仅 daily rolling，不 forward fill | defer |
| monthly revenue | false | 必须按 announcement_date/available_at join，禁止 period join | 可从 available_at 安全 forward fill，并保留 source_period/days_since_last_report | defer |
| valuation PER/PBR | false | 必须证明 date/available_at 口径 | 可按 available_at forward fill | defer |

FinMind 摘要显示 institutional/margin/monthly revenue/valuation 当前归档 count 为 0，且没有可审计的 `available_at`/`announcement_date` 字段，因此不能进入 v1。

## 7. 特征覆盖率

| feature | source | coverage_pct | start_date | end_date | point_in_time_safe | v1_status | reason |
|---|---|---:|---|---|---|---|---|
| qlib_score | qlib prediction.csv | 100.00% | 2022-01-03 | 2026-06-09 | true | include | Historical prediction artifacts are available; raw score must be calibrated by date. |
| qlib_rank | qlib top50/prediction rank | 100.00% | 2022-01-03 | 2026-06-09 | true | include | Top30/Top50 flags can be reconstructed from rank. |
| qlib_score_percentile_by_date | derived from qlib score | 100.00% | 2022-01-03 | 2026-06-09 | true | include | Percentile is available where daily candidate count >= 2. |
| qlib_score_zscore_by_date | derived from qlib score | 100.00% | 2022-01-03 | 2026-06-09 | true | include | Z-score is available where daily score std > 0. |
| adjusted_close | Yahoo/Scrapling adjusted OHLCV | 100.00% | 2015-01-05 | 2026-06-09 | true | include | Adjusted close is complete enough for return features and later label construction. |
| future_return_label_base | Yahoo/Scrapling adjusted OHLCV | 100.00% | 2015-01-05 | 2026-06-09 | true | include | Adjusted close is complete enough for return features and later label construction. |
| volume | Yahoo/Scrapling adjusted OHLCV | 100.00% | 2015-01-05 | 2026-06-09 | true | include | Volume is complete enough for liquidity and volume-ratio features. |
| trading_value_proxy | volume * vwap | 100.00% | 2015-01-05 | 2026-06-09 | true | include | Direct trading_money is absent in normalized bars, but volume*vwap is usable as a proxy. |
| MA5 | derived from adjusted OHLCV | 100.00% | 2015-01-05 | 2026-06-09 | true | include | No stable indicator archive found, but feature is reproducible from OHLCV. |
| MA10 | derived from adjusted OHLCV | 100.00% | 2015-01-05 | 2026-06-09 | true | include | No stable indicator archive found, but feature is reproducible from OHLCV. |
| MA20 | derived from adjusted OHLCV | 100.00% | 2015-01-05 | 2026-06-09 | true | include | No stable indicator archive found, but feature is reproducible from OHLCV. |
| MA60 | derived from adjusted OHLCV | 100.00% | 2015-01-05 | 2026-06-09 | true | include | No stable indicator archive found, but feature is reproducible from OHLCV. |
| RSI14 | derived from adjusted OHLCV | 100.00% | 2015-01-05 | 2026-06-09 | true | include | No stable indicator archive found, but feature is reproducible from OHLCV. |
| MACD | derived from adjusted OHLCV | 100.00% | 2015-01-05 | 2026-06-09 | true | include | No stable indicator archive found, but feature is reproducible from OHLCV. |
| Bollinger_position | derived from adjusted OHLCV | 100.00% | 2015-01-05 | 2026-06-09 | true | include | No stable indicator archive found, but feature is reproducible from OHLCV. |
| ret20 | derived from adjusted OHLCV | 100.00% | 2015-01-05 | 2026-06-09 | true | include | No stable indicator archive found, but feature is reproducible from OHLCV. |
| volatility20 | derived from adjusted OHLCV | 100.00% | 2015-01-05 | 2026-06-09 | true | include | No stable indicator archive found, but feature is reproducible from OHLCV. |
| volume_ratio20 | derived from adjusted OHLCV | 100.00% | 2015-01-05 | 2026-06-09 | true | include | No stable indicator archive found, but feature is reproducible from OHLCV. |
| avg_trading_value_20d | derived liquidity panel | 100.00% | 2015-01-05 | 2026-06-09 | true | include | Can be derived from volume, vwap, and missing-date patterns. |
| volume_stability20 | derived liquidity panel | 100.00% | 2015-01-05 | 2026-06-09 | true | include | Can be derived from volume, vwap, and missing-date patterns. |
| missing_rate20 | derived liquidity panel | 100.00% | 2015-01-05 | 2026-06-09 | true | include | Can be derived from volume, vwap, and missing-date patterns. |
| suspension_proxy | derived liquidity panel | 100.00% | 2015-01-05 | 2026-06-09 | true | include | Can be derived from volume, vwap, and missing-date patterns. |
| slippage_proxy | derived liquidity panel | 100.00% | 2015-01-05 | 2026-06-09 | true | include | Can be derived from volume, vwap, and missing-date patterns. |
| limit_up_down_proxy | OHLCV derived | 100.00% | 2015-01-05 | 2026-06-09 | true | defer | Proxy exists but official limit-up/down status is not archived. |
| TWII_close | TWII.csv | 100.00% | 2015-01-05 | 2026-05-21 | true | include | TWII continuous features are available. |
| TWII_ret20 | TWII.csv | 100.00% | 2015-01-05 | 2026-05-21 | true | include | TWII continuous features are available. |
| TWII_ret60 | TWII.csv | 100.00% | 2015-01-05 | 2026-05-21 | true | include | TWII continuous features are available. |
| TWII_close_vs_MA60 | TWII.csv | 100.00% | 2015-01-05 | 2026-05-21 | true | include | TWII continuous features are available. |
| TWII_close_vs_MA120 | TWII.csv | 100.00% | 2015-01-05 | 2026-05-21 | true | include | TWII continuous features are available. |
| market_volatility20 | TWII.csv | 100.00% | 2015-01-05 | 2026-05-21 | true | include | TWII continuous features are available. |
| market_drawdown60 | TWII.csv | 100.00% | 2015-01-05 | 2026-05-21 | true | include | TWII continuous features are available. |
| market_breadth20 | derived from stable stock pool | 100.00% | 2015-01-05 | 2026-06-09 | true | include | Breadth is not pre-archived but can be reproducibly computed from the stable pool. |
| institutional_net_buy | FinMind institutional_trades | 0.00% |  |  | false | defer | No archived rows in current FinMind summary. |
| margin_balance | FinMind margin_trading | 0.00% |  |  | false | defer | No archived rows in current FinMind summary. |
| short_balance | FinMind margin_trading | 0.00% |  |  | false | defer | No archived rows in current FinMind summary. |
| monthly_revenue_yoy_mom | FinMind monthly_revenue | 0.00% |  |  | false | defer | No archived rows in current FinMind summary. |
| valuation_PER_PBR | FinMind valuation | 0.00% |  |  | false | defer | No archived rows in current FinMind summary. |

## 8. 风险与阻塞项

- 必须修复：Phase 1 构样本前，FinMind 财务/月营收/估值若要启用，必须补齐 row-level `available_at` 或 `announcement_date`。
- 必须修复：qlib score band 必须基于 Phase 0/Phase 1 分布校准，不能沿用固定绝对 score 区间。
- 覆盖风险：historical backfill 的可用 prediction 日期主要来自已有 backfill；若 Phase 1 需要更长训练区间，需确认缺失日期是否可接受，但不能在本阶段触发刷新或回填。
- 流动性风险：直接 trading_money 在 normalized bars 缺失，v1 使用 `volume * vwap` proxy；官方滑点/涨跌停/停牌标志未归档。
- 产品边界风险：报告和后续输出必须保持 research-only，不能出现真实交易动作指令。

## 9. Phase 1 准入建议

- 可进入 Phase 1：qlib score/rank/date percentile/date z-score、Top10/Top30/Top50 flags、OHLCV 派生技术趋势、流动性 proxy、TWII 连续特征、market breadth proxy。
- 暂缓特征：FinMind institutional/margin/monthly revenue/valuation、官方 limit-up/down flag、正式 trading_money 字段。
- 拒绝特征：任何只有 period 而没有 `available_at`/`announcement_date` 的财务/月营收直接 join。
- 是否建议进入 Phase 1：建议在上述暂缓项保持暂缓的前提下进入 Phase 1；若审查者要求 FinMind 补充特征必须进入 v1，则需要先补充 PIT 归档，不能直接构样本。
