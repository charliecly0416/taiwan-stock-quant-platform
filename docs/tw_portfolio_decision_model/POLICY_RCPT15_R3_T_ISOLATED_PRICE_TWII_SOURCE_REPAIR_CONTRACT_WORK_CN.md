---
created_at: 2026-06-26
status: work
phase: RCPT15_R3_T_ISOLATED_PRICE_TWII_SOURCE_REPAIR_CONTRACT
parent_closure: docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_S_COORDINATOR_CLOSURE_AND_NEXT_STEP_CN.md
user_authorized_isolated_twii_repair: true
production_allowed: false
provider_publish_default_allowed: false
accepted_latest_switch_allowed: false
order_or_target_output_allowed: false
---

# RCPT15_R3_T Isolated Price / TWII Source Repair Contract 工作文档

## 1. 授权边界

用户已授权继续：

```text
isolated TWII source repair / data pull
```

本授权仅允许：

1. 在隔离目录中补齐 `TWII` / market index source；
2. 使用 R1 `candidate_normalized` 建立个股 price bridge；
3. 生成 R3_R 可显式消费的 readonly price/TWII bridge；
4. 不写 formal provider，不切 qlib/provider accepted latest，不写 formal latest pointer。

## 2. 背景

R3_S 已确认：

```text
formal stock price date_max = 2026-06-01
formal TWII date_max = 2026-05-21
R1 candidate stock price date_max = 2026-06-25, coverage = 99/99
local fresher TWII source = not found
```

因此完整 repair 需要：

1. stock leg：从本地 R1 candidate source 建立 isolated bridge；
2. TWII leg：授权 isolated data pull / source repair，补齐 `2026-06-18..2026-06-25` 所需 market rows。

## 3. 目标

构造一个隔离的 price/TWII bridge：

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/
```

该 bridge 后续可供 R3_R rerun 显式使用，不能自动替换正式 price provider。

## 4. 允许输入

允许读取：

```text
R1 candidate normalized stock price:
data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/option_c_ops/**/candidate_normalized/TW*.csv

formal stale TWII fallback for comparison only:
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv

R3_S diagnostics:
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_s_price_market_freshness_diagnostic/**

calendar:
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt
```

允许联网范围：

```text
Only TWII / Taiwan market index source repair, target window 2026-06-18..2026-06-25.
```

优先级：

1. 若本地存在可审计 TWII source，使用本地；
2. 若本地不存在，可联网拉取 TWII / market index；
3. 不得联网重拉全市场个股；
4. 不得 provider publish；
5. 不得 accepted latest switch。

## 5. 输出

必须输出：

```text
manifest.json
validator_report.json
stock_price_bridge_inventory.csv
twii_source_attempts.csv
twii_bridge.csv
price_twii_bridge_freshness_audit.csv
source_trace.json
forbidden_scope_audit.csv
repair_plan_for_r3_r_rerun.md
```

可选输出：

```text
stock_price_bridge/*.csv
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_T_ISOLATED_PRICE_TWII_SOURCE_REPAIR_CONTRACT_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_T_ISOLATED_PRICE_TWII_SOURCE_REPAIR_CONTRACT_REVIEW_CN.md
```

建议脚本：

```text
scripts/build_tw_policy_rcpt15_r3_t_isolated_price_twii_source_repair.py
```

## 6. 必须满足的 gate

PASS_READY_FOR_R3_R_RERUN：

```text
stock_price_bridge_symbols = 99
stock_price_bridge_min_date_max >= 2026-06-25
twii_bridge_date_max >= 2026-06-25
target_window_twii_rows >= 5
price_twii_bridge_freshness_pass = true
forbidden_scope_pass = true
provider_publish = false
accepted_latest_switch = false
formal_latest_write = false
```

STOP_REQUIRES_USER_DATA_SOURCE：

```text
TWII data pull unavailable and no local source found
```

FAIL_NEEDS_REPAIR：

```text
stock bridge incomplete
TWII bridge schema invalid
target window missing rows
forbidden action detected
```

## 7. 全自动日更纳入原则

若 T 通过，后续 daily auto 的产品化方向是：

```text
daily auto -> raw/candidate source -> readonly price/TWII bridge -> strict E4 readonly chain
```

不是：

```text
daily auto -> formal provider publish -> qlib accepted latest switch
```

也就是说，price/TWII 应纳入自动流程，但先作为 readonly bridge artifact，由 strict E4 gate 显式消费。

## 8. Executor Command

```bash
python scripts/build_tw_policy_rcpt15_r3_t_isolated_price_twii_source_repair.py
```

如脚本需要联网拉 TWII，执行者应仅对该命令申请网络权限，并在 `twii_source_attempts.csv` 与 `source_trace.json` 中记录来源、URL/API、时间、行数、失败原因。
