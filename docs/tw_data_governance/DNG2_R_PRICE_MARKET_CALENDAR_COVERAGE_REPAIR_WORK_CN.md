# DNG2_R PriceStore / TWII / Calendar 覆盖修复工作文档

生成日期：2026-06-29

## 1. 背景

DNG2 审查结论：

```text
FAIL_NEEDS_DNG2_REPAIR
```

主要阻断：

- TWII canonical store 只到 `2026-05-21`，目标 asof 是 `2026-06-25`；
- PriceStore 是 `PARTIAL_READY`；
- latest asof 缺下一交易日价格，`next_day_execution_availability` 不可确认；
- `halt_flag` 源证据不足。

## 2. Repair 目标

在不触发真实抓数、不 publish、不切 latest、不训练/推理/回放的前提下，尽量用本地已有数据修复 DNG2 覆盖问题。

## 3. 允许动作

允许：

- 只读扫描本地 TWII / market index / price source；
- 修改 DNG2 builder/validator；
- 重新生成 DNG2 canonical 产物；
- 重新生成 readiness matrix 和 validation json；
- 写 repair 执行报告。

允许读取：

```text
data_tw/**
qlib_pipeline/data_tw/**
backend/**
scripts/**
```

## 4. 必须执行的 repair

### 4.1 TWII 本地源补查

执行者必须系统查找本地可用 TWII/market index 数据源，至少覆盖：

```text
data_tw/**
qlib_pipeline/data_tw/**
backend/**
```

查找模式包括但不限于：

```text
twii
market_index
TAIEX
加權
加权
^TWII
0050 market proxy
```

如果找到比 `2026-05-21` 更新的可信本地源，必须接入 DNG2 builder，并在 lineage 中声明。

如果找不到，必须写明：

```text
TWII local source not found beyond 2026-05-21
requires external source repair
```

不得伪造 TWII。

### 4.2 halt/suspension evidence

如果本地没有正式 halt/suspension 字段，允许采用保守派生：

```text
halt_flag = true when required OHLCV is missing or volume is missing for an expected trading day
halt_flag = false only when OHLCV row exists and tradable_flag=true
halt_flag_source = derived_from_price_presence
```

必须写入 `adjustment_audit.json` 或单独 `halt_suspension_audit.json`。

### 4.3 next-day execution availability

对 latest asof，若下一交易日价格尚不存在，不得使整条历史 PriceStore 失败；应区分：

```text
historical_execution_ready
latest_next_day_execution_pending
```

规则：

- 对非最后一个交易日，只要下一交易日 open/close 可得，应标记 availability；
- 对最后一个 asof，若下一交易日尚未到来或本地未有价格，应标记 `pending_next_trade_date`；
- readiness matrix 必须说明这会阻断“执行回放/真实 next-open shadow”，但不一定阻断“asof 当日模型 score 生成”。

### 4.4 readiness 语义修复

DNG2_R 必须把 readiness 分成：

```text
can_continue_to_model_score
can_continue_to_replay
can_continue_to_shadow_execution
can_continue_to_dng3
```

不能只用一个 `can_continue=false` 混淆所有后续路线。

DNG3 是否可进入，至少要求：

```text
PriceStore canonical exists
calendar exists
TWII status is READY or PARTIAL_READY_WITH_DECLARED_GAP
no fabricated data
```

## 5. 输出产物

必须更新或生成：

```text
scripts/build_tw_canonical_price_market_calendar.py
scripts/validate_tw_canonical_price_market_calendar.py
data_tw/canonical/price_store/tw_equity_daily/{repair_run_id}/
data_tw/canonical/market_feature_store/twii_daily/{repair_run_id}/
data_tw/catalog/readiness_matrix/{asof}/price_market_calendar.json
data_tw/catalog/dng2_price_market_calendar_validation.json
docs/tw_data_governance/DNG2_R_PRICE_MARKET_CALENDAR_COVERAGE_REPAIR_EXECUTION_REPORT_CN.md
```

## 6. 禁止动作

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

## 7. 通过条件

Repair 通过需要满足：

- validator 结构通过；
- readiness matrix 使用分层 can_continue；
- TWII 覆盖问题被本地源修复，或明确标为需要外部补源；
- halt/suspension 证据存在；
- next-day execution pending 被正确表达；
- 不再把 latest next-day pending 误判为整条 PriceStore 不可用；
- 未触发 forbidden action。

如果本地无法补 TWII 到目标 asof，执行者必须停在 repair report，建议统筹决定是否授权真实补源。
