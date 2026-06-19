# Phase D0 审查与 Phase D1 工作文档

生成日期：2026-06-17

## 1. D0 审查结论

D0 审查通过，允许进入 D1。

D0 已完成“决策与回放解耦”主线的合同冻结与可行性审计：

- 没有抽取 `StrategyDecisionEngine` 实现；
- 没有生成正式 `OrderIntentArtifact`；
- 没有修改 replay 结果；
- 没有修改前端、API、日更、默认策略；
- 没有训练、调参、score recompute、replay recompute；
- 没有 provider publish、accepted latest switch、monitor、broker、quick-trade、order 越界。

D0 审计结论：

```text
ok=true
d0_conclusion=feasible_to_enter_d1
```

## 2. 审查对象

工作主文档：

```text
docs/tw_modular_contracts/TW_MODULAR_DECISION_REPLAY_DECOUPLING_WORK_CN.md
```

D0 工作冻结文档：

```text
docs/tw_modular_contracts/PHASED0_DECISION_REPLAY_DECOUPLING_WORK_CN.md
```

D0 执行报告：

```text
docs/tw_modular_contracts/PHASED0_DECISION_REPLAY_DECOUPLING_EXECUTION_REPORT_CN.md
```

D0 handoff：

```text
docs/tw_modular_contracts/PHASED0_DECISION_REPLAY_DECOUPLING_REVIEW_HANDOFF_CN.md
```

D0 审计脚本：

```text
scripts/audit_tw_modular_decision_replay_d0.py
```

D0 审计输出：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/decision_replay_decoupling_d0/
```

## 3. 复核结果

### 3.1 D0 审计复跑通过

复核命令：

```bash
python -m py_compile scripts/audit_tw_modular_decision_replay_d0.py
python scripts/audit_tw_modular_decision_replay_d0.py --json
```

结果：

```text
py_compile: pass
ok: true
phase: D0
signal_input_models: 5
rule_count: 5
d0_conclusion: feasible_to_enter_d1
```

普通 sandbox 下 Python 命令仍可能出现 `bwrap: loopback: Failed RTM_NEWADDR`，复核时使用升级执行方式完成。

### 3.2 ModelSignalArtifact 输入可行

`signal_input_audit.csv` 显示 5 个模型全部通过：

```text
fresh_qlib_adaptive: pass
fresh_qlib_2025_ltr: pass
frozen_qlib_2025_ltr: pass
e4_frozen_qlib_2023_2025_ltr: pass
frozen_qlib_2018_2022: pass
```

最低决策输入字段均存在：

```text
date
instrument
candidate_rank
buy_score
score_rank
full_qlib_rank
signal_asof
available_at
```

未发现 D0 禁止字段：

```text
future_return_*
future_excess_return_*
forward_return_*
label_*
relevance_10d_top_heavy
ltr_relevance_label
execution_price
execution_date
cash
equity
drawdown
broker_order_id
```

### 3.3 五种冻结规则均可表达为 OrderIntent

`rule_expressibility_audit.csv` 显示五规则均为 `pass`：

```text
original
top50_exit_all
top50_exit_one_worst_sell
one_sell_one_buy_correct
one_sell_one_buy_buggy_e8r
```

`one_sell_one_buy_buggy_e8r` 保持：

```text
diagnostic_only=True
not_valid_strategy_evidence=True
```

### 3.4 当前耦合点定位准确

`scripts/run_tw_modular_config_replay_matrix.py` 中当前耦合点：

```text
def choose_sells(...)
def replay_strategy(...)
sells = choose_sells(rule, holdings, state)
for symbol in buy_order:
append_order(..., f"{rule}_sell", ...)
append_order(..., f"{rule}_buy", ...)
```

D0 对耦合点判断准确：策略决策和 replay 记账仍混在 `replay_strategy()` 内。

### 3.5 Replay decoupling 可行性通过

`replay_decoupling_feasibility_audit.csv` 全部通过：

```text
current_decision_replay_coupling: pass
legacy_replay_parity_baseline_available: pass
replay_can_consume_order_intent: pass
readonly_snapshot_not_canonical_decision_input: pass
```

D3 parity 基线已存在：

```text
r2_parity_audit.csv
r10_action_window_parity_audit.csv
```

### 3.6 Readonly snapshot 边界通过

`readonly_snapshot_boundary_audit.csv` 全部通过：

```text
shadow_manifest_readonly_only: pass
shadow_links_standard_artifacts: pass
readonly_snapshot_boundary: pass
```

结论：readonly snapshot 只能作为展示层，不得作为 `StrategyDecisionEngine` 的 canonical 输入。

## 4. D1 硬 Gate 与必须澄清项

### 4.1 `buy_rank` 字段来源必须冻结

D0 冻结的 `OrderIntentArtifact` 字段包含：

```text
buy_rank
```

但当前标准 `ModelSignalArtifact` 可用字段是：

```text
candidate_rank
score_rank
full_qlib_rank
buy_score
```

D1 必须明确 `buy_rank` 的来源映射，不能在 builder 中临时发明语义。建议采用：

```text
buy_rank = score_rank
```

更完整定义为：

```text
buy_rank 是策略买入排序 rank，由 ModelSignalArtifact 中 buy_score 按日降序、instrument 升序 tie-break 得到；当前五规则中直接映射自 score_rank。
```

必须禁止：

- 在 builder 中临时重新排序却不审计；
- 用 `candidate_rank` 代替 `buy_rank`；
- 用 LTR 私有列或 legacy score 列重新计算 rank；
- qlib 与 LTR 使用不同 tie-break。

Validator 必须检查以下至少一项：

```text
order_intents.buy_rank == source_signal.score_rank
```

或：

```text
buy_rank == rank(buy_score desc, instrument asc) per signal_date
```

若 `buy_rank` 映射未定义或未被 validator 检查，D1 不得通过。

### 4.2 `PortfolioState` 来源必须冻结

D1 必须回答：

```text
StrategyDecisionEngine 在生成意图时，当前持仓从哪里来？
```

D1 只允许生成两类产物：

1. 单日 latest / sample intent；
2. 基于 legacy replay snapshots 的样例 intent。

D1 不得尝试完整替代 replay loop，也不得自行演化现金、价格、成交和持仓。

如果 D1 生成全窗口样例 intent，`PortfolioState` 必须来自：

```text
legacy replay position snapshots
```

并在 manifest 中记录：

```text
portfolio_state_source: legacy_replay_snapshot_for_d1_sample_only
not_d2_replay_execution_source: true
```

D1 不得把 readonly snapshot 的 `hold_candidates` 当作 canonical portfolio state。

D2/D3 正式拆分时，`PortfolioState` 应由 `ReplayExecutionEngine` 在每日执行完 pending intents、更新持仓后传给 `StrategyDecisionEngine`：

```text
ReplayExecutionEngine maintains portfolio state
  -> calls StrategyDecisionEngine for signal_date
  -> receives OrderIntent rows
  -> schedules next-day execution
```

### 4.3 D1 产物必须标注样例性质

如果 D1 生成 `OrderIntentArtifact`，但尚未由 D2 replay engine 消费，manifest 必须明确：

```text
artifact_stage: d1_decision_sample
not_used_for_replay_result: true
not_parity_evidence: true
```

D1 报告不得宣称：

- replay 已解耦；
- 收益已复现；
- parity 已完成；
- 可以替代旧 replay。

D1 只能宣称：

```text
StrategyDecisionEngine can emit contract-valid OrderIntentArtifact.
```

### 4.4 D0 审计是可行性审计，不是 parity 证明

D0 证明“五规则可以表达为 order intent”，但没有证明抽出后结果等价。

D1/D2 不得把 D0 的 `pass` 当成行为一致证据。真正行为等价必须在 D3 完成：

```text
summary parity
daily_nav parity
actions parity
action key parity
```

### 4.5 D1 放行 Gate

D1 放行必须全部满足：

```text
buy_rank_mapping_defined == true
buy_rank_mapping_validated == true
portfolio_state_source_defined == true
readonly_snapshot_not_portfolio_state == true
d1_artifact_marked_sample_if_not_replay_consumed == true
no_replay_execution_change == true
no_parity_claim_in_d1 == true
```

任一失败，不得进入 D2。

## 5. D1 工作目标

D1 目标：

```text
抽出 StrategyDecisionEngine，并生成独立 OrderIntentArtifact。
```

D1 只做决策模块和意图产物，不改 replay execution 主体。

允许新增：

```text
scripts/build_tw_modular_order_intent_artifact.py
scripts/validate_tw_modular_order_intent_artifact.py
data_tw/artifacts/order_intents/{strategy_rule}/{run_id}/
docs/tw_modular_contracts/PHASED1_STRATEGY_DECISION_ENGINE_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/PHASED1_STRATEGY_DECISION_ENGINE_REVIEW_HANDOFF_CN.md
```

可选新增：

```text
tests/unit/test_tw_modular_order_intent_artifact.py
docs/tw_modular_contracts/ORDER_INTENT_ARTIFACT_D1_SCHEMA_CN.md
```

## 6. D1 必须实现

### 6.1 StrategyDecisionEngine

必须实现五个独立决策函数：

```text
decide_original(...)
decide_top50_exit_all(...)
decide_top50_exit_one_worst_sell(...)
decide_one_sell_one_buy_correct(...)
decide_one_sell_one_buy_buggy_e8r(...)
```

函数只能消费：

```text
ModelSignalArtifact rows
PortfolioState
StrategyRuleConfig
```

函数只能输出：

```text
OrderIntent rows
```

不得计算：

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

### 6.2 OrderIntentArtifact

每个 artifact 至少包含：

```text
manifest.json
order_intents.csv
schema.json
strategy_decision_audit.csv
forbidden_action_audit.json
```

`order_intents.csv` 至少包含：

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

建议同时包含：

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
artifact_stage
not_used_for_replay_result
not_parity_evidence
```

`intent_action` 只能是：

```text
buy
sell
hold
skip
```

### 6.3 Validator

`validate_tw_modular_order_intent_artifact.py` 必须检查：

- required fields 存在；
- `intent_action` 枚举合法；
- 每日 `buy` 数量不超过 `max_buy_count`；
- 每日 `sell` 数量不超过 `max_sell_count`，`unbounded` 例外；
- `one_sell_one_buy_buggy_e8r` 必须 `diagnostic_only=true` 且 `not_valid_strategy_evidence=true`；
- 禁止字段不存在；
- 不含 broker/order id；
- 不含 execution/price/fee/tax/cash/nav/pnl 字段；
- 不含 future return / label 字段；
- `readonly_only=true`、`not_order=true`、`not_target_position=true`；
- `signal_artifact` 指向标准 ModelSignalArtifact；
- `buy_rank` 映射规则明确并可验证；
- `portfolio_state_source` 存在；
- 若 `portfolio_state_source=legacy_replay_snapshot_for_d1_sample_only`，必须同时有 `not_d2_replay_execution_source=true`；
- 如果 artifact 尚未被 D2 replay engine 消费，必须有 `artifact_stage=d1_decision_sample`、`not_used_for_replay_result=true`、`not_parity_evidence=true`；
- `hold` / `skip` 意图必须能由规则解释，不能作为未分类 fallback 混入。

### 6.4 样例产物范围

D1 可以生成样例 `OrderIntentArtifact`，但只能基于当前已审查的 signal artifact 和 replay config。

D1 样例 artifact 必须标记样例性质：

```text
artifact_stage: d1_decision_sample
not_used_for_replay_result: true
not_parity_evidence: true
```

如果样例使用 legacy replay snapshots 作为持仓来源，manifest 必须记录：

```text
portfolio_state_source: legacy_replay_snapshot_for_d1_sample_only
not_d2_replay_execution_source: true
```

建议至少生成：

```text
data_tw/artifacts/order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/{run_id}/
```

如果时间允许，可生成五规则全量样例。但 D1 通过最低要求是：

```text
五规则决策函数存在；
validator 可验证；
至少一个主策略样例 artifact 通过；
diagnostic 规则边界有测试。
```

## 7. D1 禁止事项

D1 禁止：

- 修改前端；
- 修改 API；
- 修改 daily orchestrator；
- 修改 provider accepted latest；
- 修改 readonly snapshot schema；
- 修改 replay execution 记账主体；
- 使用 OrderIntent 结果替换现有 replay；
- 重算 replay 收益作为策略证据；
- 训练；
- 调参；
- score recompute；
- 改默认模型；
- 改默认策略；
- broker / quick-trade / order；
- monitor scan / config save / alerts write；
- 输出 target position / target weight。

## 8. D1 验证命令

执行者至少运行：

```bash
python -m py_compile scripts/build_tw_modular_order_intent_artifact.py scripts/validate_tw_modular_order_intent_artifact.py
python scripts/build_tw_modular_order_intent_artifact.py --json
python scripts/validate_tw_modular_order_intent_artifact.py --artifact <artifact_manifest> --json
python -m pytest tests/unit/test_tw_modular_order_intent_artifact.py
python scripts/audit_tw_modular_decision_replay_d0.py --json
```

如果复用现有模块测试，也应保证：

```bash
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

## 9. D1 执行报告必须说明

D1 执行报告必须包含：

```text
新增文件清单
决策函数清单
每个规则的 buy/sell/hold/skip 映射
OrderIntentArtifact schema
validator 检查项
样例 artifact 路径
diagnostic-only 规则处理
buy_rank 映射定义
PortfolioState 来源定义
D1 样例 artifact 标记
是否声明 not_used_for_replay_result / not_parity_evidence
禁止字段审计结果
验证命令与结果
是否修改 replay execution 主体
是否声称 replay parity 或收益复现
是否触碰前端/API/daily/provider/交易链路
```

## 10. D1 审查交接必须输出

执行者完成后必须输出：

```text
docs/tw_modular_contracts/PHASED1_STRATEGY_DECISION_ENGINE_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/PHASED1_STRATEGY_DECISION_ENGINE_REVIEW_HANDOFF_CN.md
```

审查者重点审查：

- 决策函数是否真的独立；
- 是否仍有策略逻辑只能在 replay loop 内表达；
- `OrderIntentArtifact` 是否不含 execution/accounting 字段；
- validator 是否能拒绝 forbidden 字段；
- `buy_rank` 是否定义并被 validator 检查；
- `PortfolioState` 来源是否明确；
- 是否把 readonly snapshot 的 `hold_candidates` 错当 canonical portfolio state；
- D1 artifact 是否标记 `not_used_for_replay_result=true` 和 `not_parity_evidence=true`；
- D1 报告是否错误宣称 parity / replay 解耦完成；
- diagnostic 规则是否未被包装成有效策略；
- 是否没有改 replay execution 主体；
- 是否没有前端/API/daily/provider/交易链路越界。

## 11. 最终结论

D0 通过。

可以进入 D1，但 D1 只允许实现 `StrategyDecisionEngine`、`OrderIntentArtifact` builder 和 validator。不得改 replay execution 主体；D2 才处理 replay 只消费 order intent；D3 才做五规则 parity。
