# 新策略接入模板

生成日期：2026-06-18

## 1. 目的

本文档给后续开发者提供新增策略规则的标准流程。新增策略必须接入模块化链路：

```text
ModelSignalArtifact + PortfolioState + StrategyRuleConfig
  -> StrategyRule
  -> OrderIntentArtifact
  -> ReplayExecution
  -> ReplayResultArtifact
  -> Frontend / Analysis
```

策略模块只产生“意图”，不负责成交、现金、净值、手续费、交易税、收益率或实盘下单。

## 2. 开始前必须回答的问题

| 问题 | 要求 |
| --- | --- |
| 策略名称是什么？ | 使用稳定 snake_case，例如 `top50_exit_one_worst_sell`。 |
| 消费哪个模型信号？ | 必须是标准 ModelSignalArtifact。 |
| 需要哪些字段？ | 只能来自 core fields 或声明过的 extension。 |
| 卖出边界是什么？ | 例如 `qlib_top50`、`top10`、固定持仓天数等。 |
| 买入排序是什么？ | 例如 `buy_score_desc`。 |
| 每日最多买几支、卖几支？ | 明确 `max_buy_count` / `max_sell_count`。 |
| 是否 diagnostic only？ | bug 复现、压力测试、归因实验必须标记。 |
| 是否要进前端？ | 前端只能展示 validator 通过的正式策略或显式 diagnostic。 |
| 是否要进默认候选？ | 必须另走默认候选决策流程，不能在策略接入时顺手切换。 |

## 3. 必须阅读的合同

```text
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_DEPENDENCY_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_CURRENT_STRATEGY_CONTEXT_API_FIELD_DICTIONARY_CN.md
```

如果策略需要新增模型字段，还必须先更新：

```text
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
```

## 4. 新策略最小文件清单

正式策略至少需要：

```text
configs/strategy_dependencies/{strategy_rule}.yaml
策略实现代码或配置分支
OrderIntentArtifact 输出样例
validator 报告
只读 replay 结果
审查报告
```

不得只新增一个回放脚本并在脚本内部私自写策略逻辑。策略逻辑必须能单独输出 `OrderIntentArtifact`。

## 5. StrategyDependency YAML 模板

路径：

```text
configs/strategy_dependencies/{strategy_rule}.yaml
```

模板：

```yaml
strategy_rule: example_top50_one_sell_one_buy
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
required_extensions: []

ranking_usage:
  - field: buy_score
    usage: buy_ordering
  - field: full_qlib_rank
    usage: exit_worst_rank

max_buy_count: 1
max_sell_count: 1

diagnostic_only: false
not_valid_strategy_evidence: false

forbidden_fields:
  - future_return_*
  - future_excess_return_*
  - forward_return_*
  - label_*
  - relevance_10d_top_heavy
  - ltr_relevance_label
  - execution_price
  - execution_date
  - next_open
  - next_close
  - realized_pnl
  - daily_return
  - broker_order_id

forbidden_actions:
  - train_model
  - tune_model
  - read_future_price
  - read_future_label
  - write_broker_order
  - write_monitor_alert
  - provider_publish
  - accepted_latest_switch
```

说明：

- `candidate_rank` / `full_qlib_rank` 决定 universe 和卖出边界。
- `buy_score` 决定买入排序。
- 对 LTR 模型，adapter 应把 LTR 分数映射成标准 `buy_score`，但 `full_qlib_rank` 仍来自底座 Qlib。
- `diagnostic_only=true` 的策略不得作为默认策略、产品候选或收益证据。

## 6. 策略实现输入

策略实现只能消费：

```text
ModelSignalArtifact
PortfolioState
StrategyDependency YAML
StrategyRuleConfig
```

标准信号字段：

| field | 语义 |
| --- | --- |
| `date` | 信号日期。 |
| `instrument` | 股票代码。 |
| `candidate_rank` | 候选池内 rank，通常对应 qlib top50。 |
| `buy_score` | 买入排序分数。 |
| `raw_score` | 模型原始分数，仅作审计。 |
| `score_rank` | 模型排序 rank。 |
| `full_qlib_rank` | 约 150 支 universe 内 qlib rank。 |
| `signal_asof` | 信号 asof。 |
| `available_at` | 信号可用日期。 |
| `source_artifact` | 来源 manifest。 |

PortfolioState 最小字段：

| field | 语义 |
| --- | --- |
| `asof_date` | 当前持仓状态日期。 |
| `instrument` | 持仓股票。 |
| `quantity` | 持有股数或模拟单位。 |
| `cost_basis` | 成本，仅用于状态，不用于策略计算未来收益。 |
| `current_holding_flag` | 是否当前持有。 |

## 7. 策略实现输出

策略必须输出 `OrderIntentArtifact`，推荐目录：

```text
data_tw/artifacts/strategies/{strategy_rule}/{run_id}/
```

必需文件：

```text
manifest.json
order_intents.csv
schema.json
strategy_decision_audit.csv
forbidden_action_audit.json
```

`order_intents.csv` 必需字段：

| field | 语义 |
| --- | --- |
| `signal_date` | 策略读取信号并产生意图的日期。 |
| `instrument` | 股票代码。 |
| `intent_action` | `buy`、`sell`、`hold`、`skip`。 |
| `intent_reason` | 规则原因。 |
| `strategy_rule` | 策略名。 |
| `candidate_rank` | 意图产生时使用的 qlib candidate rank。 |
| `buy_rank` | 意图产生时使用的买入排序。 |
| `full_qlib_rank` | 意图产生时使用的完整 qlib rank。 |
| `max_buy_count` | 当日最大买入意图数。 |
| `max_sell_count` | 当日最大卖出意图数。 |
| `model_name` | 输入模型名称。 |
| `signal_artifact` | 输入 ModelSignalArtifact manifest。 |

禁止输出：

```text
execution_date
execution_price
execution_quantity
commission
tax
cash
equity
daily_return
realized_pnl
broker_order_id
```

## 8. 典型规则写法

### 8.1 `top50_exit_one_worst_sell`

语义：

- 持仓仍在 qlib top50 内时，不因为 LTR rank 波动主动卖出；
- 若有持仓跌出 qlib top50，每日最多卖出 `full_qlib_rank` 最差的一支；
- 每日最多买入一支；
- 买入标的是 qlib top50 内按 `buy_score` 排名最高且当前未持有的股票；
- LTR 模型只改变买入排序，不改变卖出边界。

### 8.2 多买多卖策略

如果未来新增多买多卖策略，必须显式声明：

```yaml
max_buy_count: N
max_sell_count: M
```

并在 `strategy_decision_audit.csv` 中记录每一支股票入选原因、排序和被跳过原因。

买入数量不得超过卖出释放的名额，除非 PortfolioState/StrategyRuleConfig 明确支持现金扩仓。

### 8.3 部分卖出策略

如果未来支持只卖一支股票的 50%，不得在当前 `OrderIntentArtifact` 中偷放成交数量。应先扩展合同，新增意图字段，例如：

```text
intent_weight_delta
intent_quantity_ratio
```

并同步更新 validator、replay engine 和前端展示。

## 9. Qlib 与 LTR 的统一适配

同一策略应能同时适配纯 Qlib 和 LTR：

| 模型类型 | `candidate_rank` / `full_qlib_rank` | `buy_score` |
| --- | --- | --- |
| 纯 Qlib | 来自 Qlib | 来自 Qlib |
| Qlib + LTR | 仍来自底座 Qlib | 来自 LTR 重排分数 |

因此策略代码不得写：

```text
if model_family == "ltr": change sell boundary
```

正确做法是让 ModelAdapter 负责把模型输出转为统一 `ModelSignalArtifact`。

## 10. 回放接入

回放模块只消费：

```text
OrderIntentArtifact
PriceStore
ExecutionConfig
```

回放负责：

- 确定执行日；
- 使用 next_open 或 next_close；
- 计算成交数量；
- 计算手续费、交易税、现金、净值；
- 输出 ReplayResultArtifact。

回放不得重新实现策略逻辑。如果新增策略后必须修改回放脚本，通常说明策略和回放没有解耦，需要先停下来修模块边界。

## 11. 前端接入

前端展示策略结果时，应读取标准 API 或标准 artifact 摘要：

- 今日排名：`GET /api/tw-stock/current-strategy-context`
- 今日策略意图：策略模块输出的 `OrderIntentArtifact` 对应 API
- 历史回放：ReplayResultArtifact 对应 API

前端不得：

- 直接把 `ltr_top10` 当成买入指令；
- 在组件里重新计算策略；
- 直接读取本地 CSV；
- 暴露 diagnostic-only 策略为默认候选；
- 触发 POST refresh、provider publish、accepted latest、broker/order。

## 12. 最小测试清单

新增策略至少跑：

```bash
python -m py_compile <strategy_script_or_module>
python scripts/validate_tw_modular_artifact_contract.py --artifact <order_intent_manifest>
python scripts/validate_tw_modular_order_intent_artifact.py --manifest <order_intent_manifest>
python scripts/validate_tw_modular_order_intent_replay.py --manifest <replay_result_manifest>
PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_readonly_replay_window_api.py -q
```

如果触碰 registry：

```bash
PYTHONPATH=backend python -m pytest backend/tests/test_phase_yz0_clean_registry.py -q
```

如果触碰前端：

```bash
cd frontend
corepack pnpm build
```

如果触碰日更脚本：

```bash
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
```

## 13. 审查清单

审查者至少确认：

- 策略 dependency YAML 存在且字段完整；
- 策略只读取标准 ModelSignalArtifact；
- 策略输出是 OrderIntentArtifact，不含成交、现金、净值、收益；
- 不含 future return / future label；
- qlib 与 LTR 共用同一规则逻辑；
- LTR 没有改变 qlib top50 卖出边界；
- replay 只执行意图，不重新计算策略；
- diagnostic-only 策略未进入默认候选或前端默认展示；
- 未触发 provider publish、accepted latest、monitor、broker/order；
- OOS 窗口没有落入训练集。

## 14. 新策略工作文档模板

```text
# Phase Sx 新策略接入工作文档

## 目标

新增策略 `{strategy_rule}`，只输出 OrderIntentArtifact，并用同一套回放引擎做只读 OOS replay。

## 冻结范围

- 模型：不训练、不调参、不改 ModelSignalArtifact。
- 数据：不拉新数据、不改 provider accepted latest。
- 前端：除非本阶段明确要求，否则不改前端。
- 策略：只新增 `{strategy_rule}`。
- 回放：只消费 OrderIntentArtifact。

## 执行步骤

1. 新增 dependency YAML，并写明 required fields、ranking usage、max buy/sell、diagnostic 标记。
2. 实现策略到 OrderIntentArtifact 的转换。
3. 跑 validator，确认无 forbidden fields/actions。
4. 用固定 OOS 窗口跑只读 replay。
5. 写执行报告，列出输入 artifact、输出 artifact、测试命令和风险。

## 禁止事项

- 不得训练模型。
- 不得改变默认策略。
- 不得把训练集收益当策略优劣证据。
- 不得触发 provider publish / accepted latest / monitor / broker / order。
- 不得在 replay 中重写策略。

## 验收门槛

- dependency validator 通过。
- OrderIntentArtifact validator 通过。
- ReplayResultArtifact validator 通过。
- qlib/LTR 适配逻辑一致。
- 审查者确认无未来函数、无训练集回放、无只读边界违规。
```
