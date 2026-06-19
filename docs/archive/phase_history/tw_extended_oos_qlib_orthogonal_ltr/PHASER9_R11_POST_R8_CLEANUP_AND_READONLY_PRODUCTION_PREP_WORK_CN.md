# Phase R9-R11 工作文档：Post-R8 Cleanup 与只读生产接入前准备

生成日期：2026-06-16

## 1. 背景

R8 审查结论：

- R0-R8 modular refactor 可以作为 research / audit artifact 归档；
- contract、registry、validator、canonical signal artifact、config-driven replay、extension smoke、regression 均已形成可复核闭环；
- 但尚未达到严格生产级全链路模块化。

R8 后仍有三个必须单独收口的问题：

1. `FullRankArtifact` 尚未标准化，R2/R8 config-driven replay 仍直接读取 legacy full rank CSV 与 legacy rank column；
2. baseline actions 没有 `window` 字段，action parity 依赖 prefix compatibility；
3. 任何前端、日更、API 或生产只读接入前，都需要单独 readiness 审查，不能由 R8 自动放行。

本工作文档定义 R9-R11 三个阶段，要求执行者与审查者交替执行。

## 2. 总体原则

本阶段仍为只读 cleanup / production-prep，不是策略收益研究。

必须坚持：

- 不训练 qlib / LTR；
- 不调参；
- 不重算模型 score；
- 不改变策略规则；
- 不新增策略收益结论；
- 不切换默认策略；
- 不修改前端展示逻辑，除非进入 R11 且仅做 readiness 设计；
- 不接入日更生产链路；
- 不触发 provider publish / accepted latest / monitor / broker / order。

任何 replay parity 不一致都必须停下来审查，不能自行解释后继续推进。

## 3. 阶段总览

| Phase | 名称 | 目标 |
| --- | --- | --- |
| R9 | FullRankArtifact 标准化 | 消除 replay config 对 legacy full rank CSV/列名的直接依赖 |
| R10 | Baseline action window cleanup | 消除 action parity 的 prefix compatibility 口径 |
| R11 | Readonly production readiness review | 只读生产接入前审查与 shadow plan，不实际接入 |

推进顺序：

```text
执行者完成 R9
  -> 审查者审查 R9，决定是否允许 R10
执行者完成 R10
  -> 审查者审查 R10，决定是否允许 R11
执行者完成 R11
  -> 审查者审查 R11，决定是否允许后续 shadow integration
```

不得一次性做完 R9-R11。

## 4. Phase R9：FullRankArtifact 标准化

### 4.1 问题

当前 `configs/tw_modular_replay_matrix.yaml` 中仍存在：

```yaml
full_rank_source: ...
full_rank_col: qlib_rank / qlib_rank_raw
```

`scripts/run_tw_modular_config_replay_matrix.py` 通过 `load_full_rank_source()` 读取 legacy CSV 和 legacy column。

这虽然通过了 R8 research/audit 验证，但不符合严格模块化目标：

```text
Replay engine 不应该读取 legacy 私有 rank 文件和列名。
```

### 4.2 R9 目标

新增标准 `FullRankArtifact`，让 replay engine 只读取标准 artifact manifest，而不是 legacy rank CSV。

目标链路：

```text
legacy full rank CSV
  -> FullRankArtifact adapter
  -> data_tw/artifacts/full_rank/{rank_source_name}/{run_id}/manifest.json
  -> modular replay config 引用 FullRankArtifact manifest
  -> replay engine 读取标准字段 full_qlib_rank
```

### 4.3 FullRankArtifact Contract

执行者必须新增：

```text
docs/tw_modular_contracts/FULL_RANK_CONTRACT_CN.md
```

必须定义标准字段：

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

语义：

- `full_qlib_rank` 是完整 qlib 候选空间 rank，不限于 top50 replay-ready rows；
- 用于持仓跌出 top50 后的 exit worst rank 判断；
- 不得包含模型 LTR rank；
- 不得包含 future label / return / realized pnl；
- `available_at <= signal_asof` 必须成立，legacy adapter 可声明 `available_at=date` 以保持历史 replay parity。

### 4.4 R9 Adapter 输入

至少支持：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv
```

输出建议：

```text
data_tw/artifacts/full_rank/fresh_qlib_s2b_post_filter/r9_full_rank_adapter_20260616/
data_tw/artifacts/full_rank/frozen_qlib_2018_2022_raw_oos/r9_full_rank_adapter_20260616/
```

每个目录必须包含：

```text
manifest.json
full_rank.csv
schema.json
coverage_audit.csv
forbidden_field_audit.csv
legacy_mapping_audit.csv
```

### 4.5 R9 Config 改造

更新：

```text
configs/tw_modular_replay_matrix.yaml
```

从：

```yaml
full_rank_source: legacy.csv
full_rank_col: qlib_rank_raw
```

改为：

```yaml
full_rank_artifact: data_tw/artifacts/full_rank/.../manifest.json
```

### 4.6 R9 Replay 改造

更新：

```text
scripts/run_tw_modular_config_replay_matrix.py
```

要求：

- 删除或废弃 `full_rank_source/full_rank_col` 直读 legacy 文件路径；
- 新增 `load_full_rank_artifact(manifest)`；
- replay engine 只读取标准 `full_rank.csv` 字段；
- R9 后 `rg "full_rank_source|full_rank_col|qlib_rank_raw|phasee1_raw|phase_s2b_post_filter"` 在 replay script 中不得出现，除非在错误提示或兼容注释中且不参与读取。

### 4.7 R9 验收

必须证明：

- FullRankArtifact validator 通过；
- full rank row count 与 legacy source 对齐；
- duplicate date/instrument 为 0；
- `full_qlib_rank` 非空覆盖符合旧口径；
- forbidden fields 不存在；
- config-driven replay 与 R8 modular replay `2026_ytd` parity 完全一致；
- action key parity 完全一致；
- no training / no tuning / no score recompute；
- no frontend / no daily / no provider / no accepted latest / no monitor / no broker/order。

### 4.8 R9 执行报告

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER9_FULL_RANK_ARTIFACT_EXECUTION_REPORT_CN.md
```

审查 handoff：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER9_FULL_RANK_ARTIFACT_REVIEW_HANDOFF_CN.md
```

## 5. Phase R10：Baseline Action Window Cleanup

### 5.1 问题

R8 parity 中 action parity 使用：

```text
baseline_actions_prefix_by_2026_ytd_summary_action_plus_skipped_count
```

原因是旧 formal baseline actions 缺少 `window` 字段，baseline generator 按 2026_ytd first 的文件顺序做 prefix comparison。

这是可归档的兼容口径，但不是长期可接受的 production-grade parity。

### 5.2 R10 目标

消除 baseline actions 无 `window` 字段导致的 prefix compatibility。

目标：

- baseline formal replay actions 带 `window` 字段；
- modular replay actions 带 `window` 字段；
- parity audit 直接按 `window == 2026_ytd` 过滤；
- 不再使用 prefix count。

### 5.3 R10 可选实现路径

执行者可以选择其一，但必须说明理由：

#### 路径 A：修复旧 baseline generator

更新：

```text
scripts/run_extended_oos_formal_replay_matrix.py
```

让 baseline actions 输出 `window` 字段。

然后重跑 baseline formal replay matrix。

要求：

- 除新增 `window` 字段外，summary / daily_nav / active action key 不变；
- 不改变收益；
- 不改变交易逻辑。

#### 路径 B：生成 baseline normalized action artifact

不改旧 baseline generator，新增只读 adapter：

```text
scripts/build_formal_replay_baseline_action_window_adapter.py
```

输出：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix_windowed/
```

为 baseline actions 补充 `window` 字段，并保留原始 baseline 不变。

要求：

- adapter 只做字段补充；
- 能追溯每一行来源；
- parity 不再依赖 prefix。

推荐路径：

```text
优先路径 B。
```

原因：更安全，不重写旧 baseline，不影响已归档 R8。

### 5.4 R10 Parity 要求

新增或更新 parity audit：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/r10_action_window_parity_audit.csv
```

必须检查：

- baseline actions `window` 字段存在；
- modular actions `window` 字段存在；
- 直接过滤 `window == 2026_ytd`；
- baseline action rows == modular action rows；
- action key 差异为 0；
- value mismatch 为 0；
- 不再使用 prefix compatibility。

### 5.5 R10 验收

必须证明：

- prefix compatibility 已消除；
- R8/R9 结果不变；
- replay result validator 更新并通过；
- regression runner 更新并通过；
- no training / no tuning / no score recompute；
- no frontend / no daily / no provider / no accepted latest / no monitor / no broker/order。

### 5.6 R10 执行报告

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER10_BASELINE_ACTION_WINDOW_CLEANUP_EXECUTION_REPORT_CN.md
```

审查 handoff：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER10_BASELINE_ACTION_WINDOW_CLEANUP_REVIEW_HANDOFF_CN.md
```

## 6. Phase R11：Readonly Production Readiness Review

### 6.1 目标

R11 不是生产接入，也不是前端改造。

R11 只做：

```text
只读生产接入前 readiness 审查与 shadow integration plan
```

判断模块化 artifact 链路未来能否安全进入：

- 日更 shadow run；
- readonly publish artifact；
- readonly API；
- frontend readonly display。

### 6.2 R11 必须审查模块

R11 必须输出 readiness matrix：

| 模块 | 是否可接入 | 条件 | 风险 |
| --- | --- | --- | --- |
| Data fetch | deferred | 需 Provider/Normalizer contract | 高 |
| ModelSignalArtifact | ready for shadow | R1/R9/R10 通过 | 中 |
| StrategyRule dependency | ready for shadow | registry validator 通过 | 中 |
| ReplayResultArtifact | ready for shadow | replay validator 通过 | 中 |
| AnalysisArtifact | not ready unless defined | 需另开 contract | 中 |
| Readonly API | not ready unless wrapper defined | 需安全边界审查 | 中 |
| Frontend | not ready unless publish artifact stable | 需 E2E readonly | 中 |
| Daily orchestrator | not ready for production | 只能 shadow | 高 |

### 6.3 R11 必须定义 Shadow Plan

Shadow plan 只能：

- 读取已存在的 latest accepted qlib/fresh data；
- 生成 modular signal / strategy / replay / analysis shadow artifact；
- 写入隔离目录，例如：

```text
data_tw/artifacts/shadow_modular_daily/{asof}/
```

不得：

- 修改 `latest_signal.json`；
- 修改 accepted latest；
- 覆盖现有 fresh qlib 默认策略；
- 阻塞现有日更；
- 修改前端；
- 触发 monitor / broker / order。

### 6.4 R11 必须定义 Publish Contract 草案

只读 publish artifact 草案：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/{asof}/manifest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/{asof}/strategy_snapshot.json
```

字段建议：

```text
asof
created_at
source_replay_manifest
source_signal_manifest
strategy_rule
model_name
holdings_before
candidate_buys
candidate_sells
diff_vs_previous
readonly_only
no_order_action
```

R11 只写草案，不实现生产发布。

### 6.5 R11 验收

必须证明：

- R11 没有接入真实日更；
- R11 没有修改前端/API；
- R11 没有切换默认策略；
- R11 没有 provider publish / accepted latest / monitor / broker/order；
- readiness matrix 清楚；
- shadow plan 清楚；
- publish contract 草案清楚；
- 明确后续若要真正 shadow integration，必须另开 R12。

### 6.6 R11 执行报告

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER11_READONLY_PRODUCTION_READINESS_EXECUTION_REPORT_CN.md
```

审查 handoff：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER11_READONLY_PRODUCTION_READINESS_REVIEW_HANDOFF_CN.md
```

## 7. 给执行者的 Prompt

### R9 执行者 Prompt

请按 `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER9_R11_POST_R8_CLEANUP_AND_READONLY_PRODUCTION_PREP_WORK_CN.md` 执行 Phase R9：标准化 `FullRankArtifact`。新增 `docs/tw_modular_contracts/FULL_RANK_CONTRACT_CN.md`，写 legacy full rank adapter，把 fresh S2B post-filter rank 与 frozen E1 raw OOS rank 转成标准 `data_tw/artifacts/full_rank/{rank_source}/{run_id}/manifest.json + full_rank.csv`。更新 `configs/tw_modular_replay_matrix.yaml` 和 `scripts/run_tw_modular_config_replay_matrix.py`，让 replay engine 只读取 FullRankArtifact 标准字段，不再直接读取 legacy full rank CSV/列名。必须证明 R9 replay 与 R8 modular replay 在 `2026_ytd` summary/action/nav/action key 完全一致。不得训练、调参、重算 score、改策略、改默认、改前端/日更、触发 provider/accepted latest/monitor/broker/order。报告写到 `PHASER9_FULL_RANK_ARTIFACT_EXECUTION_REPORT_CN.md`。

### R10 执行者 Prompt

请在 R9 审查通过后，按 `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER9_R11_POST_R8_CLEANUP_AND_READONLY_PRODUCTION_PREP_WORK_CN.md` 执行 Phase R10：消除 baseline actions 无 `window` 字段导致的 prefix compatibility。优先使用只读 adapter 路径 B，生成 windowed baseline action artifact，不修改已归档 R8 baseline；如选择路径 A 必须说明理由。更新 parity audit，使 action parity 直接按 `window == 2026_ytd` 过滤，不再使用 prefix count。必须证明 summary/daily_nav/action key 与 R8/R9 完全一致，replay validator 和 regression runner 通过。不得训练、调参、重算 score、改策略、改默认、改前端/日更、触发 provider/accepted latest/monitor/broker/order。报告写到 `PHASER10_BASELINE_ACTION_WINDOW_CLEANUP_EXECUTION_REPORT_CN.md`。

### R11 执行者 Prompt

请在 R10 审查通过后，按 `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER9_R11_POST_R8_CLEANUP_AND_READONLY_PRODUCTION_PREP_WORK_CN.md` 执行 Phase R11：只读生产接入前 readiness 审查。只写 readiness matrix、shadow integration plan、readonly publish contract 草案，不实际接入日更、不改前端/API、不切默认策略、不触发 provider/accepted latest/monitor/broker/order。必须明确哪些模块 ready for shadow、哪些 deferred、哪些需要另开阶段。报告写到 `PHASER11_READONLY_PRODUCTION_READINESS_EXECUTION_REPORT_CN.md`。

## 8. 给审查者的 Prompt

### R9 审查者 Prompt

请审查 `PHASER9_FULL_RANK_ARTIFACT_EXECUTION_REPORT_CN.md`、`FULL_RANK_CONTRACT_CN.md`、`data_tw/artifacts/full_rank/`、`configs/tw_modular_replay_matrix.yaml` 和 `scripts/run_tw_modular_config_replay_matrix.py`。重点确认 replay engine 是否不再直接读取 legacy full rank CSV/legacy rank column，而是读取标准 FullRankArtifact；确认 full rank adapter 没有改 rank、没用未来字段，且 R9 replay 与 R8 modular replay 在 2026_ytd summary/action/nav/action key 完全一致。若 replay 仍读取 `full_rank_source/full_rank_col` 或 legacy rank 私有列，不能放行。

### R10 审查者 Prompt

请审查 `PHASER10_BASELINE_ACTION_WINDOW_CLEANUP_EXECUTION_REPORT_CN.md` 和 R10 parity artifacts。重点确认 baseline actions 已有 `window` 字段，action parity 不再使用 prefix compatibility，而是直接按 `window == 2026_ytd` 过滤；确认 summary/daily_nav/action key 与 R8/R9 完全一致；确认 replay validator 和 regression runner 已更新并通过。若仍依赖 prefix count，不能放行。

### R11 审查者 Prompt

请审查 `PHASER11_READONLY_PRODUCTION_READINESS_EXECUTION_REPORT_CN.md`。重点确认 R11 只做 readiness matrix、shadow plan、readonly publish contract 草案，没有实际接入日更、前端、API、provider publish、accepted latest、monitor、broker/order，也没有切换默认策略。若 R11 混入生产接入或展示改造，必须要求回滚或拆分到后续 R12。

## 9. R11 后续

R11 审查通过后，后续可另开：

```text
R12：Shadow Modular Daily Integration
```

R12 只能做 shadow run，不得直接生产接入。R12 文档必须由审查者另行撰写并由用户确认后才能执行。
