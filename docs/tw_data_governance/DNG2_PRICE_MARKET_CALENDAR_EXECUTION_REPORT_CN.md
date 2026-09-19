# DNG2 PriceStore / TWII / Calendar 执行报告

生成日期：2026-06-29

执行者：DNG2 Executor

## 1. 结论

DNG2 指定的 canonical PriceStore / TWII / Calendar builder、validator 与产物已生成。

总体状态：`BLOCKED_COVERAGE`

原因：

- PriceStore 已从本地 normalized 价格源生成到 `2026-06-25`，但 `halt_flag` 源数据不可得，且 18 个标的未覆盖完整 provider calendar 历史区间，因此 PriceStore 为 `PARTIAL_READY`。
- TWII canonical artifact 只能生成到 `2026-05-21`，而 provider calendar / PriceStore asof 为 `2026-06-25`，缺 `2026-05-22` 至 `2026-06-25` 等 29 个 calendar dates，因此 TWII 为 `BLOCKED_COVERAGE`。
- readiness matrix 中 `can_continue=false`，不应进入模型推理、策略输入包、回放、readonly publish、Agent prompt 或 DNG3。

建议：不进入 DNG3；先做 DNG2 repair，补齐本地 TWII normalized 覆盖、权威 halt/suspension 字段来源，以及 next-day execution availability 所需的下一交易日价格行。

## 2. 本轮输入与安全边界

已阅读工作单要求的治理文档与输入：

- `docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md`
- `docs/tw_data_governance/DNG2_PRICE_MARKET_CALENDAR_WORK_CN.md`
- `docs/tw_data_governance/DNG1_DATA_CATALOG_REVIEW_CN.md`
- `docs/tw_modular_contracts/PRICE_STORE_CONTRACT_CN.md`
- `data_tw/catalog/data_catalog.json`
- `data_tw/catalog/latest_status.json`

本轮只读取本地数据：

- Price source：`qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized`
- TWII source：`qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv`
- Calendar source：`qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt`
- Instrument source：`qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt`

未触发真实抓数、provider refresh/publish、qlib accepted latest switch、readonly latest publish、Agent prompt publish、模型训练、模型推理、模型 score 生成、策略回放、broker/order/quick-trade、target_position 或 target_weight。

## 3. 生成脚本

新增：

- `scripts/build_tw_canonical_price_market_calendar.py`
- `scripts/validate_tw_canonical_price_market_calendar.py`

语法检查：

```bash
python -m py_compile scripts/build_tw_canonical_price_market_calendar.py scripts/validate_tw_canonical_price_market_calendar.py
```

结果：通过。

## 4. 生成产物

run_id：`dng2_price_market_calendar_20260625`

asof：`2026-06-25`

PriceStore：

- `data_tw/canonical/price_store/tw_equity_daily/dng2_price_market_calendar_20260625/manifest.json`
- `data_tw/canonical/price_store/tw_equity_daily/dng2_price_market_calendar_20260625/prices.csv`
- `data_tw/canonical/price_store/tw_equity_daily/dng2_price_market_calendar_20260625/schema.json`
- `data_tw/canonical/price_store/tw_equity_daily/dng2_price_market_calendar_20260625/coverage_audit.csv`
- `data_tw/canonical/price_store/tw_equity_daily/dng2_price_market_calendar_20260625/adjustment_audit.json`
- `data_tw/canonical/price_store/tw_equity_daily/dng2_price_market_calendar_20260625/execution_availability_audit.csv`
- `data_tw/canonical/price_store/tw_equity_daily/dng2_price_market_calendar_20260625/lineage.json`

TWII / MarketFeatureStore：

- `data_tw/canonical/market_feature_store/twii_daily/dng2_price_market_calendar_20260625/manifest.json`
- `data_tw/canonical/market_feature_store/twii_daily/dng2_price_market_calendar_20260625/twii.csv`
- `data_tw/canonical/market_feature_store/twii_daily/dng2_price_market_calendar_20260625/schema.json`
- `data_tw/canonical/market_feature_store/twii_daily/dng2_price_market_calendar_20260625/coverage_audit.csv`
- `data_tw/canonical/market_feature_store/twii_daily/dng2_price_market_calendar_20260625/lineage.json`

Catalog / readiness：

- `data_tw/catalog/readiness_matrix/2026-06-25/price_market_calendar.json`
- `data_tw/catalog/dng2_price_market_calendar_validation.json`

## 5. PriceStore 状态

PriceStore status：`PARTIAL_READY`

统计：

- date_min：`2015-01-05`
- date_max / asof：`2026-06-25`
- symbol_count：150
- row_count：400,205
- latest_complete_symbol_count：150
- required fields：全部存在
- forbidden fields：未发现
- close coverage：100%
- adj_factor coverage：100%
- next_day_execution_availability 字段覆盖：100%
- halt_flag coverage：0%，源数据无停牌字段，已留空并在 schema/manifest/coverage 中标明

覆盖审计：

- 132 个标的完整覆盖 provider calendar。
- 18 个标的为 `PARTIAL_READY`，主要是新上市或源历史较短标的。
- 最低 coverage_ratio：0.142703。

PriceStore 未被标记为 READY 的主要原因：

- 源数据没有权威 `halt_flag`。
- 部分标的未覆盖完整历史 calendar。
- asof 最新行尚无下一交易日价格行，因此不能把最新 asof 的 next-day execution availability 视为可执行确认。

## 6. TWII / MarketFeatureStore 状态

TWII status：`BLOCKED_COVERAGE`

统计：

- date_min：`2015-01-05`
- date_max：`2026-05-21`
- target asof：`2026-06-25`
- row_count：2,771
- required fields：全部存在
- forbidden fields：未发现
- coverage_ratio against provider calendar：0.989602
- missing calendar dates：29

关键缺口：

- provider calendar 最新为 `2026-06-25`。
- TWII source 最新只到 `2026-05-21`。
- 缺 `2026-05-22`、`2026-05-25` 至 `2026-06-18`、`2026-06-22` 至 `2026-06-25` 等近期交易日。

MA 字段说明：

- `ma_5`、`ma_20`、`ma_60` 和 `market_trend_state` 使用当前及历史 close 计算。
- 起始样本不足位置留空，并在 coverage 中记录。

## 7. Calendar / Readiness 状态

Calendar evidence：

- source：`qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt`
- date_min：`2015-01-05`
- date_max：`2026-06-25`
- 该 calendar 只是 provider/calendar evidence，不代表 qlib accepted latest。

Readiness matrix：

- path：`data_tw/catalog/readiness_matrix/2026-06-25/price_market_calendar.json`
- status：`BLOCKED_COVERAGE`
- can_continue：`false`

dependency 结果：

| dependency | status | can_continue | blocker |
| --- | --- | --- | --- |
| price_coverage | PARTIAL_READY / coverage READY | true | 无 asof 覆盖阻断 |
| twii_coverage | BLOCKED_COVERAGE | false | TWII 最新只到 2026-05-21 |
| calendar_coverage | READY | true | 无 |
| next_day_execution_availability | PARTIAL_READY | false | halt_flag 不可得，asof 最新行无下一交易日价格行 |
| mark_to_market_close_coverage | READY | true | 无 |
| holiday_or_no_data_evidence | READY | true | 无 |

## 8. Validator 结果

执行：

```bash
python scripts/validate_tw_canonical_price_market_calendar.py --run-id dng2_price_market_calendar_20260625 --asof 2026-06-25 --json
```

输出摘要：

```text
ok=true
status=BLOCKED_COVERAGE
errors=0
warnings=0
prices row_count=400205
twii row_count=2771
price_store status=PARTIAL_READY
twii status=BLOCKED_COVERAGE
readiness_matrix status=BLOCKED_COVERAGE
can_continue=false
```

validator 已检查：

- required files 存在；
- required fields 存在；
- manifest/schema 结构；
- row count > 0；
- forbidden fields 不存在；
- forbidden action flags 均为 false；
- readiness matrix 存在并包含 DNG2 要求的 dependencies。

完整 validation JSON：

- `data_tw/catalog/dng2_price_market_calendar_validation.json`

## 9. 禁止动作确认

本轮输出 manifest、lineage、readiness matrix 与 validator 均记录以下 flags 为 false：

- `real_data_fetch_triggered=false`
- `provider_refresh_triggered=false`
- `provider_publish_triggered=false`
- `qlib_accepted_latest_switched=false`
- `readonly_latest_published=false`
- `agent_prompt_published=false`
- `model_training_triggered=false`
- `model_inference_triggered=false`
- `strategy_replay_triggered=false`
- `broker_order_quick_trade_triggered=false`
- `target_position_or_weight_generated=false`

未生成或修改任何 accepted/latest pointer、readonly publish、Agent prompt publish、模型 score、策略回放或交易相关产物。

## 10. 下一步建议

不建议进入 DNG3。

建议先开 DNG2 repair：

1. 用本地可审计来源补齐 TWII normalized 数据到 `2026-06-25`，不得直接抓数，除非另有独立授权。
2. 引入或 catalog 权威 halt/suspension 数据源，修复 `halt_flag` 覆盖。
3. 在下一交易日价格行可用后，重新生成 next-day execution availability。
4. 重新运行 builder 与 validator，目标是 readiness matrix `status=READY` 且 `can_continue=true`。
