# POLICY_MTR2_QLIB_LTR_LINEAGE_REPAIR_AND_TRANSFER_REPLAY_WORK_CN

生成日期：2026-06-28

## 1. 任务定位

本阶段属于：

```text
POLICY_MTR_MECHANISM_TRANSFER_TO_BASELINE / MTR2
```

MTR2 的目标不是开发新模型，也不是继续搜索 policy，而是：

```text
先修复产品长 ID qlib+LTR 标准 ModelSignalArtifact lineage，
再把 MTR1 已通过的 hold buffer 机制迁移到 qlib+LTR baseline 上做 readonly replay。
```

必须使用的主线文档：

```text
docs/tw_portfolio_decision_model/POLICY_MTR_MECHANISM_TRANSFER_TO_BASELINE_MAINLINE_CN.md
```

必须参考的上一阶段结论：

```text
docs/tw_portfolio_decision_model/POLICY_MTR0_CONTRACT_AND_BASELINE_PARITY_FEASIBILITY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR1_QLIB_ONLY_ORDER_INTENT_PARITY_AND_MECHANISM_REPLAY_REVIEW_CN.md
```

MTR1 已证明 qlib-only 下唯一通过 gate 的候选是：

```text
M2_hold_rank_buffer_100
```

关键指标：

```text
baseline net_total_return_after_fee_tax = 11.82112201
M2_hold_rank_buffer_100 net_total_return_after_fee_tax = 13.71864776
turnover_reduction_vs_baseline = 0.40159028
fee_tax_reduction_vs_baseline = 0.36956596
cash_no_trade_day_count = 0
```

MTR2 必须验证该机制迁移到当前产品主线 qlib+LTR 后是否仍有价值。

## 2. 强制合同

执行者和审查者必须读取：

```text
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

允许使用上一阶段脚本作为模板：

```text
scripts/run_tw_policy_mtr1_qlib_only_order_intent_parity_and_mechanism_replay.py
```

但 MTR2 不得修改 MTR1 产物；应新增 MTR2 脚本和 MTR2 输出目录。

## 3. 输入与 blocker

MTR2 指定的产品长 ID 标准信号路径是：

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/r1_legacy_signal_adapter_20260616/manifest.json
```

MTR0/MTR1 已判定该 manifest 缺失，因此 MTR2 第一步必须修复该 lineage。

现有短 ID artifact：

```text
data_tw/artifacts/signals/e4_frozen_qlib_2023_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json
```

该短 ID 是旧中间命名，不能直接作为 MTR2 输入绕过 blocker。若执行者判断长 ID artifact 可由短 ID 标准 artifact 同源派生，必须满足以下全部条件：

```text
1. 新增长 ID 目录，而不是把策略改去读短 ID；
2. manifest.artifact_name 与 manifest.model_name 必须是 e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025；
3. model_family 必须为 ltr；
4. candidate_rank / full_qlib_rank 仍来自底座 qlib；
5. buy_score / raw_score 仍来自 LTR rerank score；
6. signals.csv row count、date/instrument key、score values、rank values 必须与同源短 ID或上游 replay-ready artifact 可审计一致；
7. input_hashes 必须记录同源输入；
8. legacy_mapping_audit.csv 必须说明 candidate_rank、buy_score、raw_score、score_rank、full_qlib_rank 的映射；
9. forbidden_field_audit.csv 必须证明 future return、label、realized pnl、execution、broker、target 字段未进入标准信号；
10. manifest 必须声明 production_allowed=false、no_provider_publish、no_accepted_latest_switch、no_default_switch；
11. 不得修改 configs/tw_product_artifact_registry.yaml、configs/tw_replay_window_policy.yaml 或 frontend/API/default 指针。
```

如果无法满足上述条件，执行者必须 STOP，并写明 lineage blocker，不能继续 replay。

## 4. 输出目录

MTR2 输出目录：

```text
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_qlib_ltr_lineage_repair_and_transfer_replay/
```

新增或修复的长 ID ModelSignalArtifact 目录：

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/r1_legacy_signal_adapter_20260616/
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTR2_QLIB_LTR_LINEAGE_REPAIR_AND_TRANSFER_REPLAY_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTR2_QLIB_LTR_LINEAGE_REPAIR_AND_TRANSFER_REPLAY_REVIEW_CN.md
```

## 5. MTR2-A: qlib+LTR 标准 lineage repair

执行者必须先产出：

```text
manifest.json
signals.csv
schema.json
coverage_audit.csv
forbidden_field_audit.csv
legacy_mapping_audit.csv
```

并在 MTR2 输出目录中额外产出：

```text
lineage_repair_audit.csv
long_id_short_id_equivalence_audit.csv
input_signal_lineage_audit.csv
model_signal_validator_report.json
```

最低检查项：

```text
artifact_type = model_signal
artifact_name = e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
model_name = e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
model_family = ltr
quality_status = pass
capabilities.core_signal_v1 = true
capabilities.candidate_boundary = qlib_top50
capabilities.buy_ordering = buy_score_desc
capabilities.full_rank_exit = full_qlib_rank
capabilities.supports_ltr_rerank = true
duplicate_key_count = 0
```

signals.csv 必须包含 core fields：

```text
date
instrument
model_name
model_family
candidate_rank
buy_score
raw_score
score_rank
full_qlib_rank
signal_asof
available_at
source_artifact
source_model_artifact
source_feature_artifact
```

LTR 语义必须保持：

```text
candidate_rank <- base qlib rank
full_qlib_rank <- base qlib full rank
buy_score <- orthogonal LTR rerank score
raw_score <- orthogonal LTR rerank score
score_rank <- same-day descending rank of buy_score with stable tie-breaker
```

不得让 LTR 改 qlib top50 candidate universe 或 sell boundary。

## 6. MTR2-B: baseline parity on qlib+LTR

只有 MTR2-A 通过后，才允许执行 MTR2-B。

必须先在 qlib+LTR 长 ID 标准信号上跑 baseline parity：

```text
baseline_top50_exit_one_worst_sell
M0_baseline_parity
```

产物：

```text
order_intent_artifact_index.csv
order_intent_validator_report.json
baseline_order_intent_parity_audit.csv
replay_artifact_index.csv
replay_validator_report.json
baseline_replay_parity_audit.csv
```

通过要求：

```text
OrderIntent parity = pass
Replay metric parity = pass
核心 replay metrics delta = 0 或在明确小数舍入容忍内
```

baseline parity 不通过时必须 STOP 或进入 repair，不得解释为机制失败。

## 7. MTR2-C: transfer replay candidate

MTR2 主候选只允许：

```text
M2_hold_rank_buffer_100
```

允许作为审计对照：

```text
M0_baseline_parity
M2_hold_rank_buffer_75
```

不得新增后验候选，不得调参搜索。M1/M3/M4/C1-C3 可以不重跑；若执行者认为需要重跑，只能作为 supplemental audit，不能改变 MTR2 主结论。

必须输出：

```text
mechanism_candidate_contract.csv
mechanism_replay_comparison.csv
turnover_cost_audit.csv
holding_overlap_audit.csv
rank_overlap_audit.csv
cash_no_trade_audit.csv
forbidden_field_audit.csv
forbidden_action_audit.csv
```

主要 gate：

```text
small_tolerance = 0.02
material_turnover_reduction = at least 20% lower than qlib+LTR baseline average_turnover
material_cost_reduction = at least 20% lower than qlib+LTR baseline total_fee_plus_tax
max_drawdown_worse_tolerance = 0.05 absolute
cash_no_trade_degenerate_threshold = >10% replay days no valid holding/action due to gating
```

MTR2 通过条件：

```text
M2_hold_rank_buffer_100 net_total_return_after_fee_tax >= qlib+LTR baseline net_total_return_after_fee_tax - 0.02
M2_hold_rank_buffer_100 average_turnover <= qlib+LTR baseline average_turnover * 0.8
M2_hold_rank_buffer_100 total_fee_plus_tax <= qlib+LTR baseline total_fee_plus_tax * 0.8
M2_hold_rank_buffer_100 max_drawdown >= qlib+LTR baseline max_drawdown - 0.05
cash/no-trade ratio <= 0.10
```

若 net 提升但 drawdown 明显恶化，结论最多为 `PASS_WITH_RISK_CONDITION`，不得直接建议生产。

若 turnover/cost 下降但 net 明显低于 baseline，则结论为 `FAIL_NEEDS_REPAIR_OR_CLOSE`，不得因成本下降单独通过。

## 8. Forbidden actions

MTR2 全阶段禁止：

```text
训练模型
调参
根据 replay return 后验筛候选
读取 LTR private artifact 作为策略输入
把短 ID artifact 直接当 MTR2 输入绕过长 ID blocker
读取 future return / label / realized pnl / replay return 作为策略输入
读取 next_open / next_close / execution_price 作为策略输入
修改 replay engine 让其读取策略私有字段
修改 production/default/frontend/API/Agent/daily/provider/latest
provider publish
accepted latest switch
monitor scan/config save/alerts write
broker / quick-trade / real order
输出 target_weight / target_position / quantity instruction
```

注意：ReplayResult 输出侧可以有 `quantity`、`execution_price`、`commission`、`tax`、`cash_after` 等合同字段；这些只能是 replay 执行结果，不能进入策略输入或 OrderIntent。

## 9. Stop conditions

出现任一情况必须停止：

```text
长 ID ModelSignalArtifact 无法合规生成；
无法证明长 ID 与上游 LTR/短 ID 同源；
candidate_rank/full_qlib_rank 不是底座 qlib rank；
buy_score 不是 LTR rerank score；
signals.csv core fields 不完整；
forbidden fields 泄漏；
baseline OrderIntent parity 不通过；
baseline Replay parity 不通过；
执行需要改生产默认、frontend/API、daily/provider/latest；
执行需要 target_weight/target_position 或真实订单；
执行需要用 future/replay return 决策。
```

## 10. 执行报告必须包含

执行报告必须按以下结构：

```text
1. Scope
2. Documents / Contracts / Skills Read
3. MTR2-A Lineage Repair
4. MTR2-B Baseline Parity
5. MTR2-C Transfer Replay
6. Candidate Metrics
7. Validator / Audit Evidence
8. Forbidden Actions Audit
9. Files Changed
10. Verdict And Recommendation
```

若 MTR2-A 阻断，不需要跑 MTR2-B/C，但报告必须清楚写出 blocker。

## 11. 审查者重点

审查者必须独立检查：

```text
1. 是否真的新增/修复产品长 ID ModelSignalArtifact；
2. 是否没有把短 ID artifact 直接作为 MTR2 输入；
3. 长 ID artifact 是否保持 LTR 语义；
4. baseline parity 是否先通过；
5. M2_hold_rank_buffer_100 是否严格来自 MTR1 通过候选；
6. 是否没有后验扩参；
7. 是否没有 production/default/frontend/API/Agent/daily/provider/latest 改动；
8. replay 是否只消费 OrderIntentArtifact、PriceStore、ExecutionConfig、InitialPortfolioState；
9. 通过结论是否同时看 net、turnover、fee/tax、drawdown、cash/no-trade。
```

审查 verdict 只能是：

```text
PASS_MTR2_QLIB_LTR_WITH_TRANSFER_CANDIDATE
PASS_MTR2_WITH_RISK_CONDITION
FAIL_NEEDS_REPAIR
STOP_LINEAGE_BLOCKED
STOP_SCOPE_VIOLATION
```

## 12. 下一步

若 MTR2 通过：

```text
进入 MTR3 robustness / window / regime attribution。
```

若 MTR2 因 lineage 阻断：

```text
先修 ModelSignalArtifact lineage，不讨论策略效果。
```

若 MTR2 baseline parity 失败：

```text
先修 OrderIntent / replay parity，不讨论机制效果。
```

若 MTR2 机制失败：

```text
关闭 qlib+LTR transfer 或回到 qlib-only research-only closure，不进入生产化。
```
