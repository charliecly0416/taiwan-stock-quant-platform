# DNG2 PriceStore / TWII / Calendar 规范化工作文档

生成日期：2026-06-29

## 1. 背景

DNG1 审查结论：

```text
PASS_WITH_CONDITIONS_GO_DNG2
```

DNG2 只推进 canonical PriceStore / TWII / Calendar / execution readiness，不做 publish、latest switch、模型 score、LTR、策略回放。

## 2. 目标

建立可被后续模型推理、策略输入包、回放和 shadow 复用的 canonical 基础层：

```text
data_tw/canonical/price_store/{price_store_id}/{run_id}/
data_tw/canonical/market_feature_store/twii_daily/{run_id}/
data_tw/catalog/readiness_matrix/{asof}/price_market_calendar.json
```

## 3. 必须生成

脚本：

```text
scripts/build_tw_canonical_price_market_calendar.py
scripts/validate_tw_canonical_price_market_calendar.py
```

产物：

```text
data_tw/canonical/price_store/tw_equity_daily/{run_id}/manifest.json
data_tw/canonical/price_store/tw_equity_daily/{run_id}/prices.csv
data_tw/canonical/price_store/tw_equity_daily/{run_id}/schema.json
data_tw/canonical/price_store/tw_equity_daily/{run_id}/coverage_audit.csv
data_tw/canonical/price_store/tw_equity_daily/{run_id}/adjustment_audit.json
data_tw/canonical/price_store/tw_equity_daily/{run_id}/execution_availability_audit.csv
data_tw/canonical/price_store/tw_equity_daily/{run_id}/lineage.json
data_tw/canonical/market_feature_store/twii_daily/{run_id}/manifest.json
data_tw/canonical/market_feature_store/twii_daily/{run_id}/twii.csv
data_tw/canonical/market_feature_store/twii_daily/{run_id}/schema.json
data_tw/canonical/market_feature_store/twii_daily/{run_id}/coverage_audit.csv
data_tw/canonical/market_feature_store/twii_daily/{run_id}/lineage.json
data_tw/catalog/readiness_matrix/{asof}/price_market_calendar.json
data_tw/catalog/dng2_price_market_calendar_validation.json
docs/tw_data_governance/DNG2_PRICE_MARKET_CALENDAR_EXECUTION_REPORT_CN.md
```

## 4. 数据来源要求

优先从现有本地数据与 DNG1 catalog 中选择来源。允许读取：

```text
data_tw/**
qlib_pipeline/data_tw/**
data_tw/catalog/data_catalog.json
data_tw/catalog/latest_status.json
```

不得触发真实抓数。

如果 canonical 价格或 TWII 无法完整生成，允许生成 partial canonical artifact，但必须：

- status 标为 `PARTIAL_READY` 或 `BLOCKED_COVERAGE`；
- readiness matrix 中 `can_continue=false`；
- 写明缺失标的、缺失日期、缺失字段、建议 repair。

## 5. PriceStore 字段

`prices.csv` 至少包含：

```text
price_date
instrument
open
high
low
close
volume
adj_factor
tradable_flag
halt_flag
next_day_execution_availability
price_source
adjustment_policy
```

如果某字段源数据不可得，不得伪造。必须在 schema/coverage/manifest 中标明。

## 6. TWII / MarketFeature 字段

`twii.csv` 至少包含：

```text
date
open
high
low
close
volume
return_1d
ma_5
ma_20
ma_60
market_trend_state
source
```

若 MA 样本不足，字段可为空，但必须有 coverage audit。

## 7. Calendar / Readiness

readiness matrix 必须检查：

```text
price_coverage
twii_coverage
calendar_coverage
next_day_execution_availability
mark_to_market_close_coverage
holiday_or_no_data_evidence
```

## 8. Validator 要求

`scripts/validate_tw_canonical_price_market_calendar.py` 必须支持：

```text
python scripts/validate_tw_canonical_price_market_calendar.py --run-id <run_id> --asof <YYYY-MM-DD> --json
```

检查：

- required files；
- required fields；
- manifest schema；
- row count > 0；
- forbidden fields；
- readonly/no publish/no latest switch flags；
- readiness matrix 存在；
- 输出 JSON。

## 9. 禁止动作

不得执行：

```text
真实抓数
provider refresh / publish
qlib accepted latest switch
readonly latest publish
Agent prompt latest publish
模型训练
模型推理
模型 score 生成
策略回放
broker/order/quick-trade
target_position / target_weight
```

## 10. 执行报告

报告必须说明：

1. source 数据从哪里来。
2. 生成的 asof/date range/symbol count。
3. PriceStore/TWII/calendar/readiness 状态。
4. validator 输出。
5. 未触发 forbidden actions。
6. 是否建议进入 DNG3，或需要 DNG2 repair。
