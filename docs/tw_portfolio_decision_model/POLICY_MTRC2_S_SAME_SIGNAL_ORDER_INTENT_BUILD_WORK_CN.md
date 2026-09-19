---
created_at: 2026-06-28
status: work_doc
phase: MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD
parent_phase: MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT
parent_review: docs/tw_portfolio_decision_model/POLICY_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT_REVIEW_CN.md
readonly_only: true
simulation_only: true
diagnostic_only: true
production_allowed: false
model_training_authorized: false
model_inference_authorized: false
model_signal_artifact_authorized: false
strategy_contract_authorized: true
order_intent_build_authorized: true
replay_result_build_authorized: false
return_replay_authorized: false
ledger_build_authorized: false
strategy_tuning_authorized: false
new_candidate_authorized: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
frontend_default_switch_allowed: false
broker_authorized: false
---

# POLICY_MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD_WORK_CN

## 1. 目标

MTRC2_S 只做一件事：

```text
基于 MTRC1D research-only broad full-rank signal，
按 MTRC2_R 冻结的 M2_hold_rank_buffer_100 / rank_buffer=100 / mechanism_transfer_top50_cost_aware_v1 合同，
生成 readonly、simulation-only、diagnostic-only 的 same-signal OrderIntentArtifact。
```

本阶段是 OrderIntent build 阶段，不是 replay 阶段。MTRC2_S 不得选择 price store，不得生成 ReplayResult，不得生成 ledger，不得计算收益、回撤、集中度或窗口诊断。

MTRC2_S 必须证明：

```text
1. OrderIntent 的 signal_artifact 严格等于 MTRC1D broad signal manifest；
2. candidate_id、mechanism、rank_buffer、target_holding_count、candidate_k、max buy/sell 未漂移；
3. buy intent 只来自 top50，且任何 buy 的 candidate_rank <= 50；
4. non-top50 rows 只能用于 visibility / hold-sell 边界，不进入买入排序；
5. 输出字段符合 OrderIntentArtifact 合同，不含成交、仓位、现金、NAV、PnL、broker/order 字段；
6. 旧 MTR2_R/E3 OrderIntent 没有被复用为 MTRC2_S 产物。
```

## 2. 必读输入

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT_REVIEW_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
configs/strategy_dependencies/mechanism_transfer_top50_cost_aware_v1.yaml
```

必须消费的输入产物：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/manifest.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/signals.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/validator_report.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract/same_signal_order_intent_build_contract.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract/non_top50_buy_validator_contract.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract/m2_100_parameter_freeze_contract.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract/strategy_dependency_contract.csv
```

允许参考但不得复用为输出的旧模板：

```text
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/order_intents/M2_hold_rank_buffer_100/manifest.json
```

## 3. 冻结参数

MTRC2_S 必须严格使用以下参数：

```text
input_model_signal = data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/manifest.json
strategy_rule = mechanism_transfer_top50_cost_aware_v1
candidate_id = M2_hold_rank_buffer_100
mechanism = hold_rank_buffer
rank_buffer = 100
target_holding_count = 10
candidate_k = 50
max_buy_count = 1
max_sell_count = 1
sell_boundary = qlib_top50_by_candidate_rank_and_full_qlib_rank
buy_order = buy_score_desc_only_within_top50
tie_breaker = full_qlib_rank_asc, instrument_asc
readonly_only = true
simulation_only = true
diagnostic_only = true
production_allowed = false
```

不得新增候选、不得改变 `rank_buffer`、不得把 non-top50 加入 buy universe、不得根据 replay 或收益结果调参。

## 4. OrderIntent 生成语义

执行者应实现一个确定性 builder：

```text
scripts/build_tw_policy_mtrc2_s_same_signal_order_intent.py
```

核心逻辑：

```text
1. 读取 MTRC1D signals.csv；
2. 对每个 signal_date，按 candidate_rank <= 50 形成 buy universe；
3. buy universe 内按 buy_score desc 排序，tie-breaker 为 full_qlib_rank asc、instrument asc；
4. 维护模拟持仓状态，仅用于决定 hold/sell/buy 意图，不得输出数量、权重、现金或成交；
5. 若持仓 instrument 跌出 qlib top50，使用 candidate_rank/full_qlib_rank 边界选出最多 1 个 sell intent；
6. 若当日卖出后持仓数低于 target_holding_count，或初始建仓阶段未满 10 支，则在 top50 buy universe 中选出最多 1 个未持有标的生成 buy intent；
7. 每日 buy intent 数 <= 1，每日 sell intent 数 <= 1；
8. 可输出 hold/skip 审计意图，但不得让审计行引入 replay/交易字段。
```

允许使用持仓状态的目的是复现策略意图序列；该持仓状态不是真实组合账本，不得包含成本、现金、NAV、PnL、数量或成交价。

## 5. 允许输出

输出目录：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_s_same_signal_order_intent_build/
```

允许生成：

```text
manifest.json
order_intents.csv
schema.json
strategy_decision_audit.csv
non_top50_buy_validator_report.json
candidate_parameter_audit.csv
signal_lineage_audit.csv
forbidden_field_audit.csv
forbidden_action_audit.json
old_mtr2r_reuse_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD_REVIEW_CN.md
```

builder 只能写 MTRC2_S 输出目录和 MTRC2_S 执行报告，不得写 MTRC1D/MTRC2_R 产物，不得写 registry、configs、provider、latest、frontend、API、Agent、daily 或 production 目录。

## 6. order_intents.csv 必需字段

`order_intents.csv` 必须至少包含：

```text
signal_date
instrument
intent_action
intent_reason
strategy_rule
candidate_rank
buy_rank
full_qlib_rank
max_buy_count
max_sell_count
model_name
signal_artifact
```

建议审计字段：

```text
current_holding_flag
target_holding_count
candidate_k
tie_breaker
diagnostic_only
candidate_id
mechanism
rank_buffer
readonly_only
simulation_only
production_allowed
```

所有日期必须来自输入 signal 的 `date` / `signal_date` 语义；不得读取未来价格、未来收益、label、replay return 或成交结果。

## 7. hard validator

MTRC2_S validator 必须 hard fail：

```text
signal_artifact_equals_mtrc1d_broad
candidate_id_equals_M2_hold_rank_buffer_100
mechanism_equals_hold_rank_buffer
rank_buffer_equals_100
strategy_rule_equals_mechanism_transfer_top50_cost_aware_v1
target_holding_count_equals_10
candidate_k_equals_50
required_order_intent_fields_present
daily_buy_count_lte_1
daily_sell_count_lte_1
buy_candidate_rank_lte_50
buy_score_present_only_for_top50_buy_candidates
non_top50_buy_intent_count_equals_0
full_qlib_rank_used_for_sell_boundary
no_execution_price_cash_nav_fee_tax_quantity_target_fields
no_future_label_or_future_return_fields
old_mtr2r_order_intent_not_reused
readonly_simulation_diagnostic_only
production_allowed_false
negative_sample_non_top50_buy_fails_or_documented
```

其中 negative sample 可以用独立 validator 逻辑证明：若手工构造一行 `intent_action=buy` 且 `candidate_rank > 50`，validator 必须拒绝；如果不写入负样本文件，也必须在 `validator_report.json` 中记录该逻辑检查。

## 8. 禁止字段

`order_intents.csv`、schema、audit、manifest 中不得把下列字段作为策略输出或执行语义：

```text
execution_date
execution_price
execution_quantity
quantity
quantity_to_buy
quantity_to_sell
shares
lots
target_position
target_weight
allocation_weight
commission
fee
tax
cash
cash_after
nav
equity
daily_return
realized_pnl
unrealized_pnl
replay_return
broker
broker_order_id
order_id
quick_trade
provider_publish_status
accepted_latest_status
future_return_*
future_excess_return_*
forward_return_*
label_*
ltr_relevance_label
```

如果 audit 文件需要记录“禁止项检查结果”，只能以检查名或 pass/fail 状态出现，不得引入可被下游误解为交易指令的字段。

## 9. 明确禁止动作

MTRC2_S 禁止：

```text
训练模型
调参
模型 inference
重新计算 LTR score
生成或修改 ModelSignalArtifact
选择 price store
生成 ReplayResultArtifact
生成 ledger
运行收益 replay
计算收益、回撤、集中度、rolling window 或 risk-off 诊断
新增策略候选
修改 M2_hold_rank_buffer_100 参数
修改 strategy dependency YAML 或 registry/default
复用旧 MTR2_R/E3 OrderIntent 作为本阶段输出
修改 production/default/latest/provider/frontend/API/Agent/daily
provider refresh / publish
accepted latest switch
monitor config / scan / alerts write
broker / quick-trade / real order
target_weight / target_position / quantity instruction
解除 MTR5 clean_extended_lineage_found=false blocker
宣称 production readiness
```

## 10. PASS / FAIL 标准

PASS 条件：

```text
1. 生成完整 MTRC2_S OrderIntentArtifact；
2. manifest 明确 readonly_only=true、simulation_only=true、diagnostic_only=true、production_allowed=false；
3. signal_artifact 严格等于 MTRC1D broad signal manifest；
4. candidate/parameter freeze 全部通过；
5. non_top50_buy_intent_count = 0；
6. 每日 buy/sell 意图数不超过 1/1；
7. 必需字段完整且 forbidden fields 缺失；
8. old_mtr2r_reuse_audit 明确 same_signal=false 的旧产物未被复用；
9. 未出现 replay、ledger、收益诊断、生产接入或交易动作；
10. 执行报告完整列出证据和 forbidden actions audit。
```

FAIL / STOP 条件：

```text
输入 MTRC1D signal 缺失或 validator 不通过；
MTRC2_R 合同缺失；
无法基于标准字段构建 OrderIntent；
任何 buy intent 的 candidate_rank > 50；
任何日期 buy/sell 数超过 1/1；
输出包含成交、现金、NAV、PnL、broker、target、quantity 字段；
旧 MTR2_R/E3 OrderIntent 被复用为本阶段产物；
执行者需要 replay、price store 或收益结果才能继续；
发现必须修改默认策略、registry、provider/latest、frontend/API/Agent/daily 或生产链路。
```

## 11. 审查者 audit brief

审查者必须独立检查：

```text
1. MTRC2_S 输出文件是否只在授权目录内；
2. builder 是否只写 MTRC2_S 输出和执行报告；
3. order_intents.csv 必需字段、action 值域、每日 buy/sell 上限；
4. 所有 buy candidate_rank <= 50，non_top50_buy_intent_count=0；
5. manifest / signal_lineage_audit 的 signal_artifact 是否严格等于 MTRC1D manifest；
6. candidate_parameter_audit 是否冻结 M2_hold_rank_buffer_100 / rank_buffer=100；
7. forbidden_field_audit 是否覆盖 OrderIntent 合同禁止字段；
8. old_mtr2r_reuse_audit 是否证明旧产物未复用；
9. 是否无 ReplayResult、ledger、price store selection、收益结论、production readiness；
10. dirty worktree 中是否有本阶段无关修改被误归因。
```

审查 verdict 只能是：

```text
PASS_READY_FOR_MTRC2_T_SAME_SIGNAL_REPLAY_INPUT_BUILD_CONTRACT
PASS_WITH_CONDITIONS_READY_FOR_MTRC2_T_AFTER_NAMED_FIXES
FAIL_NEEDS_MTRC2_S_REPAIR
STOP_COORDINATOR_DECISION_REQUIRED
```

即使 PASS，也只能放行到 MTRC2_T 的 replay input/build contract；不得直接进入 replay、MTRC3 diagnostic 或 production readiness。

## 12. 执行命令

```text
请执行 MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD。
只生成 readonly/simulation-only/diagnostic-only 的 same-signal OrderIntentArtifact、validator/audit/report。
不得 replay、不得 ledger、不得 price store selection、不得收益诊断、不得生产接入、不得交易字段或 target/quantity 字段。
```
