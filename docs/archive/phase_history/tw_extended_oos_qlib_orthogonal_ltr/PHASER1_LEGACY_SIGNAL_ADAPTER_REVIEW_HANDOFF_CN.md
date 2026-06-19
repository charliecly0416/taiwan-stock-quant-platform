# Phase R1 Legacy Signal Adapter 审查说明

生成日期：2026-06-16

## 1. 审查范围

本 handoff 供审查者复核 R1。R1 只新增 legacy signal adapter 和标准 `ModelSignalArtifact`，不进入 R2。

## 2. 新增/修改文件

```text
scripts/build_tw_modular_legacy_signal_adapter.py
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER1_LEGACY_SIGNAL_ADAPTER_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER1_LEGACY_SIGNAL_ADAPTER_REVIEW_HANDOFF_CN.md
data_tw/artifacts/signals/{model_name}/{run_id}/
```

## 3. Artifact 清单

| model_name | family | rows | duplicate_key | quality | window | manifest |
| --- | --- | ---: | ---: | --- | --- | --- |
| fresh_qlib_adaptive | qlib | 30630 | 0 | pass | 2025-07-01..2026-05-07 | `data_tw/artifacts/signals/fresh_qlib_adaptive/r1_legacy_signal_adapter_20260616/manifest.json` |
| fresh_qlib_2025_ltr | ltr | 3950 | 0 | pass | 2026-01-02..2026-05-07 | `data_tw/artifacts/signals/fresh_qlib_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json` |
| frozen_qlib_2025_ltr | ltr | 3950 | 0 | pass | 2026-01-02..2026-05-07 | `data_tw/artifacts/signals/frozen_qlib_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json` |
| e4_frozen_qlib_2023_2025_ltr | ltr | 3950 | 0 | pass | 2026-01-02..2026-05-07 | `data_tw/artifacts/signals/e4_frozen_qlib_2023_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json` |
| frozen_qlib_2018_2022 | qlib | 119862 | 0 | pass | 2023-01-03..2026-05-07 | `data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json` |

每个 artifact 目录必须包含：

```text
manifest.json
signals.csv
schema.json
coverage_audit.csv
forbidden_field_audit.csv
legacy_mapping_audit.csv
```

## 4. 建议复核命令

```bash
python scripts/build_tw_modular_legacy_signal_adapter.py --run-id r1_legacy_signal_adapter_20260616
find data_tw/artifacts/signals -path "*/r1_legacy_signal_adapter_20260616/manifest.json" -print
rg -n "fail" data_tw/artifacts/signals/*/r1_legacy_signal_adapter_20260616/*_audit.csv
git status --short frontend/src/views/tw-stock-monitor/index.vue scripts/run_daily_tw_stock_auto_update.py scripts/run_extended_oos_formal_replay_matrix.py
```

预期：

- 所有 manifest 的 `quality_status` 为 `pass`；
- audit 中无 `fail`；
- 前端、日更脚本、formal replay matrix 不应出现 R1 修改；
- `signals.csv` 只包含标准字段，不含 legacy 私有分数字段或 future label/return 字段。

## 5. 放行 R2 前必须确认

- row count 与 legacy 输入一致；
- `date + instrument` duplicate key 为 0；
- `candidate_rank`、`buy_score`、`full_qlib_rank` 对齐 legacy mapping；
- LTR 未改变 qlib top50 boundary；
- 未训练、未调参、未重算分数、未产生策略收益结论；
- 未触发 provider / accepted latest / monitor / broker / order。
