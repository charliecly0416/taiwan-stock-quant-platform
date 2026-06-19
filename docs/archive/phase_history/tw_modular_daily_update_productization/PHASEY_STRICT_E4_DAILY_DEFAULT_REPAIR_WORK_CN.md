# Phase Y 严格 E4 日更默认候选 Repair 工作文档

生成日期：2026-06-18

## 1. 背景

当前发现一个口径偏差：用户要求默认候选应为严格 E4：

```text
2018-2022 frozen qlib
+ 2023-2025 orthogonal LTR
-> qlib Top50 rerank
```

但当前真正能产出今日 LTR Top10 的链路是旧 P3：

```text
fresh qlib / option_c_daily_signal
+ O4 orthogonal LTR
-> daily_ltr_rerank
```

这不是用户指令变化，而是执行与审查没有把 `model_id=e4_frozen_qlib_2023_2025_ltr` 和真实每日非空产物对齐。

Phase Y 目标是在 X 路线完成后，用 1-2 步把这个偏差修掉。

## 2. Repair 目标

Phase Y 只做：

```text
严格 E4 每日 qlib scoring
严格 E4 每日 LTR rerank
严格 E4 Top10 readonly artifact
前端/后端禁止 fallback 到 fresh qlib + O4 LTR
默认候选只有在严格 E4 当日 artifact 非空且验证通过时才可用
```

Phase Y 不做：

```text
训练新 qlib
训练新 LTR
调参
切 provider accepted latest / qlib accepted latest
写 monitor config / scan / alerts
broker / quick-trade / real orders
改变真实交易逻辑
```

## 3. 冻结的严格 E4 身份

必须使用以下身份，不得替换：

```text
qlib_base_model_id = frozen_qlib_2018_2022
qlib_model_path = data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/run/phasee1_frozen_qlib_model.pkl
qlib_train_window = 2018-01-01..2022-12-31

ltr_model_id = phasee3_orthogonal_ltr_2023_2025
ltr_model_path = data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_ltr_model.pkl
ltr_train_window = 2023-01-01..2025-12-31

candidate_scope = daily 150 universe -> qlib rank -> qlib Top50 -> LTR rerank -> Top10 readonly display
```

旧 P3 日更 LTR 必须降级/标记为：

```text
model_id = fresh_qlib_o4_ltr_legacy_daily_candidate
role = legacy_parallel_candidate / not_default
```

不得把它冒充严格 E4。

## 4. 阶段安排

只分两步：

```text
Y0 Strict E4 Contract and Mismatch Audit
Y1 Strict E4 Daily Inference Repair and Acceptance
```

## 5. Phase Y0：合同冻结与偏差审计

### 5.1 目标

确认当前偏差，并冻结 repair 的输入、输出、禁止事项。

### 5.2 执行者必做

1. 列出现有两条链路：

```text
P3 daily_ltr_rerank = fresh qlib + O4 LTR
E4 daily_default_candidate = frozen qlib 2018-2022 + E3 LTR 2023-2025
```

2. 证明当前问题：

```text
P3 有 2026-06-17 非空 daily_ltr_rerank
严格 E4 latest 只到 2026-05-07
任何当前前端/后端若把 E4 设为 ready/default，必须能指出真实非空 E4 asof artifact
```

3. 冻结严格 E4 输出目录：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/daily_strict_e4_default_candidate/<asof>/
```

建议输出：

```text
strict_e4_daily_qlib_top150_scores_<asof>.csv
strict_e4_daily_ltr_top50_rerank_<asof>.csv
strict_e4_daily_target_top10_<asof>.csv
strict_e4_daily_manifest_<asof>.json
strict_e4_daily_coverage_audit_<asof>.csv
strict_e4_daily_pit_audit_<asof>.csv
strict_e4_daily_forbidden_action_audit_<asof>.json
```

### 5.3 Y0 交付

```text
docs/tw_modular_daily_update_productization/PHASEY0_STRICT_E4_CONTRACT_AND_MISMATCH_AUDIT_EXECUTION_REPORT_CN.md
```

### 5.4 Y0 通过标准

```text
严格 E4 身份冻结
P3 legacy daily LTR 与严格 E4 明确区分
确认当前没有严格 E4 今日非空 artifact
确认不得 fallback 到 P3
没有训练 / 调参 / provider latest / monitor / broker/order
```

## 6. Phase Y1：严格 E4 日更推理修复与验收

### 6.1 目标

补出严格 E4 的当日非空 readonly artifact，并把默认候选 guard 修正为“只有严格 E4 当前 asof 非空且验证通过才 ready”。

### 6.2 执行者必做

1. 新增或修复严格 E4 daily inference 脚本：

```text
load phasee1 frozen qlib model
score daily 150 universe for target_asof
rank qlib top150
select qlib Top50
build E3 feature schema compatible orthogonal features
load phasee3 LTR model
rerank qlib Top50
write Top10 readonly artifact
```

2. 增加 guard：

```text
if strict E4 current-asof artifact missing -> E4 unavailable
if strict E4 signals row_count == 0 -> E4 unavailable
if strict E4 qlib rows < expected universe threshold -> E4 unavailable
if strict E4 top50 rows != 50 -> E4 unavailable
if strict E4 LTR rows != 50 -> E4 unavailable
if PIT audit fails -> E4 unavailable
never fallback to fresh qlib + O4 LTR
```

3. 修正前端/后端展示：

```text
默认候选 = strict E4 only when ready
P3 fresh qlib + O4 LTR = legacy parallel candidate, not default
不可用时显示：严格 E4 今日结果未生成 / 验证失败
```

4. 验证：

```text
Y1 validator 通过
当前 asof strict E4 target_top10 非空
frontend/API 显示 model_id 与 artifact lineage 一致
network audit 无 provider accepted latest / monitor / broker/order
```

### 6.3 Y1 交付

```text
docs/tw_modular_daily_update_productization/PHASEY1_STRICT_E4_DAILY_INFERENCE_REPAIR_EXECUTION_REPORT_CN.md
```

### 6.4 Y1 通过标准

```text
严格 E4 当前 asof Top10 可读取
Top10 lineage 指向 phasee1 frozen qlib + phasee3 LTR
P3 不再被误称为 E4
默认候选不会 fallback
前端用户能看懂 ready/unavailable 原因
只读边界未破坏
```

## 7. 给执行者的 Prompt

```text
请按 docs/tw_modular_daily_update_productization/PHASEY_STRICT_E4_DAILY_DEFAULT_REPAIR_WORK_CN.md 执行 Phase Y0。目标是修复默认 E4 名义与真实日更产物不一致的问题。

Y0 只做合同冻结与偏差审计，不训练、不调参、不改默认、不触发 provider accepted latest、不写 monitor、不接 broker/order。请明确区分 P3 daily_ltr_rerank=fresh qlib+O4 LTR 与 strict E4=frozen qlib 2018-2022+E3 LTR 2023-2025，并证明当前 strict E4 今日 artifact 是否存在、是否非空。输出 PHASEY0_STRICT_E4_CONTRACT_AND_MISMATCH_AUDIT_EXECUTION_REPORT_CN.md。
```

## 8. 给审查者的 Prompt

```text
请审查 docs/tw_modular_daily_update_productization/PHASEY0_STRICT_E4_CONTRACT_AND_MISMATCH_AUDIT_EXECUTION_REPORT_CN.md，判断是否可以进入 Y1。

重点确认：
1. 是否冻结 strict E4 = phasee1 frozen qlib 2018-2022 + phasee3 LTR 2023-2025；
2. 是否明确 P3 fresh qlib + O4 LTR 只能作为 legacy parallel candidate，不得冒充 E4；
3. 是否证明当前 strict E4 今日 artifact 的真实状态；
4. 是否禁止 fallback；
5. 是否未触发训练、provider latest、monitor、broker/order。

如果任何一项不清楚，不允许进入 Y1。
```

## 9. 收口口径

Phase Y 收口后才能说：

```text
默认候选严格等于 E4
今日 Top10 来自 2018-2022 frozen qlib + 2023-2025 orthogonal LTR
P3 fresh qlib + O4 LTR 不再被误认为默认 E4
```

Phase Y 收口前只能说：

```text
当前已有 fresh qlib + O4 LTR 日更候选；严格 E4 今日链路待 repair。
```
