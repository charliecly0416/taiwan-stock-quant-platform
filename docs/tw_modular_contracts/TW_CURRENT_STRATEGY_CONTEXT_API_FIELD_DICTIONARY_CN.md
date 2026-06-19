# 当前策略上下文 API 字段字典

生成日期：2026-06-18

## 1. 目的

本文档说明前端和只读 Agent 应如何使用当前统一策略上下文 API：

```text
GET /api/tw-stock/current-strategy-context
```

该 API 是台股产品前端的统一只读入口。它把当前产品模型、排名、策略快照、产品化状态、模拟账户上下文和一致性审计合并成一个 payload，避免前端各模块分别读取旧 CSV、旧 latest pointer 或历史实验 artifact。

它不是交易 API，不输出真实订单，不连接 broker，不写 monitor，不切 provider accepted latest。

## 2. 入口代码

后端入口：

```text
backend/app/routes/tw_stock.py
backend/app/services/tw_stock_current_strategy_context.py
```

前端入口：

```text
frontend/src/api/tw-stock.js
frontend/src/views/tw-stock-monitor/index.vue
```

产品默认模型、默认策略和 artifact 路径来自：

```text
configs/tw_product_artifact_registry.yaml
```

前端不得硬编码默认模型、默认策略或 `data_tw/artifacts/...` 路径。

## 3. 顶层字段

| field | type | 语义 |
| --- | --- | --- |
| `ok` | bool | API 是否成功返回上下文。 |
| `schema_version` | string | 当前为 `tw_current_strategy_context_v1`。 |
| `readonly_only` | bool | 固定为 true，表示只读展示。 |
| `not_order` | bool | 固定为 true，表示不是订单。 |
| `not_target_position` | bool | 固定为 true，表示不是目标仓位指令。 |
| `not_investment_advice` | bool | 固定为 true，表示不是投资建议。 |
| `production_trade_enabled` | bool | 固定为 false，表示不启用实盘交易。 |
| `context` | object | 当前 asof、模型、策略、执行价口径等摘要。 |
| `rankings` | object | Qlib 与 LTR 的标准化排名。 |
| `strategy_snapshot` | object | 当前只读策略快照摘要。 |
| `productization_status` | object | YZ 产品化状态、价格可得性、paper apply gate 等。 |
| `paper_portfolio_context` | object | 模拟账户只读上下文。 |
| `source_manifests` | object | 上游标准 artifact manifest 路径。 |
| `consistency_audit` | object | asof 对齐和前端使用建议。 |
| `no_write_guarantees` | object | 只读安全声明。 |

## 4. `context`

| field | type | 语义 |
| --- | --- | --- |
| `context_asof` | YYYY-MM-DD | 本 payload 的显示 asof。策略快照与信号一致时使用快照 asof，否则使用信号 asof。 |
| `display_asof` | YYYY-MM-DD | 前端展示用日期，当前等同 `context_asof`。 |
| `signal_asof` | YYYY-MM-DD | 模型信号日期。例：2026-06-17 的信号用于生成 2026-06-18 的候选。 |
| `target_date` | YYYY-MM-DD | 信号对应的下一交易日或策略目标日期。 |
| `default_model_id` | string | 当前默认展示的 treatment 模型 ID。 |
| `display_model_id` | string | 兼容旧文案的展示名，不等于产品主键。 |
| `base_model_id` | string | 底座 Qlib 模型 ID。 |
| `strategy_rule` | string | 当前默认策略规则。 |
| `ranking_source` | string | 当前为 `ltr_rerank_within_qlib_top50`。 |
| `candidate_boundary` | string | 当前为 `qlib_top50`，表示 LTR 只在 qlib top50 内重排。 |
| `execution_price_mode` | string | 当前产品化口径为 `next_open`。 |

当前产品默认值：

```text
base_model_id = e4_frozen_qlib_2018_2022
default_model_id = e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
strategy_rule = top50_exit_one_worst_sell
```

## 5. `rankings`

`rankings` 是前端、策略解释、模拟账户和后续决策模块最重要的共享输入。

### 5.1 `model_a`

底座 Qlib 信号摘要。

| field | type | 语义 |
| --- | --- | --- |
| `model_id` | string | 底座 Qlib 模型 ID。 |
| `manifest` | path | Model A 的 `manifest.json`。 |
| `row_count` | int | 信号行数。产品期望接近 150。 |
| `signals` | path | Model A 的 `signals.csv`。 |

### 5.2 `model_b`

正交 LTR 信号摘要。

| field | type | 语义 |
| --- | --- | --- |
| `model_id` | string | treatment 模型 ID。 |
| `display_model_id` | string | 兼容旧展示名。 |
| `manifest` | path | Model B 的 `manifest.json`。 |
| `row_count` | int | LTR 重排行数。产品期望覆盖 qlib top50。 |
| `signals` | path | Model B 的 `signals.csv`。 |
| `source_feature_artifact` | path/string | LTR 使用的正交特征来源。 |
| `source_model_artifact` | path/string | LTR 模型来源。 |

### 5.3 `qlib_top150`

底座 Qlib 在生产 universe 上的完整排序列表。每行主要字段：

| field | type | 语义 |
| --- | --- | --- |
| `instrument` / `symbol` | string | 股票代码。当前服务按 artifact 原样返回，通常为 `TWxxxx`。 |
| `signal_asof` | YYYY-MM-DD | 信号日期。 |
| `available_at` | YYYY-MM-DD | 该信号可用日期，不得晚于 `signal_asof`。 |
| `qlib_full_rank` | int | Qlib 在约 150 支股票 universe 内的完整排名，越小越好。 |
| `qlib_score_rank` | int | Qlib score rank，缺省时与 full rank 对齐。 |
| `qlib_candidate_rank` | int/null | Qlib top50 内候选 rank。 |
| `qlib_buy_score` | number/null | Qlib 买入排序分数。 |
| `qlib_raw_score` | number/null | Qlib 原始分数。 |
| `in_qlib_top50` | bool | 是否在 Qlib top50 内。 |
| `source_base_qlib_signal` | path | 来源 Model A manifest。 |

### 5.4 `qlib_top50`

`qlib_top150` 的前 50 行。它是：

- Qlib 纯模型前端展示的核心候选；
- LTR 卖出边界的来源；
- LTR 重排的输入 universe。

策略不得用 LTR rank 改写这个边界。

### 5.5 `ltr_top50`

在 `qlib_top50` 内经过正交 LTR 重排后的列表。每行主要字段：

| field | type | 语义 |
| --- | --- | --- |
| `instrument` / `symbol` | string | 股票代码。 |
| `signal_asof` | YYYY-MM-DD | 信号日期。 |
| `available_at` | YYYY-MM-DD | 信号可用日期。 |
| `ltr_score_rank` | int | LTR 重排后的 rank，越小越好。 |
| `ltr_buy_score` | number/null | LTR 买入排序分数。 |
| `ltr_raw_score` | number/null | LTR 原始分数。 |
| `qlib_candidate_rank` | int/null | 该股票在底座 Qlib top50 内的原 candidate rank。 |
| `qlib_full_rank` | int/null | 该股票在底座 Qlib 约 150 支 universe 内的完整 rank。 |
| `qlib_score_rank` | int/null | 底座 Qlib score rank。 |
| `qlib_buy_score` | number/null | 底座 Qlib 买入分数。 |
| `qlib_raw_score` | number/null | 底座 Qlib 原始分数。 |
| `in_qlib_top50` | bool | 应为 true。 |
| `source_model_signal` | path | LTR signal manifest。 |
| `source_base_qlib_signal` | path | Qlib signal manifest。 |

### 5.6 `ltr_top10`

`ltr_top50` 的前 10 行。它只是前端快速展示和人工观察列表，不是“必须买入 10 支”的策略决策。

真正买卖动作必须由策略模块基于完整 `ltr_top50`、`qlib_top50` 和 portfolio state 输出 `OrderIntentArtifact`。

### 5.7 `field_contract`

| field | 语义 |
| --- | --- |
| `ltr_score_rank` | qlib top50 内 LTR 重排 rank。 |
| `qlib_candidate_rank` | LTR 前的 qlib top50 内 rank。 |
| `qlib_full_rank` | 约 150 支生产 universe 内的 qlib rank。 |
| `buy_score` | LTR 模块用 `ltr_buy_score`；纯 qlib 模块用 `qlib_buy_score`。 |

## 6. `strategy_snapshot`

策略快照来自：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

但前端不应直接读取该文件，应通过本 API 读取摘要。

| field | type | 语义 |
| --- | --- | --- |
| `ok` | bool | 是否存在有效快照。 |
| `asof` | YYYY-MM-DD | 快照生成日期。 |
| `signal_asof` | YYYY-MM-DD | 快照使用的信号日期。 |
| `target_date` | YYYY-MM-DD | 快照对应目标日期。 |
| `model_id` | string | canonical model ID。 |
| `display_model_id` | string | 展示名。 |
| `strategy_rule` | string | 快照策略规则。 |
| `top_candidates` | array | 模型排序后的顶部候选，用于展示，不等于买入指令。 |
| `exit_candidates` | array | 根据当前持仓和规则识别的可能退出候选，用于展示，不等于成交。 |
| `manifest` | path | 快照 manifest。 |
| `latest_pointer` | path | latest pointer。 |
| `validation` | object | 快照 validator 结果。 |
| `checksum` | string/object | 快照校验信息。 |

如果 `ok=false`，前端应展示“快照暂不可用”，但仍可展示 `rankings`。

## 7. `productization_status`

该对象来自 YZ 产品化状态服务，通常包含：

```text
ok
signal_asof
execution_price_readiness
paper_apply_allowed
paper_apply_blocked_reason
```

前端应重点使用：

| field | 语义 |
| --- | --- |
| `ok` | 产品化状态是否可读。 |
| `signal_asof` | 状态对应信号日期。 |
| `execution_price_readiness` | next_open / next_close 等执行价可得性。 |
| `paper_apply_allowed` | 是否允许进入模拟账户只读 apply。 |
| `paper_apply_blocked_reason` | 不允许时的原因。 |

## 8. `paper_portfolio_context`

| field | type | 语义 |
| --- | --- | --- |
| `apply_allowed` | bool | 是否允许根据当前只读状态生成模拟账户动作。 |
| `blocked_reason` | string | 阻断原因。 |
| `execution_price_readiness` | object | 执行价可得性。 |
| `source_status` | string | 来源状态服务。 |

这仍然不是实盘交易授权。

## 9. `source_manifests`

| field | 语义 |
| --- | --- |
| `model_a` | 底座 Qlib manifest。 |
| `model_b` | 正交 LTR manifest。 |
| `orthogonal_feature_package` | YZ2 正交特征包 manifest。 |
| `execution_price_readiness` | YZ2R 执行价可得性 manifest。 |
| `readonly_strategy_snapshot` | 当前只读策略快照 manifest。 |

前端可以展示路径摘要，但不应直接读取这些文件。

## 10. `consistency_audit`

`asof_alignment` 用于检查各子 payload 是否与主 `signal_asof` 对齐。

| status | 语义 |
| --- | --- |
| `pass` | 所有可用子 payload 与当前信号日期一致。 |
| `mixed` | 至少一个子 payload 缺失或日期不一致。 |

`frontend_guidance` 当前约束：

```text
primary_context_source = this endpoint
use_ltr_for_strategy_snapshot = true
use_qlib_top50_for_base_model_views = true
legacy_daily_readonly_latest_removed = true
```

## 11. `no_write_guarantees`

这些字段必须保持 true：

| field | 语义 |
| --- | --- |
| `read_only_http_method` | API 只通过 GET 使用。 |
| `reads_static_artifacts_only` | 只读取静态 artifact。 |
| `does_not_touch_provider_accepted_latest` | 不切 provider accepted latest。 |
| `does_not_touch_qlib_accepted_latest` | 不切 qlib accepted latest。 |
| `does_not_touch_monitor_or_alerts` | 不写 monitor/alerts。 |
| `does_not_touch_broker_or_orders` | 不连接 broker，不下单。 |

## 12. 前端使用原则

前端应遵守：

- 当前策略快照、今日候选、模型排名、模拟账户入口优先读取本 API。
- 不再使用 `daily_readonly_latest`、`readonly-daily-update-runs` 或 provider readiness 旧 API。
- 切换模型时，只在本 API 返回的标准 ranking 字段之间切换展示，不读取模型私有 CSV。
- 策略决策展示必须来自策略模块输出，不得把 `ltr_top10` 直接解释成买入清单。
- 回放展示必须来自 ReplayResultArtifact 或只读回放 API，不得在前端临时计算收益。

## 13. 最小 smoke

```bash
PYTHONPATH=backend python - <<'PY'
from app.services.tw_stock_current_strategy_context import load_current_strategy_context

payload = load_current_strategy_context()
print(payload["ok"])
print(payload["context"]["signal_asof"])
print(payload["context"]["default_model_id"])
print(payload["context"]["strategy_rule"])
print(len(payload["rankings"]["qlib_top50"]))
print(len(payload["rankings"]["ltr_top10"]))
PY
```

预期：

- `ok=True`
- `qlib_top50` 接近或等于 50
- `ltr_top10` 等于 10，除非上游 LTR artifact 不完整
- 不触发任何 provider、monitor、broker、order 写入
