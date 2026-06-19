# Phase P3RRR 工作文档：Orthogonal Source Freshness Repair

生成日期：2026-06-15

依据：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEP3RR_ORTHOGONAL_DAILY_FEATURE_REFRESH_WORK_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEP3RR_ORTHOGONAL_DAILY_FEATURE_REFRESH_EXECUTION_REPORT_CN.md
```

## 1. 当前结论

P3RR 已正确降级：

```text
gate = phase_p3rr_degraded_requires_review
orthogonal_refresh_status = stale_degraded
P3 candidate status = degraded
```

原因：

```text
signal_asof = 2026-06-15
institutional_latest_trade_date = 2026-06-10
institutional_latest_available_at = 2026-06-11
margin_latest_trade_date = 2026-06-10
margin_latest_available_at = 2026-06-11
```

P3RR 已生成 latest feature table，但源数据本身仍落后，不能声称 LTR 日更完整闭环。

## 2. P3RRR 目标

P3RRR 只修复正交源数据 freshness，不改模型、不改策略。

目标：

```text
确认 daily auto update 的 institutional / margin 数据是否应更新到 signal_asof 附近；
若应更新但没有更新，修复 FinMind/raw archive/DB 写入链路；
若数据源天然延迟，则把 delayed/stale 状态作为正式产品状态输出。
```

目标 gate：

```text
phase_p3rrr_orthogonal_source_freshness_resolved
```

## 3. 必须审计

执行者必须检查：

```text
1. scripts/run_daily_tw_stock_auto_update.py 的 finmind-scope 实际配置；
2. backend/scripts/update_tw_stock_daily.py 是否真的拉取 institutional / margin；
3. raw DB 表 qd_tw_stock_institutional_trades / qd_tw_stock_margin_trading 最新日期；
4. raw archive 文件最新日期；
5. FinMind/source 响应是否有 2026-06-11..2026-06-15 数据；
6. 失败是 source delay、API failure、symbol coverage、DB write failure、还是 daily scope 跳过。
```

## 4. 允许改动

只允许最小修复：

```text
修复 institutional / margin raw archive 或 DB 写入；
补充 freshness audit artifact；
修复 daily auto update 参数，使 full scope 默认包含 institutional/margin；
让 P3RR builder 正确读取最新 raw/DB；
保持 stale/degraded 状态可解释。
```

## 5. 禁止事项

禁止：

```text
重训 qlib；
重训 LTR；
调参；
改 O4 model / feature whitelist；
扩大 qlib Top50；
切换 accepted latest；
provider publish / refresh；
monitor scan/config/alerts；
broker/orders/quick-trade；
target position / target weight；
真实买卖建议；
收益、胜率或上涨概率承诺。
```

## 6. 输出报告

执行者必须写：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEP3RRR_ORTHOGONAL_SOURCE_FRESHNESS_REPAIR_EXECUTION_REPORT_CN.md
```

报告必须回答：

```text
1. institutional / margin 缺口根因是什么？
2. 是否是 daily auto 配置跳过？
3. 是否是数据源本身延迟？
4. 是否修复到 current_or_pit_delayed？
5. 若仍 stale_degraded，是否明确不能收尾？
6. fresh qlib 默认链路是否不受影响？
7. 是否保持只读安全边界？
```

## 7. 给执行者的指令

请执行 Phase P3RRR：只审计并修复 institutional/margin 正交源数据 freshness。不得改模型、不得改策略、不得切 accepted latest 或 provider。若源数据能更新，修复 raw/DB/feature builder 到 `current_or_pit_delayed`；若源数据天然延迟或当前不可得，必须保持 `stale_degraded` 并说明根因，不得声称 LTR 日更完整闭环。
