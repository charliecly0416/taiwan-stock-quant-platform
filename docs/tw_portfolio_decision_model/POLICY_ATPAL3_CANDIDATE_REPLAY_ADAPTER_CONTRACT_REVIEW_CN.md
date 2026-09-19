---
created_at: 2026-06-23
status: pass_ready_for_atpal4_work_doc
phase_reviewed: ATPAL3_CANDIDATE_REPLAY_ADAPTER_CONTRACT
mainline_doc: docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_ATPAL3_CANDIDATE_REPLAY_ADAPTER_CONTRACT_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_ATPAL3_CANDIDATE_REPLAY_ADAPTER_CONTRACT_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal3_candidate_adapter_contract
reviewer_role: independent_reviewer
atpal3_passed: true
atpal4_work_doc_authorized: true
candidate_replay_authorized_in_atpal3: false
strategy_experiment_authorized: false
rule_selection_authorized: false
threshold_selection_authorized: false
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# ATPAL3 Candidate Replay Adapter Contract 审查意见

## 1. Verdict

审查结论：

```text
PASS_READY_FOR_ATPAL4_WORK_DOC
```

ATPAL3 已按主线和工作文档完成 future candidate replay adapter contract。产物只定义合同、字段映射、delta 口径和 future concentration gate 输入，没有运行 candidate replay，没有产出 candidate performance result，没有判断候选策略通过，也没有选择规则或阈值。

因此允许进入 ATPAL4，但 ATPAL4 只能对既有 FPA4 失败候选做 PnL attribution backfill diagnostic，不得 repair FPA4，不得改变 FPA4 失败结论。

## 2. Findings

### Critical

无 blocking finding。

### High

1. ATPAL3 必需产物齐全：

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

2. `validator_report.json` 通过：

```text
ok = true
status = PASS_ATPAL3_CANDIDATE_REPLAY_ADAPTER_CONTRACT_READY_FOR_REVIEW
failed_count = 0
final_recommendation = READY_FOR_REVIEWER_TO_CONSIDER_ATPAL4_WORK_DOC
candidate_replay_run = false
strategy_experiment_run = false
rule_selection_run = false
threshold_selection_run = false
strict_test_used = false
model_training_run = false
production_allowed = false
```

3. `candidate_replay_adapter_contract.md` 明确 ATPAL3 只定义 adapter contract：

```text
does not run any candidate replay
does not produce candidate performance results
does not judge whether a candidate strategy passes
```

4. `candidate_concentration_gate_contract.csv` 覆盖 ATPAL2 要求的 concentration metrics，并明确：

```text
pass_fail_allowed_in_atpal3 = False
threshold_selection_allowed = False
```

覆盖指标包括：

```text
top1_symbol_contribution_share
top3_symbol_contribution_share
top1_date_contribution_share
top5_date_contribution_share
top1_symbol_date_contribution_share
top10_symbol_date_contribution_share
contribution_hhi
positive_contribution_symbol_count
negative_contribution_symbol_count
top_abs_trade_share
top_abs_lifecycle_share
fee_tax_share_of_total_abs_contribution
fee_tax_share_of_trade_notional
turnover_proxy
top_symbol_turnover_share
top_date_turnover_share
```

5. `candidate_vs_baseline_delta_contract.csv` 把 delta 字段限定为 diagnostic attribution label，且：

```text
diagnostic_only = True
not_rule_feature = True
```

6. `required_candidate_replay_fields.csv` 对 PnL attribution 字段保持边界：

```text
realized_pnl_after_fee_tax:
  attribution_label_only = True
  not_rule_feature = True

unrealized_pnl_change:
  attribution_label_only = True
  not_rule_feature = True

net_symbol_date_contribution:
  attribution_label_only = True
  not_rule_feature = True
```

7. `forbidden_consumer_audit.csv` 显示 forbidden consumer failed rows = 0。

### Medium

1. `required_candidate_replay_fields.csv` 中部分非 PnL 诊断字段 `not_rule_feature=False`，例如 `split`、`strategy_rule`、`candidate_id`、`action_trace_id`。

这不阻塞 ATPAL3，因为这些字段是 linkage/context 口径，不是 PnL attribution label。后续若进入真正 candidate replay，应由执行文档明确哪些 context 字段允许作为策略输入，哪些只用于审计。

2. `candidate_concentration_gate_contract.csv` 的 `direction` 已给出 future gate 的方向性描述，例如 `lower_or_not_worse_than_baseline`。

该描述仍属于合同设计，不是阈值选择，也不是候选 pass/fail。后续执行者不得把这些方向描述解释为 ATPAL3 已经设定通过阈值。

### Low

1. ATPAL3 执行报告偏摘要化，但合同 CSV 和 validator 证据足够，且产物均可独立审计。

## 3. Mainline Compliance

| Requirement | Review |
|---|---|
| 只定义 candidate replay adapter contract | pass |
| 不运行候选策略 | pass |
| 不运行 candidate replay | pass |
| 不输出 candidate performance result | pass |
| 不判断候选策略通过 | pass |
| 不选择规则或阈值 | pass |
| 不使用 strict_test | pass |
| 不训练模型 | pass |
| 不触碰生产链路 | pass |
| 定义 candidate_id mapping | pass |
| 定义 candidate-vs-baseline delta contract | pass |
| 定义 candidate concentration gate contract | pass |
| 定义 required candidate replay fields | pass |
| forbidden consumer audit | pass |

## 4. Evidence Checked

审查了执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL3_CANDIDATE_REPLAY_ADAPTER_CONTRACT_EXECUTION_REPORT_CN.md
```

审查了 ATPAL3 产物目录：

```text
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal3_candidate_adapter_contract/
```

重点核对：

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

审查了生成脚本：

```text
scripts/build_tw_policy_atpal3_candidate_adapter_contract.py
```

脚本语法检查：

```text
python -m py_compile scripts/build_tw_policy_atpal3_candidate_adapter_contract.py
```

结果：通过。

## 5. Missing Evidence Or Open Questions

ATPAL3 无需 repair。

下一步 ATPAL4 只能解释既有 FPA4 失败候选，不得新增候选、不得重跑规则搜索、不得调阈值、不得改变 FPA4 失败结论。

## 6. Forbidden Actions Audit

审查未发现越权：

```text
candidate_replay = false
candidate_performance_result = false
candidate_pass_fail_judgement = false
strategy_experiment = false
rule_selection = false
threshold_selection = false
validation_mining = false
strict_test = false
model_training = false
production_strategy_switch = false
OrderIntent output = false
target_weight = false
target_position = false
quantity_instruction = false
broker_order = false
quick_trade = false
provider_publish = false
accepted_latest_switch = false
monitor_write = false
frontend_default_switch = false
Agent_recommendation = false
```

## 7. Next Work Document

下一步进入 ATPAL4：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL4_FPA4_BACKFILL_DIAGNOSTIC_WORK_CN.md
```

ATPAL4 只允许对既有 FPA4 失败候选做 PnL attribution backfill diagnostic。该阶段不是 FPA4 repair，不允许改变 `STOP_NO_PREDECLARED_RULE_SANITY_PASS` 结论。
