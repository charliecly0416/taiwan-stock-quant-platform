# ModelSignal Extension Schema 合同

生成日期：2026-06-16

## 1. 目的

本合同定义 `ModelSignalArtifact` 的 optional extension fields 如何声明、校验和被策略消费。Extension 只扩展信息，不改变 core fields 的语义。

## 2. Manifest Schema

若 `signals.csv` 包含 extension fields，manifest 必须包含：

```json
{
  "extensions": {
    "schema_version": "model_signal_extension_v1",
    "fields": {
      "ext_risk_volatility_score": {
        "dtype": "float",
        "semantic_role": "risk_score",
        "availability_policy": "available_at_lte_signal_asof",
        "producer": "feature_builder_or_model_adapter",
        "allowed_consumers": ["risk_filter_v1"],
        "ranking_allowed": false,
        "required_for_core_replay": false,
        "description": "Optional ex-ante risk score."
      }
    }
  }
}
```

## 3. Required Metadata

每个 extension field 必须声明：

| metadata | required | 说明 |
| --- | --- | --- |
| dtype | yes | `float`、`int`、`string`、`bool`、`category`。 |
| semantic_role | yes | `risk_score`、`sector`、`horizon_score`、`ensemble_score` 等。 |
| availability_policy | yes | 必须支持 PIT 检查。 |
| producer | yes | 生成模块或 adapter。 |
| allowed_consumers | yes | 可消费该字段的 strategy / analysis 名称。 |
| ranking_allowed | yes | 是否允许进入排序。默认 false。 |
| required_for_core_replay | yes | 是否为 core replay 必需。默认 false。 |
| description | yes | 简短说明。 |

## 4. Allowed Semantic Roles

初始允许：

```text
risk_score
sector
industry
horizon_score
ensemble_score
liquidity
volatility
exposure
diagnostic
```

`diagnostic` 字段不得进入策略决策，只能进入 audit / analysis。

## 5. Forbidden Extension Fields

Extension 不得声明：

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

Extension 也不得直接保留 legacy 私有列名作为策略输入，例如：

```text
phasee6_branch_a_fresh_ltr_score
phasee6_branch_b_frozen_ltr_score
phasee3_extended_oos_ltr_score
adaptive_score_baseline
qlib_score_raw
qlib_rank_raw
```

Legacy 字段必须先映射到 core field 或受控 `ext_*` 字段，并声明语义。

## 6. 不同扩展类型的处理

### 6.1 Horizon Score

多 horizon score 可声明为：

```text
ext_horizon_5d_score
ext_horizon_20d_score
```

策略若使用它，必须声明：

- horizon；
- ranking direction；
- tie breaker；
- 是否替代 `buy_score`。

默认不得替代 core `buy_score`。

### 6.2 Risk Score

风险字段可用于过滤、仓位上限或 analysis，但必须声明是否影响 order intent。

如果影响 order intent，strategy dependency 必须写明：

```yaml
required_extensions:
  - field: ext_risk_volatility_score
    semantic_role: risk_score
    usage: risk_filter
```

### 6.3 Sector / Exposure

行业、产业、暴露字段只能在声明的 sector-aware strategy 中使用。普通 top50 replay 不得隐式读取。

### 6.4 Ensemble Score

Ensemble score 可以作为 extension 保存，但若用于买入排序，必须作为新 strategy 或新 core contract version 审查，不得静默替代 `buy_score`。

## 7. Validator 最小检查

Validator 至少检查：

- extension 字段均以 `ext_` 开头；
- manifest 中每个 extension field metadata 完整；
- signals.csv 中没有未声明 extension field；
- declared extension field 在 signals.csv 中存在；
- dtype 可解析；
- forbidden fields 不存在；
- `ranking_allowed=false` 的字段未被 strategy dependency 用作 ranking；
- strategy dependency 的 required extension 全部存在。
