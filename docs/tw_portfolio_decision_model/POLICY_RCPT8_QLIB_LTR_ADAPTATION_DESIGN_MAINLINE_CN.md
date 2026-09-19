---
created_at: 2026-06-24
status: coordinator_mainline
route: RCPT8_QLIB_LTR_ADAPTATION_DESIGN_AND_VALIDATION
parent_closure: docs/tw_portfolio_decision_model/POLICY_RCPT7C_ADAPTIVE_SCORE_ALIGNED_CLOSURE_REVIEW_CN.md
selected_research_candidate: Candidate_B_Top50_Adaptive_Score_PLUS_RULE_05_Sell_Overlay
production_allowed: false
order_or_target_output_allowed: false
model_training_authorized: false
---

# RCPT8 Qlib+LTR Adaptation Design 合同与验证路线

## 1. 统筹结论

RCPT7 已经关闭，结论是：

```text
Candidate B = Top50 Adaptive Score + RULE_05 Sell Overlay
```

可以作为 research candidate 进入 qlib+LTR adaptation design。

但 RCPT7 的证据来自：

```text
qlib-only replay
```

不能直接外推为：

```text
qlib+LTR production-ready 策略
```

因此 RCPT8 的任务不是生产化，而是合同化回答：

```text
当输入信号从 qlib-only score/rank 变成 qlib+LTR rerank/score 后，
Candidate B 的 adaptive score 与 sell overlay 是否仍然定义清楚、PIT-safe、可 replay、可验证，并且是否仍有收益/回撤 tradeoff 价值。
```

## 2. 当前必须继承的事实

### 2.1 RCPT7C 已通过

RCPT7C 审查结论：

```text
PASS_RCPT7_CLOSED_READY_FOR_QLIB_LTR_ADAPTATION_DESIGN
```

有效候选只有：

```text
Candidate B: PASS_NON_BASELINE_EQUIVALENT
```

无效候选：

```text
Candidate A: FAIL_RETURN_CAPTURE
Candidate C: BASELINE_EQUIVALENT_NO_OP
```

RCPT8 不得重新包装 Candidate A/C。

### 2.2 Candidate B 的 qlib-only 关键证据

在 2023-01-03 至 2025-06-30 qlib-only TEST fold strict OOS candidate 中：

```text
adaptive baseline net_return_after_fee_tax = 0.32670955
Candidate B net_return_after_fee_tax = 0.31383997
Candidate B return_capture = 0.96060850
adaptive baseline max_drawdown severity = 0.56426863
Candidate B max_drawdown severity = 0.36230989
Candidate B average_cash_rate = 0.30328641
Candidate B cash_gt_90pct_equity_day_share = 0.01675042
```

解释：

```text
Candidate B 不是收益增强策略；
它是少量牺牲收益、明显改善回撤的风控 overlay。
```

## 3. 最大风险：LTR 数据切分污染

本路线必须正视一个核心问题：

```text
如果当前 qlib+LTR / orthogonal LTR 模型使用 2023-2025 训练或选择，
则 2023-2025 不能再作为该 qlib+LTR 策略的严格 OOS 测试。
```

因此 RCPT8 中窗口语义必须冻结为：

```text
2022:
  downturn diagnostic only；
  不能称为 qlib+LTR strict OOS，除非存在独立可用且未用 2022 训练/调参的 LTR lineage。

2023-2025:
  qlib+LTR lineage / integration / in-sample-or-contaminated diagnostic；
  若 LTR 在 2023-2025 训练或选择，不得称为 strict OOS。

2026:
  potential untouched strict OOS / holdout diagnostic；
  但若样本过短，只能称为 narrow strict OOS diagnostic，不得生产化。
```

如果执行者发现存在其他独立 lineage，例如：

```text
2015-2020 qlib + 2021 LTR train + 2022 test
```

则必须先提交 lineage audit，由审查者批准后才能把 2022 升级为严格测试。

## 4. 目标

RCPT8 要回答：

```text
1. qlib+LTR signal artifact 是否足够标准化，能支持 adaptive score + RULE_05 sell overlay；
2. LTR score/rank 与 qlib score/rank 在字段语义上如何映射；
3. Candidate B 是否应使用 qlib score、LTR score，还是组合 score 作为 adaptive_score_baseline 的 score component；
4. 哪些窗口可以作为 diagnostic，哪些窗口可以作为 strict OOS；
5. 是否能在 qlib+LTR 输入下复现“高收益捕获 + 明显回撤改善”的 tradeoff；
6. 是否值得进入后续 qlib+LTR predeclared replay。
```

## 5. 非目标

RCPT8 当前不授权：

```text
1. 直接生产化 Candidate B；
2. 修改 production/default/provider/latest/frontend/Agent/monitor/order 链路；
3. 输出 OrderIntent、target_weight、target_position、quantity_instruction；
4. broker / quick-trade / real order；
5. 训练新 qlib、LTR、policy、RL 或 deep learning 模型；
6. 根据 replay 结果调阈值；
7. 无界 grid search；
8. 新增 Candidate D/E/F；
9. 把 2023-2025 qlib+LTR 结果称为 strict OOS，除非 lineage audit 证明没有训练/选择污染；
10. 把 2026 窄窗口结果称为 production-grade。
```

## 6. 授权范围

RCPT8 授权读取和审计：

```text
1. 标准 ModelSignalArtifact 或等价 signal manifest；
2. qlib score/rank 字段；
3. LTR / orthogonal LTR rerank score/rank 字段；
4. signal lineage、train/valid/test split、artifact manifest；
5. readonly replay 所需价格、现金、费用、持仓 accounting artifact。
```

但授权分阶段生效：

```text
RCPT8A 只做 signal lineage 与可用性合同；
RCPT8B 只做 adaptation rule contract；
RCPT8C 才允许按预声明合同 replay；
RCPT8D 才允许 closure。
```

RCPT8A/RCPT8B 不允许 replay。

## 7. Signal Adaptation 合同

### 7.1 不允许改动的部分

Candidate B 的核心结构冻结为：

```text
base strategy:
  rank_rotate_top50_adaptive_score-like ranking / buy selection

overlay:
  RULE_05 weak-rank-deterioration sell overlay
```

不允许改：

```text
RULE_05 sell trigger 逻辑；
费用/税率；
交易执行价格口径；
cash/equity accounting；
持仓限制；
replay accounting ledger 语义。
```

### 7.2 允许设计但必须预冻结的部分

RCPT8B 可以在 replay 前冻结最多三个 score component mapping，不得 replay 后再选择：

```text
Mapping 1: qlib_score_component
  adaptive_score_baseline 沿用 qlib raw score z-score。
  LTR 只改变 top50 内排序或比较对象。

Mapping 2: ltr_score_component
  adaptive_score_baseline 的 score component 改为 LTR score 同日 z-score。
  必须证明 LTR score coverage、方向、缺失处理、rank tie 处理。

Mapping 3: blended_score_component
  adaptive_score_baseline 的 score component 使用固定组合：
    alpha * qlib_score_zscore_by_date + (1 - alpha) * ltr_score_zscore_by_date
  alpha 必须在 RCPT8B 预冻结。
```

建议默认优先级：

```text
1. Mapping 1
2. Mapping 2
3. Mapping 3
```

理由：

```text
Mapping 1 最接近 RCPT7 已验证机制；
Mapping 2 检查 LTR 是否能直接替代 qlib score；
Mapping 3 风险最高，必须限制为一个预声明 alpha，不得搜索。
```

## 8. Baseline 合同

RCPT8 replay 必须比较：

```text
1. qlib+LTR baseline current/replay equivalent；
2. qlib+LTR adaptive-score baseline without RULE_05 overlay；
3. qlib+LTR Candidate B adaptation with RULE_05 overlay；
4. qlib-only RCPT7 Candidate B reference；
5. qlib-only rank_rotate_top50_adaptive_score reference。
```

主比较对象：

```text
qlib+LTR adaptive-score baseline without RULE_05 overlay
```

原因：

```text
RCPT8 要验证的是 overlay 在 qlib+LTR 输入下是否有增量风控价值，
不能只和 qlib-only baseline 比。
```

## 9. Gate 合同

### 9.1 Integration Gate

必须满足：

```text
signal lineage PASS
ModelSignalArtifact schema PASS
score/rank direction PASS
PIT availability PASS
price/accounting coverage PASS
no production/order target fields PASS
```

### 9.2 Return Capture Gate

对每个可 replay 窗口：

```text
candidate_return_capture_vs_qlib_ltr_adaptive_baseline >= 0.85
ideal >= 0.90
```

若 baseline return 为负：

```text
candidate loss 不得比 qlib+LTR adaptive baseline 明显更差；
允许最多 3pp loss widening。
```

### 9.3 Drawdown Gate

候选必须满足至少一个：

```text
max_drawdown severity 改善 >= 5pp
或
max_drawdown severity 不差于 baseline 且 downside month/day concentration 改善
```

如果收益牺牲超过 5pp，则必须有明显 drawdown 或亏损月改善，否则失败。

### 9.4 Participation / All-cash Gate

候选不得靠空仓通过：

```text
average_cash_rate <= 0.65
cash_gt_90pct_equity_day_share <= 0.25
average_position_count >= 5
```

如 qlib+LTR baseline 本身持仓更少，执行者必须报告相对口径。

### 9.5 Fee / Turnover Gate

必须报告：

```text
fee_tax_total
turnover
action_count
sell_overlay_trigger_count
buy_block_count
```

若费用增加但收益未补偿，不能通过。

### 9.6 Strict OOS Gate

只有满足以下条件的窗口可称 strict OOS：

```text
1. signal model 未在该窗口训练；
2. 未用该窗口做 model selection / threshold selection / early stopping；
3. candidate rule 和 gate 在 replay 前冻结；
4. label/future return 未进入策略输入；
5. lineage manifest 可审计。
```

否则只能称：

```text
diagnostic
```

## 10. 阶段计划

### RCPT8A: Qlib+LTR Signal Lineage And Coverage Contract

目标：

```text
冻结可用 qlib+LTR signal artifact；
审计 LTR train/valid/test split；
判定 2022、2023-2025、2026 各自窗口语义；
确认是否存在足够 PIT-safe score/rank 字段。
```

不允许 replay。

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt8a_qlib_ltr_signal_lineage_contract/
```

必须输出：

```text
manifest.json
signal_artifact_inventory.csv
lineage_window_semantics.csv
model_training_contamination_audit.csv
score_rank_schema_audit.csv
coverage_by_window.csv
pit_availability_audit.csv
forbidden_action_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT8A_QLIB_LTR_SIGNAL_LINEAGE_CONTRACT_EXECUTION_REPORT_CN.md
```

审查结论只能是：

```text
PASS_READY_FOR_RCPT8B_ADAPTATION_RULE_CONTRACT
FAIL_NEEDS_RCPT8A_REPAIR
STOP_NO_VALID_QLIB_LTR_SIGNAL_LINEAGE
STOP_SCOPE_OR_FORBIDDEN_ACTION_VIOLATION
```

### RCPT8B: Adaptation Rule Contract

前提：

```text
RCPT8A PASS
```

目标：

```text
预冻结 qlib+LTR 下 Candidate B 的精确定义；
预冻结 score component mapping；
预冻结 baseline、窗口、gate、ledger schema。
```

不允许 replay。

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt8b_qlib_ltr_adaptation_rule_contract/
```

必须输出：

```text
manifest.json
candidate_b_adaptation_contract.md
score_component_mapping_contract.csv
baseline_contract.csv
replay_window_contract.csv
gate_contract.md
ledger_schema_contract.md
forbidden_action_audit.csv
validator_report.json
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT8B_QLIB_LTR_ADAPTATION_RULE_CONTRACT_EXECUTION_REPORT_CN.md
```

审查结论只能是：

```text
PASS_READY_FOR_RCPT8C_PREDECLARED_REPLAY
FAIL_NEEDS_RCPT8B_REPAIR
STOP_MAPPING_OR_GATE_NOT_FROZEN
STOP_SCOPE_OR_FORBIDDEN_ACTION_VIOLATION
```

### RCPT8C: Predeclared Qlib+LTR Replay

前提：

```text
RCPT8B PASS
```

目标：

```text
只按 RCPT8B 冻结合同 replay；
不得新增 mapping；
不得调阈值；
不得重命名窗口语义。
```

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt8c_qlib_ltr_predeclared_replay/
```

必须输出：

```text
manifest.json
window_metric_summary.csv
candidate_vs_qlib_ltr_adaptive_baseline.csv
gate_decision_by_window.csv
gate_decision_by_mapping.csv
daily_nav.csv
actions.csv
trigger_attribution.csv
cash_exposure_audit.csv
fee_turnover_audit.csv
concentration_audit.csv
lineage_replay_audit.json
forbidden_action_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT8C_QLIB_LTR_PREDECLARED_REPLAY_EXECUTION_REPORT_CN.md
```

审查结论只能是：

```text
PASS_READY_FOR_RCPT8D_CLOSURE
FAIL_NEEDS_RCPT8C_REPAIR
FAIL_NO_MAPPING_PASSES_GATE
STOP_SCOPE_OR_LINEAGE_VIOLATION
```

### RCPT8D: Closure

目标：

```text
判断 qlib+LTR adaptation 是否成立；
明确是否继续到更长期 strict OOS / retrain lineage；
明确是否仍然禁止生产化。
```

允许结论：

```text
PASS_QLIB_LTR_ADAPTATION_RESEARCH_CANDIDATE
PASS_NEEDS_LONGER_STRICT_OOS_BEFORE_PRODUCTION
FAIL_QLIB_LTR_ADAPTATION_NOT_SUPPORTED
STOP_LINEAGE_OR_DATA_CONTRACT_VIOLATION
```

默认不允许生产化。若要生产化，必须另开：

```text
RCPT9 production readiness / readonly acceptance / safety boundary route
```

## 11. 第一阶段执行者工作文档

### 11.1 RCPT8A 执行者任务

执行者必须：

```text
1. 读取本主线；
2. 读取 RCPT7C closure review；
3. 盘点现有 qlib+LTR / orthogonal LTR / ModelSignalArtifact 产物；
4. 找到每个候选 signal artifact 的 manifest、score 文件、训练窗口、测试窗口；
5. 判断 2022、2023-2025、2026 是否分别可用；
6. 对每个窗口标记 strict_oos / diagnostic / unavailable；
7. 检查字段是否支持 qlib_score、qlib_rank、ltr_score、ltr_rank、date、instrument；
8. 检查是否 PIT-safe；
9. 写出是否建议进入 RCPT8B。
```

执行者不得：

```text
1. replay；
2. 训练模型；
3. 调阈值；
4. 修改 artifact；
5. 改 production 链路；
6. 输出交易/仓位/数量指令。
```

### 11.2 RCPT8A Reviewer 任务

审查者必须确认：

```text
1. signal artifact inventory 是否完整；
2. lineage/window 语义是否诚实；
3. 2023-2025 是否没有被错误称为 qlib+LTR strict OOS；
4. 2026 如果样本过短，是否只称 narrow strict OOS diagnostic；
5. 是否没有 replay 或越权；
6. 是否真的有足够证据进入 RCPT8B。
```

## 12. Stop Conditions

必须停止并回报统筹：

```text
1. 找不到可审计 qlib+LTR signal artifact；
2. 找不到 LTR 训练窗口/测试窗口 manifest；
3. score/rank 字段方向不明；
4. 2023-2025 被污染但执行者仍试图作为 strict OOS；
5. 2026 样本太短但执行者试图生产化；
6. 需要训练或重训模型才能继续；
7. 需要改生产/default/provider/latest/frontend/Agent/order 链路才能继续。
```

## 13. 统筹建议

当前建议先执行：

```text
RCPT8A_QLIB_LTR_SIGNAL_LINEAGE_CONTRACT
```

只有当 RCPT8A 证明存在可审计 qlib+LTR signal lineage，并且窗口语义可以诚实冻结后，才进入 RCPT8B。

本路线最可能的合理结果是：

```text
qlib+LTR adaptation research candidate
```

而不是：

```text
production-ready strategy
```

若 2026 strict OOS 样本过短，则即使 RCPT8C gate 通过，也只能进入更长时间滚动观察或另开重训/保留窗口路线。
