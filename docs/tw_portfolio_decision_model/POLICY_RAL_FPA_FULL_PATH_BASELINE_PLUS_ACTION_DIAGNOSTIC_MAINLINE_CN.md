---
created_at: 2026-06-23
status: coordinator_mainline
route: RAL_FPA_FULL_PATH_BASELINE_PLUS_ACTION_DIAGNOSTIC
previous_review: docs/tw_portfolio_decision_model/POLICY_RAL_ED2_A_BASELINE_REPLAY_ACCOUNTING_AUDIT_REVIEW_CN.md
previous_opinion: docs/tw_portfolio_decision_model/POLICY_RAL_ED2_A_COORDINATOR_POST_AUDIT_OPINION_CN.md
baseline_signal: data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json
baseline_rule: top50_exit_one_worst_sell
policy_training_authorized: false
rule_selection_authorized_initially: false
strict_test_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity: true
---

# RAL-FPA Full-path Baseline-plus Action Diagnostic 主线

## 1. 统筹结论

当前已完成：

```text
RAL-ED2 predeclared block-buy rule sanity；
RAL-ED2-A baseline/replay accounting audit。
```

结论是：

```text
baseline/replay 可信；
block-buy-only 规则没有超过 baseline；
block-buy-only route 应关闭为 negative evidence。
```

但这不等于 policy/rule 方向完全没有提升空间。ED2 失败的核心原因是动作空间太窄：

```text
只挡 baseline buy；
不替换买入；
不调整卖出时点；
不改变持仓延续；
不重配现金；
不做完整组合路径 replay。
```

下一步应切换到：

```text
RAL-FPA = Rule Attribution Ledger - Full-path Baseline-plus Action Diagnostic
```

核心目标：

```text
先用完整 readonly portfolio path diagnostic 判断：
baseline-plus 动作空间是否存在扣费税后超过 baseline 的上界空间。
```

如果上界都没有，再写规则或训练模型没有意义。

如果上界存在，再从上界归因中提炼少量预声明规则，进入下一阶段。

## 2. 目标

本主线只回答一个问题：

```text
在可信 qlib baseline 基础上，
是否存在完整路径动作调整空间，
能在扣费税后收益上稳定超过 baseline？
```

重点动作空间：

```text
1. replacement buy：
   当 baseline buy 被过滤时，不持现金，而是在同日候选中替换买入。

2. sell timing：
   对 baseline sell 尝试提前卖、延后卖、保留持仓。

3. hold continuation：
   对 baseline 准备卖出的持仓，评估继续持有是否改善收益。

4. regime participation：
   按市场趋势、波动、回撤、score dispersion 调整参与节奏。

5. transaction-cost marginal：
   只允许预期边际收益能覆盖费用税和换手的动作。
```

第一阶段不是写规则，而是做 diagnostic / upper-bound。

## 3. 非目标

本主线不授权：

```text
1. strict_test。
2. 模型训练、深度学习、强化学习。
3. validation threshold mining。
4. 无界规则 grid search。
5. 生产默认策略切换。
6. provider publish / accepted latest switch。
7. monitor write / frontend default / Agent integration。
8. broker / quick-trade / real order。
9. OrderIntent target_weight / target_position / quantity。
```

本主线也不允许：

```text
用低换手、低成本、低回撤替代收益；
用 cash/no-trade 通过；
用 baseline clone 通过；
用单日/单股集中收益通过；
用 strict_test 反向找规则；
把 oracle diagnostic 当成可交易策略。
```

## 4. 基线事实

当前可信 baseline：

```text
window = 2025 validation
start_date = 2025-01-02
end_date = 2025-12-31
initial_cash = 1000000.0
final_equity = 1953767.53
net_return_after_fee_tax = 0.95376753
net_return_if_liquidated_at_period_end = 0.94512277
max_drawdown = -0.34681374
action_count = 436
buy_count = 223
sell_count = 213
turnover_proxy = 42.18778217
fee_and_tax = 146214.73
average_cash_rate = 0.12981877
max_holding_count = 10
missing_price_count = 0
negative_cash_count = 0
```

市场对比：

```text
TWII_2025_return = 0.26854957
baseline_2025_return = 0.95376753
baseline_excess_vs_TWII = 0.68521796
```

审查口径：

```text
baseline 很强，但不是不可挑战；
要挑战它，必须保持有效市场暴露，并改善替换、卖出、持仓延续或 regime 参与。
```

## 5. 阶段计划

### FPA0：关闭 Block-buy-only Route

目标：

```text
把 RAL-ED2 + ED2-A 归档为 negative evidence；
防止执行者继续调 block-buy 阈值。
```

输出：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED2_BLOCK_BUY_ROUTE_CLOSURE_CN.md
```

必须说明：

```text
baseline 可信；
block-buy-only 动作空间失败；
后续不得继续 ED2/ED3/block-buy tuning；
后续若继续，只能进入 RAL-FPA full-path diagnostic。
```

### FPA1：Replay State Contract Freeze

目标：

```text
冻结 full-path readonly replay state contract，
确保 replacement buy / sell timing / hold continuation 可以在完整组合路径中模拟。
```

产物目录：

```text
data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/
```

必须输出：

```text
manifest.json
full_path_replay_state_contract.md
required_state_field_audit.csv
action_space_contract.csv
forbidden_output_audit.csv
validator_report.json
```

动作空间只能使用内部 simulation 字段，不得输出生产指令字段。

允许内部模拟字段：

```text
simulation_action_type
candidate_symbol
replacement_candidate_rank
simulation_cash_before
simulation_cash_after
simulation_holding_count_before
simulation_holding_count_after
simulation_fee_tax
simulation_turnover
simulation_nav
```

禁止输出或作为生产合同字段：

```text
target_weight
target_position
quantity
broker_order
OrderIntent
quick_trade
provider publish
accepted latest switch
```

### FPA2：Oracle-style Upper-bound Diagnostic

目标：

```text
不写规则，只评估动作空间是否存在上界收益。
```

产物目录：

```text
data_tw/experiments/full_path_action_diagnostic/fpa2_oracle_upper_bound/
```

必须做四类 diagnostic：

```text
1. replacement_buy_oracle:
   当 baseline buy 被判定为弱买入时，允许在同日 topK 后续候选中替换。

2. sell_timing_oracle:
   对 baseline sell 尝试提前 N 天、延后 N 天、继续持有到下一 rebalance。

3. hold_continuation_oracle:
   对被卖出的持仓，比较继续持有 5/10/20 个交易日的路径。

4. regime_participation_oracle:
   按 market trend / volatility / drawdown / score dispersion 分桶，评估在哪些 regime 改动作有正贡献。
```

注意：

```text
oracle diagnostic 可以使用事后结果做上界分析；
但必须标记 not_rule_candidate；
不得把 oracle 结果当作可交易策略；
不得进入 strict_test。
```

必须输出：

```text
manifest.json
source_baseline_manifest.json
replacement_buy_upper_bound.csv
sell_timing_upper_bound.csv
hold_continuation_upper_bound.csv
regime_participation_upper_bound.csv
transaction_cost_marginal_audit.csv
symbol_date_concentration_audit.csv
train_validation_direction_audit.csv
oracle_leakage_boundary_audit.csv
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

通过条件：

```text
1. 至少一个动作空间在 train 与 validation 都有正 upper-bound。
2. 正收益不是来自单日/单股集中。
3. 扣费税后仍超过 baseline。
4. 不靠 cash/no-trade。
5. 不靠明显不可实现的 oracle 泄漏直接形成规则。
6. 能归因到低维可观测特征。
```

失败条件：

```text
1. 所有动作空间 upper-bound 都不稳定或为负。
2. 正收益只存在于 validation 或少数日期。
3. 收益被费用税或换手吃掉。
4. 必须依赖未来收益才能定义动作，无法转化为可观测规则。
```

### FPA3：Pre-rule Attribution Diagnostic

只有 FPA2 通过才允许进入。

目标：

```text
把 FPA2 的 positive upper-bound 归因到可观测低维特征。
```

候选特征：

```text
score absolute / percentile / zscore
score gap / score dispersion
rank_delta / score_delta
holding_days
holding unrealized return bucket
current holding rank
market trend / volatility / drawdown
transaction cost edge
candidate replacement rank
```

输出：

```text
feature_bucket_action_delta_attribution.csv
train_validation_direction_audit.csv
candidate_predeclared_rule_hypothesis_audit.csv
diagnostic_findings.md
```

通过条件：

```text
至少一个 hypothesis 低维、可观测、非 oracle-only、非 baseline clone、非 cash-only。
```

### FPA4：Predeclared Full-path Rule Sanity

只有 FPA3 通过才允许进入。

目标：

```text
测试少量预声明 full-path baseline-plus rules。
```

限制：

```text
candidate_count <= 5
threshold_versions_per_candidate <= 2
threshold_source 只能来自 train 或 fixed rationale
不得使用 validation mining
不得使用 strict_test
```

通过条件：

```text
validation net_return_after_fee_tax > baseline；
rolling OOS mean excess > 0；
rolling OOS median excess > 0；
not baseline clone；
not cash/no-trade；
turnover/cost 可解释；
symbol/date concentration 通过。
```

## 6. FPA1 首轮工作文档

请审查者先写：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA1_REPLAY_STATE_CONTRACT_WORK_CN.md
```

执行者第一轮只做 FPA1，不得跳到 FPA2。

FPA1 工作文档必须要求执行者读取：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED2_A_BASELINE_REPLAY_ACCOUNTING_AUDIT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED2_A_COORDINATOR_POST_AUDIT_OPINION_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FULL_PATH_BASELINE_PLUS_ACTION_DIAGNOSTIC_MAINLINE_CN.md
scripts/run_tw_policy_action_model_pa1.py
```

FPA1 输出执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA1_REPLAY_STATE_CONTRACT_EXECUTION_REPORT_CN.md
```

FPA1 审查输出：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA1_REPLAY_STATE_CONTRACT_REVIEW_CN.md
```

## 7. FPA1 执行者任务

执行者必须：

```text
1. 从 PA1 replay engine 与 ED2-A audit 中梳理 full-path replay 需要的 state。
2. 定义 replacement buy、sell timing、hold continuation、regime participation 的 simulation-only action contract。
3. 列出每类动作需要哪些字段，哪些字段已存在，哪些字段缺失。
4. 明确哪些字段只是内部 simulation accounting，不是策略输出。
5. 写 forbidden output audit，确保没有 OrderIntent、target、quantity、broker、production 字段输出。
6. 写 validator_report.json。
```

执行者不得：

```text
1. 跑 oracle。
2. 跑规则。
3. 选择阈值。
4. 使用 strict_test。
5. 训练模型。
6. 修改生产策略或默认配置。
```

## 8. FPA1 审查者任务

审查者必须检查：

```text
1. contract 是否足以支持完整路径 replay。
2. 是否保留 readonly/simulation-only 边界。
3. 是否混入 target_weight / target_position / quantity / broker order。
4. 是否提前授权 FPA2/FPA3/FPA4。
5. 缺失字段是否被诚实标为 blocker。
```

FPA1 审查结论只能是：

```text
PASS_READY_FOR_FPA2_WORK_DOC
FAIL_NEEDS_CONTRACT_REPAIR
STOP_FIELD_BLOCKER
```

即使 PASS，也只能允许审查者写 FPA2 工作文档，不自动执行 FPA2。

## 9. 总体停止条件

任一阶段出现以下情况，应 STOP 回统筹：

```text
1. 需要 strict_test 才能判断。
2. 需要训练模型。
3. 需要生产订单字段。
4. 需要 target_weight / target_position / quantity 作为策略输出。
5. 上界收益只能来自未来信息，无法转化为可观测规则。
6. 正收益高度集中于少数日期或股票。
7. 扣费税后不能超过 baseline。
8. 结果主要来自 cash/no-trade 或 baseline clone。
```

## 10. 给执行者的第一条命令

```text
请严格阅读：
1. docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FULL_PATH_BASELINE_PLUS_ACTION_DIAGNOSTIC_MAINLINE_CN.md
2. docs/tw_portfolio_decision_model/POLICY_RAL_ED2_A_BASELINE_REPLAY_ACCOUNTING_AUDIT_REVIEW_CN.md
3. docs/tw_portfolio_decision_model/POLICY_RAL_ED2_A_COORDINATOR_POST_AUDIT_OPINION_CN.md
4. scripts/run_tw_policy_action_model_pa1.py

然后只执行 FPA1 Replay State Contract Freeze。
不得跑规则、不得跑 oracle、不得 strict_test、不得训练、不得输出订单/target/quantity。
完成后写：
docs/tw_portfolio_decision_model/POLICY_RAL_FPA1_REPLAY_STATE_CONTRACT_EXECUTION_REPORT_CN.md
```

## 11. 给审查者的第一条命令

```text
请基于本主线撰写：
docs/tw_portfolio_decision_model/POLICY_RAL_FPA1_REPLAY_STATE_CONTRACT_WORK_CN.md

工作文档必须只授权 FPA1 contract freeze，
不得授权 FPA2 oracle、FPA3 attribution、FPA4 rule sanity、strict_test、模型训练或生产集成。
```

## 12. 一句话

```text
不要继续删 baseline 买入；
先建立完整路径 replay contract，
再用 upper-bound diagnostic 判断替换买入、卖出时点、持仓延续和 regime participation 是否真的有超过 baseline 的空间。
```
