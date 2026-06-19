# Phase R9 FullRankArtifact 标准化执行报告

生成日期：2026-06-16

## 1. 执行范围

本阶段根据：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER9_R11_POST_R8_CLEANUP_AND_READONLY_PRODUCTION_PREP_WORK_CN.md
```

仅执行 R9：

```text
FullRankArtifact 标准化
```

目标是消除 config-driven replay 对 legacy full rank CSV 和 legacy rank column 的直接依赖。

## 2. 新增/修改内容

新增合同：

```text
docs/tw_modular_contracts/FULL_RANK_CONTRACT_CN.md
```

新增 adapter：

```text
scripts/build_tw_modular_full_rank_adapter.py
```

新增 FullRankArtifact 输出：

```text
data_tw/artifacts/full_rank/fresh_qlib_s2b_post_filter/r9_full_rank_adapter_20260616/
data_tw/artifacts/full_rank/frozen_qlib_2018_2022_raw_oos/r9_full_rank_adapter_20260616/
```

每个目录包含：

```text
manifest.json
full_rank.csv
schema.json
coverage_audit.csv
forbidden_field_audit.csv
legacy_mapping_audit.csv
```

更新：

```text
configs/tw_modular_replay_matrix.yaml
scripts/run_tw_modular_config_replay_matrix.py
scripts/validate_tw_modular_artifact_contract.py
scripts/run_tw_modular_contract_regression.py
tests/unit/test_validate_tw_modular_artifact_contract.py
configs/tw_modular_registry.yaml
```

## 3. FullRankArtifact 输出

执行命令：

```bash
python scripts/build_tw_modular_full_rank_adapter.py --json
```

结果：

```text
ok: true
fresh_qlib_s2b_post_filter rows: 169366
frozen_qlib_2018_2022_raw_oos rows: 119862
```

### 3.1 fresh full rank

```text
manifest: data_tw/artifacts/full_rank/fresh_qlib_s2b_post_filter/r9_full_rank_adapter_20260616/manifest.json
row_count: 169366
date_count: 2260
start_date: 2017-01-10
end_date: 2026-05-07
instrument_count: 150
duplicate_key_count: 0
full_qlib_rank_non_null_count: 169366
pit_available_at_after_signal_asof_count: 0
status: pass
```

### 3.2 frozen full rank

```text
manifest: data_tw/artifacts/full_rank/frozen_qlib_2018_2022_raw_oos/r9_full_rank_adapter_20260616/manifest.json
row_count: 119862
date_count: 802
start_date: 2023-01-03
end_date: 2026-05-07
instrument_count: 150
duplicate_key_count: 0
full_qlib_rank_non_null_count: 119862
pit_available_at_after_signal_asof_count: 0
status: pass
```

## 4. Config / Replay 改造

`configs/tw_modular_replay_matrix.yaml` 已从：

```text
full_rank_source
full_rank_col
```

改为：

```text
full_rank_artifact: data_tw/artifacts/full_rank/.../manifest.json
```

`scripts/run_tw_modular_config_replay_matrix.py` 已改为：

```text
load_full_rank_artifact(manifest)
```

replay runner 只读取标准字段：

```text
date
instrument
full_qlib_rank
signal_asof
available_at
```

R9 legacy 关键词扫描：

```bash
rg -n "full_rank_source|full_rank_col|qlib_rank_raw|phasee1_raw|phase_s2b_post_filter|load_full_rank_source" \
  scripts/run_tw_modular_config_replay_matrix.py
```

结果：无匹配。

## 5. Validator

`scripts/validate_tw_modular_artifact_contract.py` 已支持：

```text
artifact_type: full_rank
```

验证项包括：

- artifact type；
- schema / contract version；
- `full_rank.csv` 存在；
- core fields；
- duplicate key；
- forbidden fields；
- `full_qlib_rank` 非空；
- `available_at <= signal_asof`；
- manifest row count；
- required audit files。

两个 FullRankArtifact validator 均为：

```text
ok: true
```

## 6. Replay Parity

执行命令：

```bash
python scripts/run_tw_modular_config_replay_matrix.py --config configs/tw_modular_replay_matrix.yaml
```

结果：

```text
ok: true
parity_status: pass
```

Parity：

```text
summary: pass, 25 vs 25
daily_nav: pass, 1975 vs 1975
actions: pass, 3651 vs 3651
```

Action key parity：

```text
baseline_filtered_rows: 3651
modular_action_rows: 3651
baseline_not_modular_count: 0
modular_not_baseline_count: 0
duplicate_baseline_action_key_count: 0
duplicate_modular_action_key_count: 0
value_mismatch_count: 0
status: pass
```

说明：R9 没有处理 baseline actions 无 `window` 的历史问题，该问题按工作文档留给 R10。

## 7. Regression

`scripts/run_tw_modular_contract_regression.py` 已纳入 FullRankArtifact validation。

执行命令：

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

结果：

```text
ok: true
signal_manifest_count: 5
strategy_dependency_count: 6
full_rank_artifact_count: 2
signal_validation_rows: 35
full_rank_validation_rows: 5
```

输出：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/full_rank_artifact_validation.csv
```

5 个 method 的 full rank validation 均为 `True`。

## 8. Tests

执行命令：

```bash
python -m py_compile scripts/build_tw_modular_full_rank_adapter.py scripts/run_tw_modular_config_replay_matrix.py scripts/validate_tw_modular_artifact_contract.py scripts/run_tw_modular_contract_regression.py
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：

```text
py_compile: pass
pytest: 13 passed
```

## 9. 边界确认

R9 未执行、未修改：

- qlib / LTR 训练；
- 调参；
- score recompute；
- R1 canonical signals；
- 策略规则；
- 默认策略；
- 新策略收益结论；
- 前端；
- 日更脚本；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker / quick-trade / order。

R9 重跑了 config-driven modular replay，仅用于验证 FullRankArtifact 切换后的 parity，未新增策略逻辑。

## 10. 残余风险

1. baseline actions 仍无 `window` 字段，action parity 仍使用 R5/R8 已归档的 prefix compatibility 口径。该问题属于 R10。
2. FullRankArtifact adapter 仍从 legacy rank CSV 构建，但 replay runner 已不直接读取 legacy path/column。
3. `available_at=date` 是 legacy parity mode，不代表真实生产 data availability governance。

## 11. 结论

R9 已完成。

R9 后：

- FullRankArtifact contract 已定义；
- 两个 full rank artifact 已生成并通过 validator；
- replay config 已切换为引用 FullRankArtifact manifest；
- replay runner 不再直读 legacy full rank CSV/column；
- R8 modular replay parity 保持完全一致；
- regression 与单测通过。
