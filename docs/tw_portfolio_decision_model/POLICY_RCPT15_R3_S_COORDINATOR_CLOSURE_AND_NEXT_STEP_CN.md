---
created_at: 2026-06-26
status: coordinator_closure
phase: RCPT15_R3_S_PRICE_MARKET_FRESHNESS_DIAGNOSTIC
verdict: STOP_REQUIRES_ISOLATED_TWII_SOURCE_REPAIR_OR_DATA_PULL_AUTHORIZATION
---

# RCPT15_R3_S 统筹闭环与下一步意见

## 1. 结论

`RCPT15_R3_S_PRICE_MARKET_FRESHNESS_DIAGNOSTIC` 已完成执行和复审。

执行结论：

```text
PASS_READY_FOR_REPAIR
```

复审结论：

```text
STOP_REQUIRES_DATA_PULL_AUTHORIZATION
```

统筹采纳复审结论：诊断已经完整，但完整修复 R3_R price/TWII freshness 前，还需要授权 isolated TWII source repair 或提供更近的本地 TWII source。

## 2. 已定位的 stale 来源

R3_R 不是脚本误读错列，而是固定读取正式目录：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty
```

该目录当前状态：

```text
R3_R stock symbols checked = 99
formal stock price date_max = 2026-06-01
formal TWII date_max = 2026-05-21
```

所以 R3_R 的技术指标与市场指标虽然 PIT-safe，但不够 fresh。

## 3. 本地更近数据情况

已找到更近的个股价格来源：

```text
R1 isolated candidate_normalized
job_id = rcpt15_r1_option_c_yahoo_scrapling_refresh_20260625
symbols covered = 99 / 99
date_max = 2026-06-25
```

未找到更近的 TWII 来源：

```text
best local TWII source = qlib_pipeline/.../normalized_nonempty/TWII.csv
date_max = 2026-05-21
fresh_source_count = 0
```

因此：

```text
stock price bridge 可以本地隔离修
TWII/market feature repair 需要 isolated TWII source repair 或数据拉取授权
```

## 4. 对全自动日更的判断

local price/TWII 应该纳入全自动日更，但第一阶段必须接在：

```text
readonly / isolated normalized bridge
```

不应默认接到：

```text
formal provider publish
qlib accepted latest switch
provider accepted latest switch
formal latest pointer
```

原因：

1. daily auto 已能拉 FinMind raw daily bars；
2. strict E4 / O4 LTR 实际消费的是 YZ2 price/TWII feature source；
3. 目前 raw/candidate/formal provider 之间缺一个安全桥；
4. 直接打开 legacy provider publish 或 accepted latest 风险太高；
5. readonly bridge 可以先服务 strict E4 shadow / RCPT repair，不改变生产 accepted latest。

## 5. 下一步建议

建议开：

```text
RCPT15_R3_T_ISOLATED_PRICE_TWII_SOURCE_REPAIR_CONTRACT
```

目标：

1. 用 R1 candidate_normalized 为 99 个 R3 symbols 建立 isolated stock price bridge；
2. 明确 TWII source repair 方案；
3. 如果本地无更近 TWII，则请求授权联网拉取 TWII 或指定可信本地 TWII source；
4. 输出 isolated price/TWII bridge，不写 formal provider；
5. bridge 通过后再重跑 R3_R，比较 rerank 差异。

## 6. 需要用户授权的点

若要完整继续，至少需要授权其一：

```text
授权 isolated TWII source data pull / repair
```

或：

```text
提供本地可审计的 TWII source，覆盖 2026-06-18..2026-06-25
```

未授权前，不应继续声称 R3_R freshness 已完整修复。

## 7. 已完成文档

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_S_PRICE_MARKET_FRESHNESS_DIAGNOSTIC_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_S_PRICE_MARKET_FRESHNESS_DIAGNOSTIC_REVIEW_CN.md
```

诊断产物：

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_s_price_market_freshness_diagnostic/
```
