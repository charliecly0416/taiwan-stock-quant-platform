# Phase 0 数据审计执行报告

## 1. 本步目标、输入、输出、禁止事项

### 1.1 本步目标

依据 `prompt_execute.md`、`docs/TW_STOCK_DECISION_META_MODEL_DESIGN_CN.md`、`docs/tw_decision_model/PHASE0_REVIEW_BASELINE_AND_NEXT_WORK_CN.md` 执行 Phase 0 数据审计与特征可用性确认。

本步只确认 Decision Model v1 可用的数据范围、时间覆盖、缺失情况、point-in-time 规则，以及哪些特征可以进入 Phase 1 样本构建。

### 1.2 输入

- qlib historical prediction / Top50 signal：
  - `qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill`
  - `qlib_pipeline/data_tw/experiments/option_c_daily_signal`
- adjusted OHLCV：
  - `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized`
- 稳定股票池：
  - `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt`
- TWII：
  - `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv`
- FinMind 归档摘要：
  - `qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill/option_c_historical_backfill_20260101_20260531/finmind_archive_apply_summary.json`
- 当前 baseline / stress replay 输出：
  - `data_tw/experiments/strategy_stress_replay/*`

### 1.3 输出

本步生成以下审查入口文件：

- `docs/tw_decision_model/phase0_feature_availability_report.md`
- `data_tw/experiments/decision_model/phase0_feature_coverage.csv`
- `data_tw/experiments/decision_model/phase0_data_sources.json`
- `data_tw/experiments/decision_model/phase0_point_in_time_rules.md`
- `scripts/audit_tw_decision_phase0.py`

### 1.4 禁止事项执行情况

本步未执行以下动作：

- 未训练模型。
- 未生成 Entry / Exit 标签。
- 未生成真实交易建议。
- 未调用 broker / orders / quick-trade / target position。
- 未触发 provider refresh / provider publish。
- 未切换 accepted latest。
- 未修改 monitor config / alerts / 模拟账户。
- 未提交、未推送。

## 2. 代码变更

新增只读审计脚本：

- `scripts/audit_tw_decision_phase0.py`

脚本行为：

- 只读取本地 CSV / JSON / 文档化归档。
- 只写入 Phase 0 审计报告目录。
- 不导入或调用任何刷新、发布、下单、交易、monitor 写入入口。
- 对 qlib prediction 按 `date + instrument` 去重，避免同日多次运行导致候选数量重复累计。
- 对 daily signal 与 historical backfill 的 Top50 都纳入完整性审计。

## 3. 数据源审计结果摘要

| 数据源 | 日期范围 | 覆盖 | 状态 |
|---|---:|---:|---|
| qlib historical prediction | 2022-01-03 ~ 2026-06-09 | 829 个交易日，每日 146~150 rows | include |
| qlib Top50 signals | 2022-01-03 ~ 2026-06-09 | Top50 完整日期 829 / 829 | include |
| adjusted OHLCV 150 | 2015-01-05 ~ 2026-06-09 | 150 symbols | include |
| TWII | 2015-01-05 ~ 2026-05-21 | 1 index | include |
| FinMind archive summary | 2025-07-01 ~ 2026-06-02 | daily OHLCV archive 150 symbols；institutional/margin/monthly revenue/valuation 为 0 | partial / defer |

## 4. qlib Score 分布审计

- prediction 文件数：891。
- historical Top50 文件数：875。
- daily Top50 文件数：16。
- 覆盖交易日：829。
- 每日候选数量：min 146，median 150，max 150。
- raw score 范围：-0.06571911267422426 ~ 0.14159364654664783。
- raw score 均值：0.0016438985013703888。
- date percentile 可计算日期：829 / 829。
- date z-score 可计算日期：829 / 829。
- Top50 完整日期：829 / 829。

结论：

- qlib raw score 具备审计覆盖，但绝对值不可直接作为规则。
- Phase 1 必须生成 `qlib_score_percentile_by_date` 与 `qlib_score_zscore_by_date`。
- 不允许写死 `0.4-0.8`、`0.04-0.08` 或其他固定绝对 score 区间作为准入规则。

## 5. OHLCV / 技术指标 / 流动性审计

adjusted OHLCV 覆盖 150 支稳定股票池，日期范围 2015-01-05 ~ 2026-06-09。

可进入 v1：

- adjusted close
- volume
- `volume * vwap` trading value proxy
- MA5 / MA10 / MA20 / MA60
- RSI14
- MACD
- Bollinger position
- 20d return
- 20d volatility
- volume ratio
- 20d average trading value
- volume stability
- missing rate
- suspension proxy
- slippage proxy

暂缓：

- 官方 limit-up / limit-down flag：当前未发现稳定归档，只能用 OHLCV proxy，不能宣称官方字段可用。

## 6. TWII / 大盘状态审计

TWII 连续特征可用：

- TWII close
- ret20 / ret60
- close vs MA60 / MA120
- 20d volatility
- drawdown from 60d high

market breadth 未发现独立稳定归档，但可从稳定股票池同日横截面复算，例如：

- 站上 MA20 的股票比例。
- 20d return 为正的股票比例。

结论：

- 连续大盘特征可进入 Phase 1。
- `market_regime` 只能作为解释摘要和分组评估，不能作为唯一硬买卖闸门。

## 7. FinMind Point-in-Time 审计

当前 `finmind_archive_apply_summary.json` 显示：

- daily OHLCV archive：33582 rows，150 symbols，2025-07-01 ~ 2026-06-02。
- institutional trades：0 rows。
- margin trading：0 rows。
- monthly revenue：0 rows。
- valuation：0 rows。
- corporate actions：0 rows。
- 未发现 row-level `available_at` / `announcement_date`。

结论：

- FinMind institutional / margin / monthly revenue / valuation 不能进入 v1。
- 财务/月营收/估值类特征必须等到具备 `source_period`、`available_at`、`days_since_last_report` 后才能进入 Phase 1。
- 任何按 `period` 直接 join 的方案应拒绝。
- 若后续使用 FinMind daily OHLCV archive，也必须采用保守 T+1 available_at 规则；当前 price v1 优先使用 adjusted OHLCV。

## 8. v1 特征准入摘要

本次输出 `phase0_feature_coverage.csv` 共 37 行：

- include：31。
- defer：6。
- reject：0。

可进入 Phase 1：

- qlib score / rank / date percentile / date z-score。
- Top10 / Top30 / Top50 flags。
- adjusted OHLCV 与技术趋势派生特征。
- 流动性与滑点 proxy。
- TWII 连续特征。
- market breadth proxy。

暂缓：

- FinMind institutional net buy。
- FinMind margin balance / short balance。
- FinMind monthly revenue yoy / mom。
- FinMind valuation PER / PBR。
- 官方涨跌停 flag。
- 正式 `trading_money` 字段。

拒绝：

- 仅有 period、没有 `available_at` / `announcement_date` 的财务/月营收直接 join。

## 9. 验证命令与结果

已执行：

```bash
python -m py_compile scripts/audit_tw_decision_phase0.py
python scripts/audit_tw_decision_phase0.py
python -m json.tool data_tw/experiments/decision_model/phase0_data_sources.json
rg -n "买入|卖出|立即|下单|order|broker|quick-trade|target position|accepted latest|publish|refresh" docs/tw_decision_model/phase0_feature_availability_report.md data_tw/experiments/decision_model/phase0_point_in_time_rules.md data_tw/experiments/decision_model/phase0_data_sources.json scripts/audit_tw_decision_phase0.py
```

结果：

- `py_compile` 通过。
- Phase 0 脚本执行成功，生成 4 个指定审计产物。
- JSON 可解析。
- 安全边界关键词扫描命中的内容均为禁止事项或 research-only 边界说明，不是真实交易动作。

备注：

- 当前环境普通沙箱多次出现 `bwrap: loopback: Failed RTM_NEWADDR`，本地审计和只读检查命令按权限流程提权执行。
- 提权命令仍只读本地数据并写指定审计报告，不触发刷新、发布或交易。

## 10. 风险与待审查问题

必须审查：

- 是否认可 FinMind institutional / margin / monthly revenue / valuation 在 v1 暂缓。
- 是否认可 market breadth 由稳定股票池横截面复算，而不是要求已有归档。
- 是否认可 `volume * vwap` 作为 v1 交易额 proxy。
- 是否认可官方 limit-up/down flag 暂缓，仅保留 OHLCV proxy。
- 是否认可在 FinMind 补充特征暂缓的前提下进入 Phase 1。

主要风险：

- FinMind 补充特征目前不能证明 point-in-time 安全。
- qlib historical prediction 日期覆盖足够做 Phase 1 初版，但若审查者要求更长训练区间，需要先确认缺失日期处理策略。
- TWII 覆盖到 2026-05-21，股票池 OHLCV 覆盖到 2026-06-09，Phase 1 构样本时需处理 2026-05-22 之后 TWII 缺口。
- normalized bars 没有正式 `trading_money` 字段，v1 使用 `volume * vwap` proxy。

## 11. Phase 1 建议

建议进入 Phase 1，但限定如下：

- 只使用 Phase 0 标为 include 的特征。
- FinMind institutional / margin / monthly revenue / valuation 暂不进入样本。
- 所有特征必须按 `asof` 或 trailing window 构造。
- qlib score 必须同时保留 raw、date percentile、date z-score。
- 不生成单一固定阈值标签；Phase 1 必须同时生成或审计动态标签、连续收益目标、排序目标，并报告正负样本比例。

