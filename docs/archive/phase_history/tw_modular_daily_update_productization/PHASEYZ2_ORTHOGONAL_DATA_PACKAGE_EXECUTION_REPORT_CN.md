# PHASE YZ2 Orthogonal Data Package / Execution Price Readiness 执行报告

执行日期：2026-06-18

## 1. 执行范围

本次执行 `PHASEYZ1_REVIEW_AND_PHASEYZ2_WORK_CN.md` 中的 YZ2。

本阶段完成：

- 构建 strict E4 scoped top50 orthogonal feature package
- 使用 YZ1 Model A qlib top50 作为唯一候选范围
- 使用 E3 LTR model 生成 Model B 50 行 ModelSignalArtifact
- 生成 execution price readiness audit
- 生成 YZ2 门禁测试

本阶段未做：前端展示、paper apply/reset、replay 收益优劣判断、daily orchestrator 接入、accepted latest 切换、provider publish/refresh、新训练/调参、broker/order/quick-trade。

## 2. 修改文件

- `scripts/build_phase_yz2_orthogonal_package.py`
- `scripts/validate_tw_daily_model_signal_artifact.py`
- `backend/tests/test_phase_yz2_orthogonal_package.py`

## 3. Orthogonal Readiness 脱离 P3/Fresh

YZ2 不再把以下文件作为 strict E4 全局 readiness：

```text
data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_latest.json
```

该路径仅在 source freshness audit 中作为“未使用”的审计证据出现：

```text
p3_daily_ltr_rerank_latest_used_as_readiness = false
```

YZ2 orthogonal package 的候选范围来自：

```text
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_a/manifest.json
```

并显式声明：

```text
scoped_model_id = e4_frozen_qlib_2018_2022
model_neutral_full150 = false
```

## 4. Orthogonal Feature Package

产物：

```text
data_tw/artifacts/phase_yz/yz2_orthogonal_feature_package/2026-06-17/manifest.json
```

关键结果：

- `artifact_type = YZ2StrictE4OrthogonalFeaturePackage`
- `signal_asof = 2026-06-17`
- `row_count = 50`
- `covered_symbols = 50`
- `missing_symbols = []`
- `coverage_ratio = 1.0`
- `feature_schema_column_count = 78`
- `pit_violation_count = 0`
- `no_fallback = true`

特征列对齐审计：

```text
data_tw/artifacts/phase_yz/yz2_orthogonal_feature_package/2026-06-17/feature_schema_alignment_audit.csv
```

结果：`78,78,,,pass`

strict E4 top50 覆盖审计：

```text
data_tw/artifacts/phase_yz/yz2_orthogonal_feature_package/2026-06-17/strict_e4_top50_coverage_audit.csv
```

结果：50/50 覆盖。

PIT available_at 审计：

```text
data_tw/artifacts/phase_yz/yz2_orthogonal_feature_package/2026-06-17/pit_available_at_audit.csv
```

结果：`checked_rows=50`, `pit_violation_count=0`, `status=pass`。

forbidden field audit：

```text
data_tw/artifacts/phase_yz/yz2_orthogonal_feature_package/2026-06-17/forbidden_field_audit.csv
```

结果：`forbidden_field_count=0`, `status=pass`。

source freshness audit：

```text
data_tw/artifacts/phase_yz/yz2_orthogonal_feature_package/2026-06-17/source_freshness_audit.json
```

审计摘要：

- O2 PIT-safe source 覆盖 50 symbols
- O2 latest `available_at_max = 2026-06-11`
- 本地 normalized price latest date 为 `2026-06-01`
- `p3_daily_ltr_rerank_latest_used_as_readiness = false`

说明：YZ2 为完成 Model B rerank，对缺少当日实时更新的部分技术/rank-change字段采用审计可见的中性填充策略；不使用 future label/return/PnL，也不使用 P3/fresh candidate readiness。

## 5. Model B Artifact

产物：

```text
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b_yz2/manifest.json
```

关键结果：

- `model_id = e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`
- `row_count = 50`
- `source_model_a_manifest` 指向 YZ1 Model A
- `source_model_artifact` 指向 E3 LTR model
- `source_feature_artifact` 指向 YZ2 orthogonal package
- `candidate_rank` / `full_qlib_rank` 保留 Model A qlib top50 rank
- `score_rank` 来自 E3 LTR rerank score

source trace：

```text
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b_yz2/source_trace.json
```

关键审计：

```text
input_scope = YZ1 Model A qlib top50 only
fallback_to_p3_fresh_o4_bridge = false
```

validator result：

```text
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b_yz2/validator_result.json
```

结果：`ok=true`, `status=passed`, `row_count=50`。

## 6. Execution Price Readiness

产物：

```text
data_tw/artifacts/phase_yz/yz2_execution_price_readiness/2026-06-17/manifest.json
```

price availability audit：

```text
data_tw/artifacts/phase_yz/yz2_execution_price_readiness/2026-06-17/price_availability_audit.csv
```

结果：

- `row_count = 50`
- `close_on_or_before_signal_asof_available_count = 50`
- `missing_signal_close_count = 0`
- `next_open_available_count = 0`
- `next_close_available_count = 0`
- `missing_next_open_count = 50`
- `missing_next_close_count = 50`
- `status = execution_price_unavailable`
- `no_fallback_to_next_close = true`

原因：本地 qlib calendar 截止 `2026-06-17`，没有 `2026-06-18`；本地 normalized price source 也无法提供 `2026-06-18` next open/close。YZ2 按要求只做 readiness 审计，不 fallback 到 next close，也不做 open-vs-close 收益比较。

## 7. 验证命令与结果

已执行：

```bash
python -m py_compile scripts/build_phase_yz2_orthogonal_package.py scripts/validate_tw_daily_model_signal_artifact.py backend/tests/test_phase_yz2_orthogonal_package.py
```

结果：通过。

已执行：

```bash
python scripts/build_phase_yz2_orthogonal_package.py --signal-asof 2026-06-17 --json
```

结果：生成 YZ2 orthogonal package、Model B 50 行 artifact、execution price readiness。

已执行：

```bash
python scripts/validate_tw_daily_model_signal_artifact.py --manifest data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b_yz2/manifest.json --json --output-json data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b_yz2/validator_result.json
```

结果：`ok=true`, `status=passed`。

已执行：

```bash
python -m pytest backend/tests/test_phase_yz0_clean_registry.py backend/tests/test_phase_yz1_strict_e4_model_adapters.py backend/tests/test_phase_yz2_orthogonal_package.py -q
```

结果：`13 passed in 1.10s`

## 8. 禁止动作确认

本阶段未执行：

- 训练模型
- 调参
- provider refresh / publish
- accepted latest / qlib accepted latest switch
- monitor config / scan / alerts 写入
- broker / orders / quick-trade
- paper apply/reset 写路径改造
- 前端改造
- replay 收益优劣判断

## 9. 结论与 YZ3 建议

YZ2 的 orthogonal package 与 Model B 生成链路已完成：strict E4 Model A top50 覆盖 50/50，schema 78 列对齐，PIT 违规 0，Model B 50 行 LTR rerank artifact 已通过 validator。

但 execution price readiness 尚未通过 next_open 要求：当前本地数据没有 `2026-06-18` next open/close，因此 `status=execution_price_unavailable`。建议不要进入需要 replay/paper next_open 成交口径落地的 YZ3，除非先补齐本地价格 calendar 与 next trading day OHLC 数据；如果 YZ3 只审查模型选择/只读展示，也必须保留 execution price blocked 状态。
