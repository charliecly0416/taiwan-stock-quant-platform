# Phase D2 ReplayExecutionEngine 解耦执行报告

生成日期：2026-06-17

## 1. 执行范围

本轮按照 `PHASED1_REVIEW_AND_PHASED2_WORK_CN.md` 执行 D2：新增 parallel D2 replay runner，让 replay execution 消费 `OrderIntentArtifact`。

D2 本轮没有直接修改旧 replay 脚本：

```text
scripts/run_tw_modular_config_replay_matrix.py
```

这样保留旧 replay/parity 基线不变。D2 通过新增 runner 证明 replay execution 可以从 OrderIntentArtifact 执行初步回放。

新增/修改文件：

```text
scripts/run_tw_modular_order_intent_replay.py
scripts/validate_tw_modular_order_intent_replay.py
tests/unit/test_tw_modular_order_intent_replay.py
scripts/build_tw_modular_order_intent_artifact.py
scripts/validate_tw_modular_order_intent_artifact.py
tests/unit/test_tw_modular_order_intent_artifact.py
docs/tw_modular_contracts/PHASED2_REPLAY_ENGINE_DECOUPLING_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/PHASED2_REPLAY_ENGINE_DECOUPLING_REVIEW_HANDOFF_CN.md
```

说明：D1 builder/validator 做了向后兼容扩展，新增 `artifact_stage=d2_replay_input`，D1 默认 `d1_decision_sample` 不变。

## 2. D2 输入产物

D2 replay input OrderIntentArtifact：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/d2_order_intent_20260506_20260617T042642Z/manifest.json
```

关键属性：

```text
artifact_stage=d2_replay_input
model_name=e4_frozen_qlib_2023_2025_ltr
strategy_rule=top50_exit_one_worst_sell
signal_date=2026-05-06
not_parity_evidence=true
portfolio_state_source=legacy_replay_snapshot_for_d2_initial_state_sample_only
```

该 OrderIntentArtifact 通过：

```bash
python scripts/validate_tw_modular_order_intent_artifact.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/d2_order_intent_20260506_20260617T042642Z/manifest.json --json
```

结果：`ok=true`。

## 3. ReplayExecutionEngine 输入/输出合同

D2 runner 输入：

```text
OrderIntentArtifact
PriceStore
ExecutionConfig
InitialPortfolioState
```

D2 runner 从 OrderIntentArtifact 读取决策字段：

```text
signal_date
instrument
intent_action
intent_reason
strategy_rule
model_name
```

D2 runner 不读取 `ModelSignalArtifact` 重新决定买卖。`ModelSignalArtifact` 只作为 OrderIntentArtifact 的 provenance 出现。

D2 replay output：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/d2_order_intent_replay_20260506_20260617T042642Z/manifest.json
```

输出文件：

```text
summary.csv
actions.csv
daily_nav.csv
position_snapshots.csv
coverage_audit.csv
position_integrity_audit.csv
forbidden_field_audit.csv
execution_audit.csv
decision_source_audit.csv
manifest.json
```

## 4. 如何确认 replay 不再调用 choose_sells / buy_order 决策逻辑

D2 新 runner：

```text
scripts/run_tw_modular_order_intent_replay.py
```

不包含：

```text
def choose_sells
choose_sells(
candidate_rank <=
buy_score
score_rank
```

单测 `test_d2_runner_source_does_not_embed_strategy_decision` 对以上模式做静态检查。

D2 manifest 和 `decision_source_audit.csv` 均声明：

```text
decision_source=order_intent_artifact
no_inline_strategy_decision=true
no_choose_sells_call=true
no_model_signal_decision_read=true
```

## 5. Execution / Accounting 保持说明

D2 runner 复用现有 S2D price/execution primitives：

```text
PriceStore
FEE_RATE
SELL_TAX_RATE
LOT_SIZE
```

执行语义：

- `intent_action=sell` 转换为 next-day `historical_risk_reduce`；
- `intent_action=buy` 转换为 next-day `historical_add`；
- sell 先于 buy 执行；
- sell 使用当前持仓数量；
- buy 使用现金与剩余持仓槽位计算整手数量；
- commission/tax 在 execution date 记账；
- daily_nav 在 signal date 与 execution date 输出；
- 缺 price 或无法成交写 skip。

D2 未修改旧 replay execution 主体，也未改变旧 replay matrix 输出。

## 6. D2 ReplayResultArtifact

D2 replay artifact：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/d2_order_intent_replay_20260506_20260617T042642Z/manifest.json
```

validator 结果：

```text
ok=true
action_count=2
skipped_action_count=0
```

actions：

```text
2026-05-06 -> 2026-05-07 TW2467 historical_risk_reduce
2026-05-06 -> 2026-05-07 TW2337 historical_add
```

所有 active actions 均满足：

```text
execution_date > signal_date
quantity > 0
order_intent_artifact == D2 input artifact
```

## 7. Validator 检查项

`validate_tw_modular_order_intent_replay.py` 检查：

- artifact_type / schema_version；
- decision_source 必须为 `order_intent_artifact`；
- OrderIntentArtifact 存在；
- `not_d3_parity_evidence=true`；
- `parity_status=not_claimed_d2_single_strategy_sample`；
- `no_inline_strategy_decision=true`；
- `no_choose_sells_call=true`；
- `no_model_signal_decision_read=true`；
- required output files 存在；
- actions required columns 存在；
- active action execution_date > signal_date；
- active quantity > 0；
- active actions 引用同一个 OrderIntentArtifact；
- coverage / integrity / forbidden / execution audit / decision source audit 无 fail。

## 8. 是否只完成主策略初步 replay

是。

D2 本轮只完成：

```text
e4_frozen_qlib_2023_2025_ltr + top50_exit_one_worst_sell + 2026-05-06
```

这是单日主策略初步 replay，用于证明 ReplayExecutionEngine 可以消费 OrderIntentArtifact。

D2 明确未完成：

```text
五规则 parity
summary parity
daily_nav parity
actions parity
action key parity
```

这些属于 D3。

## 9. 验证结果

已执行：

```bash
python -m py_compile scripts/build_tw_modular_order_intent_artifact.py scripts/validate_tw_modular_order_intent_artifact.py scripts/run_tw_modular_order_intent_replay.py scripts/validate_tw_modular_order_intent_replay.py
```

结果：pass。

```bash
python scripts/run_tw_modular_order_intent_replay.py --json
```

结果：`ok=true`，生成 D2 replay artifact。

```bash
python scripts/validate_tw_modular_order_intent_replay.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/d2_order_intent_replay_20260506_20260617T042642Z/manifest.json --json
```

结果：`ok=true`。

```bash
python scripts/validate_tw_modular_order_intent_artifact.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/d2_order_intent_20260506_20260617T042642Z/manifest.json --json
```

结果：`ok=true`。

```bash
python -m pytest tests/unit/test_tw_modular_order_intent_artifact.py tests/unit/test_tw_modular_order_intent_replay.py
```

结果：`9 passed`。

```bash
python scripts/audit_tw_modular_decision_replay_d0.py --json
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

结果：全部 `ok=true`。

## 10. 禁止事项确认

D2 未触碰：

```text
frontend
backend/API
backend_api_python
src/api
scripts/run_daily_tw_stock_auto_update.py
provider accepted latest
monitor
broker
quick-trade
order
target position
target weight
```

D2 未执行训练、调参、score recompute，未修改默认模型或默认策略。

D2 未宣称 D3 parity 已完成，未将初步 replay 结果作为产品化收益证据。

## 11. D2 结论

D2 已完成 parallel ReplayExecutionEngine 样例：replay execution 可只消费 `OrderIntentArtifact` 执行单日主策略初步回放，并输出可验证的 `ReplayResultArtifact`。

D3 需要继续完成五规则全窗口 parity。
