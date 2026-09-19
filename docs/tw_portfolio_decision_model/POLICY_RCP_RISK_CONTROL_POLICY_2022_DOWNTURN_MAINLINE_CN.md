---
created_at: 2026-06-23
status: coordinator_mainline
route: RCP_RISK_CONTROL_POLICY_2022_DOWNTURN
previous_closure: docs/tw_portfolio_decision_model/POLICY_RESEARCH_FINAL_CLOSURE_AND_RISK_CONTROL_PIVOT_CN.md
rcp0_decision: docs/tw_portfolio_decision_model/POLICY_RCP0_COORDINATOR_DECISION_ACCEPT_2022_DIAGNOSTIC_CN.md
test_year: 2022
required_signal_model: qlib_trained_2015_2020
risk_control_not_return_enhancement: true
test_year_semantic: downturn_validation_diagnostic_only
strict_oos_2022: false
model_training_authorized_initially: false
strict_test_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity_instruction: true
---

# RCP Risk-control Policy 2022 Downturn 主线

## 1. 统筹结论

收益增强型 policy 路线已关闭。新方向转为：

```text
Risk-control Policy
```

核心问题：

```text
在下跌市场中，能否通过规则化风险控制降低回撤和亏损，
在可接受收益牺牲下改善风险收益特征？
```

首个诊断窗口：

```text
2022-01-01..2022-12-31
```

原因：

```text
2022 是大盘下跌年；
适合测试风险控制 policy；
不能使用 2018-2022 qlib 模型，因为 2022 属于其训练期。
```

RCP0 后统筹决策：

```text
接受 2022 作为 downturn validation diagnostic；
不得称为 strict OOS / final OOS / independent test。
```

因此必须使用：

```text
2015-2020 qlib 模型信号
```

或先把 RCP0 找到的 2021/2022 WF-VAL 候选合同化为 diagnostic-only replay input。

## 2. 目标

RCP 要回答：

```text
使用 2015-2020 qlib 信号作为 ranking alpha，
在 2022 下跌年 diagnostic 窗口中，
是否存在 readonly risk-control policy，
能改善 max drawdown、downside risk 和 risk-adjusted return？
```

RCP 不以绝对收益超过强上涨年 baseline 为目标。

通过必须看：

```text
1. max_drawdown improvement；
2. negative-return period loss reduction；
3. net_return_after_fee_tax 不可崩坏；
4. fee/tax/turnover 不可过高；
5. cash exposure / participation 变化可解释；
6. 不是 no-trade / all-cash 伪通过。
```

## 3. 非目标

本主线不授权：

```text
1. 训练新 qlib 模型，除非 RCP0 证明 2015-2020 artifact 缺失并由统筹另行授权 rebuild。
2. 深度学习 / 强化学习 policy。
3. strict_test。
4. 生产默认策略切换。
5. provider publish / accepted latest switch。
6. monitor / frontend / Agent 集成。
7. broker / quick-trade / real order。
8. OrderIntent target_weight / target_position / quantity_instruction。
```

本主线也不允许：

```text
all-cash / no-trade 作为通过；
只看低回撤不看净收益；
用 2022 反复调阈值；
用 2018-2022 qlib 模型测试 2022；
把风险控制研究写成投资建议。
```

## 4. 数据与切分

目标模型：

```text
qlib train = 2015-01-01..2020-12-31
risk-control design / calibration = 2021, if available and OOS to qlib
primary downturn diagnostic = 2022-01-01..2022-12-31
```

如果 2021 signal 不完整，则 RCP0 必须明确：

```text
能否只用 fixed rationale / predeclared thresholds；
或者是否需要重建 artifact。
```

2022 只能作为：

```text
downturn validation diagnostic
```

不能作为阈值挖掘窗口。

并且不得在报告中称为：

```text
strict OOS
final OOS
independent test
```

## 5. 风险控制 policy 候选机制

候选机制必须低维、可解释、PIT-safe。

允许研究：

```text
1. market trend risk-off：
   index below MA / negative momentum 时减少新买入或提高买入门槛。

2. drawdown brake：
   portfolio drawdown 达到预声明阈值时暂停新买或降低替换频率。

3. score strength gate：
   risk-off 中只允许 score / score_gap 足够强的买入。

4. sell timing risk control：
   market risk-off 中更快卖出跌出 top50 或弱 score 持仓。

5. holding continuation defensive rule：
   下跌年中避免频繁替换，减少费用与错误换仓。

6. volatility / breadth regime gate：
   大盘波动上升或市场广度恶化时降低 participation。
```

禁止：

```text
事后收益驱动；
未来收益标签；
2022 validation mining；
无界 grid search；
all-cash policy。
```

## 6. 评价指标

RCP 必须同时报告：

```text
net_return_after_fee_tax
gross_return
max_drawdown
drawdown_duration
downside_volatility
worst_month_return
monthly_win_rate
Calmar-like ratio
turnover_proxy
fee_and_tax
action_count
buy_count
sell_count
average_cash_rate
max_cash_rate
participation_rate
baseline_clone_status
no_trade_cash_status
symbol/date concentration
```

主通过口径不是单一收益，而是风险收益 tradeoff。

最低要求：

```text
max_drawdown must improve materially；
net_return_after_fee_tax cannot deteriorate beyond predeclared tolerance；
no all-cash / no-trade；
turnover and fee/tax must be explainable；
concentration gate must pass。
```

## 7. 阶段计划

### RCP0：2015-2020 Qlib Artifact Discovery / Contract

目标：

```text
确认 2015-2020 qlib 模型与 signal artifact 是否存在、可读取、覆盖 2021/2022。
```

输出：

```text
docs/tw_portfolio_decision_model/POLICY_RCP0_2015_2020_QLIB_ARTIFACT_DISCOVERY_EXECUTION_REPORT_CN.md
data_tw/experiments/risk_control_policy_2022/rcp0_artifact_discovery/
```

必须输出：

```text
manifest.json
candidate_artifact_inventory.csv
selected_signal_artifact_contract.json
coverage_audit.csv
model_train_window_audit.csv
oos_window_audit.csv
field_availability_audit.csv
rebuild_need_audit.csv
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

RCP0 只做 discovery，不跑策略。

### RCP1A：Diagnostic Signal Adapter / Contract

只有 RCP0 通过后执行。

目标：

```text
把 RCP0 选中的 2021/2022 WF-VAL qlib 候选信号合同化为 diagnostic-only replay input。
```

不得做 baseline replay 或 risk-control policy。

输出：

```text
docs/tw_portfolio_decision_model/POLICY_RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT_EXECUTION_REPORT_CN.md
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/
```

### RCP1B：2022 Diagnostic Baseline Replay Audit

只有 RCP1A 通过后执行。

目标：

```text
用 diagnostic-only 2015-2020 qlib signal 在 2022 回放 baseline rule，
建立风险控制对照基线。
```

不得做 risk-control policy。
不得称为 strict OOS baseline。

### RCP2：Risk-control Rule Design Contract

目标：

```text
预声明少量 risk-control rules 和阈值来源。
```

阈值来源只能是：

```text
fixed rationale
2021 calibration, if available
pre-2022 market statistics
```

不得使用 2022 调阈值。

### RCP3：Risk-control Replay Sanity

目标：

```text
在 2022 下跌年 readonly replay 预声明 rules。
```

通过不要求绝对收益最高，但要求风险收益 tradeoff 真实。

### RCP4：Closure / Decision

目标：

```text
判断风险控制 policy 是否有价值，是否值得未来扩展到更多下跌/震荡年份。
```

## 8. RCP0 首轮工作文档

审查者下一步应写：

```text
docs/tw_portfolio_decision_model/POLICY_RCP0_2015_2020_QLIB_ARTIFACT_DISCOVERY_WORK_CN.md
```

执行者第一轮只做 RCP0。

## 9. RCP0 审查 gate

RCP0 通过条件：

```text
1. 找到明确 2015-2020 qlib signal/model artifact；
2. 证明 2022 对该模型是 OOS；
3. signal 覆盖 2022；
4. 字段足以运行 baseline replay；
5. 不需要使用 2018-2022 qlib；
6. 不触碰 strict_test / production / order。
```

如果找不到 artifact：

```text
RCP0 不得擅自训练；
必须 STOP 回统筹，建议是否授权 rebuild 2015-2020 qlib。
```

## 10. 一句话

```text
RCP 是新问题：不是收益增强，而是下跌年风险控制。
第一步必须先确认 2015-2020 qlib artifact，确保 2022 是干净 OOS。
```
