---
created_at: 2026-06-23
status: coordinator_mainline
route: ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER
previous_closure: docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FINAL_CLOSURE_REVIEW_CN.md
previous_opinion: docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FINAL_COORDINATOR_OPINION_CN.md
purpose: build_foundational_pnl_attribution_ledger_not_strategy_search
strategy_experiment_authorized: false
rule_selection_authorized: false
threshold_selection_authorized: false
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

# ATPAL Action / Trade PnL Attribution Ledger 主线

## 1. 统筹结论

RAL / ED / FPA 已经证明：

```text
1. baseline/replay accounting 可信；
2. block-buy-only 规则失败；
3. full-path oracle upper-bound 存在；
4. 低维可观测规则无法稳定提取 upper-bound；
5. FPA4 缺少 trade-level / symbol-date PnL attribution，集中度 gate 无法严格判断。
```

因此下一步不应继续：

```text
规则搜索；
阈值调参；
strict_test；
模型训练；
生产策略切换。
```

新主线切换为基础设施：

```text
ATPAL = Action / Trade PnL Attribution Ledger
```

目标是补齐可审计账本，让未来任何 policy/rule 研究都能回答：

```text
某个动作的收益来自哪里？
收益是否来自少数股票或少数日期？
realized / unrealized / cost / turnover 分别贡献多少？
局部 action delta 与 full-path portfolio delta 是否一致？
```

这条主线不是为了立刻找新策略，而是为了建立后续研究的证据地基。

## 2. 目标

ATPAL 要建立四层账本：

```text
1. trade-level ledger：
   每笔 buy/sell 的成交、费用税、已实现 PnL、关联 intent/action。

2. position-lifecycle ledger：
   每段持仓从 entry 到 exit 或 period end 的生命周期、成本、持有天数、已实现/未实现贡献。

3. position-day / symbol-date ledger：
   每只股票每天对 NAV 的 mark-to-market 贡献、现金贡献、费用贡献。

4. candidate/action attribution ledger：
   baseline action、candidate policy action、replacement/sell/hold action 与 PnL 贡献之间的映射。
```

最终要支持：

```text
candidate-level concentration gate；
symbol-date contribution audit；
trade-level realized/unrealized split；
action-space attribution；
future rule sanity evidence。
```

## 3. 非目标

本主线不授权：

```text
1. 新策略规则。
2. 规则候选选择。
3. 阈值选择。
4. validation mining。
5. strict_test。
6. 模型训练、深度学习、强化学习。
7. 生产默认策略切换。
8. provider publish / accepted latest switch。
9. monitor / frontend / Agent 集成。
10. broker / quick-trade / real order。
11. OrderIntent target_weight / target_position / quantity。
```

本主线产物也不得用于：

```text
直接宣称某策略通过；
把 PnL attribution 当作投资建议；
输出可交易指令；
替代正式 replay；
绕过 rolling OOS / concentration gate。
```

## 4. 输入与基线

首轮只针对可信 baseline 构建账本。

输入：

```text
baseline_signal_artifact =
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json

baseline_replay_engine =
scripts/run_tw_policy_action_model_pa1.py

baseline_rule =
top50_exit_one_worst_sell

price_source =
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty
```

窗口：

```text
train = 2023-01-01..2024-12-31
validation = 2025-01-01..2025-12-31
strict_test = 2026-01-01..2026-05-07 declared only, not used
```

已审计 baseline 事实：

```text
2025 validation net_return_after_fee_tax = 0.95376753
net_return_if_liquidated_at_period_end = 0.94512277
fee_and_tax = 146214.73
turnover_proxy = 42.18778217
missing_price_count = 0
negative_cash_count = 0
```

## 5. 核心设计原则

### 5.1 Replay-first

账本必须从 replay 产生，不能从 summary 反推。

必须保留：

```text
signal_date
execution_date
mark_date
instrument
action_type
price_source
replay_rule
split
```

### 5.2 PIT-safe

用于 action/context 的字段必须是 action 前可用。

PnL 字段可以是事后归因结果，但必须标记：

```text
attribution_label_only = true
not_rule_feature = true
```

### 5.3 Accounting reconciliation

账本必须能回推出 replay summary：

```text
cash + market_value = equity
sum fees/taxes = summary fee_and_tax
sum action notional / avg equity = turnover_proxy
realized + unrealized + cash + fees/taxes = NAV change
```

若无法 reconciliation，不得进入下一阶段。

### 5.4 No production semantics

内部可以记录 simulation quantity，因为 replay 已经有成交股数；但字段必须命名为：

```text
simulated_executed_quantity
```

并且必须标记：

```text
diagnostic_only = true
not_order_instruction = true
```

禁止出现：

```text
target_weight
target_position
quantity_instruction
broker_order
OrderIntent output
```

## 6. 分阶段计划

### ATPAL0：Schema / Contract Freeze

目标：

```text
冻结 Action / Trade PnL Attribution Ledger 合同。
```

产物目录：

```text
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal0_contract/
```

必须输出：

```text
manifest.json
atpal_schema_contract.md
ledger_table_contract.csv
field_dictionary.csv
reconciliation_rule_contract.csv
pnl_component_definition.csv
forbidden_field_audit.csv
validator_report.json
```

ATPAL0 不生成正式账本，只冻结字段与校验规则。

### ATPAL1：Baseline Ledger Builder

目标：

```text
基于 baseline replay 生成 train + validation 的四层账本。
```

产物目录：

```text
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_baseline_ledger/
```

必须输出：

```text
manifest.json
source_artifact_manifest.json
trade_level_pnl_ledger.csv
position_lifecycle_ledger.csv
position_day_pnl_ledger.csv
symbol_date_pnl_ledger.csv
action_context_ledger.csv
cash_fee_tax_ledger.csv
baseline_summary_reconciliation.csv
nav_reconciliation_audit.csv
fee_tax_turnover_reconciliation_audit.csv
missing_price_audit.csv
forbidden_field_audit.csv
validator_report.json
diagnostic_findings.md
```

### ATPAL2：Concentration / Contribution Audit

目标：

```text
用 ATPAL1 账本生成 baseline 的 symbol/date/trade concentration 诊断。
```

产物目录：

```text
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit/
```

必须输出：

```text
manifest.json
symbol_contribution_summary.csv
date_contribution_summary.csv
symbol_date_contribution_matrix.csv
top_contributor_audit.csv
trade_pnl_distribution_audit.csv
position_lifecycle_distribution_audit.csv
fee_tax_contribution_audit.csv
turnover_contribution_audit.csv
baseline_concentration_gate_design.md
validator_report.json
diagnostic_findings.md
```

本阶段仍然不找策略。

### ATPAL3：Candidate Replay Adapter Contract

目标：

```text
定义未来 rule / policy candidate 如何接入 ATPAL ledger，
以便 candidate-level concentration gate 可复用。
```

产物目录：

```text
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal3_candidate_adapter_contract/
```

必须输出：

```text
manifest.json
candidate_replay_adapter_contract.md
candidate_id_mapping_contract.csv
candidate_vs_baseline_delta_contract.csv
candidate_concentration_gate_contract.csv
required_candidate_replay_fields.csv
forbidden_consumer_audit.csv
validator_report.json
```

ATPAL3 只定义适配合同，不运行候选策略。

### ATPAL4：FPA4 Backfill Diagnostic

只有 ATPAL1/2/3 通过后才允许。

目标：

```text
对既有 FPA4 失败候选做 PnL attribution backfill，
解释其收益/亏损来自哪些 symbol/date/trade。
```

这不是 repair，不允许改变 FPA4 结论。

必须输出：

```text
fpa4_candidate_trade_pnl_attribution.csv
fpa4_candidate_symbol_date_concentration.csv
fpa4_candidate_delta_component_breakdown.csv
fpa4_failure_attribution_report.md
```

## 7. ATPAL0 工作要求

审查者下一步应先写：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL0_SCHEMA_CONTRACT_WORK_CN.md
```

执行者第一轮只做 ATPAL0。

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FINAL_CLOSURE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FINAL_COORDINATOR_OPINION_CN.md
scripts/run_tw_policy_action_model_pa1.py
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
```

ATPAL0 执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL0_SCHEMA_CONTRACT_EXECUTION_REPORT_CN.md
```

ATPAL0 审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL0_SCHEMA_CONTRACT_REVIEW_CN.md
```

## 8. ATPAL Schema 初稿要求

ATPAL0 至少要定义以下表。

### 8.1 trade_level_pnl_ledger

必须包含：

```text
ledger_id
split
strategy_rule
candidate_id
action_trace_id
position_lifecycle_id
signal_date
execution_date
instrument
action_type
intent_reason
execution_price
simulated_executed_quantity
trade_notional
commission
sell_tax
fee_tax_total
cash_before
cash_after
position_before
position_after
realized_pnl_before_fee_tax
realized_pnl_after_fee_tax
diagnostic_only
readonly_research_only
not_order_instruction
```

### 8.2 position_lifecycle_ledger

必须包含：

```text
position_lifecycle_id
split
strategy_rule
candidate_id
instrument
entry_signal_date
entry_execution_date
entry_price
entry_quantity
exit_signal_date
exit_execution_date
exit_price
exit_quantity
holding_days
entry_fee
exit_fee_tax
gross_pnl
net_pnl_after_fee_tax
unrealized_pnl_at_period_end
exit_status
```

`exit_status`：

```text
closed
open_at_period_end
forced_liquidation_diagnostic
```

### 8.3 position_day_pnl_ledger

必须包含：

```text
position_lifecycle_id
date
split
instrument
quantity
cost_basis
previous_close
mark_close
daily_unrealized_pnl_change
cumulative_unrealized_pnl
market_value
holding_days_asof
```

### 8.4 symbol_date_pnl_ledger

必须包含：

```text
date
split
instrument
strategy_rule
candidate_id
realized_pnl_after_fee_tax
unrealized_pnl_change
fee_tax_total
net_symbol_date_contribution
abs_contribution
contribution_share_of_total_abs
```

### 8.5 action_context_ledger

必须包含：

```text
action_trace_id
split
date
instrument
strategy_rule
candidate_id
baseline_action_type
candidate_action_type
action_context
candidate_rank
score
score_rank
full_qlib_rank
holding_days_before
unrealized_return_before
market_regime
available_before_action
attribution_label_only
```

## 9. Reconciliation Gate

ATPAL1 之后必须能通过：

```text
1. summary final_equity reconciliation；
2. fee_and_tax reconciliation；
3. turnover reconciliation；
4. trade action_count reconciliation；
5. realized + unrealized + cash movement reconciliation；
6. missing price reconciliation；
7. no negative cash reconciliation；
8. baseline 2025 metrics reproduce ED2-A audited summary。
```

核心误差阈值：

```text
net_return_after_fee_tax absolute diff <= 1e-6
fee_and_tax absolute diff <= 0.01
turnover_proxy absolute diff <= 1e-6
action_count diff = 0
missing_price_count diff = 0
negative_cash_count diff = 0
```

## 10. Concentration Gate 设计方向

ATPAL2 需要设计但不用于通过策略：

```text
top1_symbol_contribution_share
top3_symbol_contribution_share
top1_date_contribution_share
top5_date_contribution_share
top1_symbol_date_contribution_share
top10_symbol_date_contribution_share
positive_contribution_symbol_count
negative_contribution_symbol_count
contribution_hhi
```

未来候选若要通过，需要证明：

```text
收益不是由单一股票、单一日期或极少数 symbol-date 贡献。
```

但 ATPAL2 只建立度量，不评价新策略。

## 11. 禁止事项

整个 ATPAL 主线禁止：

```text
strict_test；
新策略 replay；
候选规则选择；
阈值选择；
模型训练；
使用 PnL 作为 rule feature；
生产默认策略切换；
OrderIntent 输出；
target_weight / target_position / quantity_instruction；
broker_order；
provider/latest/monitor/frontend/Agent 集成。
```

允许出现的数量字段仅限：

```text
simulated_executed_quantity
```

且必须只在 replay accounting / diagnostic ledger 中使用。

## 12. 停止条件

任一阶段遇到以下情况应 STOP：

```text
1. 无法复现 baseline summary；
2. PnL component 无法 reconciliation；
3. 需要未来价格作为 action feature；
4. 字段语义混入生产订单；
5. 输出 target/quantity instruction/broker 字段；
6. 执行者试图顺手做策略筛选或阈值搜索；
7. validator 无法证明 readonly/simulation-only；
8. 账本不能支持 symbol-date concentration。
```

## 13. 首轮给审查者的指令

请审查者撰写：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL0_SCHEMA_CONTRACT_WORK_CN.md
```

该工作文档只能授权 ATPAL0 schema / contract freeze。

不得授权：

```text
ATPAL1 ledger builder；
ATPAL2 contribution audit；
ATPAL3 candidate adapter；
FPA4 backfill；
任何策略 replay；
strict_test；
模型训练；
生产集成。
```

## 14. 首轮给执行者的指令

```text
请严格阅读：
1. docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md
2. docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FINAL_CLOSURE_REVIEW_CN.md
3. docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FINAL_COORDINATOR_OPINION_CN.md
4. scripts/run_tw_policy_action_model_pa1.py
5. docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
6. docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md

然后只执行 ATPAL0 Schema / Contract Freeze。
不得生成正式账本，不得跑策略，不得 strict_test，不得训练模型，不得输出订单或生产字段。
完成后写：
docs/tw_portfolio_decision_model/POLICY_ATPAL0_SCHEMA_CONTRACT_EXECUTION_REPORT_CN.md
```

## 15. 一句话

```text
ATPAL 不是新策略路线；
它是补齐 action/trade/symbol-date PnL attribution 的基础账本路线，
为未来判断规则收益是否真实、稳定、非集中提供证据。
```
