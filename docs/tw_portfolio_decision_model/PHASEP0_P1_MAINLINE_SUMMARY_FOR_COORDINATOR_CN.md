---
created_at: 2026-06-21
status: submitted_to_coordinator_for_mainline_check
scope: portfolio_decision_optimizer_v1
current_mainline: docs/tw_portfolio_decision_model/PHASEP_PORTFOLIO_DECISION_OPTIMIZER_MAINLINE_CN.md
covered_phases: P0,P1A,P1B-A_to_P1B-G,P1B_repairs
readonly_only: true
simulation_only: true
not_order: true
not_target_position: true
not_investment_advice: true
---

# P0/P1 主线执行总结与统筹审查说明

## 1. 给统筹的结论

本总结用于请统筹核对：

```text
P0 与 P1 是否偏离 docs/tw_portfolio_decision_model/PHASEP_PORTFOLIO_DECISION_OPTIMIZER_MAINLINE_CN.md。
```

当前 reviewer 结论：

```text
P0/P1 的执行结果总体符合主线。
```

核心判断：

```text
1. P0 做的是合同冻结，没有实现策略、没有 replay、没有默认化。
2. P1A 做的是合同脚手架和 validator / golden samples。
3. P1B 按主线明确的 A-G 单机制 ablation 顺序完成。
4. P1B-A-R 与 P1B-G-R 是审查发现问题后的最小修复轮，不是新增主线阶段。
5. P1B-G0 是为了满足主线中 P1B-G 的前置条件：OrderIntent 合同必须先支持 simulation-only partial intent。
6. 前序工作未进入 P2、P3、P4、P5。
7. 前序工作未切换默认模型、默认策略、frontend default 或 latest。
8. 前序工作未 provider publish / accepted latest switch / monitor write / broker / quick-trade / real order。
```

已发现并纠正的 reviewer 偏离：

```text
Reviewer 曾把 P2 错误拆成 P2A/P2B/P2C。
该拆分已撤回并修正为主线的一轮 Phase P2：只读 replay 与压力测试。
```

纠正文档：

```text
docs/tw_portfolio_decision_model/PHASEP_MAINLINE_DEVIATION_AUDIT_AND_CORRECTION_CN.md
docs/tw_portfolio_decision_model/PHASEP1B_G_R_REVIEW_AND_PHASEP2_WORK_CN.md
```

## 2. 主线要求摘要

主线对 P 路线的定位：

```text
Portfolio Decision Optimizer v1
= 排序模型之后的只读组合动作策略层
```

它不是：

```text
新 Qlib
新 LTR
Entry rerank v2
实盘交易系统
```

当前产品基线：

```text
Base Qlib:
e4_frozen_qlib_2018_2022

Orthogonal LTR:
e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025

Default strategy:
top50_exit_one_worst_sell
```

短期路线：

```text
P0 合同冻结
P1 规则化组合优化器
P2 只读 replay 与压力测试
P3 解释 artifact
P4 风险过滤输入
P5 才考虑监督动作模型
```

全程禁止：

```text
real order
broker / quick-trade
target_position / target_weight
provider publish / refresh
accepted latest switch
monitor config / scan / alerts write
default model switch
default strategy switch
frontend default switch
future return / label / realized pnl as strategy input
same-day unavailable execution price
```

## 3. P0 做了什么

P0 文件：

```text
docs/tw_portfolio_decision_model/PHASEP0_CONTRACT_FREEZE_WORK_REPORT_CN.md
docs/tw_portfolio_decision_model/PHASEP0R_REVIEW_AND_PHASEP1A_WORK_CN.md
```

P0 实际完成：

```text
1. 冻结 strategy_rule = portfolio_decision_optimizer_v1。
2. 冻结 P 路线只能作为排序模型后的只读组合动作层。
3. 冻结输入边界：ModelSignalArtifact、PortfolioState / PaperPortfolioState、StrategyRuleConfig、execution readiness 等。
4. 冻结输出边界：OrderIntentArtifact / Readonly ReplayResultArtifact / DecisionExplanationArtifact 的后续合同方向。
5. 冻结 action / reason code / execution_price_gate / forbidden fields / forbidden actions。
6. 明确 P1 不训练模型、不跑收益筛选、不切默认、不进入实盘。
7. 明确 P1B 要以 top50_exit_one_worst_sell 为骨架做逐项 ablation。
```

P0 未做：

```text
1. 未实现策略。
2. 未生成正式 OrderIntentArtifact。
3. 未生成 ReplayResultArtifact。
4. 未跑收益 replay。
5. 未训练或调参模型。
6. 未改默认模型、默认策略、frontend default 或 latest。
7. 未触发 provider / monitor / broker / order。
```

Reviewer 判断：

```text
P0 符合主线。
```

## 4. P1A 做了什么

P1A 文件：

```text
docs/tw_portfolio_decision_model/PHASEP1A_CONTRACT_SCAFFOLD_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/PHASEP1A_REVIEW_AND_PHASEP1B_A_WORK_CN.md
```

P1A 实际完成：

```text
1. 建立 portfolio_decision_optimizer_v1 的 StrategyDependency / 多输入边界。
2. 建立 validator 与 golden sample 脚手架。
3. 建立 dry-run builder 的基本路径。
4. 建立 forbidden fields / forbidden actions 检查。
5. 明确 P1B 后续只能做单机制 ablation。
```

P1A 的限制：

```text
1. 未实现完整组合优化策略。
2. 未生成正式 OrderIntentArtifact / ReplayResultArtifact。
3. 未跑收益 replay。
4. 未切默认路径。
```

Reviewer 判断：

```text
P1A 符合主线。
```

说明：

```text
P1A review 曾要求后续接入统一 modular regression。
该要求通过 P1B-A-R 的 regression hook 修复完成。
```

## 5. P1B 做了什么

P1B 是主线明确允许分轮的部分，因为主线写明了 A-G 的 ablation 顺序。

P1B 的共同边界：

```text
1. baseline 始终是 top50_exit_one_worst_sell。
2. 每一轮只验证一个机制。
3. 不允许 all-gates。
4. 不允许 cumulative strategy。
5. 不允许把某一轮机制结论当作收益有效性结论。
6. 不允许生成正式 artifact 或切默认路径。
7. 不允许 provider / monitor / broker / order。
```

### 5.1 P1B-A execution_price_gate

目标：

```text
baseline + execution_price_gate
```

实际完成：

```text
1. 验证 next_open 不可得时只做 blocked / skip。
2. 不改变 next_open ready 时的 baseline 买卖逻辑。
3. 禁止读取 next_open 价格本体或 execution_price。
```

审查结果：

```text
P1B-A 需要 P1B-A-R 修复 regression hook 与 artifact guard。
```

### 5.2 P1B-A-R regression hook repair

性质：

```text
修复轮，不是新增主线阶段。
```

实际完成：

```text
1. 将 portfolio decision optimizer validator 接入模块回归。
2. dry-run builder 拒绝 --out 写入 data_tw/artifacts/**。
3. dry-run builder 拒绝 manifest.json / order_intents.csv 这类正式 artifact 文件名。
```

审查结果：

```text
PASS
```

### 5.3 P1B-B tiny_no_trade_buffer

目标：

```text
baseline + tiny_no_trade_buffer
```

实际完成：

```text
1. 只阻断排名或分数差极小的低价值换仓。
2. 不复用 execution_price_gate。
3. 不用 future return / replay return / PnL 作为输入。
```

审查结果：

```text
PASS
```

### 5.4 P1B-C confidence_gap

目标：

```text
baseline + confidence_gap
```

实际完成：

```text
1. 新候选必须显著优于当前最弱持仓才允许替换。
2. 不复用 tiny_no_trade_buffer 或 execution_price_gate。
3. 不阻断强信号样本。
```

审查结果：

```text
PASS
```

### 5.5 P1B-D min_holding_days_with_exception

目标：

```text
baseline + min_holding_days_with_exception
```

实际完成：

```text
1. 短持有原则上不卖。
2. 深度跌出 top50 或达到例外条件时允许 baseline 行为保留。
3. 不复用 P1B-A/B/C gate。
```

审查结果：

```text
PASS
```

### 5.6 P1B-E turnover_budget

目标：

```text
baseline + turnover_budget
```

实际完成：

```text
1. 动作预算超限时暂停低优先级替换。
2. 不暂停强信号替换。
3. 不把低换手本身作为通过标准。
```

审查结果：

```text
PASS
```

### 5.7 P1B-F risk_off_raised_threshold

目标：

```text
baseline + risk_off_raised_threshold
```

实际完成：

```text
1. risk_off 只提高弱信号门槛。
2. 不全面禁买。
3. 不把 risk_off 当作已验证 alpha gate。
```

审查结果：

```text
PASS
```

### 5.8 P1B-G0 partial intent contract support

性质：

```text
前置合同支持，不是主线外新增策略阶段。
```

为什么需要：

```text
主线明确 P1B-G partial_adjustment 只能在 OrderIntent 合同支持 simulation-only partial intent 后启动。
```

实际完成：

```text
1. 合同支持 simulated_buy_small / simulated_reduce_partial。
2. partial intent 只能通过 reason code 与 diagnostic fields 表达。
3. 仍禁止 execution_quantity / shares / lots / target_position / target_weight / cash / NAV / PnL / broker/order。
4. 未实现 partial_adjustment 策略机制。
```

审查结果：

```text
PASS
```

### 5.9 P1B-G partial_adjustment

目标：

```text
baseline + partial_adjustment
```

实际完成：

```text
1. baseline sell -> simulated_reduce_partial。
2. baseline buy -> simulated_buy_small。
3. hold / skip / 非交易行保持 baseline。
4. 不输出数量、权重、现金、NAV、成交、PnL、broker/order 字段。
```

审查结果：

```text
FAIL_NEEDS_REPAIR
```

原因：

```text
builder 当时允许 strategy_config.partial_adjustment.sell_reason / buy_reason 任意覆盖，
未知 reason code 下仍返回 ok=true。
```

### 5.10 P1B-G-R partial reason contract repair

性质：

```text
修复轮，不是新增主线阶段。
```

实际完成：

```text
1. builder 固定 sell_reason = simulated_reduce_partial。
2. builder 固定 buy_reason = simulated_buy_small。
3. 未知 sell_reason / buy_reason 直接失败。
4. validator 拒绝未知 partial reason config。
5. validator 拒绝 candidate rows 中合同外 partial reason。
6. 新增 fail_p1b_g_unknown_partial_reason golden sample。
```

审查结果：

```text
PASS
```

## 6. P0/P1 没有做什么

前序工作明确没有做：

```text
1. 没有训练新模型。
2. 没有调参或选择新模型。
3. 没有切换默认模型。
4. 没有切换默认策略。
5. 没有切换 frontend default。
6. 没有 provider publish / refresh。
7. 没有 accepted latest switch。
8. 没有 monitor write / scan / alerts write。
9. 没有 broker / quick-trade / real order。
10. 没有输出 target_position / target_weight。
11. 没有把 future return / replay return / realized pnl / net_return / gross_return 作为策略输入。
12. 没有进入 P2 replay。
13. 没有生成 P3 DecisionExplanationArtifact。
```

## 7. 已发现的偏离与修正

### 7.1 Reviewer 曾错误拆分 P2

偏离：

```text
Reviewer 曾把 P2 拆成 P2A / P2B / P2C。
```

为什么偏离：

```text
主线文档中 P2 是一轮：
Phase P2：只读 replay 与压力测试。
```

修正：

```text
1. 错误 P2A 工作入口已删除。
2. 已改为 docs/tw_portfolio_decision_model/PHASEP1B_G_R_REVIEW_AND_PHASEP2_WORK_CN.md。
3. 新文档明确禁止拆 P2A/P2B/P2C。
4. 新文档明确 P2 必须一轮完成主线要求。
```

影响：

```text
该偏离发生在下一步工作文档层面，未被执行者执行，
因此未污染 P0/P1 代码、样本或执行结果。
```

## 8. 统筹需要重点确认的问题

请统筹确认以下判断是否接受：

```text
1. P1B-A-R 是否接受为审查修复轮，而不是主线偏离。
2. P1B-G0 是否接受为 P1B-G 的必要合同前置，而不是新增策略阶段。
3. P1B-G-R 是否接受为审查修复轮，而不是主线偏离。
4. 当前纠正后的 P2 工作文档是否符合主线“一轮 P2”的粒度。
```

如果统筹不同意其中任意一项，应在进入 P2 前先回写主线或补充纠偏要求。

## 9. 当前下一步

当前唯一合法下一步：

```text
Phase P2: 只读 replay 与压力测试
```

工作文档：

```text
docs/tw_portfolio_decision_model/PHASEP1B_G_R_REVIEW_AND_PHASEP2_WORK_CN.md
```

执行报告应写：

```text
docs/tw_portfolio_decision_model/PHASEP2_READONLY_REPLAY_PRESSURE_TEST_EXECUTION_REPORT_CN.md
```

禁止下一步：

```text
P1B-H
P2A
P2B
P2C
任何主线未授权的新 P2 子阶段
```

## 10. Reviewer 建议

建议统筹如果认可本总结，则允许执行者直接进入 P2；如果不认可，应先给出主线修订或纠偏意见。

P2 执行时必须一次性覆盖主线要求的 replay 与压力测试，不再拆小轮。
