---
created_at: 2026-06-24
status: rcpt3_closure_review_completed
phase: RCPT3_CLOSURE_REVIEW
parent_mainline: docs/tw_portfolio_decision_model/POLICY_RCP_RISK_CONTROL_POLICY_2022_DOWNTURN_MAINLINE_CN.md
rcpt2_execution_report: docs/tw_portfolio_decision_model/POLICY_RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY_EXECUTION_REPORT_CN.md
rcpt2_review: docs/tw_portfolio_decision_model/POLICY_RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY_REVIEW_CN.md
artifact_root: data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity
verdict: PASS_DIAGNOSTIC_CANDIDATE_READY_FOR_RCPT4_NARROW_ROBUSTNESS_AND_RULE05_MECHANISM_ATTRIBUTION_WORK_DOC
diagnostic_only: true
strict_oos: false
production_allowed: false
model_training_authorized: false
strict_test_authorized: false
---

# RCPT3 Closure Review

## 1. Verdict

`PASS_DIAGNOSTIC_CANDIDATE_READY_FOR_RCPT4_NARROW_ROBUSTNESS_AND_RULE05_MECHANISM_ATTRIBUTION_WORK_DOC`

RCPT2 的 adaptive threshold replay sanity 可以闭环为：

```text
在 2022 downturn validation diagnostic 窗口内，
RCPT1_RULE_05 是第一个通过现金、参与度、集中度、阈值合同、诊断语义和禁区审计的风险控制候选。
```

但本结论只能说明：

```text
卖出侧 risk-off early sell / weak-rank-deterioration 风险控制机制值得继续做窄范围 robustness 与归因。
```

不能说明：

```text
1. RULE_05 已经是可上线策略；
2. 2022 是 strict OOS / final OOS / independent test；
3. 该规则已经可以写入 production/default/provider/frontend/Agent/monitor/order chain；
4. 该规则可以输出 OrderIntent、target_weight、target_position 或 quantity_instruction；
5. 可以根据 2022 结果继续调阈值。
```

## 2. Evidence Checked

本轮 closure review 读取并核对：

```text
docs/tw_portfolio_decision_model/POLICY_RCP_RISK_CONTROL_POLICY_2022_DOWNTURN_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP0_2015_2020_QLIB_ARTIFACT_DISCOVERY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY_REVIEW_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/manifest.json
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/adaptive_rule_replay_summary.csv
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/adaptive_rule_baseline_comparison.csv
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/adaptive_rule_gate_decision.csv
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/risk_metric_summary_by_rule.csv
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/cash_no_trade_audit_by_rule.csv
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/turnover_fee_tax_audit_by_rule.csv
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/concentration_audit_by_rule.csv
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/threshold_contract_compliance_audit.csv
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/diagnostic_findings.md
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/rules/RCPT1_RULE_05/rule_trigger_ledger.csv
```

## 3. Core Result

2022 diagnostic baseline：

```text
baseline_net_return_after_fee_tax = -0.33609220
baseline_max_drawdown = -0.42634734
baseline_turnover_proxy = 48.45575343
baseline_fee_and_tax = 112926.17
```

`RCPT1_RULE_05`：

```text
rule_net_return_after_fee_tax = -0.18603880
net_delta = +0.15005340

rule_max_drawdown = -0.22907360
max_drawdown_delta = +0.19727374
max_drawdown_relative_improvement = 46.270663%

rule_turnover_proxy = 47.89271616
turnover_delta = -0.56303727

rule_fee_and_tax = 121293.38
fee_and_tax_delta = +8367.21

buy_count = 245
sell_count = 237
action_count = 482
accelerated_sell_count = 105
participation_rate = 0.99593496
average_cash_rate = 0.57052970
average_holding_count = 3.49186992
max_holding_count = 8
max_symbol_weight = 0.12189486
```

判断：

```text
RULE_05 的改善不是 no-trade / all-cash 伪通过。
```

原因：

```text
1. participation_rate 与 baseline 一样接近满参与；
2. buy_count 与 baseline 接近，甚至略高于 baseline；
3. 规则没有大规模 block buy / block sell；
4. 主要新增机制是 risk-off 下最多每日一笔 early sell；
5. 净亏损和最大回撤同时大幅改善。
```

## 4. Why RULE_05 Passed

`RCPT1_RULE_05` 的机制不是重新挑股票、不是扩大动作空间，也不是重训模型，而是在 baseline 买入路径之外增加：

```text
risk-off 中，当持仓不再满足 mid-band/trend support，
且 rank_change_5d > 0 或 rank_change_3d > 0 表示排名恶化时，
每天最多提前卖出 1 笔弱化持仓。
```

这与前面多轮 policy 失败结论一致：

```text
我们的项目中，买入侧很难稳定超过 qlib ranking baseline；
但下跌年中，卖出侧风险控制有更明确的边际空间。
```

RULE_05 通过的底层含义是：

```text
模型 score / rank 仍作为 alpha 来源；
policy 不试图替代 ranking model；
policy 只在大盘 risk-off 且持仓自身排名恶化时修正退出时机。
```

这比大规模 ML/RL policy 更适配当前项目，因为：

```text
1. 动作更低维，减少过拟合；
2. 机制可解释；
3. 不需要训练新的 policy model；
4. 直接服务于 2022 下跌年 baseline 的最大痛点：回撤过深、弱持仓退出太慢。
```

## 5. Failed Rules Closure

### RCPT1_RULE_01

关闭为：

```text
FAIL_CASH_OR_NO_TRADE
```

它虽然显著改善净收益和回撤，但平均现金率 `0.65216193` 超过 0.60 上限。该规则更像强买入门槛导致的高现金防御，不应作为当前主候选。

### RCPT1_RULE_02

关闭为：

```text
FAIL_CASH_OR_NO_TRADE
```

它严格按冻结 `score_percentile_floor=0.10` / `score_percentile_ceiling=0.40` 回放，未扩展到 H03/top_40_60，但平均现金率 `0.74958201` 过高。即使收益回撤改善，也不能排除 all-cash-like bias。

### RCPT1_RULE_03

关闭为：

```text
FAIL_CASH_OR_NO_TRADE
```

平均现金率 `0.63417325` 仍高于 0.60。该规则说明 mid-band + trend buy filter 在 2022 有防御价值，但目前防御过强。

### RCPT1_RULE_04

关闭为：

```text
FAIL_NO_RISK_REWARD_TRADEOFF
```

它与 baseline 结果相同，未形成有效 policy。

## 6. Remaining Risks

### Critical

无。

### High

无。

### Medium

1. `RCPT1_RULE_05` 只在 2022 downturn validation diagnostic 上通过，且 2022 不是 strict OOS。
   因此不能直接进入生产、不能称为最终验证成功。

2. RULE_05 的 `average_cash_rate = 0.57052970`，距离 0.60 guardrail 较近。
   虽然不构成 no-trade / all-cash 失败，但下一步必须拆解现金暴露来自哪里：是 early sell 后未能快速补仓，还是持仓数量自然下降。

3. RULE_05 的 fee/tax 比 baseline 高 `8367.21`。
   由于净收益和最大回撤仍显著改善，本轮 gate 可接受；但下一步必须做 fee/tax reconciliation，确认改善不是被偶然行情掩盖的过度交易。

4. RULE_05 的 drawdown_duration 为 `242`，高于 baseline 的 `223`。
   它改善了最大回撤深度，但不一定缩短水下时间。下一步不能只看 max drawdown，必须继续检查 monthly/worst-period risk profile。

### Low

1. `rules/*/actions.csv` 作为 replay accounting ledger 包含 `quantity`、`execution_price`、`cash_after`、`position_after` 等字段。
   这在诊断 replay 内部可接受，但必须持续标注为 internal ledger only，不能被误读为 OrderIntent 或实盘订单。

## 7. Forbidden Actions Audit

本 closure review 未执行，也不授权：

```text
model_training
strict_test
production/default/provider switch
frontend/Agent/monitor integration
broker / quick-trade / real order
OrderIntentArtifact
target_weight
target_position
quantity_instruction
new rule
new threshold
2022 replay-result-driven tuning
```

RCPT3 只完成 closure review，不新增 replay、不改策略代码、不改生产合同。

## 8. Closure Decision

RCPT threshold route 当前可以阶段性闭环为：

```text
1. 固定 risk-control rule 直接回放未通过；
2. score/rank/regime threshold discovery 找到了 2022 下跌年中值得关注的中分数段现象；
3. adaptive threshold 规则中，买入侧 gate 改善风险但容易现金过高；
4. 卖出侧 weak-rank-deterioration early sell 是当前唯一通过现金/风险收益审计的候选。
```

因此：

```text
RCPT 不应关闭为失败；
RCPT 也不能关闭为策略成功上线；
RCPT 应关闭为 diagnostic candidate discovered，
并进入窄范围 robustness + mechanism attribution。
```

## 9. Next Work Document

下一步阶段名称：

```text
RCPT4_NARROW_ROBUSTNESS_AND_RULE05_MECHANISM_ATTRIBUTION
```

### 9.1 Goal

只围绕 `RCPT1_RULE_05` 做窄范围验证与机制归因，回答：

```text
RULE_05 的 2022 改善到底来自什么？
它是否稳定来自 risk-off 中提前卖出恶化持仓？
还是来自现金暴露、费用核算、单一月份/少数股票、或偶然路径？
```

### 9.2 Required Inputs

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT3_CLOSURE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY_REVIEW_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/rules/RCPT1_RULE_05/nav.csv
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/rules/RCPT1_RULE_05/actions.csv
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/rules/RCPT1_RULE_05/position_snapshots.csv
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/rules/RCPT1_RULE_05/rule_trigger_ledger.csv
data_tw/experiments/risk_control_policy_2022/rcpt2_adaptive_threshold_replay_sanity/rules/RCPT1_RULE_05/execution_audit.csv
data_tw/experiments/risk_control_policy_2022/rcp1b_diagnostic_baseline_replay_audit/
```

如需 2021 replay，只能使用 RCP1A 已合同化的 2021 diagnostic signal 和 PIT-safe market features；不得训练或新增数据源。

### 9.3 Required Outputs

输出目录建议：

```text
data_tw/experiments/risk_control_policy_2022/rcpt4_rule05_mechanism_attribution/
```

必须生成：

```text
manifest.json
rule05_mechanism_summary.csv
rule05_vs_baseline_monthly_comparison.csv
rule05_trigger_day_attribution.csv
rule05_accelerated_sell_pnl_attribution.csv
rule05_cash_exposure_attribution.csv
rule05_fee_tax_reconciliation.csv
rule05_symbol_concentration_attribution.csv
rule05_subperiod_stability.csv
rule05_2021_optional_diagnostic_replay_summary.csv 或 2021_not_available_audit.json
diagnostic_semantics_audit.json
forbidden_action_audit.csv
validator_report.json
diagnostic_findings.md
```

文档输出：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT4_NARROW_ROBUSTNESS_AND_RULE05_MECHANISM_ATTRIBUTION_EXECUTION_REPORT_CN.md
```

### 9.4 Required Analyses

执行者必须至少完成：

```text
1. Monthly attribution：
   比较 baseline 与 RULE_05 每月 net return、max drawdown、fee/tax、cash、holding_count。

2. Trigger-day attribution：
   对 105 次 accelerated sell 逐笔归因，统计卖出后 5/10/20 日相对继续持有的 avoided loss / missed gain。

3. Cash exposure attribution：
   拆解平均现金率 0.57052970 是否主要由 early sell 后未补仓造成。

4. Fee/tax reconciliation：
   解释 turnover 低于 baseline 但 fee/tax 高于 baseline 的原因。

5. Symbol/date concentration：
   检查收益改善是否集中在少数股票、少数月份、少数 trigger day。

6. 2021 optional diagnostic：
   如 2021 market feature 与 price coverage 足够，则冻结 RULE_05 原样 replay 2021；
   如不足，则写明不可做，不得临时补外部数据或调规则。
```

### 9.5 Pass / Fail Gate

RCPT4 通过条件：

```text
1. RULE_05 改善来源可归因，不是单一股票/单一月份偶然贡献；
2. accelerated sell 后的 avoided loss 解释了主要 drawdown 改善；
3. cash exposure 未退化成 all-cash-like 防御；
4. fee/tax 上升有合理解释，且未吞噬主要净收益改善；
5. 没有 future leakage、threshold retuning、new rule、new threshold；
6. 2021 optional diagnostic 若可做，结果不出现明显灾难性退化；若不可做，证据充分说明不可做。
```

RCPT4 失败或停止条件：

```text
1. 改善主要来自单一股票/单一月份/少数极端事件；
2. 主要收益来自接近 all-cash 的暴露下降，而不是卖弱化持仓；
3. fee/tax reconciliation 显示 accounting 口径不可信；
4. 发现 replay 使用 future return label 或 2022 tuning；
5. 为了让规则通过而新增阈值、调阈值或换规则。
```

### 9.6 Reviewer Duties

审查者必须核对：

```text
1. RCPT4 是否只分析 RULE_05；
2. 是否没有新增规则/阈值/训练/strict_test/生产改动；
3. 机制归因是否能从 durable artifacts 复核；
4. 2021 optional diagnostic 是否保持 diagnostic-only；
5. 是否没有把 2022 结论升级为 strict OOS；
6. 是否明确下一步是继续窄验证、停止，还是准备单独的 strict OOS 设计。
```

### 9.7 Command For Executor

```text
请执行 RCPT4_NARROW_ROBUSTNESS_AND_RULE05_MECHANISM_ATTRIBUTION。
严格读取 docs/tw_portfolio_decision_model/POLICY_RCPT3_CLOSURE_REVIEW_CN.md，
只围绕 RCPT1_RULE_05 做机制归因与窄范围 robustness。
不得新增规则、调阈值、训练模型、执行 strict_test、修改生产/default/provider/frontend/Agent/monitor/order 链路，
不得输出 OrderIntent、target_weight、target_position、quantity_instruction。
完成后写入 docs/tw_portfolio_decision_model/POLICY_RCPT4_NARROW_ROBUSTNESS_AND_RULE05_MECHANISM_ATTRIBUTION_EXECUTION_REPORT_CN.md。
```

### 9.8 Command For Reviewer

```text
请独立审查 RCPT4 执行报告和所有产物。
重点判断 RULE_05 的 2022 改善是否来自可解释、可复核的卖出侧风险控制机制，
还是来自现金暴露、费用/会计口径、少数股票/月度偶然、或 scope violation。
审查结论只能是：
PASS_READY_FOR_COORDINATOR_DECISION_ON_STRICT_OOS_DESIGN,
FAIL_NEEDS_RCPT4_REPAIR,
STOP_RULE05_MECHANISM_NOT_SUPPORTED,
STOP_SCOPE_OR_DIAGNOSTIC_SEMANTICS_VIOLATION。
```
