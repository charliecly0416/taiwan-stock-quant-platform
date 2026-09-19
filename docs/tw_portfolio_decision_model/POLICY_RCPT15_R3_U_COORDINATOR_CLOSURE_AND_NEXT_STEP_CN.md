---
created_at: 2026-06-26
status: coordinator_closure
phase: RCPT15_R3_U_RERUN_WITH_ISOLATED_PRICE_TWII_BRIDGE
verdict: PASS_CLOSE_R3_U
production_allowed: false
provider_publish_default_allowed: false
accepted_latest_switch_allowed: false
network_allowed_in_closure: false
order_or_target_output_allowed: false
---

# RCPT15_R3_U Coordinator Closure And Next Step

## 1. 结论

`RCPT15_R3_U_RERUN_WITH_ISOLATED_PRICE_TWII_BRIDGE` 可以闭环，结论为：

```text
PASS_CLOSE_R3_U
```

执行与复审共同证明：使用 R3_T isolated stock price bridge 与 isolated TWII bridge 后，R3_U 能在不联网、不写正式 latest、不切换 accepted latest、不输出交易指令的前提下，完整重跑 78-feature package 与 frozen O4 LTR rerank。

## 2. 已审查文件

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_U_RERUN_WITH_ISOLATED_PRICE_TWII_BRIDGE_EXECUTION_REPORT_CN.md
```

复审报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_U_RERUN_WITH_ISOLATED_PRICE_TWII_BRIDGE_REVIEW_CN.md
```

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_u_rerun_with_isolated_price_twii_bridge/
```

核心脚本：

```text
scripts/build_tw_policy_rcpt15_r3_u_rerun_with_isolated_price_twii_bridge.py
```

## 3. Pass Gate 结果

R3_U validator 与 reviewer 已确认：

```text
feature_whitelist_count = 78
missing_required_feature_count = 0
feature_package_rows = 250
rerank_score_rows = 250
top30_rows = 150
top50_rows = 250
stock_price_bridge_used = true
twii_bridge_used = true
price_latest_used_date_max = 2026-06-25
market_latest_used_date_max = 2026-06-25
coverage_pass = true
pit_pass = true
forbidden_pass = true
no_network = true
no_fallback_or_fake_rerank = true
```

本阶段脚本也已通过语法编译：

```text
python -m py_compile scripts/build_tw_policy_rcpt15_r3_u_rerun_with_isolated_price_twii_bridge.py
```

## 4. 关键发现

### 4.1 stale price/TWII 会实质影响 rerank

R3_R 使用的 formal/local price 与 TWII 明显过旧：

```text
R3_R price latest max: 2026-06-01
R3_R market latest max: 2026-05-21
```

R3_U 使用 R3_T isolated bridge 后：

```text
R3_U price latest max: 2026-06-25
R3_U market latest max: 2026-06-25
```

rerank 变化不是微小扰动：

```text
changed_rank_rows_total = 237 / 250
top30_membership_changed_rows = 70
top5_membership_changed_rows = 36
top1_changed = all 5 eligible days
top30 overlap by day = 24, 25, 23, 22, 21
```

因此，R3_R stale-source rerank 不应继续作为严肃 shadow / production readiness 判断依据。它只能作为 stale-source diagnostic baseline。

### 4.2 R3_U 证明的是“新鲜度桥接可行”，不是“生产可启用”

R3_U 仍然是 isolated / readonly / diagnostic artifact。它没有授权：

```text
provider publish
qlib/provider accepted latest switch
formal latest pointer write
daily_ltr_rerank_latest write
latest_orthogonal_features_latest write
production/default/frontend/Agent/monitor mutation
OrderIntent / target_weight / target_position / quantity_instruction / broker
```

R3_U 也没有证明新 rerank 的收益或风险控制效果，只证明 stale price/TWII 会显著影响 frozen O4 rerank，且 fresh bridge 下的重跑链路可审查、PIT 安全、feature 完整。

## 5. 对当前项目状态的判断

当前 RCPT15 / strict E4 shadow backfill 的主要 blocker 已从“无法构造完整 YZ2 rerank feature”转为：

```text
如何把 price/TWII freshness bridge 纳入每日 readonly shadow 生产准备链路，
同时继续隔离 provider/latest/accepted latest 与真实交易边界。
```

换句话说，下一步不应回到 R3_R 的 stale rerank，也不应直接发布 R3_U 结果；应该基于 R3_U 的 fresh bridge rerank 做连续 shadow 和生产化安全合同。

## 6. 下一步建议

建议进入：

```text
RCPT15_R3_V_SHADOW_CONTINUATION_WITH_FRESH_BRIDGE_RERANK
```

目标：

1. 使用 R3_U fresh bridge rerank 作为 strict E4 readonly shadow 的输入候选；
2. 对 2026-06-18、2026-06-22、2026-06-23、2026-06-24、2026-06-25 做 shadow continuation replay；
3. 继续禁止 provider/latest/accepted latest 写入；
4. 继续禁止 order/target/broker；
5. 输出每日 top30/top50、M1 risk-control overlay、shadow candidate change、freshness lineage、PIT audit、forbidden scope audit；
6. 比较 R3_R stale rerank 与 R3_U fresh rerank 对 M1 shadow 决策的实际影响。

如果 R3_V 通过，再开单独生产化合同：

```text
RCPT15_R3_W_DAILY_AUTO_READONLY_PRICE_TWII_BRIDGE_INTEGRATION_CONTRACT
```

该合同只允许把 local price/TWII isolated bridge 纳入每日 auto 的 readonly strict E4 chain，不允许自动切换 provider/latest，不允许发布正式 signal latest，不允许真实交易。

## 7. 给执行者的下一步工作边界

执行者在 R3_V 中必须：

1. 读取本 closure、R3_U work/report/review、R3_T closure；
2. 只消费 R3_U 输出作为 fresh rerank 输入；
3. 不重训 O4，不调参；
4. 不联网；
5. 不读 stale formal price/TWII 作为 rerank price/TWII source；
6. 不写 provider/latest/formal latest/accepted latest；
7. 不输出 OrderIntent、target_weight、target_position、quantity、broker；
8. 产出完整 shadow continuation artifacts 与执行报告。

## 8. 给审查者的下一步审查重点

审查者在 R3_V 中必须重点确认：

1. R3_V 是否真的使用 R3_U fresh bridge rerank，而不是 R3_R stale rerank；
2. 每日 shadow input lineage 是否能追到 R3_T bridge 与 R3_U rerank；
3. PIT / freshness / forbidden scope 是否仍通过；
4. M1 overlay 或 risk-control 判断是否只是 readonly diagnostic；
5. 是否存在任何 provider/latest/accepted latest/order/target/broker 越界；
6. fresh rerank 对 shadow 决策的变化是否被清楚量化。

## 9. Coordinator 决策

R3_U 已完成并通过。授权进入 R3_V 的前提是继续保持 isolated / readonly / diagnostic 边界。

不授权任何生产发布、latest pointer 改写、accepted latest switch、真实交易、目标仓位或目标权重输出。
