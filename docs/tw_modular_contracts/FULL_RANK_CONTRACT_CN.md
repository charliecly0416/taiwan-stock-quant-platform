# FullRankArtifact 合同

生成日期：2026-06-16

## 1. 目的

`FullRankArtifact` 是完整 qlib 候选空间 rank 的标准化 artifact。

它用于 replay strategy 在持仓跌出 top50 replay-ready rows 后，仍能按完整 qlib rank 判断 exit worst rank。

R9 后，config-driven replay 不应再直接读取 legacy full rank CSV 或 legacy rank column，而应读取：

```text
data_tw/artifacts/full_rank/{rank_source_name}/{run_id}/manifest.json
```

再通过 manifest 读取标准：

```text
full_rank.csv
```

## 2. 必需字段

`full_rank.csv` 必须包含：

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

## 3. 字段语义

| 字段 | 语义 |
|---|---|
| `date` | rank 对应的信号日期 |
| `instrument` | 标准 TW symbol，例如 `TW2330` |
| `rank_source_name` | rank source 稳定名称 |
| `rank_family` | rank 家族，例如 `fresh_qlib` / `frozen_qlib` |
| `full_qlib_rank` | 完整 qlib 候选空间 rank，不限于 top50 replay-ready rows |
| `signal_asof` | 策略可见的信号日期 |
| `available_at` | 数据可用日期，必须不晚于 `signal_asof` |
| `source_artifact` | legacy source 或上游 artifact 路径 |

## 4. 禁止字段

`FullRankArtifact` 禁止包含：

```text
future_return_*
future_excess_return_*
forward_return_*
label_*
relevance_10d_top_heavy
ltr_relevance_label
realized_pnl
realized_return
action
holding
position
target_position
order_qty
execution_price
execution_date
broker_order_id
qlib_score_raw
qlib_rank_raw
adaptive_score_baseline
phasee3_extended_oos_ltr_score
phasee6_branch_a_fresh_ltr_score
phasee6_branch_b_frozen_ltr_score
```

## 5. 可见性要求

必须满足：

```text
available_at <= signal_asof
```

legacy adapter 为保持历史 replay parity，可声明：

```text
available_at = date
signal_asof = date
```

## 6. Rank 边界

`full_qlib_rank`：

- 只能表示 qlib full candidate rank；
- 不得表示 LTR rank；
- 不得表示 future-return rank；
- 不得表示 realized PnL rank；
- 允许用于 exit worst rank；
- 不应用于新增收益筛选或默认策略切换。

## 7. 必需审计文件

每个 `FullRankArtifact` 目录必须包含：

```text
manifest.json
full_rank.csv
schema.json
coverage_audit.csv
forbidden_field_audit.csv
legacy_mapping_audit.csv
```

## 8. Manifest 最小字段

`manifest.json` 至少包含：

```text
artifact_type: full_rank
artifact_name
run_id
created_at
created_by
schema_version
contract_version
rank_source_name
rank_family
source_artifact
source_rank_column
row_count
duplicate_key_count
full_qlib_rank_non_null_count
quality_status
output_files
forbidden_actions
capabilities
```

## 9. 禁止事项

生成 `FullRankArtifact` 时禁止：

- 训练 qlib / LTR；
- 调参；
- 重算模型 score；
- 修改 R1 canonical signals；
- 修改 R2/R5 replay results；
- 新增策略收益结论；
- 修改默认策略；
- 修改前端；
- 修改日更脚本；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker、quick-trade 或 order。
