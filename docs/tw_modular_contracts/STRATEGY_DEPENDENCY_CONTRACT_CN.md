# Strategy Dependency Contract

生成日期：2026-06-16

## 1. 目的

策略必须声明自己依赖哪些 core fields、capabilities 和 extension fields。Validator 根据该声明判断某个 `ModelSignalArtifact` 是否可被该策略消费。

策略依赖声明不能触发 replay、训练或默认策略切换。

## 2. Dependency Manifest

建议每个策略有一个 dependency yaml：

```text
configs/strategy_dependencies/{strategy_rule}.yaml
```

示例：

```yaml
strategy_rule: top50_exit_one_worst_sell
dependency_version: strategy_dependency_v1
required_core_fields:
  - date
  - instrument
  - candidate_rank
  - buy_score
  - full_qlib_rank
  - signal_asof
  - available_at
required_capabilities:
  - core_signal_v1
  - candidate_boundary:qlib_top50
  - buy_ordering:buy_score_desc
  - full_rank_exit:full_qlib_rank
optional_extensions: []
forbidden_fields:
  - future_return_*
  - label_*
max_buy_count: 1
max_sell_count: 1
diagnostic_only: false
```

## 3. Required Core Fields

策略只能依赖 core contract 中声明的字段，或 extension schema 中声明的字段。

基础策略最小依赖：

| strategy | required core fields |
| --- | --- |
| original | `candidate_rank`, `buy_score`, `signal_asof`, `available_at` |
| top50_exit_all | `candidate_rank`, `buy_score`, `signal_asof`, `available_at` |
| top50_exit_one_worst_sell | `candidate_rank`, `buy_score`, `full_qlib_rank`, `signal_asof`, `available_at` |
| one_sell_one_buy_correct | `candidate_rank`, `buy_score`, `full_qlib_rank`, `signal_asof`, `available_at` |
| one_sell_one_buy_buggy_e8r | diagnostic only；不得作为 valid strategy dependency |

## 4. Extension Dependencies

若策略需要 extension fields，必须声明：

```yaml
required_extensions:
  - field: ext_sector_code
    semantic_role: sector
    usage: sector_cap
    required: true
```

Validator 必须检查：

- field 在 signals.csv 中存在；
- field 在 manifest `extensions.fields` 中声明；
- semantic_role 匹配；
- usage 在 allowed_consumers 中；
- 字段不是 forbidden field；
- PIT policy 满足。

## 5. Capability Matching

Artifact manifest capabilities 必须满足 strategy dependency。

示例匹配：

```yaml
required_capabilities:
  - core_signal_v1
  - candidate_boundary:qlib_top50
  - buy_ordering:buy_score_desc
```

Artifact：

```json
{
  "capabilities": {
    "core_signal_v1": true,
    "candidate_boundary": "qlib_top50",
    "buy_ordering": "buy_score_desc"
  }
}
```

若缺失能力，validator 必须 fail。

## 6. Forbidden Dependencies

策略不得声明依赖：

```text
future_return_*
future_excess_return_*
forward_return_*
label_*
realized_pnl
execution_price
execution_date
broker_order_id
legacy private score/rank columns
```

策略也不得声明会触发：

```text
provider_publish
accepted_latest_switch
monitor_scan
broker_order
quick_trade
```

## 7. Diagnostic Rule

`one_sell_one_buy_buggy_e8r` 必须：

```yaml
diagnostic_only: true
not_valid_strategy_evidence: true
allowed_outputs:
  - audit
  - diff
  - anomaly_attribution
```

不得进入：

- 默认策略；
- 收益筛选；
- 产品展示；
- 日更 publish；
- order intent production。

## 8. Validator 输出

Validator 应输出：

```json
{
  "ok": true,
  "artifact": "path/to/manifest.json",
  "strategy_dependency": "path/to/dependency.yaml",
  "checks": [
    {"name": "required_core_fields", "status": "pass"},
    {"name": "capabilities", "status": "pass"},
    {"name": "extensions", "status": "pass"},
    {"name": "forbidden_fields", "status": "pass"}
  ]
}
```

任一 required check fail，则该 strategy 不得消费该 artifact。
