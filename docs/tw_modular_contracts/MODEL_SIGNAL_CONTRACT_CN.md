# ModelSignalArtifact 合同

生成日期：2026-06-16

## 1. 目的

`ModelSignalArtifact` 是模型输出与策略/回放链路之间的唯一标准信号接口。任何 qlib、LTR 或后续新增模型，只有输出本合同定义的字段并通过校验后，才能被策略规则消费。

本合同只冻结研究/回放链路的最小字段，不改变现有模型、不训练模型、不重算收益、不切换默认策略。

## 2. Artifact 结构

推荐目录：

```text
data_tw/artifacts/signals/{model_name}/{run_id}/
```

必需文件：

```text
manifest.json
signals.csv
schema.json
coverage_audit.csv
forbidden_field_audit.csv
legacy_mapping_audit.csv
```

`signals.csv` 的唯一键为：

```text
date
instrument
```

同一个 artifact 内 `date + instrument` 不得重复。

## 3. Required Fields

`signals.csv` 必须包含以下字段：

| field | type | required | 语义 |
| --- | --- | --- | --- |
| date | YYYY-MM-DD | yes | 信号所属交易日。 |
| instrument | string | yes | 标准股票代码，使用 `TWxxxx` 格式。 |
| model_name | string | yes | 模型或 legacy adapter 的稳定名称。 |
| model_family | string | yes | `qlib`、`ltr` 或后续受控扩展值。 |
| candidate_rank | numeric | yes | qlib 候选排名，只用于 top50 universe / exit boundary。 |
| buy_score | numeric | yes | top50 内买入排序分数。 |
| raw_score | numeric | yes | 原始模型分数，保留溯源，不直接定义策略边界。 |
| score_rank | numeric | yes | 与 `buy_score` 对应的日内排序名次；1 表示最高优先级。 |
| full_qlib_rank | numeric | yes | 完整 qlib rank，用于持仓跌出 top50 后判断最差持仓。 |
| signal_asof | YYYY-MM-DD | yes | 策略可使用该信号的 as-of 日期。 |
| available_at | ISO-8601 或 YYYY-MM-DD | yes | 信号可见时间，必须不晚于策略读取时间。 |
| source_artifact | string | yes | legacy 输入或上游信号产物路径。 |
| source_model_artifact | string | yes | 训练模型或 legacy 模型来源；legacy 适配可填源文件路径。 |
| source_feature_artifact | string | yes | 特征来源；legacy 适配不可得时填 `legacy_unknown` 并在 mapping audit 说明。 |

## 4. 核心语义

`candidate_rank`：

- 只决定 qlib top50 universe / exit boundary。
- `candidate_rank <= 50` 表示进入策略可选候选池。
- 不得由 LTR 直接替换，除非后续有单独合同和审查批准。

`buy_score`：

- 只决定 qlib top50 内的买入优先级。
- 分数越高，买入优先级越高。
- 对同分情况，策略/回放必须使用稳定 tie-breaker，例如 `instrument` 升序。

`full_qlib_rank`：

- 表示完整 qlib 截面的排名，而不是仅 top50 内排名。
- 用于持仓不在 top50 时判断需要卖出的最差持仓。
- 不得用 LTR rank 替代。

## 5. qlib 与 LTR 映射

纯 qlib 模型：

```text
candidate_rank <- qlib rank
buy_score <- qlib score 或受控 qlib-derived adaptive score
raw_score <- qlib 原始 score
score_rank <- buy_score 的日内降序排名
full_qlib_rank <- 完整 qlib rank
```

LTR 模型：

```text
candidate_rank <- 底座 qlib rank
buy_score <- LTR rerank score
raw_score <- LTR 原始 score
score_rank <- buy_score 的日内降序排名
full_qlib_rank <- 底座完整 qlib rank
```

LTR 只能在 qlib top50 内重排买入顺序；不得静默扩大、缩小或替换 qlib candidate universe。

## 6. Legacy Mapping 要求

R1 adapter 必须按以下映射产出标准信号，R0 仅冻结合同：

`fresh_qlib_adaptive`：

```text
candidate_rank <- qlib_rank
buy_score <- adaptive_score_baseline
raw_score <- qlib_score_raw
full_qlib_rank <- phase_s2b_post_filter_score_rank.qlib_rank
```

`fresh_qlib_2025_ltr`：

```text
candidate_rank <- qlib_rank
buy_score <- phasee6_branch_a_fresh_ltr_score
raw_score <- phasee6_branch_a_fresh_ltr_score
full_qlib_rank <- phase_s2b_post_filter_score_rank.qlib_rank
```

`frozen_qlib_2025_ltr`：

```text
candidate_rank <- qlib_rank
buy_score <- phasee6_branch_b_frozen_ltr_score
raw_score <- phasee6_branch_b_frozen_ltr_score
full_qlib_rank <- phasee1_raw_oos_score_rank_2023_2026.qlib_rank_raw
```

`e4_frozen_qlib_2023_2025_ltr`：

```text
candidate_rank <- qlib_rank
buy_score <- phasee3_extended_oos_ltr_score
raw_score <- phasee3_extended_oos_ltr_score
full_qlib_rank <- phasee1_raw_oos_score_rank_2023_2026.qlib_rank_raw
```

`frozen_qlib_2018_2022`：

```text
candidate_rank <- qlib_rank_raw
buy_score <- qlib_score_raw
raw_score <- qlib_score_raw
full_qlib_rank <- qlib_rank_raw
```

## 7. Forbidden Fields

`signals.csv`、`manifest.json`、schema 和 audit 中不得把以下字段作为策略输入：

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
```

训练标签、未来收益、实际成交、持仓和订单字段不得进入标准信号表。

## 8. Forbidden Actions

生成或校验 `ModelSignalArtifact` 时禁止：

- 训练模型；
- 调参或根据 OOS 收益筛选模型；
- 重跑收益筛选；
- 修改默认策略；
- 修改前端；
- 修改日更主链路；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker、quick-trade 或 order 行为。

## 9. 最小校验

R1 起 validator 至少检查：

- required fields 全部存在；
- `date + instrument` duplicate key 为 0；
- `candidate_rank`、`buy_score`、`full_qlib_rank` 可转为数值；
- `available_at <= signal_asof` 或在 manifest 中明确 legacy 可见性政策；
- forbidden fields 不存在；
- LTR 的 `candidate_rank` 与底座 qlib 来源一致；
- legacy adapter 不改变 score 数值、不改变排序、不改变 row count。
