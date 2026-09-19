---
created_at: 2026-06-25
status: coordinator_mainline
route: RCPT9_LONGER_STRICT_OOS_OR_RETRAIN_HOLDOUT_LINEAGE
parent_closure: docs/tw_portfolio_decision_model/POLICY_RCPT8D_QLIB_LTR_ADAPTATION_CLOSURE_EXECUTION_REPORT_CN.md
production_allowed: false
order_or_target_output_allowed: false
model_training_authorized: false
---

# RCPT9 Longer Strict OOS / Retrain-Holdout Lineage 主线

## 1. 统筹结论

RCPT8D 已确认：

```text
qlib+LTR adaptation 可作为 research candidate。
```

但 RCPT8D 也明确：

```text
不能生产化；
需要更长 strict OOS 或 retrain-holdout lineage。
```

原因：

```text
1. 2023-2025 已被 E3 LTR train 污染，只能作为 integration diagnostic；
2. 2026-01-02..2026-05-07 虽是 narrow strict OOS diagnostic，但只有 79 个交易日；
3. M1/M2 在 W2 通过 gate，但 drawdown improvement 为 0；
4. 当前证据不足以证明生产级风控改善。
```

因此 RCPT9 的目标不是继续调规则，而是建立更强证据：

```text
更长、未污染、可审查、可复现的 strict OOS。
```

## 2. 非目标

RCPT9 当前不授权：

```text
1. 直接生产化；
2. 修改 production/default/provider/latest/frontend/Agent/monitor/order 链路；
3. 输出 OrderIntent、target_weight、target_position、quantity_instruction；
4. broker / quick-trade / real order；
5. 在 RCPT9A 合同阶段训练模型；
6. 在 RCPT9A 合同阶段 replay；
7. 根据 RCPT8C/RCPT9 结果调阈值；
8. 新增无限 mapping 或搜索 alpha；
9. 把训练污染窗口包装为 strict OOS。
```

## 3. 当前事实

RCPT8C W2 结果：

| mapping | W2 gate | return capture | drawdown improvement | production ready |
| --- | --- | ---: | ---: | --- |
| M1 qlib score component | PASS | 0.98484347 | 0.0 | no |
| M2 LTR score component | PASS | 0.87591135 | 0.0 | no |
| M3 blend | FAIL | 0.91046791 | 0.0 | no |

解释：

```text
M1/M2 在短 OOS 中没有崩；
但尚未证明下跌/震荡环境下有实际 drawdown 改善。
```

## 4. 两条合法证据路线

### Route A: Forward Paper Strict OOS Accumulation

含义：

```text
冻结 RCPT8 M1/M2 合同；
不重训、不调阈值；
随着 2026 后续交易日自然到来，持续追加 daily/paper replay；
形成更长 untouched forward OOS。
```

优点：

```text
污染最少；
不需要重训；
最接近真实 future evidence。
```

缺点：

```text
需要等时间；
短期内仍不足以生产化。
```

### Route B: Retrain-Holdout Lineage Design

含义：

```text
重新设计 qlib/LTR split，使一个足够长的历史窗口完全不参与 qlib/LTR 训练、调参、阈值选择或 mapping 选择。
```

可能方案必须由 RCPT9A 合同阶段审计后冻结，例如：

```text
方案 B1:
  qlib train = 2015-2020
  LTR train = 2021
  holdout = 2022

方案 B2:
  qlib train = 2015-2021
  LTR train = 2022-2023
  holdout = 2024-2025

方案 B3:
  qlib train = 2018-2022
  LTR train = 2023-2024
  holdout = 2025 + 2026 available
```

但每个方案都必须审计：

```text
1. qlib 是否会污染 holdout；
2. LTR 是否会污染 holdout；
3. 正交特征是否有 PIT coverage；
4. label 是否可构造；
5. holdout 是否足够长且有不同市场状态；
6. 是否会牺牲太多 LTR train 样本导致模型不可学；
7. 是否需要重新训练 qlib/LTR。
```

## 5. 优先级

统筹建议优先级：

```text
Priority 1: RCPT9A split/lineage feasibility contract
Priority 2: 若 B 路线可行，选择一个 retrain-holdout contract
Priority 3: 同时保留 A 路线作为 forward paper observation
Priority 4: 训练/replay 必须另开 RCPT9B/RCPT9C，不能在 RCPT9A 执行
```

理由：

```text
直接继续在现有 E3 lineage 上做更多历史 replay，不能解决 2023-2025 污染问题；
直接生产化又被 RCPT8D 明确禁止。
```

## 6. 候选策略冻结

RCPT9 不重新开发策略。

只允许验证 RCPT8D 接受的：

```text
M1_QLIB_SCORE_COMPONENT_PRIMARY
M2_LTR_SCORE_COMPONENT_SECONDARY
```

不允许：

```text
M3 复活；
新增 M4/M5；
调 alpha；
改 RULE_05；
改 adaptive score 权重；
replay 后调 gate。
```

## 7. Gate 原则

RCPT9 的最终生产前 gate 必须比 RCPT8 更严格：

```text
1. 至少 1 个完整年度或 >= 180 个交易日 strict OOS；
2. 至少包含一个非单边上涨环境，最好包含震荡或下跌期；
3. return_capture >= 0.85，ideal >= 0.90；
4. max_drawdown severity 改善 >= 5pp，或 downside month/day concentration 明显改善；
5. average_cash_rate <= 0.65；
6. cash_gt_90pct_equity_day_share <= 0.25；
7. average_position_count >= 5；
8. fee/turnover 不得恶化且无补偿；
9. 不靠单月、单股、单 trigger 贡献；
10. no production/order/target fields。
```

如果 strict OOS 仍然只有短窗口，则只能继续 research，不得生产化。

## 8. 阶段计划

### RCPT9A: Split And Lineage Feasibility Contract

目标：

```text
盘点数据与现有 artifact，判断 Route A/B 哪些可执行；
冻结一个推荐的 longer strict OOS / retrain-holdout 方案；
不训练、不 replay。
```

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt9a_split_lineage_feasibility_contract/
```

必须输出：

```text
manifest.json
candidate_split_plan.csv
data_coverage_by_window.csv
feature_pit_coverage_by_window.csv
label_feasibility_by_window.csv
contamination_audit_by_plan.csv
recommended_lineage_contract.md
forward_paper_oos_contract.md
gate_contract.md
forbidden_action_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT9A_SPLIT_LINEAGE_FEASIBILITY_CONTRACT_EXECUTION_REPORT_CN.md
```

审查结论只能是：

```text
PASS_READY_FOR_RCPT9B_LINEAGE_BUILD_OR_FORWARD_OOS
FAIL_NEEDS_RCPT9A_REPAIR
STOP_NO_FEASIBLE_LONGER_STRICT_OOS_LINEAGE
STOP_SCOPE_OR_FORBIDDEN_ACTION_VIOLATION
```

### RCPT9B: Lineage Build

前提：

```text
RCPT9A PASS
```

目标：

```text
只按 RCPT9A 冻结方案构建必要 lineage。
```

如果选择 Route A：

```text
只构建 forward paper OOS reader / accumulator，不训练。
```

如果选择 Route B：

```text
只按冻结 split 训练一个 qlib/LTR lineage；
不得用 holdout 做训练、调参、early stopping、mapping/gate 选择。
```

RCPT9B 训练授权必须由 RCPT9A 明确给出，否则不允许训练。

### RCPT9C: Predeclared Longer OOS Replay

前提：

```text
RCPT9B PASS
```

目标：

```text
只 replay M1/M2；
只使用冻结 holdout；
不得调阈值。
```

### RCPT9D: Closure

目标：

```text
判断是否有足够证据进入 production readiness；
否则继续 research/forward OOS。
```

允许结论：

```text
PASS_READY_FOR_PRODUCTION_READINESS_ROUTE
PASS_RESEARCH_ONLY_CONTINUE_FORWARD_OOS
FAIL_LONGER_OOS_NOT_SUPPORTED
STOP_LINEAGE_OR_SCOPE_VIOLATION
```

## 9. RCPT9A 执行者任务

执行者必须：

```text
1. 读取本主线；
2. 读取 RCPT8D closure；
3. 盘点可用价格/特征/label/model artifact；
4. 枚举至少 Route A 与 Route B1/B2/B3；
5. 对每个 plan 做 contamination audit；
6. 对每个 plan 做数据覆盖、PIT 特征覆盖、label 可行性审计；
7. 判断是否需要重训 qlib/LTR；
8. 推荐一个主方案和一个 fallback；
9. 写明下一阶段是否授权训练，训练哪些模型，禁止使用哪些窗口。
```

执行者不得：

```text
1. 训练；
2. replay；
3. 调阈值；
4. 修改生产链路；
5. 输出交易/仓位/数量指令。
```

## 10. RCPT9A Reviewer 任务

审查者必须判断：

```text
1. plan 是否真的能产生更长 strict OOS；
2. 是否诚实处理训练污染；
3. 是否没有把短窗口包装成生产证据；
4. 是否没有训练/replay 越权；
5. 推荐路线是否合理；
6. 是否可以进入 RCPT9B。
```

## 11. Stop Conditions

必须 STOP：

```text
1. 没有任何可行 longer strict OOS；
2. 所有方案都需要用 holdout 训练/调参；
3. PIT 特征或 label 无法覆盖推荐窗口；
4. 执行者需要修改生产链路才能继续；
5. 需要外部数据或网络才能判断但未获授权。
```
