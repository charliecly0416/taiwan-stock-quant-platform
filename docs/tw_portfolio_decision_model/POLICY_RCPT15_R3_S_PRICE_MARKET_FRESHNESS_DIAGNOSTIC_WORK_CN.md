---
created_at: 2026-06-26
status: work
phase: RCPT15_R3_S_PRICE_MARKET_FRESHNESS_DIAGNOSTIC
parent_closure: docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_R_COORDINATOR_CLOSURE_AND_NEXT_STEP_CN.md
production_allowed: false
provider_publish_default_allowed: false
accepted_latest_switch_allowed: false
order_or_target_output_allowed: false
---

# RCPT15_R3_S Price / Market Freshness Diagnostic 工作文档

## 1. 目标

审计 `RCPT15_R3_R_FULL_YZ2_FEATURE_PACKAGE_REPAIR` 中技术/市场特征 freshness 风险：

```text
target signal days = 2026-06-18..2026-06-25
local_readonly_price latest_used_date_max = 2026-06-01
local_readonly_market latest_used_date_max = 2026-05-21
```

本阶段只做诊断和路线判断，不做 provider publish、qlib accepted latest switch、production latest 切换。

## 2. 要回答的问题

执行者必须回答：

1. R3_R 为什么只用到 `2026-06-01 / 2026-05-21`？
2. 是 `normalized_nonempty` 本身 stale，还是脚本选错目录？
3. R1 isolated candidate normalized price 是否包含更近数据？
4. 是否存在本地 TWII / market index 更近来源？
5. 如果存在更近本地 readonly source，是否能在隔离目录构造 price/TWII freshness bridge？
6. local price/TWII 是否应纳入全自动日更？
7. 如果纳入，应纳入哪一层：raw pull、readonly normalized bridge、formal provider publish、还是 qlib accepted latest？

## 3. 允许读取

```text
R3_R artifacts:
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_r_full_yz2_feature_package_repair/**

formal readonly price/calendar:
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/**
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt

R1 isolated staged refresh:
data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/option_c_ops/**

daily auto logs:
data_tw/ops/daily_auto_update/**

daily scripts:
scripts/run_daily_tw_stock_auto_update.py
backend/scripts/update_tw_stock_daily.py
```

## 4. 禁止动作

禁止：

```text
联网拉数据
provider publish
qlib accepted latest switch
formal latest pointer write
daily_ltr_rerank_latest write
latest_orthogonal_features_latest write
production/default/frontend/Agent/monitor mutation
OrderIntent / target_weight / target_position / quantity_instruction / broker
重跑 R3_R 并覆盖其 pass 结论
```

如判断必须联网或补源，必须输出下一步 repair work doc，不得本阶段直接执行。

## 5. 输出目录

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_s_price_market_freshness_diagnostic/
```

必须输出：

```text
manifest.json
validator_report.json
r3_r_used_freshness_audit.csv
formal_price_source_freshness.csv
r1_candidate_price_source_freshness.csv
twii_market_source_inventory.csv
daily_auto_price_market_chain_audit.csv
recommended_repair_plan.md
forbidden_scope_audit.csv
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_S_PRICE_MARKET_FRESHNESS_DIAGNOSTIC_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_S_PRICE_MARKET_FRESHNESS_DIAGNOSTIC_REVIEW_CN.md
```

建议脚本：

```text
scripts/build_tw_policy_rcpt15_r3_s_price_market_freshness_diagnostic.py
```

## 6. 判断标准

PASS_READY_FOR_REPAIR 条件：

```text
已定位 stale 来源
已确认是否有更近 local isolated price/TWII source
已给出不切 accepted latest 的 repair 路线
forbidden_scope_audit pass
```

PASS_NO_REPAIR_NEEDED 条件：

```text
证明 R3_R 使用的 price/TWII freshness 已符合目标日要求
```

STOP_REQUIRES_DATA_PULL_AUTHORIZATION 条件：

```text
本地没有更近 price/TWII source，必须联网补源
```

FAIL_NEEDS_REPAIR 条件：

```text
审计缺关键来源、无法解释 stale、或证据不完整
```

## 7. 对全自动日更的初步统筹意见

统筹初步判断：

```text
local price/TWII 应纳入全自动日更，但第一阶段应接在 readonly/isolated normalized bridge，
不要默认进入 formal provider publish 或 qlib accepted latest switch。
```

原因：

1. strict E4 / O4 LTR 的技术与市场特征依赖 price/TWII；
2. 只更新 institutional/margin 不够；
3. 若 price/TWII stale，rerank 虽 PIT-safe 但不够 current；
4. daily auto 已有 FinMind raw price update，但 formal `normalized_nonempty` / TWII 可能没有被推进；
5. 正确路线是先证明 readonly price/TWII bridge 能补齐 R3_R，再考虑接入 daily strict E4 gate。

## 8. Executor Command

```bash
python scripts/build_tw_policy_rcpt15_r3_s_price_market_freshness_diagnostic.py
```
