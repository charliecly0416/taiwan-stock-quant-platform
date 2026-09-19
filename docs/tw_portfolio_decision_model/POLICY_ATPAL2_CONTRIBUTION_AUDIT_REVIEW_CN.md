---
created_at: 2026-06-23
status: pass_ready_for_atpal3_work_doc
phase_reviewed: ATPAL2_CONTRIBUTION_CONCENTRATION_AUDIT
mainline_doc: docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_ATPAL2_CONTRIBUTION_AUDIT_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_ATPAL2_CONTRIBUTION_AUDIT_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit
reviewer_role: independent_reviewer
atpal2_passed: true
atpal3_work_doc_authorized: true
atpal4_authorized: false
candidate_replay_authorized: false
strategy_experiment_authorized: false
rule_selection_authorized: false
threshold_selection_authorized: false
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# ATPAL2 Contribution / Concentration Audit 审查意见

## 1. Verdict

审查结论：

```text
PASS_READY_FOR_ATPAL3_WORK_DOC
```

ATPAL2 已按主线和工作文档完成 baseline contribution / concentration audit。产物来自 ATPAL1-R repaired baseline ledger，覆盖 symbol/date/symbol-date、trade、position lifecycle、fee/tax、turnover 与 future candidate concentration gate design。

本阶段未进入 ATPAL3/4，未运行 candidate replay 或新策略，未选择规则或阈值，未使用 strict_test，未训练模型，未触碰生产链路。

## 2. Findings

### Critical

无 blocking finding。

### High

1. 必需 ATPAL2 产物齐全。

产物目录：

```text
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit/
```

已核对存在：

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
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

2. `validator_report.json` 通过：

```text
ok = true
status = PASS_ATPAL2_CONTRIBUTION_AUDIT_READY_FOR_REVIEW
failed_count = 0
final_recommendation = READY_FOR_REVIEWER_TO_CONSIDER_ATPAL3_WORK_DOC
source_atpal1_root = data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair
```

3. 所有核心 audit 表均覆盖：

```text
split = train, validation, all
```

独立抽查覆盖表：

```text
symbol_contribution_summary.csv
date_contribution_summary.csv
symbol_date_contribution_matrix.csv
top_contributor_audit.csv
trade_pnl_distribution_audit.csv
position_lifecycle_distribution_audit.csv
fee_tax_contribution_audit.csv
turnover_contribution_audit.csv
```

4. top contributor audit 给出了主线要求的 concentration metrics：

```text
train:
  top1_symbol_contribution_share = 0.0554565801
  top3_symbol_contribution_share = 0.1513068307
  top1_date_contribution_share = 0.0081998489
  top5_date_contribution_share = 0.0363180522
  top1_symbol_date_contribution_share = 0.0064477264
  top10_symbol_date_contribution_share = 0.0367614345
  contribution_hhi = 0.022049535

validation:
  top1_symbol_contribution_share = 0.0607301284
  top3_symbol_contribution_share = 0.1629622214
  top1_date_contribution_share = 0.01567772
  top5_date_contribution_share = 0.0738089117
  top1_symbol_date_contribution_share = 0.0108893715
  top10_symbol_date_contribution_share = 0.0723960962
  contribution_hhi = 0.0264257497
```

5. fee/tax 与 turnover 指标保持 ATPAL1-R baseline 口径：

```text
validation fee_tax_total = 146214.73
validation turnover_proxy = 42.18778213
validation trade_count = 436
validation buy_count = 223
validation sell_count = 213
```

这与主线已审计 baseline 事实一致，浮点尾差可接受。

6. `baseline_concentration_gate_design.md` 明确限定为 future candidate gate 设计：

```text
ATPAL2 is a baseline diagnostic audit.
not a strategy pass
not a candidate policy evaluation
not a rule or threshold selection stage
never as a replacement for rolling OOS
never as a way to mine validation results
```

### Medium

1. 执行报告第 3 节称“已输出工作文档要求的 12 个文件”，但实际目录和工作文档要求为 13 个文件。

这是执行报告文字计数错误，不影响产物完整性，也不阻塞通过。后续执行报告应避免这种计数不一致。

2. `turnover_contribution_audit.csv` 的 `all` 行 `average_equity` 与 `turnover_proxy` 为空。

该处理符合脚本逻辑：train/validation 的 turnover_proxy 来自 split-level reconciliation，`all` 没有单一 replay summary 对应值。此项不阻塞 ATPAL2，但 ATPAL3/后续 candidate contract 应明确 candidate-level turnover gate 以 per-split 为主，避免误解 all-level turnover。

### Low

1. `diagnostic_findings.md` 主要摘录 top contributor、trade distribution 和 validator 摘要，内容偏摘要化。

由于完整 CSV 已存在，且 ATPAL2 目标是产出可审计表格，此项不阻塞。

## 3. Mainline Compliance

| Requirement | Review |
|---|---|
| 只执行 ATPAL2 contribution / concentration audit | pass |
| 输入来自 ATPAL1-R repaired baseline ledger | pass |
| 输出 symbol/date/symbol-date contribution | pass |
| 输出 trade PnL distribution | pass |
| 输出 position lifecycle distribution | pass |
| 输出 fee/tax contribution | pass |
| 输出 turnover contribution | pass |
| 输出 baseline concentration gate design | pass |
| 覆盖 train / validation / all | pass |
| 未进入 ATPAL3/4 | pass |
| 未运行 candidate replay | pass |
| 未运行新策略 | pass |
| 未选择规则或阈值 | pass |
| 未使用 strict_test | pass |
| 未训练模型 | pass |
| 未触碰生产链路 | pass |

## 4. Evidence Checked

审查了执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL2_CONTRIBUTION_AUDIT_EXECUTION_REPORT_CN.md
```

审查了 ATPAL2 产物目录：

```text
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit/
```

重点核对：

```text
manifest.json
validator_report.json
forbidden_consumer_audit.csv
top_contributor_audit.csv
symbol_contribution_summary.csv
date_contribution_summary.csv
symbol_date_contribution_matrix.csv
trade_pnl_distribution_audit.csv
position_lifecycle_distribution_audit.csv
fee_tax_contribution_audit.csv
turnover_contribution_audit.csv
baseline_concentration_gate_design.md
diagnostic_findings.md
```

审查了生成脚本：

```text
scripts/build_tw_policy_atpal2_contribution_audit.py
```

脚本语法检查：

```text
python -m py_compile scripts/build_tw_policy_atpal2_contribution_audit.py
```

结果：通过。

## 5. Missing Evidence Or Open Questions

ATPAL2 无需 repair。

下一步应进入 ATPAL3，但 ATPAL3 只能定义 candidate replay adapter contract，不得运行 candidate replay，不得做策略实验。

## 6. Forbidden Actions Audit

`forbidden_consumer_audit.csv` 显示 forbidden consumer failed rows = 0。

审查未发现越权：

```text
candidate_replay_run = false
strategy_experiment_run = false
rule_selection_run = false
threshold_selection_run = false
strict_test_used = false
model_training_run = false
production_allowed = false
OrderIntent output = false
target_weight = false
target_position = false
quantity_instruction = false
broker_order = false
quick_trade = false
```

## 7. Next Work Document

下一步进入 ATPAL3：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL3_CANDIDATE_REPLAY_ADAPTER_CONTRACT_WORK_CN.md
```

ATPAL3 只允许定义 future rule / policy candidate 如何接入 ATPAL ledger 的 adapter contract。不得运行候选策略，不得进行 candidate replay，不得输出 candidate 结果，不得选择规则或阈值。
