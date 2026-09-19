---
created_at: 2026-06-26
status: work
phase: RCPT15_R3_U_RERUN_WITH_ISOLATED_PRICE_TWII_BRIDGE
parent_closure: docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_T_COORDINATOR_CLOSURE_AND_NEXT_STEP_CN.md
production_allowed: false
provider_publish_default_allowed: false
accepted_latest_switch_allowed: false
network_allowed: false
order_or_target_output_allowed: false
---

# RCPT15_R3_U Rerun With Isolated Price / TWII Bridge 工作文档

## 1. 目标

使用 R3_T 已生成的隔离 price/TWII bridge，重跑 R3_R 的完整 78-feature package 与 frozen O4 LTR rerank。

本阶段要验证：

```text
stale formal price/TWII source -> isolated fresh price/TWII bridge
```

是否改变 R3_R rerank 结果，并产出可审查的差异报告。

## 2. 输入

必须显式读取：

```text
stock bridge:
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/stock_price_bridge/

TWII bridge:
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/twii_bridge.csv

R3_R stale-source baseline:
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_r_full_yz2_feature_package_repair/
```

继续读取：

```text
R1 shadow top50
R2 isolated O2
O4 frozen model / whitelist
```

## 3. 禁止动作

禁止：

```text
联网
provider publish
qlib/provider accepted latest switch
formal latest pointer write
daily_ltr_rerank_latest write
latest_orthogonal_features_latest write
production/default/frontend/Agent/monitor mutation
OrderIntent / target_weight / target_position / quantity_instruction / broker
训练或调参
fallback qlib score
```

## 4. 输出目录

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_u_rerun_with_isolated_price_twii_bridge/
```

必须输出：

```text
manifest.json
validator_report.json
feature_package.csv
feature_schema_audit.csv
feature_source_trace.csv
pit_audit.csv
forbidden_scope_audit.csv
rerank_score_snapshot.csv
rerank_top30.csv
rerank_top50.csv
freshness_before_after_audit.csv
rerank_diff_vs_r3_r.csv
top30_overlap_by_day.csv
rank_change_summary.csv
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_U_RERUN_WITH_ISOLATED_PRICE_TWII_BRIDGE_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_U_RERUN_WITH_ISOLATED_PRICE_TWII_BRIDGE_REVIEW_CN.md
```

建议脚本：

```text
scripts/build_tw_policy_rcpt15_r3_u_rerun_with_isolated_price_twii_bridge.py
```

## 5. Pass Gate

```text
feature_whitelist_count = 78
missing_required_feature_count = 0
feature_package_rows = 250
rerank_score_rows = 250
top30_rows = 150
top50_rows = 250
stock_price_bridge_used = true
twii_bridge_used = true
price_latest_used_date_max >= 2026-06-25
market_latest_used_date_max >= 2026-06-25
pit_pass = true
forbidden_pass = true
no_network = true
no_fallback_or_fake_rerank = true
```

## 6. 必须比较

与 R3_R stale-source baseline 比较：

```text
feature freshness before/after
ltr_score delta distribution
top30 overlap by day
rank movement by symbol/day
top1/top5/top10 changes
```

## 7. Executor Command

```bash
python scripts/build_tw_policy_rcpt15_r3_u_rerun_with_isolated_price_twii_bridge.py
```

## 8. Reviewer Audit Brief

审查者必须确认：

1. R3_U 没有联网；
2. price/TWII source 不是 stale formal `normalized_nonempty`；
3. feature package 仍完整 78-feature；
4. rerank 来自 frozen O4 model；
5. diff artifacts 能解释与 R3_R 的变化；
6. forbidden scope 全部通过。
