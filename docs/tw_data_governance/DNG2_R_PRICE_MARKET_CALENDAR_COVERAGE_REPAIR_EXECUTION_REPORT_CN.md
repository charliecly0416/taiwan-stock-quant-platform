# DNG2_R PriceStore / TWII / Calendar 覆盖修复执行报告

生成日期：2026-06-29

执行者：DNG2_R

## 1. 执行结论

本次 DNG2_R 已完成本地 repair，未触发真实抓数、provider refresh/publish、qlib accepted latest switch、readonly/Agent publish、模型训练/推理/score、策略回放、broker/order/quick-trade、target_position 或 target_weight。

repair run id：

```text
dng2_r_price_market_calendar_20260625
```

validator 结果：

```text
ok=true
status=PARTIAL_READY
errors=0
warnings=0
prices row_count=400205
twii row_count=2795
price_store=PARTIAL_READY
twii=PARTIAL_READY_WITH_DECLARED_GAP
readiness_matrix=PARTIAL_READY
can_continue_to_model_score=true
can_continue_to_replay=false
can_continue_to_shadow_execution=false
can_continue_to_dng3=true
external_source_repair_required=false
```

结论：可以进入 DNG3。不得进入 replay 或 shadow next-open execution，原因是 latest asof `2026-06-25` 没有下一本地交易日价格行，`next_day_execution_status=pending_next_trade_date`。

## 2. 本地 TWII 源查找结果

本次系统检查了本地 TWII / market index 相关来源，核心候选如下：

| source_label | path | date_max | 结论 |
| --- | --- | --- | --- |
| formal_normalized_nonempty | `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv` | `2026-05-21` | 不足以覆盖目标 asof |
| rcpt15_r3_t_isolated_twii_bridge | `data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/twii_bridge.csv` | `2026-06-25` | 作为本次 DNG2_R 本地输入接入 |

说明：`twii_bridge.csv` 是本地已存在 isolated bridge artifact。本次 DNG2_R 只是读取该本地文件并转为 canonical TWII store，没有重放其历史网络补源，也没有发起新抓数。

TWII canonical 输出：

```text
data_tw/canonical/market_feature_store/twii_daily/dng2_r_price_market_calendar_20260625/
```

TWII 状态为 `PARTIAL_READY_WITH_DECLARED_GAP`：覆盖目标 asof `2026-06-25`，但相对 provider calendar 仍有 5 个早期历史缺口：

```text
2015-07-10
2015-09-29
2016-07-08
2016-09-27
2016-09-28
```

这些缺口已在 coverage audit、manifest、lineage 和 readiness matrix 中声明。目标 asof 不需要用户授权真实补源；若后续路线要求全历史 calendar 100% TWII 覆盖，则需要单独补源或 route-level 豁免。

## 3. halt / suspension evidence 修复

本地没有正式 halt/suspension 字段。本次采用保守派生：

```text
halt_flag=true when required OHLCV or volume is missing
halt_flag=false only when OHLCV row exists and tradable_flag=true
halt_flag_source=derived_from_price_presence
```

新增输出：

```text
data_tw/canonical/price_store/tw_equity_daily/dng2_r_price_market_calendar_20260625/halt_suspension_audit.json
```

PriceStore 中 `halt_flag` 与 `halt_flag_source` 覆盖率均为 100%。

## 4. next-day execution availability 语义修复

本次不再把 latest asof 没有下一交易日价格行解释为整条 PriceStore 不可用。

修复后语义：

```text
historical_execution_ready: 历史行有下一本地同标的交易行时可用于执行语义
latest_next_day_execution_pending: 最新 asof 没有下一本地交易行时标记 pending_next_trade_date
```

因此：

| route | can_continue |
| --- | --- |
| model_score | true |
| replay | false |
| shadow_execution | false |
| dng3 | true |

## 5. readiness matrix 修复

已更新：

```text
data_tw/catalog/readiness_matrix/2026-06-25/price_market_calendar.json
```

矩阵从单一 `can_continue=false` 拆分为：

```text
can_continue_to_model_score=true
can_continue_to_replay=false
can_continue_to_shadow_execution=false
can_continue_to_dng3=true
```

整体 `can_continue=false` 被保留为 “所有路线均可继续” 的严格汇总；route-level 判断必须读取上述四个字段。

## 6. 更新文件

脚本：

```text
scripts/build_tw_canonical_price_market_calendar.py
scripts/validate_tw_canonical_price_market_calendar.py
```

产物：

```text
data_tw/canonical/price_store/tw_equity_daily/dng2_r_price_market_calendar_20260625/
data_tw/canonical/market_feature_store/twii_daily/dng2_r_price_market_calendar_20260625/
data_tw/catalog/readiness_matrix/2026-06-25/price_market_calendar.json
data_tw/catalog/dng2_price_market_calendar_validation.json
```

报告：

```text
docs/tw_data_governance/DNG2_R_PRICE_MARKET_CALENDAR_COVERAGE_REPAIR_EXECUTION_REPORT_CN.md
```

## 7. 验证命令

已执行：

```bash
python -m py_compile scripts/build_tw_canonical_price_market_calendar.py scripts/validate_tw_canonical_price_market_calendar.py
python scripts/build_tw_canonical_price_market_calendar.py --run-id dng2_r_price_market_calendar_20260625 --asof 2026-06-25
python scripts/validate_tw_canonical_price_market_calendar.py --run-id dng2_r_price_market_calendar_20260625 --asof 2026-06-25 --json
```

结果：通过，退出码 0。

## 8. 禁止动作确认

本次 forbidden action flags 全部为 false：

```text
real_data_fetch_triggered=false
provider_refresh_triggered=false
provider_publish_triggered=false
qlib_accepted_latest_switched=false
readonly_latest_published=false
agent_prompt_published=false
model_training_triggered=false
model_inference_triggered=false
strategy_replay_triggered=false
broker_order_quick_trade_triggered=false
target_position_or_weight_generated=false
```
