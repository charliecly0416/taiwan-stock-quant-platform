---
created_at: 2026-06-26
status: work
phase: RCPT15_R3_V_SHADOW_CONTINUATION_WITH_FRESH_BRIDGE_RERANK
parent_closure: docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_U_COORDINATOR_CLOSURE_AND_NEXT_STEP_CN.md
production_allowed: false
provider_publish_default_allowed: false
accepted_latest_switch_allowed: false
network_allowed: false
order_or_target_output_allowed: false
---

# RCPT15_R3_V Shadow Continuation With Fresh Bridge Rerank 工作文档

## 1. 目标

基于 `RCPT15_R3_U` 已通过审查的 fresh bridge rerank，构造 readonly shadow continuation 证据包，判断：

```text
R3_U fresh rerank 是否能作为 strict E4 / M1 readonly shadow 的后续输入候选。
```

本阶段不是收益回测、不是生产发布、不是正式 latest 切换。它只验证 fresh bridge rerank 进入 shadow continuation 后的 lineage、PIT、禁区和与 stale-source rerank 的决策层差异。

## 2. 背景事实

`RCPT15_R3_U` 已证明：

```text
R3_R stale price latest max = 2026-06-01
R3_R stale TWII latest max = 2026-05-21
R3_U fresh price latest max = 2026-06-25
R3_U fresh TWII latest max = 2026-06-25
feature_whitelist_count = 78
missing_required_feature_count = 0
rerank_score_rows = 250
top50_rows = 250
top30_rows = 150
pit_pass = true
forbidden_pass = true
no_network = true
```

R3_U 与 R3_R 的 rerank 差异明显：

```text
changed_rank_rows_total = 237 / 250
top30_membership_changed_rows = 70
top5_membership_changed_rows = 36
top1_changed = all 5 eligible days
top30 overlap by day = 24, 25, 23, 22, 21
```

因此 R3_V 必须以 R3_U fresh rerank 为主输入，不得回退到 R3_R stale rerank。

## 3. 必须读取的输入

R3_U fresh rerank：

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_u_rerun_with_isolated_price_twii_bridge/manifest.json
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_u_rerun_with_isolated_price_twii_bridge/validator_report.json
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_u_rerun_with_isolated_price_twii_bridge/rerank_score_snapshot.csv
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_u_rerun_with_isolated_price_twii_bridge/rerank_top30.csv
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_u_rerun_with_isolated_price_twii_bridge/rerank_top50.csv
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_u_rerun_with_isolated_price_twii_bridge/pit_audit.csv
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_u_rerun_with_isolated_price_twii_bridge/forbidden_scope_audit.csv
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_u_rerun_with_isolated_price_twii_bridge/freshness_before_after_audit.csv
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_u_rerun_with_isolated_price_twii_bridge/top30_overlap_by_day.csv
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_u_rerun_with_isolated_price_twii_bridge/rank_change_summary.csv
```

R3_R stale-source baseline comparison：

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_r_full_yz2_feature_package_repair/rerank_top30.csv
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_r_full_yz2_feature_package_repair/rerank_top50.csv
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_r_full_yz2_feature_package_repair/validator_report.json
```

M1 / shadow 历史参考，只能作为格式与状态参考：

```text
data_tw/experiments/risk_control_policy_2022/rcpt14a_shadow_continuation_longer_accumulation/
data_tw/experiments/risk_control_policy_2022/rcpt12_multi_day_m1_shadow_accumulation_and_blocker_burn_down/
```

## 4. 禁止动作

禁止：

```text
联网
训练或调参
fallback qlib score
provider publish
qlib/provider accepted latest switch
formal latest pointer write
daily_ltr_rerank_latest write
latest_orthogonal_features_latest write
production/default/frontend/Agent/monitor mutation
OrderIntent / target_weight / target_position / quantity_instruction / broker
任何真实交易、模拟下单或目标仓位建议
```

R3_V 输出中的所有字段必须是 readonly / diagnostic / research signal，不得出现可执行交易语义。

## 5. 输出目录

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_v_shadow_continuation_with_fresh_bridge_rerank/
```

必须输出：

```text
manifest.json
fresh_rerank_shadow_input.csv
fresh_rerank_top30_shadow.csv
fresh_vs_stale_shadow_diff.csv
daily_shadow_continuation_evidence.csv
freshness_lineage_audit.csv
pit_audit.csv
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_V_SHADOW_CONTINUATION_WITH_FRESH_BRIDGE_RERANK_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_V_SHADOW_CONTINUATION_WITH_FRESH_BRIDGE_RERANK_REVIEW_CN.md
```

建议脚本：

```text
scripts/build_tw_policy_rcpt15_r3_v_shadow_continuation_with_fresh_bridge_rerank.py
```

## 6. 产物字段要求

`fresh_rerank_shadow_input.csv` 应该包含每个 eligible day 的 top50 readonly shadow rows，字段至少包含：

```text
date
symbol
candidate_id
score
rank
score_component
ltr_score
diagnostic_only
research_signal_not_order
pit_pass
source_phase
source_artifact
source_lineage_note
readonly_shadow_only
fresh_price_latest_used_date
fresh_market_latest_used_date
```

`candidate_id` 建议：

```text
M1_STRICT_E4_FRESH_BRIDGE_RERANK
```

`fresh_vs_stale_shadow_diff.csv` 必须逐日比较：

```text
date
fresh_top50_count
stale_top50_count
fresh_top30_count
stale_top30_count
top30_overlap_count
top30_entered_symbols
top30_exited_symbols
top1_fresh
top1_stale
top1_changed
rank_changed_rows
top5_membership_changed_rows
top30_membership_changed_rows
```

`daily_shadow_continuation_evidence.csv` 必须逐日汇总：

```text
date
candidate_id
fresh_top50_count
fresh_top30_count
avg_score
min_rank
max_rank
pit_pass
freshness_pass
forbidden_pass
readonly_shadow_only
acceptance_state
acceptance_reason
```

## 7. Pass Gate

R3_V 通过条件：

```text
r3_u_validator_ok = true
source_is_r3_u_fresh_rerank = true
eligible_days = 5
fresh_rerank_shadow_input_rows = 250
fresh_rerank_top30_shadow_rows = 150
all_rows_diagnostic_only = true
all_rows_research_signal_not_order = true
all_rows_readonly_shadow_only = true
pit_pass = true
freshness_pass = true
forbidden_pass = true
no_network = true
no_provider_or_latest_write = true
no_order_target_quantity_broker = true
diff_artifacts_present = true
```

允许 `2026-06-19` 缺席，因为此前已确认为无 signal input / 非有效 shadow rerank day。

## 8. Stop Conditions

必须 STOP：

1. R3_U validator 不存在或不通过；
2. R3_U top50/top30 缺失；
3. 需要联网才能继续；
4. 需要写正式 latest/provider/accepted latest 才能继续；
5. fresh rerank shadow input 无法追溯到 R3_U/R3_T bridge；
6. 输出中出现 order/target/quantity/broker/target_weight/target_position；
7. 发现 fallback qlib score、重训或调参。

## 9. Executor Command

```bash
python scripts/build_tw_policy_rcpt15_r3_v_shadow_continuation_with_fresh_bridge_rerank.py
```

## 10. Reviewer Audit Brief

审查者必须确认：

1. R3_V 只使用 R3_U fresh rerank 作为主输入；
2. 没有回退到 R3_R stale rerank 生成 shadow input；
3. 只把 R3_R 用作 comparison baseline；
4. lineage 能追到 R3_U fresh rerank 与 R3_T isolated price/TWII bridge；
5. PIT / freshness / forbidden scope 全部通过；
6. 输出是 readonly diagnostic，不含任何交易执行语义；
7. diff artifacts 清楚量化 fresh rerank 对 shadow candidate 的影响；
8. 是否可以进入 `RCPT15_R3_W_DAILY_AUTO_READONLY_PRICE_TWII_BRIDGE_INTEGRATION_CONTRACT`。
