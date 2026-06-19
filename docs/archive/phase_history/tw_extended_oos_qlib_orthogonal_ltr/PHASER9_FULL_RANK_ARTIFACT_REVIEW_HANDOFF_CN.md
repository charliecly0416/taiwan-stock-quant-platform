# Phase R9 FullRankArtifact 标准化审查交接

生成日期：2026-06-16

## 1. 本阶段目标

R9 根据 post-R8 cleanup 文档执行：

```text
FullRankArtifact 标准化
```

目标是让 config-driven replay 不再直接读取 legacy full rank CSV 和 legacy rank column。

## 2. 审查对象

新增：

```text
docs/tw_modular_contracts/FULL_RANK_CONTRACT_CN.md
scripts/build_tw_modular_full_rank_adapter.py
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER9_FULL_RANK_ARTIFACT_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER9_FULL_RANK_ARTIFACT_REVIEW_HANDOFF_CN.md
data_tw/artifacts/full_rank/fresh_qlib_s2b_post_filter/r9_full_rank_adapter_20260616/
data_tw/artifacts/full_rank/frozen_qlib_2018_2022_raw_oos/r9_full_rank_adapter_20260616/
```

更新：

```text
configs/tw_modular_replay_matrix.yaml
scripts/run_tw_modular_config_replay_matrix.py
scripts/validate_tw_modular_artifact_contract.py
scripts/run_tw_modular_contract_regression.py
tests/unit/test_validate_tw_modular_artifact_contract.py
configs/tw_modular_registry.yaml
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/
```

## 3. 一键复核命令

```bash
python scripts/build_tw_modular_full_rank_adapter.py --json
python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/artifacts/full_rank/fresh_qlib_s2b_post_filter/r9_full_rank_adapter_20260616/manifest.json \
  --json
python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/artifacts/full_rank/frozen_qlib_2018_2022_raw_oos/r9_full_rank_adapter_20260616/manifest.json \
  --json
python scripts/run_tw_modular_config_replay_matrix.py --config configs/tw_modular_replay_matrix.yaml
python scripts/run_tw_modular_contract_regression.py --json
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

## 4. 当前复核结果

FullRank adapter：

```text
ok: true
fresh rows: 169366
frozen rows: 119862
```

FullRank validators：

```text
fresh full rank: ok=true
frozen full rank: ok=true
```

Replay parity：

```text
ok: true
parity_status: pass
summary: pass, 25 vs 25
daily_nav: pass, 1975 vs 1975
actions: pass, 3651 vs 3651
```

Action key parity：

```text
baseline_not_modular_count: 0
modular_not_baseline_count: 0
duplicate_baseline_action_key_count: 0
duplicate_modular_action_key_count: 0
value_mismatch_count: 0
status: pass
```

Regression：

```text
ok: true
signal_manifest_count: 5
strategy_dependency_count: 6
full_rank_artifact_count: 2
signal_validation_rows: 35
full_rank_validation_rows: 5
```

Tests：

```text
pytest: 13 passed
```

## 5. Legacy 直读清除检查

复核命令：

```bash
rg -n "full_rank_source|full_rank_col|qlib_rank_raw|phasee1_raw|phase_s2b_post_filter|load_full_rank_source" \
  scripts/run_tw_modular_config_replay_matrix.py
```

当前结果：

```text
no matches
```

说明：

- legacy source path / legacy rank column 仅存在于 FullRank adapter 和 FullRank artifact manifest/audit 中；
- replay runner 不再直接读取 legacy full rank CSV 或 legacy rank column。

## 6. 边界说明

R9 未执行：

- 训练；
- 调参；
- score recompute；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker / quick-trade / order。

R9 未修改：

- R1 canonical signals；
- 策略规则；
- 默认策略；
- 前端；
- 日更脚本。

R9 重跑 modular replay matrix，仅用于证明 FullRankArtifact 切换不改变 R8 parity。

## 7. R10 前置提醒

R9 没有解决 baseline actions 无 `window` 字段问题。

当前 action parity 仍显示：

```text
filter_policy: baseline_actions_prefix_by_2026_ytd_summary_action_plus_skipped_count
```

该问题应在 R10 按工作文档单独处理。

## 8. 建议审查重点

建议审查者重点看：

1. `FULL_RANK_CONTRACT_CN.md` 是否覆盖 R9 必需字段和禁止字段；
2. 两个 FullRankArtifact 的 row count / duplicate / non-null / PIT audit；
3. `configs/tw_modular_replay_matrix.yaml` 是否只引用 `full_rank_artifact`；
4. replay runner 是否不再直读 legacy full rank CSV/column；
5. replay parity 是否仍为 pass；
6. regression 是否纳入 full rank validation；
7. R9 是否没有越界执行 R10/R11。

## 9. 建议结论

若审查者确认以上输出可复核，建议 R9 通过，并允许进入 R10。
