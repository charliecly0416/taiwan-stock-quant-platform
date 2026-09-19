---
created_at: 2026-06-26
status: coordinator_closure
phase: RCPT15_R3_T_ISOLATED_PRICE_TWII_SOURCE_REPAIR_CONTRACT
verdict: PASS_READY_FOR_R3_R_RERUN
---

# RCPT15_R3_T 统筹闭环与下一步意见

## 1. 结论

`RCPT15_R3_T_ISOLATED_PRICE_TWII_SOURCE_REPAIR_CONTRACT` 已完成执行与复审。

最终结论：

```text
PASS_READY_FOR_R3_R_RERUN
```

本轮解决了 R3_S 的核心阻塞：

```text
个股 price bridge 已覆盖 99/99 symbols 至 2026-06-25
TWII bridge 已覆盖至 2026-06-25
target window TWII rows = 5
```

## 2. 关键产物

脚本：

```text
scripts/build_tw_policy_rcpt15_r3_t_isolated_price_twii_source_repair.py
```

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/
```

主要 artifacts：

```text
manifest.json
validator_report.json
stock_price_bridge_inventory.csv
stock_price_bridge/*.csv
twii_source_attempts.csv
twii_bridge.csv
price_twii_bridge_freshness_audit.csv
source_trace.json
forbidden_scope_audit.csv
repair_plan_for_r3_r_rerun.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_T_ISOLATED_PRICE_TWII_SOURCE_REPAIR_CONTRACT_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_T_ISOLATED_PRICE_TWII_SOURCE_REPAIR_CONTRACT_REVIEW_CN.md
```

## 3. Freshness Gate

通过：

```text
stock_price_bridge_symbols = 99
stock_price_bridge_min_date_max = 2026-06-25
twii_bridge_date_max = 2026-06-25
target_window_twii_rows = 5
price_twii_bridge_freshness_pass = true
forbidden_scope_pass = true
```

TWII source：

```text
Yahoo ^TWII = attempted, HTTP 403
FinMind TAIEX = successful, HTTP 200, rows = 24
selected_source = finmind:TAIEX
```

联网范围：

```text
network_used = true
scope = TWII / market index only
full_market_stock_network_pull = false
```

## 4. Forbidden Scope

复审确认：

```text
provider_publish = false
accepted_latest_switch = false
formal_latest_write = false
daily_ltr_rerank_latest_write = false
latest_orthogonal_features_latest_write = false
order_or_target_output = false
broker = false
```

## 5. 对自动日更的结论

现在可以更明确地说：

```text
local price/TWII 应纳入全自动日更，但应先纳入 readonly/isolated normalized bridge。
```

建议后续产品化路径：

```text
daily auto
  -> raw / candidate source refresh
  -> readonly stock price bridge
  -> readonly TWII bridge
  -> strict E4 readonly chain
```

仍不建议默认：

```text
formal provider publish
qlib accepted latest switch
provider accepted latest switch
```

## 6. 下一步授权建议

下一步进入：

```text
RCPT15_R3_U_RERUN_WITH_ISOLATED_PRICE_TWII_BRIDGE
```

目标：

1. 修改或新增 R3_R rerun 脚本，使其显式读取 T 阶段 isolated bridge；
2. 不读取 stale formal `normalized_nonempty` 作为 price/TWII source；
3. 重建 78-feature package；
4. 使用 frozen O4 LTR predict；
5. 输出 rerank snapshot/top30/top50；
6. 与 R3_R stale-source rerank 做差异比较；
7. 仍不写 formal latest/provider/accepted latest/order/target/broker。

必须比较：

```text
feature freshness before/after
rerank top30 overlap
ltr_score delta distribution
top rank changes
forbidden scope
```

## 7. 执行者提醒

R3_U 不应重新联网。它应只消费 T 阶段已经生成的 isolated bridge：

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/stock_price_bridge/
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/twii_bridge.csv
```

如果 R3_U 再次需要联网，应 STOP，而不是自动补源。
