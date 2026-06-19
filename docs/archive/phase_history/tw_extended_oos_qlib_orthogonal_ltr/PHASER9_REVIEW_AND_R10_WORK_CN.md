# Phase R9 审查与 R10 工作建议

生成日期：2026-06-16

## 1. 审查结论

R9 审查通过，允许进入 R10。

本次未发现阻塞 R10 的问题。R9 已完成 `FullRankArtifact` 标准化的核心目标：

- 新增 `FullRankArtifact` 合同；
- 生成两个标准 full rank artifacts；
- replay config 从 legacy `full_rank_source/full_rank_col` 切换为 `full_rank_artifact` manifest；
- replay runner 不再直读 legacy full rank CSV 或 legacy rank column；
- ReplayResult manifest 记录 `full_rank_artifacts`；
- FullRankArtifact validator 通过；
- config-driven replay parity 保持 pass；
- full registry regression 纳入 full rank validation；
- 未越界执行 R10/R11；
- 未接入前端、日更、provider publish、accepted latest、monitor 或交易链路。

## 2. 审查对象

R9 工作基准：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER9_R11_POST_R8_CLEANUP_AND_READONLY_PRODUCTION_PREP_WORK_CN.md
```

R9 handoff：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER9_FULL_RANK_ARTIFACT_REVIEW_HANDOFF_CN.md
```

R9 执行报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER9_FULL_RANK_ARTIFACT_EXECUTION_REPORT_CN.md
```

关键实现：

```text
docs/tw_modular_contracts/FULL_RANK_CONTRACT_CN.md
scripts/build_tw_modular_full_rank_adapter.py
scripts/run_tw_modular_config_replay_matrix.py
scripts/validate_tw_modular_artifact_contract.py
scripts/run_tw_modular_contract_regression.py
configs/tw_modular_replay_matrix.yaml
configs/tw_modular_registry.yaml
```

## 3. 复核结果

### 3.1 FullRankArtifact 合同覆盖 R9 必需字段

`FULL_RANK_CONTRACT_CN.md` 定义的标准字段：

```text
date
instrument
rank_source_name
rank_family
full_qlib_rank
signal_asof
available_at
source_artifact
```

合同已明确：

- `full_qlib_rank` 是完整 qlib 候选空间 rank；
- 不得表示 LTR rank；
- 不得包含 future label / return / realized pnl；
- `available_at <= signal_asof`；
- legacy adapter 可用 `available_at=date` 保持历史 replay parity；
- 生成 artifact 时禁止训练、调参、score recompute、前端、日更、publish、accepted latest、monitor、broker/order。

### 3.2 FullRankAdapter 可复跑

复核命令：

```bash
python scripts/build_tw_modular_full_rank_adapter.py --json
```

结果：

```text
ok: true
fresh_qlib_s2b_post_filter rows: 169366
frozen_qlib_2018_2022_raw_oos rows: 119862
```

R9 adapter 从 legacy rank CSV 构建标准 full rank artifact，这是 R9 允许的 adapter 边界。关键是 replay runner 不再直接读取 legacy source。

### 3.3 FullRankArtifact validators 通过

复核命令：

```bash
python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/artifacts/full_rank/fresh_qlib_s2b_post_filter/r9_full_rank_adapter_20260616/manifest.json \
  --json

python scripts/validate_tw_modular_artifact_contract.py \
  --artifact data_tw/artifacts/full_rank/frozen_qlib_2018_2022_raw_oos/r9_full_rank_adapter_20260616/manifest.json \
  --json
```

结果均为：

```text
ok: true
artifact_type: pass
schema_version: pass
contract_version: pass
full_rank_file_declared: pass
core_fields: pass
duplicate_key: pass
forbidden_fields: pass
full_qlib_rank_non_null: pass
available_at_lte_signal_asof: pass
manifest_row_count: pass
quality_status: pass
schema_exists: pass
coverage_audit_exists: pass
forbidden_field_audit_exists: pass
legacy_mapping_audit_exists: pass
```

关键数值：

```text
fresh full rank: 169366/169366 full_qlib_rank non-null, duplicate_key=0, PIT violations=0
frozen full rank: 119862/119862 full_qlib_rank non-null, duplicate_key=0, PIT violations=0
```

### 3.4 Replay config 已切换到 full_rank_artifact

`configs/tw_modular_replay_matrix.yaml` 中五个 method 均使用：

```text
full_rank_artifact: data_tw/artifacts/full_rank/.../manifest.json
```

未发现 `full_rank_source` 或 `full_rank_col`。

### 3.5 Replay runner 已清除 legacy full-rank 直读

复核命令：

```bash
rg -n "full_rank_source|full_rank_col|qlib_rank_raw|phasee1_raw|phase_s2b_post_filter|load_full_rank_source" \
  scripts/run_tw_modular_config_replay_matrix.py
```

结果：无匹配。

`run_tw_modular_config_replay_matrix.py` 现在通过：

```text
load_full_rank_artifact(entry)
```

读取 full rank manifest，并只消费：

```text
date
instrument
full_qlib_rank
signal_asof
available_at
```

ReplayResult manifest 也正确记录：

```text
full_rank_artifacts
```

五个 method 分别指向两个 R9 FullRankArtifact manifest。

### 3.6 Replay parity 复跑通过

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

R9 重跑 modular replay matrix 是为了证明切换 FullRankArtifact 后不改变 R8 parity，不代表新增策略收益结论。

### 3.7 Regression 纳入 full rank validation

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

`full_rank_artifact_validation.csv` 中 5 个 method 均为：

```text
ok: True
```

说明 full-rank manifest 已被 regression 覆盖。

### 3.8 Tests 通过

复核命令：

```bash
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：

```text
13 passed
```

### 3.9 Forbidden scope 通过

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

## 4. 非阻塞发现

### P2：`formal_replay_coverage_audit.csv` 的 `full_rank_artifact` 列值写错

位置：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_coverage_audit.csv
scripts/run_tw_modular_config_replay_matrix.py
```

现象：

`formal_replay_coverage_audit.csv` 中 `full_rank_artifact` 列当前填的是 signal manifest 路径，例如：

```text
data_tw/artifacts/signals/fresh_qlib_adaptive/r1_legacy_signal_adapter_20260616/manifest.json
```

而不是 R9 full rank manifest 路径，例如：

```text
data_tw/artifacts/full_rank/fresh_qlib_s2b_post_filter/r9_full_rank_adapter_20260616/manifest.json
```

判断：

- 这不影响 replay 实际读取路径，因为 `formal_replay_manifest.json.full_rank_artifacts` 正确；
- 这不影响 parity，R9 回放结果已通过；
- 但它削弱了 coverage audit 的追溯性，与 R9 “FullRankArtifact 标准化”目标不完全一致。

建议：

在 R10 开始前或 R10 中顺手修复 `coverage_row()` 的参数，让 coverage audit 同时准确记录：

```text
signal_artifact
full_rank_artifact
```

修复后应重跑：

```bash
python scripts/run_tw_modular_config_replay_matrix.py --config configs/tw_modular_replay_matrix.yaml
python scripts/run_tw_modular_contract_regression.py --json
```

并确认 parity 仍为 pass。

该问题不阻塞 R10，因为 R9 的 replay engine 边界和 manifest 追溯已经正确，但不应遗留到生产 readiness 阶段。

## 5. 残余风险

### 5.1 Baseline action window 仍未清理

R9 未解决 baseline actions 无 `window` 字段问题。当前 action parity 仍使用：

```text
baseline_actions_prefix_by_2026_ytd_summary_action_plus_skipped_count
```

这是 R10 的主任务，不应在 R9 中继续扩大。

### 5.2 FullRankAdapter 仍依赖 legacy source

R9 标准化的是 replay 输入，不是完全消除 legacy source。FullRankArtifact adapter 仍从 legacy rank CSV 构建，并在 manifest / mapping audit 中记录 legacy source 和 source rank column。

这是合理边界，但后续若要进入生产，应补充真实 data availability governance，而不能把 `available_at=date` 直接当作生产级 PIT 政策。

### 5.3 R9 replay 仍是研究/审计 replay

R9 只证明 full-rank 输入标准化后 R8 parity 不变，不证明任何策略应进入生产、默认策略、前端或日更链路。

## 6. R10 工作建议

允许执行 R10：Baseline Action Window Cleanup。

R10 目标：

- 消除 baseline actions 无 `window` 字段导致的 prefix compatibility；
- 让 baseline 和 modular actions 都可按 `window == 2026_ytd` 直接过滤；
- parity audit 不再依赖 baseline actions first N rows；
- 不改变收益、策略规则、交易逻辑或默认策略。

R10 推荐路径：

优先采用工作文档中的路径 B：

```text
新增 baseline normalized action artifact / adapter
```

理由：

- 不改旧 baseline generator，风险更小；
- 原始 baseline 保持不变；
- 可以单独审查 window 字段补充是否纯粹；
- 更符合 post-R8 cleanup 的只读边界。

R10 必须同时处理 R9 非阻塞发现：

- 修复 `formal_replay_coverage_audit.csv.full_rank_artifact` 的路径记录；
- 或至少在 R10 execution report 中明确说明该问题另开 R9R/R11 前修复。

## 7. R10 禁止事项

R10 禁止：

- 训练；
- 调参；
- score recompute；
- 修改 R1 canonical signals；
- 修改策略规则；
- 改默认策略；
- 产生新策略收益结论；
- 前端接入；
- 日更接入；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker、quick-trade 或 order。

## 8. 最终结论

R9 通过。

R9 已把 replay runner 从 legacy full-rank CSV/列名直读中解耦出来，切换为标准 `FullRankArtifact` manifest 输入，并保持 R8 parity。允许进入 R10，但需在 R10 或 R11 前修复 coverage audit 中 `full_rank_artifact` 路径记录不准确的问题。
