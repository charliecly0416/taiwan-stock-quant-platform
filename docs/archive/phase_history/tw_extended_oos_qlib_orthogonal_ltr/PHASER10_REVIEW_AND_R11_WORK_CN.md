# Phase R10 审查与 R11 工作建议

生成日期：2026-06-16

## 1. 审查结论

R10 审查通过，允许进入 R11。

本次未发现阻塞 R11 的问题。R10 已完成 baseline action window cleanup 的核心目标：

- 采用路径 B，新建 windowed baseline action artifact；
- 原始 baseline formal replay matrix 保持不变；
- baseline actions 已补 `window` 字段；
- modular actions 已有 `window` 字段；
- action parity 改为直接按 `window == 2026_ytd` 过滤；
- action key 包含 `window`；
- prefix compatibility 口径已清除；
- R9 发现的 `formal_replay_coverage_audit.csv.full_rank_artifact` 路径记录错误已修复；
- replay parity、ReplayResult validator、regression、unit tests 均通过；
- 未修改策略规则、默认策略、前端、日更或生产链路。

## 2. 审查对象

R10 handoff：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER10_BASELINE_ACTION_WINDOW_CLEANUP_REVIEW_HANDOFF_CN.md
```

R10 执行报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER10_BASELINE_ACTION_WINDOW_CLEANUP_EXECUTION_REPORT_CN.md
```

新增 adapter：

```text
scripts/build_formal_replay_baseline_action_window_adapter.py
```

Windowed baseline artifact：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix_windowed/
```

关键更新：

```text
configs/tw_modular_replay_matrix.yaml
scripts/run_tw_modular_config_replay_matrix.py
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/
```

## 3. 复核结果

### 3.1 Baseline window adapter 可复跑

复核命令：

```bash
python scripts/build_formal_replay_baseline_action_window_adapter.py --json
```

结果：

```text
ok: true
windowed_action_rows: 23571
source_action_rows: 23571
```

Adapter 行为：

- 读取原始 baseline `formal_replay_summary.csv` 和 `formal_replay_actions.csv`；
- 按 summary 原始写出顺序和 `action_count + skipped_trade_count` 为 actions 补 `window`；
- 保留 `source_action_row_index`；
- 生成 `action_window_assignment_audit.csv`；
- 不修改原始 baseline 目录。

`action_window_assignment_audit.csv` 全部为 `pass`，总分配行数为 `23571`，与 source actions 行数一致。

### 3.2 Config 已切换到 windowed baseline

`configs/tw_modular_replay_matrix.yaml`：

```text
baseline.dir: data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix_windowed
baseline.source_dir: data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix
baseline.window_adapter_manifest: data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix_windowed/manifest.json
```

说明：

- parity 使用 windowed baseline；
- 原始 baseline formal replay matrix 保持只读不变；
- source_dir 和 adapter manifest 保留追溯入口。

### 3.3 Action parity 已改为 direct window filter

`scripts/run_tw_modular_config_replay_matrix.py` 的 `action_key_parity()` 现在要求：

```text
baseline actions 必须包含 window
modular actions 必须包含 window
baseline.window == 2026_ytd
modular.window == 2026_ytd
action key 包含 window
```

复核旧兼容口径：

```bash
rg -n "baseline_actions_prefix|first N rows|head\\(expected_rows\\)|expected_rows|prefix count" \
  scripts/run_tw_modular_config_replay_matrix.py \
  data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/r10_action_window_parity_audit.csv \
  data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/r2_action_key_parity_audit.csv
```

结果：无匹配。

保留说明：

- Adapter 生成 windowed baseline 时仍依赖 baseline summary 写出顺序和 row count，这是路径 B 的定义；
- parity 阶段不再使用 prefix comparison，而是使用标准 `window` 字段直接过滤。

### 3.4 R10 action window parity 通过

复核文件：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/r10_action_window_parity_audit.csv
```

结果：

```text
filter_policy: direct_window_filter_2026_ytd
baseline_window_field_present: True
modular_window_field_present: True
baseline_total_rows: 23571
baseline_filtered_rows: 3651
modular_action_rows: 3651
baseline_unique_action_keys: 3651
modular_unique_action_keys: 3651
baseline_not_modular_count: 0
modular_not_baseline_count: 0
duplicate_baseline_action_key_count: 0
duplicate_modular_action_key_count: 0
value_mismatch_count: 0
status: pass
```

### 3.5 Replay parity 复跑通过

复核命令：

```bash
python scripts/run_tw_modular_config_replay_matrix.py --config configs/tw_modular_replay_matrix.yaml
```

结果：

```text
ok: true
parity_status: pass
summary: pass, 25 vs 25
daily_nav: pass, 1975 vs 1975
actions: pass, 3651 vs 3651
```

`formal_replay_manifest.json` 已更新为：

```text
schema_version: replay_result_r10_action_window_cleanup
baseline_windowed_dir: data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix_windowed
action_key_parity_audit: .../r10_action_window_parity_audit.csv
action_window_compatibility.direct_window_filter_2026_ytd: true
action_window_compatibility.parity_key_includes_window: true
action_window_compatibility.parity_key_excludes_window_for_baseline_compatibility: false
capabilities.action_window_parity_no_prefix: true
```

### 3.6 R9 coverage audit 问题已修复

复核文件：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_coverage_audit.csv
```

现在同时记录：

```text
signal_artifact
full_rank_artifact
```

`full_rank_artifact` 正确指向：

```text
data_tw/artifacts/full_rank/fresh_qlib_s2b_post_filter/r9_full_rank_adapter_20260616/manifest.json
data_tw/artifacts/full_rank/frozen_qlib_2018_2022_raw_oos/r9_full_rank_adapter_20260616/manifest.json
```

不再误写为 signal manifest 路径。

### 3.7 ReplayResult validator 通过

复核命令：

```bash
python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json \
  --json
```

结果：

```text
ok: true
schema_version: replay_result_r10_action_window_cleanup
actions_window_field: pass
parity_audit_status: pass
action_key_parity_audit_status: pass
manifest_parity_status: pass
```

### 3.8 Regression 通过

复核命令：

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

`parity_summary.csv` 已显示：

```text
actions: pass
details: direct window filter: baseline.window == modular.window == 2026_ytd
filter_policy: direct_window_filter_2026_ytd
```

### 3.9 Tests 通过

复核命令：

```bash
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：

```text
13 passed
```

### 3.10 Forbidden scope 通过

`forbidden_scope_audit.csv`：

```text
frontend/src/views/tw-stock-monitor/index.vue: pass
scripts/run_daily_tw_stock_auto_update.py: pass
scripts/run_extended_oos_formal_replay_matrix.py: pass
backend_api_python: pass
src/api: pass
```

额外 tracked diff 复核对象：

```text
data_tw/artifacts/signals/*/r1_legacy_signal_adapter_20260616/signals.csv
frontend/src/views/tw-stock-monitor/index.vue
scripts/run_daily_tw_stock_auto_update.py
scripts/run_extended_oos_formal_replay_matrix.py
```

结果：无 tracked diff。

## 4. 非阻塞建议

### P3：Windowed baseline artifact 后续发布前建议补 checksum

R10 adapter 已记录 `source_action_row_index` 和 assignment audit，足以支持本阶段审查。

如果后续进入 release packaging 或 production readiness，建议补充：

```text
source formal_replay_actions.csv checksum
windowed formal_replay_actions.csv checksum
summary checksum
daily_nav checksum
```

用途：

- 证明 windowed artifact 只新增 `window` 和 `source_action_row_index`；
- 防止正式打包时混入非 R10 范围内的 baseline 改动；
- 方便 R11 或后续 shadow integration 做不可变产物检查。

该项不阻塞 R11。

### P3：生成报告仍沿用 R2 文件名

`scripts/run_tw_modular_config_replay_matrix.py` 仍会写：

```text
PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_EXECUTION_REPORT_CN.md
PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_REVIEW_HANDOFF_CN.md
```

这是历史脚本行为，不影响 R10 的核心 artifact 和 R10 handoff，但后续如果继续维护该脚本，建议将自动生成报告从固定 R2 名称解耦，避免 post-R8 cleanup 阶段误导审查者。

该项不阻塞 R11。

## 5. 残余风险

### 5.1 Window assignment 仍依赖 baseline summary 写出顺序

路径 B 的本质是用 baseline summary 的原始顺序和 `action_count + skipped_trade_count` 给 actions 补 window。R10 已通过 audit 证明行数覆盖完整，并通过 direct window parity 证明 `2026_ytd` action keys 与 modular 完全一致。

后续生产 readiness 不应把该 adapter 解释为重新生成 baseline 回放，只能解释为 baseline action window normalization。

### 5.2 R10 仍不是生产接入

R10 只清理 parity 审计口径，不代表：

- 策略可上线；
- 默认策略可切换；
- 可接前端；
- 可接日更；
- 可 provider publish / accepted latest；
- 可 monitor / broker / order。

## 6. R11 工作建议

允许执行 R11：Readonly Production Readiness Review。

R11 目标不是实际接入生产，而是形成只读生产接入前审查和 shadow plan。

R11 必须产出：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER11_READONLY_PRODUCTION_READINESS_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER11_READONLY_PRODUCTION_READINESS_REVIEW_HANDOFF_CN.md
```

建议 R11 覆盖：

- 当前 canonical artifacts 清单；
- R9/R10 后 replay result manifest；
- checksum / package manifest 草案；
- frontend/API 只读展示 contract 草案；
- daily update 只读 shadow plan；
- provider publish 与 accepted latest governance；
- failure / retry / rollback policy；
- monitor、broker、quick-trade、order 隔离审计；
- 哪些内容允许 shadow 观察；
- 哪些内容仍禁止生产启用。

R11 必须明确：

- 不实际修改前端；
- 不实际修改日更 orchestrator；
- 不 provider publish；
- 不切换 accepted latest；
- 不触发 monitor scan/config save；
- 不触发 broker、quick-trade 或 order；
- 不根据 replay 收益切换默认策略。

## 7. R11 禁止事项

R11 禁止：

- 训练；
- 调参；
- score recompute；
- 新 replay 策略收益结论；
- 修改 R1 canonical signals；
- 修改策略规则；
- 修改默认策略；
- 实际前端接入；
- 实际日更接入；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker、quick-trade 或 order。

## 8. 最终结论

R10 通过。

R10 已消除 baseline action parity 的 prefix compatibility 口径，action parity 现在直接基于 `window == 2026_ytd`，且 R9 full-rank coverage audit 追溯问题已修复。允许进入 R11，但 R11 只能做只读生产 readiness / shadow plan，不得实际接入生产链路。
