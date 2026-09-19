---
created_at: 2026-06-28
status: work_doc
phase: MTR5_EXTENDED_OOS_SHADOW_AND_PRODUCTION_READINESS_DIAGNOSTIC
parent_mainline: docs/tw_portfolio_decision_model/POLICY_MTR_MECHANISM_TRANSFER_TO_BASELINE_MAINLINE_CN.md
upstream_gate: PASS_READY_FOR_MTR5_EXTENDED_EVIDENCE
readonly_only: true
simulation_only: true
production_allowed: false
model_training_authorized: false
strategy_tuning_authorized: false
new_candidate_authorized: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
frontend_default_switch_allowed: false
broker_authorized: false
---

# POLICY_MTR5_EXTENDED_OOS_SHADOW_AND_PRODUCTION_READINESS_DIAGNOSTIC_WORK_CN

## 1. 目标

MTR5 的目标是按 MTR4 合同收集 extended evidence，判断：

```text
M2_hold_rank_buffer_100
是否可以进入 MTR6 production readiness proposal，
或必须保持 research-only。
```

MTR5 不是生产化阶段。任何结果都不得直接切：

```text
production/default/frontend/API/Agent/daily/provider/latest
```

MTR5 也不是调参阶段。不得修改：

```text
M2 参数
候选集合
broad full-rank signal artifact
MTR2_R replay result
MTR3 artifact
```

## 2. 背景事实

MTR3 证明 M2_100 在 qlib+LTR broad full-rank visibility 下 full-window 有明显优势：

```text
baseline net = 0.87459073
M2_100 net = 1.32852091
delta = +0.45393018
turnover delta = -0.09389302
fee/tax delta = -24497.03
drawdown delta = +0.03056197
non_top50 buy = 0
```

但 MTR3 暴露：

```text
monthly positive = 3/5
rolling_20d 有负切片
risk_off delta 仅 +0.01063245
top1 symbol share = 0.631760
top3 symbol share = 0.972756
top1 event share = 0.300709
```

MTR4 已将这些风险合同化，并给出：

```text
PASS_READY_FOR_MTR5_EXTENDED_EVIDENCE
```

因此 MTR5 必须更严格复核 rolling、负月、risk_off、drawdown、turnover/fee/tax 和集中度。

## 3. 必读输入

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_MTR_MECHANISM_TRANSFER_TO_BASELINE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR4_READINESS_DESIGN_AND_EXTENDED_EVIDENCE_CONTRACT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR4_READINESS_DESIGN_AND_EXTENDED_EVIDENCE_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR3_ROBUSTNESS_WINDOW_REGIME_AND_MECHANISM_ATTRIBUTION_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR3_ROBUSTNESS_WINDOW_REGIME_AND_MECHANISM_ATTRIBUTION_EXECUTION_REPORT_CN.md
data_tw/experiments/policy_mtr_mechanism_transfer/mtr4_readiness_design_and_extended_evidence_contract/manifest.json
data_tw/experiments/policy_mtr_mechanism_transfer/mtr4_readiness_design_and_extended_evidence_contract/*.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/manifest.json
data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/*.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/manifest.json
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
```

若 MTR4 gate 或 MTR3/MTR2_R 输入缺失，必须 STOP，不得自行补口径。

## 4. 允许输入与禁止输入

允许：

```text
读取 MTR2_R replay/order_intent 输出；
读取 MTR3 attribution artifacts；
读取 MTR4 contract artifacts；
从已有 readonly replay 输出计算 rolling/monthly/regime/drawdown/concentration diagnostics；
检查是否存在更长 strict OOS / readonly shadow lineage；
若不存在，写 data_lineage_blocker.md。
```

禁止：

```text
训练模型；
调参；
新增候选；
修改 M2 参数；
重跑 MTR2_R replay；
修改 MTR2_R/MTR3/MTR4 输入 artifacts；
把 realized pnl / replay return 反馈给 StrategyRule；
修改 production/default/frontend/API/Agent/daily/provider/latest；
provider publish；
accepted latest switch；
broker / quick-trade / real order；
target_weight / target_position / quantity instruction。
```

## 5. 输出目录与文件

输出目录：

```text
data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/
```

必须生成：

```text
manifest.json
same_window_replay_confirmation.csv
daily_rolling_window_attribution.csv
monthly_negative_inventory.csv
regime_attribution_summary.csv
drawdown_segment_attribution.csv
turnover_fee_tax_decomposition.csv
symbol_concentration_gate.csv
event_concentration_gate.csv
non_top50_buy_validator_report.json
extended_lineage_inventory.csv
data_lineage_blocker.md
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTR5_EXTENDED_OOS_SHADOW_AND_PRODUCTION_READINESS_DIAGNOSTIC_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTR5_EXTENDED_OOS_SHADOW_AND_PRODUCTION_READINESS_DIAGNOSTIC_REVIEW_CN.md
```

执行者可以新增一个 MTR5 builder 脚本：

```text
scripts/build_tw_policy_mtr5_extended_oos_shadow_diagnostic.py
```

脚本只能写 MTR5 输出目录和 MTR5 执行报告。

## 6. 必做诊断

### 6.1 Same-window replay confirmation

复核 MTR3 同窗口：

```text
2026-01-02 至 2026-05-07
baseline_top50_exit_one_worst_sell vs M2_hold_rank_buffer_100
```

必须确认：

```text
full_window_net_delta_after_fee_tax > 0
drawdown_delta >= 0
turnover_delta <= 0
fee_tax_delta <= 0
non_top50_buy_count = 0
```

### 6.2 Daily rolling window attribution

必须补每日 rolling：

```text
rolling_20d: required
rolling_40d: required if trading_day_count >= 40
```

每个 rolling window 输出：

```text
window_id
window_size
start_date
end_date
baseline_net
m2_net
net_delta
baseline_drawdown
m2_drawdown
drawdown_delta
baseline_turnover
m2_turnover
turnover_delta
baseline_fee_tax
m2_fee_tax
fee_tax_delta
status
```

MTR4 初始最低门槛：

```text
rolling_window_positive_delta_ratio >= 0.60
```

若低于门槛，MTR5 verdict 必须是：

```text
KEEP_RESEARCH_ONLY
```

### 6.3 Monthly negative inventory

必须输出所有自然月：

```text
month
baseline_net
m2_net
net_delta
is_negative_delta
probable_driver
requires_followup
```

MTR3 已知负月：

```text
2026-02
2026-05
```

MTR5 不要求消除负月，但必须解释负月是否来自：

```text
少数持仓延迟卖出；
错过 baseline replacement；
大盘 regime；
费用节省不足以覆盖机会成本；
单一事件集中。
```

### 6.4 Regime / risk_off

使用 MTR3 同口径 diagnostic regime，不得把 regime 反馈给 StrategyRule。

必须确认：

```text
risk_off_net_delta >= 0
```

若 risk_off 为负，MTR5 verdict 必须是：

```text
KEEP_RESEARCH_ONLY
```

若 risk_off 仅小幅为正，必须标记：

```text
production_not_ready_without_shadow_confirmation
```

### 6.5 Drawdown segment

必须复核：

```text
baseline max drawdown segment
M2 max drawdown segment
M2 是否在 stress segment 恶化
```

若 full-window 正收益但 drawdown segment 恶化，必须降级：

```text
KEEP_RESEARCH_ONLY
```

### 6.6 Turnover / fee / tax decomposition

必须确认 M2 的优势不是 accounting artifact：

```text
buy_count / sell_count 减少；
notional turnover 下降；
commission + tax 下降；
summary 与 actions/daily_nav 可对齐。
```

### 6.7 Concentration gate

按 MTR4 合同应用：

```text
top1_symbol_share <= 0.50: pass
0.50 < top1_symbol_share <= 0.70: warn
top1_symbol_share > 0.70: fail_or_research_only

top3_symbol_share <= 0.80: pass
0.80 < top3_symbol_share <= 0.95: warn
top3_symbol_share > 0.95: fail_or_research_only unless extended windows reduce concentration

top1_event_share <= 0.25: pass
0.25 < top1_event_share <= 0.35: warn
top1_event_share > 0.35: fail_or_research_only
```

若只存在 MTR3 同窗口，且 top3_symbol_share 仍 > 0.95，MTR5 不能进入 MTR6 production readiness proposal，只能：

```text
KEEP_RESEARCH_ONLY
```

除非执行者找到 lineage clean 的更长 OOS/shadow 窗口并证明集中度下降。

### 6.8 Permanent non-top50 buy validator

必须扫描 MTR2_R 中 baseline 和 M2_100 的 OrderIntent / trace：

```text
任何 buy intent candidate_rank 缺失、非数值、或 > 50 都 hard fail；
任何 non-top50 进入 buy trace/reason 都 hard fail。
```

hard fail verdict：

```text
STOP_LINEAGE_OR_VALIDATOR_BLOCKER
```

### 6.9 Extended lineage inventory

必须检查是否存在可用于本 MTR5 的更长 strict OOS / readonly shadow lineage。

最低要求：

```text
列出候选目录/manifest；
判断是否 same candidate, same M2 parameter, same signal lineage, same contract；
若没有 clean lineage，写 data_lineage_blocker.md；
不得拼接不等价窗口，不得使用私有模型文件冒充标准 artifact。
```

## 7. Verdict 规则

允许 verdict：

```text
GO_TO_MTR6_PRODUCTION_READINESS_PROPOSAL
KEEP_RESEARCH_ONLY
STOP_LINEAGE_OR_VALIDATOR_BLOCKER
```

### 7.1 GO_TO_MTR6 条件

必须同时满足：

```text
same-window full net/drawdown/turnover/fee_tax gates pass；
daily rolling 20d positive ratio >= 0.60；
rolling 40d positive ratio >= 0.60；
monthly positive ratio >= 0.60；
risk_off delta >= 0；
drawdown segment delta >= 0；
turnover / fee / tax decomposition pass；
non_top50 buy validator pass；
concentration 不处于 fail_or_research_only；
若 concentration 在 warn，必须有 extended clean lineage 或明确 MTR6 只做 proposal 不做生产切换。
```

### 7.2 KEEP_RESEARCH_ONLY 条件

任一成立：

```text
rolling / monthly / risk_off / drawdown 未达 MTR4 gate；
集中度仍处于 fail_or_research_only 且没有 clean extended window 降低风险；
只有 MTR3 短窗口证据，不足以进入 MTR6；
turnover/fee_tax 优势无法从 actions/daily_nav 对齐验证。
```

### 7.3 STOP 条件

任一成立：

```text
non_top50 buy validator hard fail；
MTR2_R/MTR3/MTR4 必要输入缺失；
发现 StrategyRule 使用未来数据或 replay return；
发现生产/default/latest/provider/frontend/API/Agent/daily 被本阶段修改；
发现 M2 参数或候选被本阶段改动。
```

## 8. 执行者任务

1. 读取第 3 节输入。
2. 生成第 5 节全部 artifacts。
3. 严格按 MTR4 合同执行 gate。
4. 不允许为了 GO 而补口径或放宽 gate。
5. 写执行报告，明确最终 verdict 和原因。

## 9. 审查者任务

1. 独立读取本工作文档、MTR4 review、MTR5 执行报告和 artifacts。
2. 复核所有 gate 是否按 MTR4 合同执行。
3. 重点审查：
   - rolling 20d/40d 是否每日 rolling；
   - monthly negative inventory 是否覆盖负月；
   - risk_off / drawdown 是否没有被 full-window 掩盖；
   - concentration gate 是否被正确应用；
   - non_top50 buy validator 是否 hard fail 语义足够；
   - 是否存在越界生产改动。
4. 输出 MTR5 审查报告。
5. 若通过 GO_TO_MTR6，写 MTR6 proposal 工作文档；若 KEEP_RESEARCH_ONLY，写 research-only closure/continuation 建议；若 STOP，写 repair/blocker 文档。

## 10. 给执行者的命令

```text
请执行 MTR5_EXTENDED_OOS_SHADOW_AND_PRODUCTION_READINESS_DIAGNOSTIC。
只读复用 MTR2_R/MTR3/MTR4 artifacts，生成 MTR5 extended evidence diagnostics。
不得训练、调参、新增候选、修改 M2、重跑 MTR2_R replay、修改生产/default/latest/provider/frontend/API/Agent/daily。
最终给出 GO_TO_MTR6_PRODUCTION_READINESS_PROPOSAL / KEEP_RESEARCH_ONLY / STOP_LINEAGE_OR_VALIDATOR_BLOCKER。
```

## 11. 给审查者的 brief

```text
请审查 MTR5 执行结果是否严格按 MTR4 合同执行。
重点判断：rolling、负月、risk_off、drawdown、turnover/fee/tax、集中度、non_top50 buy hard fail 是否真实覆盖。
不要因为 full-window 收益高就忽略集中度和窗口风险。
若 concentration 仍 fail_or_research_only 且没有 clean extended lineage，必须 KEEP_RESEARCH_ONLY。
```
