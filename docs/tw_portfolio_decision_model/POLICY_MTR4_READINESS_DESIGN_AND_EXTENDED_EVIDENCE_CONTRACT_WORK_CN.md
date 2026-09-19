---
created_at: 2026-06-28
status: work_doc
phase: MTR4_READINESS_DESIGN_AND_EXTENDED_EVIDENCE_CONTRACT
parent_mainline: docs/tw_portfolio_decision_model/POLICY_MTR_MECHANISM_TRANSFER_TO_BASELINE_MAINLINE_CN.md
readonly_only: true
simulation_only: true
production_allowed: false
model_training_authorized: false
strategy_tuning_authorized: false
replay_authorized: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
frontend_default_switch_allowed: false
broker_authorized: false
---

# POLICY_MTR4_READINESS_DESIGN_AND_EXTENDED_EVIDENCE_CONTRACT_WORK_CN

## 1. 目标

MTR4 的目标不是继续优化收益，也不是把 `M2_hold_rank_buffer_100` 切生产。

本阶段只冻结一套可审查的 readiness / extended evidence 合同，使后续 MTR5 能按同一把尺子判断：

```text
M2_hold_rank_buffer_100 是否只是短窗口/少数标的事件驱动，
还是可以进入更长 readonly OOS / shadow 验证与生产准备路线。
```

MTR4 必须输出 machine-readable contract package，明确：

```text
1. broad full-rank visibility 的正式合同边界；
2. non-top50 buy 永久阻断 validator；
3. extended OOS / shadow 证据要求；
4. 月度、rolling、risk_off、drawdown、turnover、fee/tax 最低门槛；
5. symbol/event concentration 风险披露或阻断规则；
6. MTR5 可执行的下一步工作范围；
7. 仍不得生产化、不得切默认、不得 provider publish。
```

## 2. 背景事实

MTR2_R 已生成 research-only qlib+LTR broad full-rank signal，并证明：

```text
top50 内 LTR buy_score 与原 top50-only LTR 等价；
non-top50 行只用于 full_qlib_rank / hold/sell visibility；
non-top50 不得成为 buy candidate。
```

MTR3 审查结论：

```text
PASS_MTR3_WITH_CONCENTRATION_OR_WINDOW_RISK
```

关键指标：

| metric | baseline | M2_100 | delta |
| --- | ---: | ---: | ---: |
| net_total_return_after_fee_tax | 0.87459073 | 1.32852091 | +0.45393018 |
| average_turnover | 0.17040339 | 0.07651037 | -0.09389302 |
| total_fee_plus_tax | 48476.04 | 23979.01 | -24497.03 |
| max_drawdown | -0.13675456 | -0.10619259 | +0.03056197 |
| hold_buffer_trigger_count | 0 | 61 | +61 |
| non_top50_buy_intent_count | 0 | 0 | 0 |

MTR3 风险：

```text
monthly_positive_delta = 3/5
negative_months = 2026-02, 2026-05
rolling_20d_negative_slice_count = 1
top1_symbol_share = 0.631760
top3_symbol_share = 0.972756
top1_event_share = 0.300709
risk_off_delta = +0.01063245
```

因此 MTR4 的判断基础是：

```text
机制有效性有初步证据；
但当前证据不足以生产化；
必须先合同化 extended evidence 和风险阻断条件。
```

## 3. 必读输入

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_MTR_MECHANISM_TRANSFER_TO_BASELINE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR2_R_BROAD_FULL_RANK_VISIBILITY_REPAIR_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR3_ROBUSTNESS_WINDOW_REGIME_AND_MECHANISM_ATTRIBUTION_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR3_ROBUSTNESS_WINDOW_REGIME_AND_MECHANISM_ATTRIBUTION_EXECUTION_REPORT_CN.md
data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/manifest.json
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
```

若任一必读输入缺失，执行者必须 STOP，不得自行补口径。

## 4. 输出目录与文件

输出目录：

```text
data_tw/experiments/policy_mtr_mechanism_transfer/mtr4_readiness_design_and_extended_evidence_contract/
```

必须生成：

```text
manifest.json
readiness_gate_contract.csv
extended_evidence_contract.csv
broad_full_rank_visibility_contract.csv
non_top50_buy_validator_contract.csv
window_regime_gate_contract.csv
concentration_risk_contract.csv
production_boundary_contract.csv
mtr5_work_recommendation.md
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTR4_READINESS_DESIGN_AND_EXTENDED_EVIDENCE_CONTRACT_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTR4_READINESS_DESIGN_AND_EXTENDED_EVIDENCE_CONTRACT_REVIEW_CN.md
```

执行者可以新增一个小型 builder 脚本来生成上述 artifacts，但脚本只能写入 MTR4 输出目录和执行报告，不得修改策略、模型、生产配置、provider/latest/default。

## 5. 合同内容要求

### 5.1 `manifest.json`

必须声明：

```text
artifact_type = policy_mtr4_readiness_design_and_extended_evidence_contract
readonly_only = true
simulation_only = true
production_allowed = false
strategy_modified = false
model_training_performed = false
strategy_tuning_performed = false
replay_performed = false
input_mtr3_manifest
source_verdict = PASS_MTR3_WITH_CONCENTRATION_OR_WINDOW_RISK
next_recommended_phase = MTR5_EXTENDED_OOS_SHADOW_AND_PRODUCTION_READINESS_DIAGNOSTIC
verdict
```

允许 verdict：

```text
PASS_READY_FOR_MTR5_EXTENDED_EVIDENCE
FAIL_NEEDS_MTR4_REPAIR
STOP_SCOPE_OR_INPUT_BLOCKER
```

### 5.2 `readiness_gate_contract.csv`

必须至少包含以下 gate：

```text
input_lineage_gate
mtr3_verdict_gate
broad_full_rank_visibility_gate
top50_ltr_equivalence_gate
non_top50_buy_zero_gate
order_intent_contract_gate
replay_result_contract_gate
forbidden_scope_gate
extended_evidence_required_gate
production_no_go_gate
```

其中 `production_no_go_gate` 在 MTR4 必须为阻断状态：

```text
production_ready = false
reason = MTR3 has concentration/window risk; MTR5 evidence not collected yet
```

### 5.3 `broad_full_rank_visibility_contract.csv`

必须明确：

```text
candidate_rank / full_qlib_rank = qlib base rank
buy_score = LTR rerank score only inside qlib top50
non_top50 broad rows are allowed only for hold/sell visibility
non_top50 broad rows are forbidden as buy candidates
LTR must not change qlib top50 universe / sell boundary
```

必须指定后续正式化要求：

```text
若未来进入生产准备，broad full-rank visibility 必须成为显式 ModelSignalArtifact extension 或标准字段覆盖方案；
不得以 research-only 临时 artifact 静默替代 accepted latest。
```

### 5.4 `non_top50_buy_validator_contract.csv`

必须定义永久 validator 口径：

```text
所有 buy intent 的 instrument 必须满足 candidate_rank <= 50；
若 candidate_rank 缺失、非数值、或 > 50，则 fail；
非 top50 行只能用于判断已有持仓是否仍在 hold_rank_buffer 内，不能用于 buy order；
validator 必须同时检查 order_intents.csv 与 strategy trace / reason 字段；
```

MTR5 及任何生产准备阶段必须以此 gate 作为 hard fail。

### 5.5 `extended_evidence_contract.csv`

必须定义 MTR5 要求的 extended evidence，不得只看 MTR3 full-window：

```text
same-window replay confirmation
daily rolling window attribution, preferably rolling 20d / 40d
monthly attribution with negative-month inventory
risk_on / neutral / risk_off attribution
drawdown segment attribution
turnover / fee / tax decomposition
symbol concentration
event concentration
non_top50 buy zero validation
shadow or recent readonly accumulation if inputs exist
```

最低证据要求：

```text
MTR5 至少复核 MTR3 2026-01-02 至 2026-05-07 全窗口；
若存在更长 strict OOS 或 readonly shadow signal lineage，必须纳入；
若不存在，必须写 data lineage blocker，不得虚构窗口。
```

### 5.6 `window_regime_gate_contract.csv`

必须将 MTR3 的风险转成后续可执行 gate。初始建议：

```text
full_window_net_delta_after_fee_tax > 0
full_window_max_drawdown_delta >= 0
average_turnover_delta <= 0
total_fee_plus_tax_delta <= 0
monthly_positive_delta_ratio >= 0.60
rolling_window_positive_delta_ratio >= 0.60
risk_off_net_delta >= 0
drawdown_segment_delta >= 0
```

注意：

```text
这些是进入 MTR5/生产准备讨论的最低线，不是生产上线线。
若 full-window delta 为正但 risk_off 或 drawdown segment 显著恶化，必须降级为 research-only。
```

### 5.7 `concentration_risk_contract.csv`

必须处理 MTR3 暴露出的集中度问题。

初始建议：

```text
top1_symbol_delta_share <= 0.50: pass
0.50 < top1_symbol_delta_share <= 0.70: warn_requires_disclosure_and_more_evidence
top1_symbol_delta_share > 0.70: fail_or_research_only

top3_symbol_delta_share <= 0.80: pass
0.80 < top3_symbol_delta_share <= 0.95: warn_requires_disclosure_and_more_evidence
top3_symbol_delta_share > 0.95: fail_or_research_only unless extended windows reduce concentration

top1_event_delta_share <= 0.25: pass
0.25 < top1_event_delta_share <= 0.35: warn_requires_event_disclosure
top1_event_delta_share > 0.35: fail_or_research_only
```

MTR3 当前应被分类为：

```text
top1_symbol_share: warn
top3_symbol_share: fail_or_research_only_pending_extended_evidence
top1_event_share: warn
```

### 5.8 `production_boundary_contract.csv`

必须明确 MTR4 仍然禁止：

```text
production/default/frontend/API/Agent/daily/provider/latest 改动
provider publish
accepted latest switch
broker / quick-trade / real order
target_weight / target_position / quantity instruction
模型训练或重训
策略调参
后验新增候选
用 realized pnl / replay return 作为策略输入
```

### 5.9 `mtr5_work_recommendation.md`

必须给出下一阶段工作文档雏形，阶段名：

```text
MTR5_EXTENDED_OOS_SHADOW_AND_PRODUCTION_READINESS_DIAGNOSTIC
```

MTR5 仍不得生产化。MTR5 目标是按 MTR4 合同执行 extended evidence：

```text
1. 复核 MTR3 同窗口；
2. 补每日 rolling window；
3. 若 lineage clean，加入更长 OOS / readonly shadow；
4. 应用 concentration gate；
5. 给出 GO_TO_MTR6_PRODUCTION_READINESS_PROPOSAL 或 KEEP_RESEARCH_ONLY。
```

## 6. 禁止事项

MTR4 禁止：

```text
修改 M2 参数
新增候选
重新跑 MTR2_R replay
新增收益实验
训练/调参
修改 ModelSignalArtifact accepted latest
修改 production/default/frontend/API/Agent/daily/provider/latest
provider publish
accepted latest switch
broker / quick-trade / real order
target_weight / target_position / quantity instruction
读取 realized pnl / replay return 作为策略输入
```

MTR4 可以引用 MTR3 后验归因结果来定义 gate，但不能把后验归因反馈给策略。

## 7. 执行者任务

执行者必须：

1. 读取第 3 节所有输入。
2. 生成第 4 节所有 artifacts。
3. 确认 MTR3 verdict 与关键风险是否被完整映射进合同。
4. 生成 validator_report，检查 artifact 完整性、字段完整性、production_no_go、forbidden scope。
5. 写执行报告，列出文件、证据、未生产化声明和下一步建议。

执行者不得在本阶段跑收益 replay；如为了读取 MTR3 artifact 做静态验证，可以读取 CSV/JSON，但不得改写 MTR2_R/MTR3 产物。

## 8. 审查者任务

审查者必须：

1. 独立读取本工作文档、MTR 主线、MTR3 审查和执行报告、MTR4 执行报告。
2. 检查 MTR4 artifacts 是否完整且 machine-readable。
3. 检查是否把 MTR3 的三个风险完整合同化：
   - 月度/rolling 稳定性；
   - risk_off / drawdown；
   - symbol/event concentration。
4. 检查 broad full-rank visibility 与 non-top50 buy validator 是否足够硬。
5. 检查是否存在生产/default/latest/provider/frontend/API/Agent 改动。
6. 给出 verdict，并写下一阶段 MTR5 工作文档或 repair 文档。

允许 verdict：

```text
PASS_READY_FOR_MTR5_EXTENDED_EVIDENCE
FAIL_NEEDS_MTR4_REPAIR
STOP_SCOPE_OR_PRODUCTION_BOUNDARY_VIOLATION
```

## 9. 验收标准

MTR4 通过条件：

```text
artifact_complete = true
all_required_contracts_present = true
mtr3_risks_mapped_to_gates = true
non_top50_buy_hard_fail_defined = true
production_no_go_explicit = true
forbidden_scope_clean = true
mtr5_next_step_defined = true
```

MTR4 不要求：

```text
收益超过 baseline
新窗口 replay 完成
生产 readiness go
默认策略切换
```

## 10. 给执行者的命令

```text
请执行 MTR4_READINESS_DESIGN_AND_EXTENDED_EVIDENCE_CONTRACT。
严格读取工作文档与必读输入，只生成 readiness/extended evidence contract package 和执行报告。
不得跑新收益 replay、不得修改策略/模型/默认/生产/provider/latest。
完成后给出 PASS_READY_FOR_MTR5_EXTENDED_EVIDENCE 或 FAIL/STOP，并列出所有产物路径。
```

## 11. 给审查者的审查 brief

```text
请审查 MTR4 执行报告和 artifacts。
重点判断：MTR3 的窗口风险、risk_off 风险、symbol/event 集中度风险是否已经被 MTR4 合同化；
broad full-rank visibility 与 non-top50 buy hard fail 是否足以进入 MTR5；
是否明确阻断生产化。
若通过，请写 MTR5_EXTENDED_OOS_SHADOW_AND_PRODUCTION_READINESS_DIAGNOSTIC 工作文档；若不通过，请写 MTR4 repair 文档。
```
