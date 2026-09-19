---
created_at: 2026-06-28
status: work_doc
phase: MTRP7_S_CLEAN_DAILY_MODELB_LTR_TOP50_ACCUMULATION_BUILD
parent_phase: MTRP7_R_CLEAN_DAILY_TIER_A_LINEAGE_REPAIR_AND_RERUN
strategy_candidate: top50_hold_rank_buffer_100
readonly_only: true
simulation_only: true
production_allowed: false
production_ready: false
default_switch_allowed: false
formal_phase_yz_write_allowed: false
latest_pointer_mutation_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
broker_authorized: false
isolated_existing_ltr_scoring_allowed: true
model_training_allowed: false
model_tuning_allowed: false
---

# POLICY_MTRP7_S_CLEAN_DAILY_MODELB_LTR_TOP50_ACCUMULATION_BUILD_WORK_CN

## 1. 目标

MTRP7_R 已确认 clean daily Tier A 缺口主要是同日 `ModelB LTR top50` 不足：

```text
ModelA ready = 14/14
Price ready = 14/14
ModelB LTR top50 ready = 3/14
eligible Tier A days = 3 / 5
```

MTRP7_S 的目标是：

```text
在隔离路径中补齐 clean daily ModelB LTR top50 ModelSignalArtifact；
使同日 ModelA + ModelB + price 的 clean Tier A days >= 5；
随后重跑 MTRP7_R；
若 MTRP7_R 通过，再给出进入 MTRP8 shadow review 的证据。
```

## 2. 授权边界

本阶段允许：

```text
读取既有 local qlib daily signal / top150 artifacts
读取既有 local PIT-safe orthogonal feature artifacts
读取既有 frozen LTR model artifact
使用既有 frozen LTR model 做 isolated scoring/adapter
生成 isolated ModelSignalArtifact
生成 isolated MTRP7_R rerun artifacts
```

本阶段禁止：

```text
训练新模型
调参
更换模型
重新训练/重算 LTR 模型
网络/provider refresh
provider publish
accepted latest switch
latest pointer mutation
formal phase_yz 写入
formal PriceStore 写入
production/default registry 修改
frontend/API/Agent 修改
daily auto 主链路/default path 修改
broker / quick-trade / real order
target_weight / target_position / quantity instruction
收益筛选或用收益调参
```

说明：

```text
这里的 isolated_existing_ltr_scoring_allowed 只允许加载已有 frozen LTR model artifact，
对已有 PIT-safe feature rows 做 deterministic scoring，以补 ModelB top50 artifact。
这不是训练，不是调参，不是生产推理发布，也不得写 latest。
```

## 3. 输入候选

执行者必须优先读取本地既有 artifact：

```text
qlib_pipeline/data_tw/experiments/option_c_daily_signal/
data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/daily_e4_default_candidate/
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/strict_e4_daily_prework/
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_t_isolated_price_twii_source_repair/stock_price_bridge/
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/
```

推荐补齐目标日期：

```text
2026-06-01
2026-06-02
2026-06-03
2026-06-04
2026-06-05
2026-06-08
2026-06-09
2026-06-10
2026-06-11
2026-06-12
2026-06-16
```

这些日期在 MTRP7_R 中大多已有 ModelA + price，缺 ModelB。

## 4. ModelB 构造要求

每个补齐日期的 isolated ModelB artifact 必须包含：

```text
manifest.json
signals.csv
schema.json
coverage_audit.csv
pit_available_at_audit.csv
feature_source_audit.csv
model_load_audit.json
forbidden_field_audit.csv
forbidden_action_audit.json
source_trace.json
validator_result.json
```

`signals.csv` 必须满足：

```text
rows = 50
date/signal_asof = target signal_asof
instrument 使用 TWxxxx
candidate_rank = LTR rank 1..50
buy_score = LTR score
raw_score = LTR score
score_rank = LTR rank
full_qlib_rank 来自同日 ModelA / qlib rank
available_at <= signal_asof
production_candidate = true
production_allowed = false
not_published_latest = true
readonly_only = true
simulation_only = true
```

必须禁止字段：

```text
future_return*
forward_return*
label*
replay_return
realized_pnl
execution_price
execution_date
cash
nav
equity
target_weight
target_position
quantity
broker
broker_order_id
```

## 5. PIT / feature 要求

执行者必须验证：

```text
feature_available_at_max <= signal_asof
pit_pass = true
missing_feature_family_count = 0，或明确解释并 STOP
model feature schema 与 frozen LTR whitelist 对齐
source qlib top50/top150 与 ModelB 日期一致
```

若某日期 feature 不足或 PIT 不通过，不得补该日。

## 6. MTRP7_R 重跑要求

若补齐后 clean Tier A days >= 5：

1. 必须修复/参数化 MTRP7_R，让它真实读取 MTRP7_S isolated ModelB root。
2. 必须真实重跑 MTRP7_R，不得只写 manifest-only pass。
3. 必须确认 rerun verdict 为：

```text
PASS_TIER_A_LINEAGE_REPAIRED_MTRP7_READY_FOR_MTRP8
```

或明确失败/STOP。

MTRP7_R rerun 输出必须保存在 MTRP7_S root 内的：

```text
mtrp7_r_rerun/
```

不得写 formal phase_yz 或 latest。

## 7. 输出要求

新增 builder：

```text
scripts/build_tw_policy_mtrp7_s_clean_daily_modelb_ltr_top50_accumulation.py
```

输出 root：

```text
data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp7_s_clean_daily_modelb_ltr_top50_accumulation_build/
```

必须输出：

```text
manifest.json
source_inventory.csv
model_a_price_ready_dates.csv
modelb_build_plan.csv
modelb_artifact_register.csv
model_load_audit.json
feature_schema_audit.csv
pit_available_at_audit.csv
forbidden_field_audit.csv
forbidden_scope_audit.csv
mtrp7_r_rerun_summary.json
mtrp7_r_rerun_validator_report.json
validator_report.json
diagnostic_findings.md
```

每个补齐日期输出：

```text
isolated_modelb_yz2/{signal_asof}/manifest.json
isolated_modelb_yz2/{signal_asof}/signals.csv
isolated_modelb_yz2/{signal_asof}/schema.json
isolated_modelb_yz2/{signal_asof}/coverage_audit.csv
isolated_modelb_yz2/{signal_asof}/pit_available_at_audit.csv
isolated_modelb_yz2/{signal_asof}/feature_source_audit.csv
isolated_modelb_yz2/{signal_asof}/model_load_audit.json
isolated_modelb_yz2/{signal_asof}/forbidden_field_audit.csv
isolated_modelb_yz2/{signal_asof}/forbidden_action_audit.json
isolated_modelb_yz2/{signal_asof}/source_trace.json
isolated_modelb_yz2/{signal_asof}/validator_result.json
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRP7_S_CLEAN_DAILY_MODELB_LTR_TOP50_ACCUMULATION_BUILD_EXECUTION_REPORT_CN.md
```

## 8. 允许 verdict

执行者 verdict：

```text
PASS_MODELB_ACCUMULATED_AND_MTRP7_R_READY_FOR_MTRP8
PASS_MODELB_ACCUMULATED_MTRP7_R_NEEDS_REPAIR
FAIL_NEEDS_MTRP7_S_REPAIR
STOP_INSUFFICIENT_PIT_SAFE_MODELB_INPUTS
STOP_COORDINATOR_DECISION_REQUIRED
```

审查者 verdict：

```text
PASS_MODELB_ACCUMULATED_AND_MTRP7_R_READY_FOR_MTRP8
PASS_MODELB_ACCUMULATED_MTRP7_R_NEEDS_REPAIR
FAIL_NEEDS_MTRP7_S_REPAIR
STOP_INSUFFICIENT_PIT_SAFE_MODELB_INPUTS
STOP_COORDINATOR_DECISION_REQUIRED
```

## 9. 审查重点

审查者必须确认：

```text
是否至少补齐 2 个新增同日 ModelB day，使 clean Tier A days >= 5
ModelB 是否来自既有 frozen LTR model + PIT-safe features，而非训练/调参
feature_available_at_max 是否 <= signal_asof
ModelB signals 是否 rows=50 且字段符合 ModelSignalArtifact
是否没有 future label / replay return / target / quantity / broker 字段
是否没有写 formal phase_yz / latest / provider / accepted latest / production/default
MTRP7_R 是否真实 rerun，而不是 manifest-only
MTRP7_R rerun 是否达到进入 MTRP8 的 gate
```

## 10. 下一步

若通过：

```text
进入 MTRP8 shadow review / readonly exposure design review。
仍不授权 production default switch。
```

若 STOP：

```text
说明本地 PIT-safe feature 或 ModelB source 不足。
下一步应先修 daily orthogonal feature accumulation 或等待/补足真实 clean daily ModelB，不得降级 Tier B。
```
