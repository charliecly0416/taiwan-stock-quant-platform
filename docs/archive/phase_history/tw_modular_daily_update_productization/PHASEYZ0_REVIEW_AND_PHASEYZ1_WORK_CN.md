# Phase YZ0 审查与 Phase YZ1 Strict E4 Daily Model Adapters 工作文档

生成日期：2026-06-18

## 1. YZ0 审查结论

YZ0 通过，可以进入 YZ1。

审查对象：

```text
docs/tw_modular_daily_update_productization/PHASEYZ_STRICT_E4_PRODUCTIZATION_CLEANUP_WORK_CN.md
docs/tw_modular_daily_update_productization/PHASEYZ0_CLEAN_REGISTRY_EXECUTION_REPORT_CN.md
configs/tw_modular_registry.yaml
configs/tw_modular_replay_matrix.yaml
configs/tw_replay_window_policy.yaml
backend/app/services/readonly_replay_window.py
backend/app/routes/readonly_replay_window.py
backend/tests/test_phase_yz0_clean_registry.py
data_tw/artifacts/phase_yz/yz0_clean_registry_audit.json
```

已复跑：

```text
python -m py_compile backend/app/services/readonly_replay_window.py backend/app/routes/readonly_replay_window.py
python -m pytest backend/tests/test_phase_yz0_clean_registry.py -q
```

结果：

```text
5 passed
```

## 2. YZ0 通过项

### 2.1 Production model registry 已收口为两个 E4 模型

`configs/tw_modular_registry.yaml` 中 `production_models.production_selectable` 精确包含：

```text
e4_frozen_qlib_2018_2022
e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
```

旧模型已移出 production：

```text
e4_frozen_qlib_2023_2025_ltr
fresh_qlib_adaptive
fresh_qlib_2025_ltr
frozen_qlib_2025_ltr
frozen_qlib_2018_2022
p3_daily_ltr_rerank
o4_controlled_ltr
bridge_ltr
```

### 2.2 Strategy registry 已分层

生产可选策略：

```text
top50_exit_one_worst_sell
```

Research-only：

```text
one_sell_one_buy_correct
one_sell_one_buy_buggy_e8r
```

Deprecated：

```text
origin
original
top50_exit_all
sector_extension_analysis_smoke
dummy_new_strategy_dependency_smoke
m2_strategy_dependency_template
```

`one_sell_one_buy_buggy_e8r` 的展示名已中性化为：

```text
单换手异常候选（研究）
```

不得作为默认，不得作为有效策略优劣证据。

### 2.3 Replay matrix 与 replay policy 已分离

`configs/tw_modular_replay_matrix.yaml` 已标记：

```text
matrix_type: historical_research_matrix
not_frontend_or_api_selectable: true
```

并新增 `clean_production_matrix`，只包含两个 E4 模型和生产策略。

`configs/tw_replay_window_policy.yaml` 已收口：

```text
policy_version: replay_window_policy_yz0_clean_v1
default_model_id: e4_frozen_qlib_2018_2022
default_strategy_rule: top50_exit_one_worst_sell
```

### 2.4 Backend replay window 已改为 registry-driven

`backend/app/services/readonly_replay_window.py` 已移除旧 `VALID_RULES` 硬编码集合，策略校验改为读取 `configs/tw_modular_registry.yaml`：

```text
production strategy -> allow
research-only strategy -> research_only_strategy_not_valid_strategy_evidence
deprecated strategy -> deprecated_strategy_rule
unknown strategy -> unknown_strategy_rule
```

`backend/app/routes/readonly_replay_window.py` 默认模型/策略从 helper 读取，不再硬编码旧模型。

### 2.5 YZ0 未越界

报告与测试证据显示 YZ0 未执行：

```text
训练 / 调参
模型推理 / score recompute
latest / accepted latest 切换
provider refresh / publish
monitor config / scan / alerts 写入
broker / order / quick-trade
```

## 3. YZ0 残留注意事项

以下不阻塞 YZ0 通过，但必须在 YZ1-YZ3 持续约束：

```text
configs/tw_modular_replay_matrix.yaml 顶层仍保留历史 fresh/P3/旧模型矩阵，但已标为 historical_research_matrix，不得作为前端/API 来源。
frontend/src/views/tw-stock-monitor/index.vue 仍可能有旧默认模型/策略硬编码，YZ0 不要求改，必须留到 YZ3 修。
daily model signal/order intent/paper portfolio 仍未切到 clean registry，YZ0 不要求改，必须由 YZ1-YZ3 分阶段处理。
```

## 4. Phase YZ1 目标

YZ1 目标是把 daily model signal 从“历史 artifact 过滤”改成“真实加载冻结模型推理”。

YZ1 只做：

```text
Strict E4 模型 adapter
ModelSignalArtifact 生成
ModelSignalArtifact validator registry-driven 改造
当前本地 latest asof 的模型 A artifact
模型 B artifact 或 blocked manifest
```

YZ1 不做：

```text
provider refresh / publish
accepted latest 切换
前端展示
paper apply/reset 改造
order intent builder 改造
daily orchestrator 接入
新训练 / 调参
```

## 5. YZ1 输入与冻结模型

模型 A：

```text
model_id: e4_frozen_qlib_2018_2022
含义: 加载 E1 frozen qlib，对当日 150 universe 打分
训练窗口: 2018-01-01..2022-12-31
```

必须使用：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/run/phasee1_frozen_qlib_model.pkl
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_training_manifest.json
```

模型 B：

```text
model_id: e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
含义: 对模型 A 的 qlib top50 使用 E3 orthogonal LTR rerank
训练窗口: qlib 2018-2022, LTR 2023-2025
```

必须使用：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_ltr_model.pkl
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_training_manifest.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_feature_schema.csv
```

## 6. YZ1 必须实现

### 6.1 Model A adapter

输入：

```text
signal_asof
daily 150 universe/provider
E1 frozen qlib model
```

输出 ModelSignalArtifact 必须覆盖 150 行，并至少包含：

```text
instrument
signal_asof
available_at
raw_score
buy_score
score_rank
full_qlib_rank
candidate_rank
model_id
model_family
source_model_artifact
source_feature_artifact
```

要求：

```text
row_count = 150
full_qlib_rank 覆盖 1..150
candidate_rank 只给 qlib top50，非 top50 可为空
available_at <= signal_asof
source_model_artifact 指向 E1 frozen qlib
不得读取 legacy signal artifact 作为模型分数来源
```

### 6.2 Model B adapter

输入：

```text
Model A qlib top50
E3 orthogonal LTR model
E2 feature schema 78 columns
orthogonal feature package
```

输出：

```text
50 行 LTR rerank ModelSignalArtifact
保留 qlib rank / full_qlib_rank
生成 LTR raw_score / buy_score / score_rank / candidate_rank
```

如果当前正交特征覆盖不足，必须输出 blocked manifest：

```text
artifact_type: ModelSignalArtifactBlocked
model_id: e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
blocked_reason: orthogonal_feature_coverage_insufficient
missing_symbols: [...]
no_fallback: true
```

禁止：

```text
不得 fallback 到 P3/fresh top50
不得使用 O4 LTR
不得使用 option_c/fresh qlib score
不得用旧 e4_frozen_qlib_2023_2025_ltr artifact 代替
```

### 6.3 Validator 改造

`scripts/validate_tw_daily_model_signal_artifact.py` 必须：

```text
读取 configs/tw_modular_registry.yaml
只接受 YZ0 production_models.production_selectable 中的 model_id
校验 schema / model_id / row_count / rank columns / PIT / source_model_artifact / source_feature_artifact
不硬编码 e4_frozen_qlib_2023_2025_ltr
```

## 7. YZ1 产物要求

执行者必须输出：

```text
docs/tw_modular_daily_update_productization/PHASEYZ1_STRICT_E4_MODEL_ADAPTERS_EXECUTION_REPORT_CN.md
```

还必须输出：

```text
模型 A ModelSignalArtifact manifest
模型 A row coverage audit，必须证明 150/150
模型 B ModelSignalArtifact manifest 或 blocked manifest
模型 B coverage audit，若生成必须证明 50/50
validator result JSON
source artifact trace
```

建议产物目录：

```text
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/<signal_asof>/
```

## 8. YZ1 验收标准

YZ1 通过标准：

```text
模型 A 必须真实加载 E1 frozen qlib
模型 A 必须输出同 asof 150 行
模型 A 必须来自 2018-2022 frozen qlib，不能来自 legacy signal artifact
模型 B 若生成，必须只对模型 A qlib top50 使用 E3 LTR rerank
模型 B 若 blocked，必须明确阻塞原因和 missing symbols，不得 fallback
validator 必须 registry-driven
PIT available_at 违规数必须为 0
source_model_artifact / source_feature_artifact 必须可追踪
```

安全 gate：

```text
不得训练模型
不得调参
不得切 latest / accepted latest
不得 provider publish / refresh
不得 monitor / broker / order / quick-trade
不得改前端
不得改 paper apply/reset 写路径
```

## 9. YZ1 建议测试

至少执行：

```text
python -m py_compile scripts/build_tw_daily_model_signal_artifact.py scripts/validate_tw_daily_model_signal_artifact.py <新增 model adapter 脚本>
python -m pytest <新增或修改的 YZ1 tests> -q
python scripts/validate_tw_daily_model_signal_artifact.py --manifest <model_a_manifest>
python scripts/validate_tw_daily_model_signal_artifact.py --manifest <model_b_manifest_or_blocked_manifest>
```

如果模型 B blocked，validator 必须能识别 blocked manifest 是显式阻塞，而不是失败沉默。

## 10. 审查重点

审查 YZ1 时必须重点确认：

```text
是否真实加载 E1 frozen qlib，而不是过滤历史 signal artifact
是否真实加载 E3 LTR，且只作用于模型 A qlib top50
是否没有 P3/fresh/O4/bridge 混入
是否没有使用旧 e4_frozen_qlib_2023_2025_ltr
是否 row_count 和 rank 语义正确
是否 PIT-safe
如果 blocked，是否诚实 blocked 且没有 fallback
```

若任一不满足，停止，不允许进入 YZ2。
