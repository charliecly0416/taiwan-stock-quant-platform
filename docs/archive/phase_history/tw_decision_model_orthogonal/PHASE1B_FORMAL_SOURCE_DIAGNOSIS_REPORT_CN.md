# Phase 1B Formal Source Diagnosis 工作报告

- 生成时间：`2026-06-11T05:35:33+00:00`
- 执行范围：只读诊断 `option_c_formal_source_missing_asof`。
- 本步骤未联网、未使用 token、未重拉数据、未生成全量 2023-2024 prediction、未训练模型、未写入或重建 Qlib provider、未执行 formal validation bypass、未进入 Phase2。
- 结论：formal-validation 失败不是 provider calendar 或 field inventory 问题，而是 accepted prediction universe 使用了静态 150 档集合，其中 `TW7769` 在 historical asof 上没有 dedicated Option C normalized OHLCV 记录。

## 1. 执行命令

```bash
python -m py_compile scripts/diagnose_tw_decision_orthogonal_phase1b_formal_source.py
python scripts/diagnose_tw_decision_orthogonal_phase1b_formal_source.py
```

说明：第一次运行诊断脚本时被本地 sandbox 的 `bwrap: loopback: Failed RTM_NEWADDR` 拦截；随后用同一只读命令在沙箱外执行成功。该命令不访问网络，只读取本地文件并写入本阶段允许的诊断产物。

## 2. Formal Validation 失败明细

| asof | status | errors | symbols_expected | symbols_found | symbols_with_asof | missing_files | missing_asof | provider_calendar_max | field_inventory |
|---|---|---|---:|---:|---:|---|---|---|---|
| 2023-01-03 | fail | option_c_formal_source_missing_asof | 150 | 150 | 149 | 空 | TW7769 | 2026-06-10 | pass |
| 2024-01-02 | fail | option_c_formal_source_missing_asof | 150 | 150 | 149 | 空 | TW7769 | 2026-06-10 | pass |
| 2024-01-03 | fail | option_c_formal_source_missing_asof | 150 | 150 | 149 | 空 | TW7769 | 2026-06-10 | pass |

判断：

- 三个目标日期均只有 `TW7769` 缺少 exact asof。
- 150 个 expected symbols 的 CSV 文件都存在，因此不是文件缺失。
- provider calendar 覆盖到 `2026-06-10`，因此不是 calendar stale。
- `open/high/low/close/volume/vwap/factor` 的 field inventory 通过，因此不是 feature bin 字段缺失。

## 3. Dedicated Option C Source 覆盖

关键覆盖证据：

| source | month | symbols | rows | note |
|---|---:|---:|---:|---|
| option_c_150_normalized | 2023-01 | 149 | 1937 | historical target month 缺 `TW7769` |
| option_c_150_normalized | 2024-01 | 149 | 3278 | historical target month 缺 `TW7769` |
| option_c_150_normalized | 2024-11 | 150 | 3150 | `TW7769` 开始进入 dedicated source 后恢复 150 |
| option_c_150_qlib_bin_calendar | 2023-01 | - | 13 | calendar 覆盖 2023-01-03 至 2023-01-31 |
| option_c_150_qlib_bin_calendar | 2024-01 | - | 22 | calendar 覆盖 2024-01-02 至 2024-01-31 |
| normalized_nonempty | 2023-01 | 1823 | 23691 | broader Yahoo normalized pool 覆盖存在，但不是当前 formal source |
| normalized_nonempty | 2024-01 | 1876 | 41213 | broader Yahoo normalized pool 覆盖存在，但不是当前 formal source |

`TW7769` 单 symbol 证据：

| source | exists | rows | min_date | max_date | has 2023-01-03 | has 2024-01-02 | has 2024-01-03 |
|---|---|---:|---|---|---|---|---|
| option_c_150_normalized | true | 388 | 2024-11-01 | 2026-06-10 | false | false | false |
| normalized_nonempty | true | 127 | 2025-11-18 | 2026-06-01 | false | false | false |
| phase0e_institutional_flow | false | 0 | - | - | false | false | false |
| phase0e_margin_short | false | 0 | - | - | false | false | false |

Phase0E archive 是后续正交增量特征 archive，不是当前 Option C formal validation 检查的 dedicated OHLCV source。它不能补足 `option_c_150_normalized/TW7769.csv` 在 2023-2024 target asof 上的缺口。

## 4. Universe 与 Symbols 对齐

accepted prediction universe 路径：

`qlib_pipeline/data_tw/experiments/option_c_forward_validation/timed_data_availability_retry_20260601T101323Z/symbols_accepted_prediction_universe.txt`

诊断结果：

- universe count 为 150。
- `TW7769` 在 accepted universe 中。
- 该 universe 是 forward validation 产物下的静态 accepted prediction universe，不是按 historical asof 动态裁剪的 universe。
- `option_c_150_qlib_bin/instruments/all.txt` 对 `TW7769` 记录为 `2024-11-01` 至 `2026-06-10`。
- 现有 formal validation 对所有 accepted universe symbols 要求 exact asof；因此在 `2023-01-03`、`2024-01-02`、`2024-01-03` 会把尚未进入 source 覆盖期的 `TW7769` 判定为缺 asof。

因此，失败原因是 universe/source 的 historical asof 对齐问题，不是全市场数据整体缺失，也不是 Phase0E archive 缺失。

## 5. 2023 pred_fast Provenance

诊断结果：

- `prediction.csv` 文件数：239。
- prediction columns 唯一格式：`asof,instrument,score,rank,diagnostic_only,research_signal_not_order`。
- 目录日期 token 形如 `2023''01''03`，ISO 日期 token 可解析数为 0。
- `run_metadata.json` 存在，但仅包含状态、asof、研究信号标记、刷新/发布/交易类 mutation flag 等有限字段。
- 未发现足够的 `config_path`、`model_path`、`recorder_id/frozen_recorder`、`provider_uri/input_source` provenance 字段。

结论：

- `pred_fast_provenance_sufficient_for_standardization=false`
- 不能把 2023 `pred_fast` artifact 直接标准化混入 Phase1B repaired baseline。

## 6. 修复路径判断

本阶段只诊断，不执行修复。

结论标记：

- `formal_source_fix_possible_without_mutation=true`
- `formal_source_repair_requires_provider_rebuild=false`
- `requires_model_training=false`
- `requires_bypass=false`
- `prediction_repair_requires_bypass_stop=false`
- `pred_fast_provenance_sufficient_for_standardization=false`

解释：

- 当前 dedicated provider 已经有 calendar 和字段，且 `TW7769` 的 provider instrument 起始日为 `2024-11-01`。失败来自 static accepted universe 在 historical asof 上包含了尚无数据的 symbol。
- 不需要通过重建 provider、训练模型或绕过 formal validation 来解释该失败。
- 潜在主线修复应是让 historical formal validation / prediction 使用 asof-aware universe，对每个 asof 只纳入 dedicated source 在该日有记录的 symbols；这属于读取与 universe 对齐逻辑修正，不是本阶段允许执行的全量 repair。
- 是否授权实现该修复并重新做 Phase1B prediction repair，需要审查者下一步裁决。

## 7. 产物

- 诊断脚本：`scripts/diagnose_tw_decision_orthogonal_phase1b_formal_source.py`
- Formal validation 明细：`data_tw/experiments/decision_orthogonal/phase1b_formal_source_diagnosis_validation.csv`
- Source coverage：`data_tw/experiments/decision_orthogonal/phase1b_formal_source_diagnosis_source_coverage.csv`
- Symbol gaps：`data_tw/experiments/decision_orthogonal/phase1b_formal_source_diagnosis_symbol_gaps.csv`
- pred_fast inventory：`data_tw/experiments/decision_orthogonal/phase1b_formal_source_diagnosis_pred_fast_inventory.csv`
- Summary：`data_tw/experiments/decision_orthogonal/phase1b_formal_source_diagnosis_summary.json`

