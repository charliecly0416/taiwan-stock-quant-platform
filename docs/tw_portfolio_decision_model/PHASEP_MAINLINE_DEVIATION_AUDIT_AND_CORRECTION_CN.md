---
created_at: 2026-06-20
status: mainline_deviation_audit_completed
scope: portfolio_decision_optimizer_v1
current_mainline: docs/tw_portfolio_decision_model/PHASEP_PORTFOLIO_DECISION_OPTIMIZER_MAINLINE_CN.md
readonly_only: true
simulation_only: true
not_order: true
not_target_position: true
not_investment_advice: true
---

# P 路线前序工作主线偏离审计与纠正说明

## 1. 审计结论

结论：

```text
总体未发现 P0 到 P1B-G-R 的执行结果偏离 PHASEP_PORTFOLIO_DECISION_OPTIMIZER_MAINLINE_CN.md 的核心路线。
```

已确认：

```text
1. P0 是合同冻结。
2. P1A 是合同脚手架。
3. P1B-A 到 P1B-G 基本按主线的单机制 ablation 顺序推进。
4. P1B-A-R 与 P1B-G-R 是审查发现问题后的修复轮，不是新增主线阶段。
5. P1B-G0 是为满足主线 “P1B-G only after OrderIntent contract supports simulation-only partial intent” 的前置合同支持，不是策略机制扩展。
6. 未发现前序执行报告宣称进入 P2、P3、P4 或 P5。
7. 未发现前序报告宣称切换默认模型、默认策略、frontend default 或 latest。
8. 未发现前序报告宣称 provider publish / accepted latest switch / monitor write / broker / quick-trade / real order。
```

已发现并纠正的偏离：

```text
Reviewer 曾把下一步 P2 错误拆成 P2A / P2B / P2C。
该拆分不符合主线文档，因为主线把 P2 定义为一轮 “只读 replay 与压力测试”。
```

纠正动作已经完成：

```text
1. 删除错误的 docs/tw_portfolio_decision_model/PHASEP1B_G_R_REVIEW_AND_PHASEP2A_WORK_CN.md。
2. 新增 docs/tw_portfolio_decision_model/PHASEP1B_G_R_REVIEW_AND_PHASEP2_WORK_CN.md。
3. 新文档明确禁止继续拆 P2A / P2B / P2C。
4. 新文档明确下一步只执行 Phase P2: 只读 replay 与压力测试。
```

## 2. 前序阶段逐项核对

### P0

状态：

```text
符合主线。
```

理由：

```text
P0 工作定位为合同冻结，未实现策略，未训练模型，未生成正式 replay 或解释产物。
```

### P1A

状态：

```text
符合主线。
```

理由：

```text
P1A 做 StrategyDependency、多输入边界、validator 和 golden sample 脚手架。
未实现完整策略，未生成正式 OrderIntentArtifact / ReplayResultArtifact。
```

### P1B-A 到 P1B-G

状态：

```text
符合主线。
```

主线顺序：

```text
P1B-A: execution_price_gate
P1B-B: tiny_no_trade_buffer
P1B-C: confidence_gap
P1B-D: min_holding_days_with_exception
P1B-E: turnover_budget
P1B-F: risk_off_raised_threshold
P1B-G: partial_adjustment
```

审计确认：

```text
1. 每轮均要求 baseline = top50_exit_one_worst_sell。
2. 每轮均强调 single-mechanism ablation。
3. 每轮均禁止 all-gates / cumulative strategy。
4. 每轮均禁止正式 artifact、provider、accepted latest、monitor、broker/order、target_position/target_weight。
5. 每轮均把收益、费用、换手、压力测试留到 P2。
```

### P1B-A-R

状态：

```text
可接受修复轮，不属于路线偏离。
```

理由：

```text
P1B-A-R 只修复 regression hook 与 dry-run artifact guard。
它没有新增策略机制，也没有改变主线阶段定义。
```

后续约束：

```text
不得把 repair round 当作可自由拆分主线阶段的先例。
只有审查结论 FAIL_NEEDS_REPAIR 或 PASS_WITH_CONDITIONS 明确要求时，才允许出现 -R。
```

### P1B-G0

状态：

```text
可接受前置合同支持，不属于策略阶段扩展。
```

理由：

```text
主线明确 P1B-G 只能在 OrderIntent 合同支持 simulation-only partial intent 后启动。
G0 只冻结 partial intent 合同支持，没有实现 partial_adjustment 策略机制。
```

后续约束：

```text
不得再为后续 P2/P3/P4 任意新增 G0 类前置阶段。
如果主线没有明确前置合同缺口，必须在该 phase 内完成。
```

### P1B-G-R

状态：

```text
可接受修复轮，不属于路线偏离。
```

理由：

```text
P1B-G-R 只修复 unknown partial reason 被 builder 接受的问题。
它没有新增 P1B-H，没有进入 P2，没有新增策略机制。
```

## 3. 已纠正偏离

### D1. Reviewer 错误拆分 P2

偏离内容：

```text
曾提出 P2A / P2B / P2C 三轮拆分。
```

为什么偏离：

```text
PHASEP_PORTFOLIO_DECISION_OPTIMIZER_MAINLINE_CN.md 中 P2 是单一阶段：
Phase P2：只读 replay 与压力测试。
主线没有授权 P2A / P2B / P2C。
```

纠正状态：

```text
已纠正。
```

纠正文件：

```text
docs/tw_portfolio_decision_model/PHASEP1B_G_R_REVIEW_AND_PHASEP2_WORK_CN.md
```

后续执行要求：

```text
1. 下一步只执行 Phase P2。
2. 不拆 P2A / P2B / P2C。
3. P2 执行报告文件为：
   docs/tw_portfolio_decision_model/PHASEP2_READONLY_REPLAY_PRESSURE_TEST_EXECUTION_REPORT_CN.md
```

## 4. 后续纠偏规则

后续所有 reviewer / executor 必须遵守：

```text
1. 以 PHASEP_PORTFOLIO_DECISION_OPTIMIZER_MAINLINE_CN.md 的 phase 粒度为准。
2. 主线写成一轮的 phase，不得自行拆成 A/B/C。
3. 只有主线本身写明子阶段的，才可按子阶段推进。
4. P1B 的 A-G 是主线明确的 ablation 顺序，因此可分轮。
5. -R 只允许作为审查失败或条件通过后的最小修复轮。
6. -R 不得引入新功能、新机制、新默认路径。
7. 每次审查输出下一步工作文档时，必须先检查主线是否授权该 phase 名称。
8. 如果主线未授权新阶段名，必须直接使用主线阶段名。
```

## 5. 当前下一步唯一合法入口

当前下一步是：

```text
Phase P2: 只读 replay 与压力测试
```

唯一工作文档：

```text
docs/tw_portfolio_decision_model/PHASEP1B_G_R_REVIEW_AND_PHASEP2_WORK_CN.md
```

执行报告应写：

```text
docs/tw_portfolio_decision_model/PHASEP2_READONLY_REPLAY_PRESSURE_TEST_EXECUTION_REPORT_CN.md
```

禁止入口：

```text
P1B-H
P2A
P2B
P2C
任何未在主线文档中授权的新 P2 子阶段
```

## 6. 对 P2 的纠偏要求

P2 必须一次性覆盖主线要求：

```text
1. default = top50_exit_one_worst_sell。
2. candidate = portfolio_decision_optimizer_v1。
3. optional diagnostic 只能使用已经存在的 readonly artifact。
4. 报告 net_return_after_fee_tax、gross_return、max_drawdown、action_count、buy_count、sell_count、skip_count、no_action_days、blocked_days、turnover_proxy、fee_and_tax、average_holding_days、median_holding_days、regime_segment_metrics、yearly_metrics、rolling_3m_metrics、rolling_6m_metrics、PnL concentration、symbol turnover concentration、missing_next_open_count、execution_block_count。
5. 标明 2023-2025 只能作为工程诊断和压力测试，不是严格 OOS 收益证据。
6. 用 2026H1 做严格 forward readonly acceptance。
7. 保持 readonly / simulation-only。
```

P2 不得：

```text
1. 拆成 P2A/P2B/P2C。
2. 新增 P1B-H。
3. 训练、调参或选择新模型。
4. 切默认模型、默认策略、frontend default 或 latest。
5. provider publish / refresh。
6. accepted latest switch。
7. monitor write / scan / alerts write。
8. broker / quick-trade / real order。
9. 输出 target_position / target_weight。
10. 使用 future return / replay return / realized pnl / unrealized pnl / net_return / gross_return 作为策略输入。
```
