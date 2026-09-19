# POLICY_MTR2_R_BROAD_FULL_RANK_VISIBILITY_REPAIR_WORK_CN

生成日期：2026-06-28

## 1. 任务定位

本阶段是：

```text
POLICY_MTR_MECHANISM_TRANSFER_TO_BASELINE / MTR2_R
```

MTR2_R 是 MTR2 的 repair，不是新策略搜索。

MTR2 已确认：

```text
lineage_repair: PASS
baseline_order_intent_parity: PASS
baseline_replay_parity: PASS
transfer_candidate_gate: FAIL_NEEDS_REPAIR
```

失败根因：

```text
当前 qlib+LTR 产品长 ID ModelSignalArtifact 每日只有 top50 行。
M2_hold_rank_buffer_75/100 需要判断持仓跌出 top50 后是否仍在 full_qlib_rank <= 75/100。
由于 signals.csv 缺少 51-100/broad universe 行，hold buffer 无法触发，M2 完全退化为 baseline。
```

MTR2_R 目标：

```text
合同化并生成 qlib+LTR broad full-rank visibility，
让策略能合法看到当前持仓在 51-100 的 qlib full rank，
同时严格禁止非 top50 行进入 LTR 买入候选。
```

## 2. 必读文档

执行者与审查者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_MTR_MECHANISM_TRANSFER_TO_BASELINE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR2_QLIB_LTR_LINEAGE_REPAIR_AND_TRANSFER_REPLAY_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR2_QLIB_LTR_LINEAGE_REPAIR_AND_TRANSFER_REPLAY_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR2_QLIB_LTR_LINEAGE_REPAIR_AND_TRANSFER_REPLAY_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md
docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
configs/strategy_dependencies/mechanism_transfer_top50_cost_aware_v1.yaml
```

可参考但不得破坏：

```text
scripts/run_tw_policy_mtr2_qlib_ltr_lineage_repair_and_transfer_replay.py
```

## 3. 输入冻结

现有产品长 ID top50-only qlib+LTR 标准信号：

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/r1_legacy_signal_adapter_20260616/manifest.json
```

允许的 broad qlib full-rank 来源：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv
```

允许的 top50 LTR 来源：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_replay_ready_scores_2026.csv
```

禁止：

```text
训练模型
重算 LTR score
使用 future return / label / realized pnl / replay return
使用非标准 private artifact 作为策略输入
```

## 4. 输出路径

MTR2_R 输出目录：

```text
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/
```

research-only broad signal artifact 路径：

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025_broad_full_rank_mtr2_r/r1_broad_full_rank_visibility_repair_20260628/
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTR2_R_BROAD_FULL_RANK_VISIBILITY_REPAIR_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTR2_R_BROAD_FULL_RANK_VISIBILITY_REPAIR_REVIEW_CN.md
```

## 5. Artifact 设计

MTR2_R 不修改原产品长 ID artifact，而是新增 research-only artifact：

```text
artifact_name = e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025_broad_full_rank_mtr2_r
model_name = e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025_broad_full_rank_mtr2_r
model_family = ltr
production_allowed = false
research_only = true
diagnostic_only = true
not_default_candidate = true
```

该 artifact 的核心语义：

```text
candidate_rank = base qlib broad rank
full_qlib_rank = base qlib broad rank
buy_score = LTR rerank score only for qlib top50 rows
raw_score = LTR rerank score only for qlib top50 rows
score_rank = LTR score rank only for qlib top50 rows
```

对于非 top50 broad 行：

```text
candidate_rank > 50
full_qlib_rank > 50
buy_score 不得用于买入排序
raw_score 不得用于买入排序
score_rank 不得用于买入排序
```

执行者可选择以下两种表示之一：

方案 A：

```text
非 top50 行 buy_score/raw_score/score_rank 为空，并在 schema/manifest/audit 声明策略不得把空值行作为 buy candidate。
```

方案 B：

```text
非 top50 行 buy_score/raw_score 使用 qlib_score_raw，score_rank 使用 qlib rank 派生；
但 manifest 必须声明 ranking_usage: buy ranking only where candidate_rank <= 50 and ltr_top50_flag=true。
```

优先采用方案 A。如果现有 validator 无法接受空值，才允许方案 B。

不论采用 A 或 B，都必须新增或声明审计字段：

```text
ext_ltr_top50_flag
ext_broad_rank_visibility_only
```

字段含义：

```text
ext_ltr_top50_flag = true only for rows with valid LTR top50 buy score
ext_broad_rank_visibility_only = true for rows added only for sell/hold full-rank lookup
```

extension metadata 必须符合 `MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md`：

```text
semantic_role = diagnostic 或 exposure
ranking_allowed = false for ext_broad_rank_visibility_only
allowed_consumers = ["mechanism_transfer_top50_cost_aware_v1"]
required_for_core_replay = false
```

## 6. MTR2_R-A: broad signal builder / validator

执行者必须生成：

```text
manifest.json
signals.csv
schema.json
coverage_audit.csv
forbidden_field_audit.csv
legacy_mapping_audit.csv
```

MTR2_R 输出目录中必须生成：

```text
broad_signal_lineage_audit.csv
broad_signal_coverage_audit.csv
top50_ltr_equivalence_audit.csv
non_top50_buy_forbidden_audit.csv
extension_schema_audit.csv
model_signal_validator_report.json
forbidden_field_audit.csv
forbidden_action_audit.csv
```

最低 gate：

```text
row_count > MTR2 top50-only row_count
daily_row_count_min >= 100
date range 与 MTR2 top50-only replay window 对齐
top50 rows 与 MTR2 long ID top50-only artifact 的 LTR buy_score/raw_score/score_rank 等价
non_top50 rows candidate_rank > 50
non_top50 rows ext_broad_rank_visibility_only = true
non_top50 rows ext_ltr_top50_flag = false
non_top50 rows 不得作为 buy candidate
forbidden fields absent
production_allowed = false
no_provider_publish = true
no_accepted_latest_switch = true
no_default_switch = true
```

如果无法生成 broad signal 或无法保证非 top50 不参与买入，必须 STOP，不得跑 replay。

## 7. MTR2_R-B: baseline parity with broad signal

只有 MTR2_R-A 通过后，才允许跑 baseline parity。

baseline parity 必须验证：

```text
baseline_top50_exit_one_worst_sell
M0_baseline_parity
```

和 MTR2 top50-only qlib+LTR baseline 相比，baseline 买卖路径应保持一致或差异可解释为 broad rank visibility bug repair。

必须输出：

```text
order_intent_artifact_index.csv
order_intent_validator_report.json
baseline_order_intent_parity_audit.csv
replay_artifact_index.csv
replay_validator_report.json
baseline_replay_parity_audit.csv
top50_only_vs_broad_baseline_audit.csv
```

通过要求：

```text
OrderIntent parity = pass
Replay metric parity = pass
非 top50 broad 行未被 baseline 买入
```

如果 baseline parity 不通过，必须 STOP 或 repair，不得讨论 M2。

## 8. MTR2_R-C: M2 transfer replay rerun

主候选：

```text
M2_hold_rank_buffer_100
```

允许对照：

```text
M0_baseline_parity
M2_hold_rank_buffer_75
```

禁止新增参数或候选。

必须输出：

```text
mechanism_candidate_contract.csv
mechanism_replay_comparison.csv
turnover_cost_audit.csv
holding_overlap_audit.csv
rank_overlap_audit.csv
cash_no_trade_audit.csv
hold_buffer_trigger_audit.csv
non_top50_buy_attempt_audit.csv
forbidden_field_audit.csv
forbidden_action_audit.csv
```

新增 `hold_buffer_trigger_audit.csv` 至少包含：

```text
date
instrument
candidate_id
previous_holding_flag
candidate_rank
full_qlib_rank
baseline_action
m2_action
hold_buffer
buffer_condition_triggered
details
```

新增 `non_top50_buy_attempt_audit.csv` 必须证明：

```text
non_top50 buy intent count = 0
```

## 9. MTR2_R 通过条件

主 gate：

```text
small_tolerance = 0.02
material_turnover_reduction = at least 20% lower than broad qlib+LTR baseline average_turnover
material_cost_reduction = at least 20% lower than broad qlib+LTR baseline total_fee_plus_tax
max_drawdown_worse_tolerance = 0.05 absolute
cash_no_trade_degenerate_threshold = >10% replay days no valid holding/action due to gating
```

MTR2_R 通过必须满足：

```text
M2_hold_rank_buffer_100 net_total_return_after_fee_tax >= baseline net_total_return_after_fee_tax - 0.02
M2_hold_rank_buffer_100 average_turnover <= baseline average_turnover * 0.8
M2_hold_rank_buffer_100 total_fee_plus_tax <= baseline total_fee_plus_tax * 0.8
M2_hold_rank_buffer_100 max_drawdown >= baseline max_drawdown - 0.05
cash/no-trade ratio <= 0.10
hold_buffer_trigger_count > 0
non_top50_buy_intent_count = 0
```

如果 `hold_buffer_trigger_count = 0`，则说明 repair 后机制仍未被触发，不能通过。

如果 turnover/cost 降低但 net 明显下降，则不能通过。

## 10. Forbidden actions

全阶段禁止：

```text
训练模型
调参
后验扩候选
让非 top50 broad rows 参与买入候选
读取 future return / label / realized pnl / replay return 作为策略输入
读取 next_open / next_close / execution_price 作为策略输入
修改生产默认、frontend/API、Agent、daily/provider/latest
provider publish
accepted latest switch
monitor scan/config save/alerts write
broker / quick-trade / real order
target_weight / target_position / quantity instruction
```

ReplayResult 输出侧允许合同字段 `quantity`、`execution_price`、`commission`、`tax`、`cash_after`，但这些不得进入 StrategyRule 或 OrderIntent。

## 11. Stop conditions

必须停止：

```text
broad qlib rank 来源缺失
top50 LTR score 与 MTR2 top50-only artifact 不一致
非 top50 行被用于买入排序
baseline parity 无法复现
hold buffer 实现需要修改 replay engine 读取私有字段
需要 target_weight/target_position/quantity instruction
需要 production/default/frontend/API/Agent/daily/provider/latest 改动
需要 future/replay return 作为判断
```

## 12. 执行报告结构

执行报告必须包含：

```text
1. Verdict
2. Scope
3. Documents / Contracts Read
4. MTR2_R-A Broad Signal Builder / Validator
5. MTR2_R-B Baseline Parity
6. MTR2_R-C M2 Transfer Replay
7. Candidate Metrics
8. Hold Buffer Trigger Audit
9. Non-top50 Buy Audit
10. Forbidden Actions Audit
11. Files Changed
12. Recommendation
```

## 13. 审查者重点

审查者必须确认：

```text
1. broad artifact 是 research-only，未替换产品默认长 ID；
2. top50 LTR rows 与 MTR2 top50-only artifact 等价；
3. 51-100/broad 行只用于 full-rank visibility，不参与买入；
4. baseline parity 先通过；
5. M2_hold_rank_buffer_100 触发次数 > 0；
6. non_top50_buy_intent_count = 0；
7. net/turnover/fee-tax/drawdown/cash-no-trade gate 同时审查；
8. 没有 production/default/frontend/API/Agent/daily/provider/latest 改动。
```

允许 verdict：

```text
PASS_MTR2_R_WITH_BROAD_FULL_RANK_TRANSFER_CANDIDATE
PASS_MTR2_R_WITH_RISK_CONDITION
FAIL_NEEDS_REPAIR
STOP_BROAD_SIGNAL_CONTRACT_BLOCKED
STOP_SCOPE_VIOLATION
```

## 14. 下一步

若 MTR2_R 通过：

```text
进入 MTR3 robustness / window / regime attribution。
```

若 MTR2_R 失败但 broad signal 合规：

```text
判断 M2 在 qlib+LTR 2026 YTD 无迁移收益；可关闭 qlib+LTR transfer 或另行授权非 M2 机制。
```

若 MTR2_R 被 broad signal 阻断：

```text
先补 ModelSignal extension / validator 合同，不能讨论 replay 表现。
```
