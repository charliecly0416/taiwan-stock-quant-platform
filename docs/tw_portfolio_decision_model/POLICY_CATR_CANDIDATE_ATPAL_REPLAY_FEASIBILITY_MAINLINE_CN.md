---
created_at: 2026-06-23
status: coordinator_mainline
route: CATR_CANDIDATE_ATPAL_REPLAY_FEASIBILITY
previous_closure: docs/tw_portfolio_decision_model/POLICY_ATPAL_FINAL_CLOSURE_REVIEW_CN.md
previous_opinion: docs/tw_portfolio_decision_model/POLICY_ATPAL_FINAL_COORDINATOR_NEXT_STEP_OPINION_CN.md
purpose: candidate_atpal_replay_feasibility_not_strategy_repair
candidate_replay_authorized_initially: false
candidate_pass_fail_authorized: false
strategy_search_authorized: false
threshold_selection_authorized: false
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity_instruction: true
---

# CATR Candidate ATPAL Replay Feasibility 主线

## 1. 统筹结论

ATPAL 主线已经闭环：

```text
baseline ATPAL ledger 已建立；
baseline contribution / concentration audit 已建立；
future candidate replay adapter contract 已建立；
既有 FPA4 失败候选已做 summary-level backfill；
但历史 FPA4 candidate 仍缺真实 candidate trade-level / symbol-date ATPAL ledger。
```

ATPAL4 明确留下缺口：

```text
candidate_symbol_date_available = false
candidate_symbol_date_backfill_status = unavailable_requires_candidate_atpal_replay
```

因此若要继续，不应直接做策略搜索，而应先开一个很窄的新支线：

```text
CATR = Candidate ATPAL Replay Feasibility
```

CATR 的目的不是让 FPA4 通过，也不是找新策略，而是判断：

```text
能否按照 ATPAL3 adapter contract，
为既有 FPA4 失败候选生成真正的 candidate trade / position / symbol-date / action-context ledger。
```

## 2. 目标

CATR 要回答：

```text
既有 FPA4 predeclared candidates 是否具备足够字段和 replay lineage，
可以被合同化重放为 ATPAL-compatible candidate ledgers？
```

若可行，后续才考虑：

```text
CATR1 Candidate ATPAL Replay Builder
```

若不可行，则应关闭 candidate backfill 路线，进入外部 closure。

## 3. 非目标

CATR 不授权：

```text
1. 新策略候选。
2. 新阈值或阈值选择。
3. validation mining。
4. candidate pass/fail judgement。
5. FPA4 repair 或 FPA4 结论变更。
6. strict_test。
7. 模型训练。
8. 生产默认策略切换。
9. provider publish / accepted latest switch。
10. monitor / frontend / Agent 集成。
11. broker / quick-trade / real order。
12. OrderIntent target_weight / target_position / quantity_instruction。
```

CATR0 尤其不授权运行 candidate replay。

## 4. 输入

必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL_FINAL_CLOSURE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_ATPAL_FINAL_COORDINATOR_NEXT_STEP_OPINION_CN.md
docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_FPA4_PREDECLARED_FULL_PATH_RULE_SANITY_REVIEW_CN.md
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal3_candidate_adapter_contract/
data_tw/experiments/full_path_action_diagnostic/fpa4_predeclared_full_path_rule_sanity/
scripts/build_tw_policy_ral_fpa4_predeclared_full_path_rule_sanity.py
scripts/run_tw_policy_action_model_pa1.py
```

## 5. 阶段计划

### CATR0：Candidate Replay Feasibility Contract

目标：

```text
只判断既有 FPA4 candidates 是否可被 ATPAL-compatible replay。
```

输出目录：

```text
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/
```

必须输出：

```text
manifest.json
source_artifact_manifest.json
fpa4_candidate_inventory.csv
candidate_replay_required_field_audit.csv
candidate_action_lineage_feasibility_audit.csv
candidate_atpal_output_contract_audit.csv
candidate_replay_blocker_audit.csv
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

CATR0 不允许输出：

```text
candidate trade ledger；
candidate symbol-date ledger；
candidate replay result；
candidate pass/fail；
new strategy result。
```

### CATR1：Candidate ATPAL Replay Builder

只有 CATR0 通过后，且统筹另行授权，才允许进入。

目标：

```text
为既有 FPA4 candidates 生成 candidate ATPAL ledgers。
```

CATR1 仍不得改变 FPA4 结论，除非后续另有新主线明确授权重新审查。

## 6. CATR0 通过条件

CATR0 通过仅表示：

```text
可写 CATR1 工作文档。
```

通过条件：

```text
1. FPA4 candidate inventory 完整，候选和阈值与原 FPA4 一致。
2. 可定位 candidate rule logic 或 replay decisions 的生成逻辑。
3. 可复用 PA1 replay engine 或等价 readonly replay path。
4. 可按 ATPAL3 contract 输出 candidate_id / action_trace_id / split / date / instrument linkage。
5. 可输出 trade-level、position-lifecycle、position-day、symbol-date、action-context 五类 candidate ledger。
6. 不需要 strict_test。
7. 不需要新策略候选或新阈值。
8. 不需要 target_weight / target_position / quantity_instruction / broker order。
9. 不需要生产链路。
```

## 7. CATR0 失败条件

任一情况应 STOP：

```text
1. FPA4 candidate logic 无法复现。
2. 缺少必要 action trace 或 decision lineage。
3. 只能通过 summary 反推 candidate PnL，无法生成真实 trade/symbol-date ledger。
4. 需要未来收益作为 replay 决策输入。
5. 需要新阈值选择或 validation mining。
6. 需要 strict_test。
7. 需要生产订单语义。
8. 输出字段混入 target/quantity_instruction/broker/OrderIntent。
```

## 8. 首轮指令

审查者/执行者均不得扩展范围。

第一轮执行文档：

```text
docs/tw_portfolio_decision_model/POLICY_CATR0_CANDIDATE_REPLAY_FEASIBILITY_CONTRACT_WORK_CN.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_CATR0_CANDIDATE_REPLAY_FEASIBILITY_CONTRACT_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_CATR0_CANDIDATE_REPLAY_FEASIBILITY_CONTRACT_REVIEW_CN.md
```

## 9. 一句话

```text
CATR0 只判断既有 FPA4 候选是否能合同化生成 candidate ATPAL ledger；
不运行候选 replay，不判断策略通过，不改变 FPA4 失败结论。
```
