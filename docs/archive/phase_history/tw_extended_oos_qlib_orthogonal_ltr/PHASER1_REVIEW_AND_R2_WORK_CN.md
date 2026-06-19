# Phase R1 审查与 R2 工作建议

生成日期：2026-06-16

## 1. 审查结论

R1 复审通过，允许进入 R2。

本次确认 R1 已完成 legacy replay-ready / score 产物到标准 `ModelSignalArtifact` 的转换，五个模型 artifact 均生成成功，`quality_status=pass`，audit 中无 `fail`，且未发现前端、日更或 formal replay matrix 的 R1 范围外 diff。

需要带入 R2 的注意事项：`fresh_qlib_adaptive` 与 `fresh_qlib_2025_ltr` 存在 `full_qlib_rank` primary source 未覆盖行，R1 使用 legacy replay-ready `candidate_rank` 作为可追溯 fallback，并以 `warn` 标记。该项不阻塞 R2，但 R2 必须验证 replay 结果与旧 formal replay 完全一致，不能把 fallback 当作新的策略语义。

## 2. 审查对象

R1 handoff：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER1_LEGACY_SIGNAL_ADAPTER_REVIEW_HANDOFF_CN.md
```

R1 执行报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER1_LEGACY_SIGNAL_ADAPTER_EXECUTION_REPORT_CN.md
```

Adapter：

```text
scripts/build_tw_modular_legacy_signal_adapter.py
```

Artifact：

```text
data_tw/artifacts/signals/{model_name}/r1_legacy_signal_adapter_20260616/
```

## 3. 复核结果

### 3.1 Adapter 可复跑

执行复核命令：

```bash
python scripts/build_tw_modular_legacy_signal_adapter.py --run-id r1_legacy_signal_adapter_20260616
```

复核结果：

```text
quality_status: pass
models:
fresh_qlib_adaptive
fresh_qlib_2025_ltr
frozen_qlib_2025_ltr
e4_frozen_qlib_2023_2025_ltr
frozen_qlib_2018_2022
```

说明：该脚本会重写同 run-id 下 artifact、执行报告和 handoff；复跑后仍为 pass。

### 3.2 Artifact 文件完整

五个模型目录均包含：

```text
manifest.json
signals.csv
schema.json
coverage_audit.csv
forbidden_field_audit.csv
legacy_mapping_audit.csv
```

模型汇总：

| model_name | family | rows | duplicate_key | quality | window |
| --- | --- | ---: | ---: | --- | --- |
| fresh_qlib_adaptive | qlib | 30630 | 0 | pass | 2025-07-01..2026-05-07 |
| fresh_qlib_2025_ltr | ltr | 3950 | 0 | pass | 2026-01-02..2026-05-07 |
| frozen_qlib_2025_ltr | ltr | 3950 | 0 | pass | 2026-01-02..2026-05-07 |
| e4_frozen_qlib_2023_2025_ltr | ltr | 3950 | 0 | pass | 2026-01-02..2026-05-07 |
| frozen_qlib_2018_2022 | qlib | 119862 | 0 | pass | 2023-01-03..2026-05-07 |

### 3.3 signals.csv 字段符合 ModelSignal contract

抽查五个 artifact 的 `signals.csv` header，字段均为：

```text
date
instrument
model_name
model_family
candidate_rank
buy_score
raw_score
score_rank
full_qlib_rank
signal_asof
available_at
source_artifact
source_model_artifact
source_feature_artifact
```

未发现 legacy 私有分数字段、future label/return、PnL、持仓、订单或成交字段进入 `signals.csv`。

### 3.4 Audit 状态

复核 `rg -n "fail|warn"` 后，未发现 `fail`。

仅有两个 `warn` 类型：

- `fresh_qlib_adaptive`: `full_rank_fallback_to_ready_candidate_rank = 8017`
- `fresh_qlib_2025_ltr`: `full_rank_fallback_to_ready_candidate_rank = 675`

其他模型 full-rank primary source 均完整覆盖。

### 3.5 越界改动复核

复核对象：

```text
frontend/src/views/tw-stock-monitor/index.vue
scripts/run_daily_tw_stock_auto_update.py
scripts/run_extended_oos_formal_replay_matrix.py
```

结果：

- 前端文件无 diff；
- 日更脚本无 diff；
- formal replay matrix 无 diff；
- `scripts/run_extended_oos_formal_replay_matrix.py` 当前仍显示为未跟踪文件，但本次 R1 未产生 tracked diff。

## 4. 关键审查判断

### 4.1 full_qlib_rank fallback 不阻塞 R2

R0 contract 对 `full_qlib_rank` 的语义是完整 qlib rank，用于持仓跌出 top50 后判断最差持仓。R1 的理想实现应从完整 qlib rank source 全量 join。

本次两个 fresh artifact 的 primary source 有覆盖缺口，adapter 使用 legacy replay-ready 的 `candidate_rank` 作为 fallback。这个 fallback 不是完美的完整 rank 证明，因此必须保留 `warn` 和来源说明。

本次不阻塞 R2 的理由：

- fallback 行被显式审计，未静默处理；
- fallback 不改变 `candidate_rank`、`buy_score`、`raw_score`；
- fallback 不改变 row count、排序或 universe；
- R1 目标是复刻旧 replay-ready / score 产物，不产生新策略语义；
- R2 的最终门槛仍是 config-driven replay 与旧 formal replay 在 `2026_ytd` 关键结果完全一致。

R2 必须把该 fallback 作为风险项纳入执行报告，若 replay 对齐失败，优先检查 full-rank fallback 是否改变了 exit worst-sell 语义。

### 4.2 LTR boundary 未被替换

R1 adapter 对 LTR 模型仍使用 legacy qlib rank 作为 `candidate_rank`，LTR score 只进入 `buy_score` / `raw_score`。这符合 R0 contract：

```text
candidate_rank <- 底座 qlib rank
buy_score <- LTR rerank score
full_qlib_rank <- 底座完整 qlib rank 或已审计 fallback
```

未发现 LTR 直接替换 qlib top50 boundary。

## 5. 残余风险

- `full_qlib_rank` fallback 是 R1 的主要残余风险，必须在 R2 replay 对齐中重点观察；
- 当前工作区仍有大量未跟踪历史文件，R2 执行报告必须明确列出 R2 新增/修改文件，避免混入历史未跟踪内容；
- R1 adapter 会重写执行报告和 handoff，后续复跑时需注意不要丢失人工审查说明。

## 6. R2 放行条件

允许进入 R2，但 R2 必须满足：

- formal replay matrix 改为读取标准 `ModelSignalArtifact manifest` + YAML config；
- 不再读取 legacy 私有分数字段；
- 不训练、不调参、不重算模型分数；
- 不修改默认策略；
- 不修改前端；
- 不修改日更；
- 不触发 provider / accepted latest / monitor / broker / order；
- 与旧 formal replay matrix 在 `2026_ytd` 的 net return、action_count、buy_count、sell_count、final equity、active action key、daily_nav 关键结果完全一致；
- 若结果不一致，必须输出 diff 并停止，不能自行推进。

## 7. 给执行者的 R2 指令

请在 R1 审查通过后执行 Phase R2：把 formal replay matrix 改为 config-driven，从标准 `ModelSignalArtifact manifest` + `configs/tw_modular_replay_matrix.yaml` 读取，不得再读取 legacy 私有列名。

输出到：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/
```

必须与当前 baseline：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix/
```

在 `2026_ytd` 的 summary / actions / daily_nav 关键结果完全一致。若不一致，必须输出 diff 并停止。

执行报告写到：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_EXECUTION_REPORT_CN.md
```
