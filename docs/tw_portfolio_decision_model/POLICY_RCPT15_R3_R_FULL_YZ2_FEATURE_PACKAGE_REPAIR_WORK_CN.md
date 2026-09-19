---
created_at: 2026-06-26
status: work
phase: RCPT15_R3_R_FULL_YZ2_FEATURE_PACKAGE_REPAIR
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_COORDINATOR_REVIEW_AND_NEXT_STEP_CN.md
production_allowed: false
provider_publish_default_allowed: false
accepted_latest_switch_allowed: false
order_or_target_output_allowed: false
---

# RCPT15_R3_R Full YZ2 Feature Package Repair 工作文档

## 1. 目标

修复 `RCPT15_R3_ISOLATED_RERANK` 的真实阻塞：

```text
STOP_RERANK_REQUIRED_FEATURES_NOT_AVAILABLE_IN_R1_R2
```

R3 已证明：

1. frozen O4 LTR 模型可加载；
2. R2 O2 institutional_flow / margin_short 已覆盖；
3. `2026-06-19` 应跳过为 no-signal/non-trading input；
4. rerank 未能执行的原因是 O4 whitelist 78 个特征中缺少 22 个技术/市场控制特征。

本阶段要在隔离目录内构造完整 78-feature YZ2-style package，并使用 frozen O4 LTR 生成真实 rerank，不允许 fallback / fake score。

## 2. 输入边界

允许读取：

```text
R1 shadow top50:
data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/shadow_signals/**

R2 isolated O2:
data_tw/experiments/risk_control_policy_2022/rcpt15_r2_o2_data_source_repair_and_feature_rebuild/candidate_o2_normalized_feature_daily.csv
data_tw/experiments/ltr_orthogonal_features_controlled/rcpt15_r2_o2_pit_safe_feature_builder/normalized_feature_daily.csv

O4 frozen model / whitelist:
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_treatment_model.pkl
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_feature_whitelist.csv

local readonly price/calendar source:
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/**
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt
```

允许复用正式 YZ2 feature builder 的计算逻辑：

```text
scripts/build_phase_yz2_orthogonal_package.py
```

但输出必须写入 RCPT15_R3_R 隔离目录，不得写正式 phase_yz latest 或 product publish 目录。

## 3. 输出目录

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_r_full_yz2_feature_package_repair/
```

必须输出：

```text
manifest.json
validator_report.json
input_artifact_inventory.csv
feature_package.csv
feature_schema_audit.csv
feature_source_trace.csv
coverage_audit.csv
pit_audit.csv
forbidden_scope_audit.csv
rerank_score_snapshot.csv
rerank_top30.csv
rerank_top50.csv
target_date_rerank_status.csv
execution_notes.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_R_FULL_YZ2_FEATURE_PACKAGE_REPAIR_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_R_FULL_YZ2_FEATURE_PACKAGE_REPAIR_REVIEW_CN.md
```

建议脚本：

```text
scripts/build_tw_policy_rcpt15_r3_r_full_yz2_feature_package_repair.py
```

## 4. 执行要求

执行者必须：

1. 读取本工作文档、R3 coordinator review、R3 execution report、R2 review；
2. 用 R1 shadow top50 确定 eligible target dates；
3. `2026-06-19` 必须记录为 no-signal/non-trading input，不纳入 rerank gate；
4. 对每个 eligible date/top50 symbol 构造 O4 whitelist 的完整 78 个特征；
5. 技术指标只允许使用 `date <= signal_asof` 的本地 price rows；
6. 大盘指标只允许使用 `TWII date <= signal_asof`；
7. O2 institutional/margin 只允许使用 `available_at <= signal_asof`；
8. 所有特征必须记录 source family、source path、latest used date / available_at；
9. 使用 frozen O4 model pickle predict，不训练、不调参；
10. 产出 top30/top50 与 full score snapshot；
11. 若任一 eligible date 不能完整构造 78-feature row，应 STOP，不得填零通过。

## 5. 禁止动作

禁止：

```text
provider publish
qlib accepted latest switch
provider accepted latest switch
formal latest pointer write
daily_ltr_rerank_latest write
latest_orthogonal_features_latest write
production/default/frontend/Agent/monitor mutation
OrderIntent
target_weight
target_position
quantity_instruction
broker / quick-trade / real order
模型训练或调参
用 qlib score / rank 代替 LTR score
缺失特征填零后标记 pass
```

## 6. Pass / Stop Gate

PASS 条件：

```text
model_load_ok = true
eligible_shadow_top50_days >= 1
feature_whitelist_count = 78
missing_required_feature_count = 0
coverage_pass = true
pit_pass = true
forbidden_pass = true
rerank_outputs_written = true
no_fallback_or_fake_rerank = true
```

STOP 条件：

```text
模型不能加载
任一 whitelist 特征无法 PIT-safe 构造
任一 eligible top50 row 缺 O2/price/market 必要来源
出现 available_at > signal_asof
需要 provider refresh/publish 或 latest switch 才能继续
```

## 7. Reviewer Audit Brief

审查者必须检查：

1. 78-feature whitelist 是否完整；
2. 是否没有 future label / realized return / execution price / order / target 字段；
3. 技术指标和大盘指标是否 PIT-safe；
4. O2 source 是否 PIT-safe；
5. `2026-06-19` 是否正确跳过；
6. rerank score 是否来自 frozen O4 model；
7. 输出是否只在隔离目录；
8. 是否没有 formal latest / provider / accepted latest / broker / order / target 产物。

## 8. Executor Command

```bash
python scripts/build_tw_policy_rcpt15_r3_r_full_yz2_feature_package_repair.py
```

## 9. Reviewer Command

```bash
python -m py_compile scripts/build_tw_policy_rcpt15_r3_r_full_yz2_feature_package_repair.py
python scripts/build_tw_policy_rcpt15_r3_r_full_yz2_feature_package_repair.py
```

审查者可重跑脚本，但必须确认重跑只写隔离目录。
