# Phase D1 StrategyDecisionEngine 执行报告

生成日期：2026-06-17

## 1. 执行范围

本轮按照 `PHASED0_REVIEW_AND_PHASED1_WORK_CN.md` 执行 D1：抽出 `StrategyDecisionEngine`，并生成独立 `OrderIntentArtifact` 样例产物。

D1 本轮只做决策模块和意图产物，不修改 replay execution 记账主体，不将 OrderIntent 接入 replay，不声明 parity。

新增文件：

```text
scripts/build_tw_modular_order_intent_artifact.py
scripts/validate_tw_modular_order_intent_artifact.py
tests/unit/test_tw_modular_order_intent_artifact.py
docs/tw_modular_contracts/PHASED1_STRATEGY_DECISION_ENGINE_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/PHASED1_STRATEGY_DECISION_ENGINE_REVIEW_HANDOFF_CN.md
```

新增样例产物：

```text
data_tw/artifacts/order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/d1_order_intent_20260507_20260617T040825Z/manifest.json
```

## 2. 决策函数清单

`build_tw_modular_order_intent_artifact.py` 已实现五个独立决策函数：

```text
decide_original(...)
decide_top50_exit_all(...)
decide_top50_exit_one_worst_sell(...)
decide_one_sell_one_buy_correct(...)
decide_one_sell_one_buy_buggy_e8r(...)
```

函数只消费：

```text
ModelSignalArtifact rows
PortfolioState
StrategyRuleConfig
```

函数只输出内存中的 OrderIntent rows，由 builder 写入 `OrderIntentArtifact`。

函数不计算：

```text
execution_date
execution_price
execution_quantity
commission
tax
cash
equity
daily_return
drawdown
realized_pnl
unrealized_pnl
```

## 3. 五规则映射

| rule | sell 映射 | buy 映射 | hold/skip | 状态 |
| --- | --- | --- | --- | --- |
| original | 卖出不在 buy top10 的持仓 | qlib top50 内按 buy_score/score_rank 候选买入 | 未卖出持仓为 hold | implemented |
| top50_exit_all | 卖出所有跌出 qlib top50 的持仓 | qlib top50 内按 buy_score/score_rank 候选买入 | 未卖出持仓为 hold | implemented |
| top50_exit_one_worst_sell | 最多卖出一支 top50 外 full_qlib_rank 最差持仓 | qlib top50 内按 buy_score/score_rank 候选买入 | 未卖出持仓为 hold | implemented |
| one_sell_one_buy_correct | 每日最多一卖；top50 外优先，否则卖买入排序最差持仓 | 每日最多一买 | 未卖出持仓为 hold | implemented |
| one_sell_one_buy_buggy_e8r | diagnostic-only 历史 bug 选择逻辑 | diagnostic-only 一买复现 | 未卖出持仓为 hold | implemented |

`skip` 在 D1 builder 中保留为合法输出，但主策略样例未产生 skip 行。validator 要求 hold/skip 不能作为未分类 fallback 混入，必须带 `_hold` / `_skip` reason。

## 4. OrderIntentArtifact Schema

样例 artifact 包含：

```text
manifest.json
order_intents.csv
schema.json
strategy_decision_audit.csv
forbidden_action_audit.json
```

`order_intents.csv` required fields：

```text
signal_date
instrument
intent_action
intent_reason
strategy_rule
candidate_rank
buy_rank
full_qlib_rank
max_buy_count
max_sell_count
model_name
signal_artifact
```

D1 额外审计字段：

```text
readonly_only
not_order
not_target_position
not_investment_advice
diagnostic_only
not_valid_strategy_evidence
source_signal_asof
source_available_at
portfolio_state_source
not_d2_replay_execution_source
artifact_stage
not_used_for_replay_result
not_parity_evidence
current_holding_flag
target_holding_count
candidate_k
tie_breaker
buy_rank_mapping
buy_rank_source
```

## 5. buy_rank 映射定义

D1 冻结 `buy_rank` 映射：

```text
buy_rank == source_signal.score_rank when source signal row exists
```

当前五规则中，候选买入和仍在候选池内的持仓均必须满足此映射，并由 validator 读取 `signal_artifact` 后逐行校验。

对于已经跌出 qlib top50、因此在当日 `ModelSignalArtifact` top50 行中不存在的 sell/hold 样例行，D1 使用：

```text
buy_rank = -1
buy_rank_source = outside_candidate_full_rank_sample_only
```

该值只用于 D1 sample artifact 的必填字段占位，不作为买入排序、产品展示排序或 replay 输入证据。真正 exit 比较仍使用 `full_qlib_rank`。

validator 对 `buy_rank >= 0` 的行执行：

```text
order_intents.buy_rank == source_signal.score_rank
```

并要求 manifest 中存在 `buy_rank_mapping_defined=true`。

## 6. PortfolioState 来源

D1 样例的 PortfolioState 来源：

```text
legacy_replay_snapshot_for_d1_sample_only
```

来源文件：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_position_snapshots.csv
```

manifest 与每行 order intent 均声明：

```text
portfolio_state_source=legacy_replay_snapshot_for_d1_sample_only
not_d2_replay_execution_source=true
readonly_snapshot_not_portfolio_state=true
```

D1 未使用 readonly snapshot 的 `hold_candidates` 作为 canonical portfolio state。

D2/D3 正式拆分时，PortfolioState 应由 ReplayExecutionEngine 在执行 pending intents 后维护并传入 StrategyDecisionEngine。

## 7. 样例 Artifact

样例 artifact：

```text
data_tw/artifacts/order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/d1_order_intent_20260507_20260617T040825Z/manifest.json
```

样例配置：

```text
model_name=e4_frozen_qlib_2023_2025_ltr
strategy_rule=top50_exit_one_worst_sell
signal_date=2026-05-07
artifact_stage=d1_decision_sample
```

样例 intent counts：

```text
buy=1
sell=1
hold=8
skip=0
```

样例明确声明：

```text
not_used_for_replay_result=true
not_parity_evidence=true
```

因此它不是 replay 解耦结果，不是收益复现证据，也不是 D3 parity 证据。

## 8. Validator 检查项

`validate_tw_modular_order_intent_artifact.py` 检查：

- artifact_type / schema_version；
- required fields；
- `intent_action` 枚举；
- 每日 buy/sell 数量不超过 max；
- `unbounded` sell 例外；
- forbidden fields 不存在；
- future return / label 字段不存在；
- broker/order/target position/target weight 字段不存在；
- `readonly_only=true`；
- `not_order=true`；
- `not_target_position=true`；
- `not_investment_advice=true`；
- `artifact_stage=d1_decision_sample`；
- `not_used_for_replay_result=true`；
- `not_parity_evidence=true`；
- `portfolio_state_source` 存在；
- legacy sample PortfolioState 必须同时 `not_d2_replay_execution_source=true`；
- readonly snapshot 不作为 portfolio state；
- `signal_artifact` 存在；
- hold/skip reason 合法；
- diagnostic 规则边界；
- `buy_rank_mapping_defined`；
- `buy_rank_mapping_validated`；
- forbidden action audit pass。

## 9. Diagnostic-only 规则处理

`one_sell_one_buy_buggy_e8r` 决策函数已实现，但保持 diagnostic-only 边界。

单测 `test_diagnostic_rule_artifact_keeps_diagnostic_boundary` 会生成 diagnostic 样例并验证：

```text
diagnostic_only=true
not_valid_strategy_evidence=true
diagnostic_rule_boundary=pass
```

该规则未被声明为有效策略证据，未进入默认策略或产品展示。

## 10. 验证结果

已执行：

```bash
python -m py_compile scripts/build_tw_modular_order_intent_artifact.py scripts/validate_tw_modular_order_intent_artifact.py
```

结果：pass。

```bash
python scripts/build_tw_modular_order_intent_artifact.py --json
```

结果：`ok=true`，生成主策略样例 artifact，`row_count=10`。

```bash
python scripts/validate_tw_modular_order_intent_artifact.py --artifact data_tw/artifacts/order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/d1_order_intent_20260507_20260617T040825Z/manifest.json --json
```

结果：`ok=true`，所有 checks pass。

```bash
python -m pytest tests/unit/test_tw_modular_order_intent_artifact.py
```

结果：`5 passed`。

```bash
python scripts/audit_tw_modular_decision_replay_d0.py --json
```

结果：`ok=true`，`d0_conclusion=feasible_to_enter_d1`。

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

结果：`ok=true`。

```bash
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

结果：`ok=true`。

## 11. 禁止事项确认

D1 未修改 replay execution 主体。

D1 未声称：

```text
replay 已解耦
收益已复现
parity 已完成
OrderIntent 可替代旧 replay
```

D1 未触碰：

```text
frontend
API
daily orchestrator
provider accepted latest
readonly snapshot schema
monitor
broker
quick-trade
order
target position
target weight
```

D1 未执行训练、调参、score recompute、replay recompute，也未修改默认模型或默认策略。

## 12. D1 Gate 结果

```text
buy_rank_mapping_defined=true
buy_rank_mapping_validated=true
portfolio_state_source_defined=true
readonly_snapshot_not_portfolio_state=true
d1_artifact_marked_sample_if_not_replay_consumed=true
no_replay_execution_change=true
no_parity_claim_in_d1=true
```

D1 结论：StrategyDecisionEngine 可以输出 contract-valid 的 D1 sample `OrderIntentArtifact`。允许审查后进入 D2，由 D2 处理 replay engine 只消费 OrderIntent。
