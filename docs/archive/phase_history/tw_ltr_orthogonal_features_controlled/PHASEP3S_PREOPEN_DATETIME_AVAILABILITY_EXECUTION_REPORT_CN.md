# Phase P3S 执行报告：Pre-open Datetime Availability 判定

生成时间：`2026-06-15T15:55:11+00:00`

## 1. 结论

- gate：`phase_p3s_preopen_datetime_availability_not_proven_stop`。
- signal_asof：`2026-06-15`。
- 结论：不能证明 institutional / margin 的 T 日数据能稳定在 T+1 开盘前取得。
- 未升级为 datetime available_at 合同，继续保留 P3RRR 后的日期级 `current_or_pit_delayed`。
- 未训练 qlib / LTR，未调参，未扩大 Top50，未切 accepted latest，未触发 provider / monitor / trading。

## 2. 判定依据

- P3RRR raw archive 有 `fetched_at`，可追溯到 raw response / normalized archive。
- 但 raw archive 与 latest feature table 没有可信 `available_at_datetime` / `used_available_at_datetime` 字段。
- P3 rerank summary 没有 `strategy_generation_time`、`target_execution_date`、`target_open_datetime` 合同字段。
- 现有 `fetched_at` 是本次 P3RRR 抓取时间，不是源数据发布或可取得时间；对历史交易日不能证明当时已在 T+1 开盘前可得。
- local raw archive 可审计最近交易日数量：`3`，要求至少 `5`；可见日期：`['2026-06-11', '2026-06-12', '2026-06-15']`。

## 3. Pre-open Coverage Audit

| feature_family | trade_date | symbol_count | raw_row_count | fetched_at_min | fetched_at_max | available_at_datetime_min | available_at_datetime_max | next_trading_day | target_open_datetime | preopen_available_symbol_count | preopen_available_ratio | late_symbol_count | missing_timestamp_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| institutional_flow | 2026-06-11 | 50 | 50 | 2026-06-15T15:34:20+00:00 | 2026-06-15T15:34:49+00:00 |  |  | 2026-06-12 | 2026-06-12T01:00:00+00:00 | 0 | 0.0 | 50 | 50 |
| institutional_flow | 2026-06-12 | 50 | 50 | 2026-06-15T15:34:20+00:00 | 2026-06-15T15:34:49+00:00 |  |  | 2026-06-15 | 2026-06-15T01:00:00+00:00 | 0 | 0.0 | 50 | 50 |
| institutional_flow | 2026-06-15 | 50 | 50 | 2026-06-15T15:34:20+00:00 | 2026-06-15T15:34:49+00:00 |  |  |  |  | 0 | 0.0 | 50 | 50 |
| margin_short | 2026-06-11 | 50 | 50 | 2026-06-15T15:34:49+00:00 | 2026-06-15T15:35:21+00:00 |  |  | 2026-06-12 | 2026-06-12T01:00:00+00:00 | 0 | 0.0 | 50 | 50 |
| margin_short | 2026-06-12 | 50 | 50 | 2026-06-15T15:34:49+00:00 | 2026-06-15T15:35:21+00:00 |  |  | 2026-06-15 | 2026-06-15T01:00:00+00:00 | 0 | 0.0 | 50 | 50 |
| margin_short | 2026-06-15 | 50 | 50 | 2026-06-15T15:34:49+00:00 | 2026-06-15T15:35:21+00:00 |  |  |  |  | 0 | 0.0 | 50 | 50 |

## 4. 是否升级合同

- 不升级。
- 阻塞原因：缺少可信 datetime 级 availability timestamp；latest feature table 也未记录 used datetime；P3 summary 未记录 strategy generation / target open datetime。
- 日期级 PIT 合同仍有效：`available_at >= next_trading_day(trade_date)` 且 as-of join 使用 `available_at <= signal_asof`。

## 5. 只读与安全边界

- P3 rerank 仍为 readonly artifact。
- qlib Top50 candidate universe 不变。
- 默认策略不变。
- 未触发 accepted latest / provider / monitor / broker / orders / quick-trade。
- 未输出 target position / target weight，未提供收益、胜率或上涨概率承诺。

## 6. 输出 Artifact

- audit CSV：`data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-15_p3s_preopen_datetime_audit.csv`
- audit JSON：`data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_2026-06-15_p3s_preopen_datetime_audit.json`
- report：`docs/tw_ltr_orthogonal_features_controlled/PHASEP3S_PREOPEN_DATETIME_AVAILABILITY_EXECUTION_REPORT_CN.md`

## 7. 执行命令

```text
python -m py_compile scripts/audit_phasep3s_preopen_datetime_availability.py
python scripts/audit_phasep3s_preopen_datetime_availability.py
```
