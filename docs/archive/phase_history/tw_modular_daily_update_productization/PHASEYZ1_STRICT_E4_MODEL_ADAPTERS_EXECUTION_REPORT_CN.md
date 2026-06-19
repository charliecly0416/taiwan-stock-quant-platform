# PHASE YZ1 Strict E4 Daily Model Adapters 执行报告

执行日期：2026-06-18

## 1. 执行范围

本次执行 `PHASEYZ0_REVIEW_AND_PHASEYZ1_WORK_CN.md` 中的 YZ1：Strict E4 Daily Model Adapters。

本阶段只做：

- Strict E4 Model A adapter
- Model A ModelSignalArtifact 生成
- Model B blocked manifest 生成
- `scripts/validate_tw_daily_model_signal_artifact.py` registry-driven 改造
- 产物 validator result JSON 与 source trace 输出

本阶段未做：provider refresh/publish、accepted latest 切换、前端展示、paper apply/reset、order intent builder、daily orchestrator 接入、新训练或调参。

## 2. 修改文件

- `scripts/build_tw_daily_model_signal_artifact.py`
- `scripts/validate_tw_daily_model_signal_artifact.py`
- `backend/tests/test_phase_yz1_strict_e4_model_adapters.py`

## 3. Model A Adapter

模型：`e4_frozen_qlib_2018_2022`

输入模型文件：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/run/phasee1_frozen_qlib_model.pkl
```

输入训练 manifest：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_training_manifest.json
```

输入 qlib provider：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin
```

执行方式：

- 加载 E1 frozen qlib pickle。
- 校验类型为 `qlib.contrib.model.gbdt.LGBModel`。
- 用 `DatasetH + Alpha158 + model.predict(dataset, segment="snapshot")` 对 `2026-06-17` 做只读推理。
- 未读取 legacy signal artifact 作为分数来源。

输出 manifest：

```text
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a/manifest.json
```

关键结果：

- `row_count = 150`
- `full_qlib_rank = 1..150`
- `candidate_rank` 仅覆盖 qlib top50，即 50 行
- `available_at <= signal_asof` 违规数为 0
- `score_source = frozen_e1_qlib_model.predict`
- `legacy_signal_artifact_used_as_score_source = false`

覆盖审计：

```text
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a/coverage_audit.csv
```

source trace：

```text
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a/source_trace.json
```

validator result：

```text
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a/validator_result.json
```

结果：`ok=true`, `status=passed`。

## 4. Model B Adapter / Blocked Manifest

模型：`e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`

输入模型文件：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_ltr_model.pkl
```

输入训练 manifest：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_training_manifest.json
```

输入 E2 feature schema：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_feature_schema.csv
```

本次未生成 Model B 50 行 LTR rerank artifact，而是输出 blocked manifest。

原因：当前本地 strict E4 prework 显示，正交特征表只覆盖 Model A qlib top50 的 24/50，缺失 26 个 symbols，不满足 E3 LTR 对 Model A qlib top50 的完整覆盖要求。

blocked manifest：

```text
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b/manifest.json
```

关键字段：

- `artifact_type = ModelSignalArtifactBlocked`
- `blocked_reason = orthogonal_feature_coverage_insufficient`
- `required_rows = 50`
- `covered_rows = 24`
- `missing_symbols` 包含 26 个 symbols
- `no_fallback = true`

未 fallback 到 P3/fresh top50、O4 LTR、option_c/fresh qlib score 或旧 `e4_frozen_qlib_2023_2025_ltr` artifact。

coverage audit：

```text
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b/coverage_audit.json
```

source trace：

```text
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b/source_trace.json
```

validator result：

```text
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b/validator_result.json
```

结果：`ok=true`, `status=passed`。

## 5. Validator 改造

`validate_tw_daily_model_signal_artifact.py` 已改为读取：

```text
configs/tw_modular_registry.yaml -> production_models.production_selectable
```

只接受 YZ0 收口后的两个 production model：

- `e4_frozen_qlib_2018_2022`
- `e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`

validator 不再硬编码旧 `e4_frozen_qlib_2023_2025_ltr`。

新增/强化校验：

- schema / artifact_type
- registry-driven `model_id`
- row count
- `date + instrument` 唯一性
- `full_qlib_rank` 覆盖 `1..row_count`
- `candidate_rank` 覆盖 top50
- numeric rank/score 字段
- PIT：`available_at <= signal_asof`
- `source_model_artifact` / `source_feature_artifact` 存在
- 禁止 legacy signal artifact 作为 score source
- 支持 `ModelSignalArtifactBlocked`，并要求 `blocked_reason`、`missing_symbols`、`no_fallback=true`

## 6. 汇总产物

YZ1 source/audit 汇总：

```text
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/source_artifact_trace.json
```

## 7. 验证命令与结果

已执行：

```bash
python -m py_compile scripts/build_tw_daily_model_signal_artifact.py scripts/validate_tw_daily_model_signal_artifact.py backend/tests/test_phase_yz1_strict_e4_model_adapters.py
```

结果：通过。

已执行：

```bash
python -m pytest backend/tests/test_phase_yz0_clean_registry.py backend/tests/test_phase_yz1_strict_e4_model_adapters.py -q
```

结果：`9 passed in 1.10s`

已执行：

```bash
python scripts/build_tw_daily_model_signal_artifact.py --signal-asof 2026-06-17 --json
```

结果：Model A 150 行生成，Model B blocked manifest 生成。

已执行：

```bash
python scripts/validate_tw_daily_model_signal_artifact.py --manifest data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a/manifest.json --json --output-json data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a/validator_result.json
```

结果：`ok=true`, `status=passed`。

已执行：

```bash
python scripts/validate_tw_daily_model_signal_artifact.py --manifest data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b/manifest.json --json --output-json data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b/validator_result.json
```

结果：`ok=true`, `status=passed`。

已执行静态检查：

```bash
rg -n "e4_frozen_qlib_2023_2025_ltr|DEFAULT_SIGNAL_MANIFEST|r1_legacy_signal_adapter" scripts/build_tw_daily_model_signal_artifact.py scripts/validate_tw_daily_model_signal_artifact.py
```

结果：无命中。

## 8. 禁止动作确认

本阶段未执行：

- 训练模型
- 调参
- 切换 latest / accepted latest
- provider refresh / publish
- monitor scan/config/alerts 写入
- broker / order / quick-trade
- 前端改造
- paper apply/reset 写路径改造
- daily orchestrator 接入

## 9. 结论

YZ1 已完成。

Model A 已用 E1 frozen qlib 模型真实加载并推理生成 150/150 ModelSignalArtifact；Model B 因当前正交特征覆盖不足诚实 blocked，且明确 no_fallback。validator 已改为 registry-driven，并通过 Model A 与 Model B blocked manifest 校验。

可进入 YZ2，但 YZ2 不应绕过 Model B blocked 状态，也不得引入 P3/fresh/O4/bridge fallback。
