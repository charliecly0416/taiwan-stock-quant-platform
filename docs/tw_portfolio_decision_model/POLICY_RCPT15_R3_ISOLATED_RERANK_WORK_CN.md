---
created_at: 2026-06-26
status: work
phase: RCPT15_R3_ISOLATED_RERANK
parent_mainline: docs/tw_portfolio_decision_model/POLICY_RCPT15_ISOLATED_SHADOW_BACKFILL_MAINLINE_CN.md
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT15_R2_O2_DATA_SOURCE_REPAIR_AND_FEATURE_REBUILD_REVIEW_CN.md
production_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
latest_pointer_write_allowed: false
order_or_target_output_allowed: false
---

# RCPT15_R3 Isolated Rerank 工作文档

## 1. 背景

RCPT15_R2 已将 O2 所需的 institutional flow 与 margin short 源修复到 RCPT15/R2 隔离目录，并授权进入：

```text
RCPT15_R3_ISOLATED_RERANK
```

R3 只能消费：

```text
R1 shadow signal/top50
R2 isolated O2 artifacts
O4 frozen LTR model pickle / training whitelist
```

不得读取或写入 formal latest pointer、provider accepted latest、qlib accepted latest、production/default/latest/frontend/Agent/order/broker/target 链路。

## 2. 目标

1. 在隔离目录生成 R3 rerank 审计和候选产物。
2. 先验证 frozen LTR model pickle 是否可直接加载。
3. 验证 R1/R2 输入是否足以覆盖 O4 training whitelist。
4. 若输入完整，生成 rerank score snapshot、top30、top50。
5. 若模型不可加载或必要特征缺失，必须 STOP，不得以 qlib score 或填零特征伪造 rerank。

## 3. 目标日期

目标窗口：

```text
2026-06-18
2026-06-19
2026-06-22
2026-06-23
2026-06-24
2026-06-25
```

其中 `2026-06-19` 在 R1 中为 no-signal/non-trading/calendar classification issue：

```text
prediction_rows = 0
top50_rows = 0
```

R3 必须跳过或单独记录，不得把它计为 O2 failure 或 rerank failure。

## 4. 允许输入

允许读取：

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/
data_tw/experiments/risk_control_policy_2022/rcpt15_r2_o2_data_source_repair_and_feature_rebuild/
data_tw/experiments/ltr_orthogonal_features_controlled/rcpt15_r2_o2_pit_safe_feature_builder/
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_treatment_model.pkl
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_feature_whitelist.csv
```

不允许为了补齐缺失特征读取 formal latest signal、accepted provider、production latest、frontend/Agent/order/broker/target 或运行数据刷新脚本。

## 5. 必需输出

脚本：

```text
scripts/build_tw_policy_rcpt15_r3_isolated_rerank.py
```

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_isolated_rerank/
```

必须输出：

```text
manifest.json
input_artifact_inventory.csv
target_date_rerank_input_status.csv
model_load_audit.json
feature_schema_audit.csv
coverage_audit.csv
pit_audit.csv
forbidden_scope_audit.csv
validator_report.json
```

若 rerank 可执行，还必须输出：

```text
rerank_score_snapshot.csv
rerank_top30.csv
rerank_top50.csv
```

若 rerank 不可执行，必须输出空 schema 文件或 skip marker，并在 `validator_report.json`、`manifest.json` 与执行报告中写明 STOP 原因。

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_ISOLATED_RERANK_EXECUTION_REPORT_CN.md
```

## 6. 允许结论

```text
PASS_READY_FOR_RCPT14A_RERUN_WITH_R3_RERANK_DAYS
STOP_MODEL_PICKLE_LOAD_FAILED
STOP_RERANK_REQUIRED_FEATURES_NOT_AVAILABLE_IN_R1_R2
STOP_NO_ELIGIBLE_R1_SHADOW_TOP50_DAYS
FAIL_NEEDS_REPAIR_R3_EVIDENCE_INCOMPLETE
STOP_SCOPE_OR_SAFETY_VIOLATION
```

## 7. 禁止动作

R3 不允许：

- provider publish。
- accepted latest switch。
- 写 `latest_signal.json`。
- 写 `daily_ltr_rerank_latest.json`。
- 写 `latest_orthogonal_features_latest.json`。
- 修改 production/default/latest/provider/frontend/Agent/monitor/order。
- 输出 `OrderIntent`、`target_weight`、`target_position`、`quantity_instruction`、broker/quick-trade/real order。
- 训练、调参、替换模型或用替代分数冒充 LTR rerank。

## 8. 执行命令

```text
请执行 RCPT15_R3_ISOLATED_RERANK。只读 R1 shadow signal/top50 与 R2 isolated O2 artifacts；先加载 LTR model pickle，加载失败即 STOP；若 R1/R2 授权输入不足以覆盖 training whitelist，也必须 STOP，不得伪造 rerank。请生成规定 artifacts 与执行报告。
```
