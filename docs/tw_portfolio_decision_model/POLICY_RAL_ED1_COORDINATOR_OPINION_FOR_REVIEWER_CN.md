---
created_at: 2026-06-23
status: coordinator_opinion_for_reviewer
scope: after_ral_ed1_attribution_diagnostic_stop
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
review_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ED1_SCORE_RANK_REGIME_HOLDING_ATTRIBUTION_DIAGNOSTIC_REVIEW_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RAL_ED1_SCORE_RANK_REGIME_HOLDING_ATTRIBUTION_DIAGNOSTIC_EXECUTION_REPORT_CN.md
recommended_next: RAL_ED1_R_COUNTERFACTUAL_TRACE_FEASIBILITY_REPAIR
ral_ed2_authorized: false
rule_replay_authorized: false
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity: true
---

# RAL-ED1 统筹意见：不进 ED2，授权受限 Counterfactual Trace Repair

## 1. 统筹结论

本轮 `RAL-ED1 Score / Rank / Regime / Holding Attribution Diagnostic` 的审查结论成立：

```text
STOP_NO_RAL_ED2_READY_HYPOTHESIS
```

不得授权：

```text
RAL-ED2 rule sanity
任何规则收益 replay / rule selection
strict_test
机器学习 / 强化学习 / bandit
qlib+LTR
OrderIntent / target_weight / target_position / quantity
provider/latest/monitor/frontend/Agent/broker/production
```

但本轮不建议关闭 RAL-ED 主线。ED1 的 STOP 不是因为显式规则方向无效，而是因为缺少进入 ED2 的上游证据：

```text
intervention-level counterfactual replay trace = 0
```

因此统筹建议授权一个受限 repair：

```text
RAL-ED1-R Counterfactual Trace Feasibility Repair
```

推荐下一步工作文档：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_R_COUNTERFACTUAL_TRACE_FEASIBILITY_REPAIR_WORK_CN.md
```

## 2. 为什么 ED1 STOP

ED1 已完成诊断产物，且没有越界：

```text
strict_test_used = false
model_training_run = false
rule_replay_run = false
order_intent_output = false
target_weight / target_position / quantity = false
```

真正阻断 ED2 的原因是：

```text
当前证据无法达到 RAL-ED 主线要求的 trace_status >= counterfactual_replay_trace。
```

关键证据：

```text
counterfactual_replay_trace_rows = 0
candidate_rule_hypothesis_audit.csv:
  eligible_for_ral_ed2_consideration = False for all candidates
```

三个候选方向的失败原因：

```text
score_gap_buy_filter:
  trace evidence below counterfactual_replay_trace

rank_score_deterioration_sell:
  no intervention counterfactual delta trace

threshold_multi_buy_filter:
  summary/proxy only and no predeclared counterfactual trace
```

因此不能进入 ED2。否则等于在没有动作级 counterfactual PnL/cost 证据的情况下直接跑规则，重走之前 validation-overfit 的老路。

## 3. 底层原因判断

### 3.1 ED1 只能观察 baseline，不足以证明干预收益

ED1 可以从 baseline ledger 中观察：

```text
score bucket
score gap bucket
rank delta
score delta
holding age
baseline buy/sell/hold contribution
```

但这类观察只能说明：

```text
baseline 当时做了什么，以及后来发生了什么。
```

它不能证明：

```text
如果 block_buy / delay_sell / accelerated_sell / multi_buy threshold 发生，
扣费税后的 delta PnL 会是多少。
```

### 3.2 Proxy 证据不能进入规则实验

RAL2 / ED1 都显示，现有 PBA action rows 多数是：

```text
derived_proxy
summary_level_only
```

这类证据可以用于发现问题和形成方向，但不能支持 ED2 rule sanity。ED2 必须建立在：

```text
native_trace
或 counterfactual_replay_trace
```

之上。

### 3.3 Repair 的目标不是调规则，而是补可审计反事实链路

下一步不应直接问：

```text
哪个 score threshold 收益最高？
```

而应先问：

```text
我们的 replay 能不能在 readonly research 中构造一个可复现的 baseline-vs-intervention trace，
并输出 delta_pnl_after_fee_tax / fee_delta / turnover_delta？
```

## 4. 是否授权 repair

授权，但必须严格限定。

授权内容：

```text
只做 counterfactual trace feasibility / minimal build。
```

不授权内容：

```text
不做 ED2 rule sanity；
不做规则收益排名；
不做 validation 选规则；
不做 strict_test；
不训练模型；
不接 production。
```

## 5. RAL-ED1-R 目标

RAL-ED1-R 要回答：

```text
现有 readonly replay 是否能构造 intervention-level counterfactual trace？
如果可以，哪些动作类型可以 native/counterfactual 还原？
如果不可以，缺哪些 replay ledger 或状态字段？
```

最小动作模板只允许用于 trace feasibility，不允许作为规则实验：

```text
block_buy_trace_probe
delay_sell_trace_probe
accelerated_sell_trace_probe
threshold_multi_buy_trace_probe
```

这些 probe 必须是：

```text
diagnostic_probe_only
not_rule_candidate
not_selected_by_validation
not_strict_test
```

## 6. RAL-ED1-R 产物建议

建议审查者要求执行者输出：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair/
  manifest.json
  counterfactual_trace_feasibility_design.md
  intervention_probe_manifest.json
  required_replay_state_field_audit.csv
  counterfactual_trace_sample.csv
  baseline_vs_intervention_delta_sample.csv
  trace_status_upgrade_audit.csv
  replay_determinism_audit.csv
  cost_turnover_delta_audit.csv
  multi_trade_gate_feasibility_audit.csv
  unavailable_field_blocker_audit.csv
  forbidden_consumer_audit.csv
  validator_report.json
  golden_samples_report.json

docs/tw_portfolio_decision_model/POLICY_RAL_ED1_R_COUNTERFACTUAL_TRACE_FEASIBILITY_REPAIR_EXECUTION_REPORT_CN.md
```

## 7. RAL-ED1-R 通过条件

RAL-ED1-R 通过不是指规则有效，而是指 trace 能力可用。

通过条件：

```text
1. 至少一种 intervention probe 能生成 counterfactual_replay_trace。
2. trace 能输出 baseline_counterfactual_trace_id。
3. trace 能输出 delta_pnl_after_fee_tax_diagnostic。
4. trace 能输出 fee_tax_delta_diagnostic。
5. trace 能输出 turnover_delta_diagnostic。
6. replay 是 deterministic。
7. trace_status 没有把 proxy/summary 冒充为 counterfactual。
8. no strict_test / no training / no production / no OrderIntent。
```

如果通过，审查者仍不得直接写 ED2。应回到统筹，由统筹决定是否授权：

```text
RAL-ED1-S: score/rank/regime attribution rerun with counterfactual traces
```

或直接写一个新的 ED1 repeat work doc。

## 8. 失败条件

若出现以下任一情况，应 STOP 回统筹：

```text
1. 现有 replay 无法构造 intervention counterfactual trace。
2. 必须引入 target_weight / quantity / OrderIntent 才能构造 trace。
3. 必须修改 production strategy 才能构造 trace。
4. delta PnL 只能 summary-level proxy，不能达到 counterfactual_replay_trace。
5. 多买/多卖 probe 无法做成本/换手 gate。
6. 需要读取 strict_test。
```

## 9. 给审查者的下一步指令

请审查者基于本意见文档撰写：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_R_COUNTERFACTUAL_TRACE_FEASIBILITY_REPAIR_WORK_CN.md
```

必须要求执行者读取：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_SCORE_RANK_REGIME_HOLDING_ATTRIBUTION_DIAGNOSTIC_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_SCORE_RANK_REGIME_HOLDING_ATTRIBUTION_DIAGNOSTIC_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
```

不得写：

```text
RAL-ED2 rule sanity 工作文档
strict_test 工作文档
模型训练工作文档
production integration 工作文档
```

## 10. 最终控制

当前最终控制：

```text
RAL-ED2: not authorized
rule replay / rule selection: not authorized
strict_test: not authorized
model training: not authorized
counterfactual trace feasibility repair: authorized
production/default/order: not authorized
```

一句话：

```text
ED1 stop 的原因是缺 counterfactual intervention trace；
下一步可以修 trace 能力，但不能跳到规则实验。
```
