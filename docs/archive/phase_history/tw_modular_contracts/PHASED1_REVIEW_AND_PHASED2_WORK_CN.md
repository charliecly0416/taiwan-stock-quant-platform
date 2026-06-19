# Phase D1 审查与 Phase D2 工作文档

生成日期：2026-06-17

## 1. D1 审查结论

D1 审查通过，允许进入 D2。

D1 已完成 `StrategyDecisionEngine` 与 D1 sample `OrderIntentArtifact`：

- 五个 `decide_*` 函数独立存在；
- builder 生成 contract-valid 的 D1 sample `OrderIntentArtifact`；
- validator 能检查 required fields、forbidden fields、buy/sell count、diagnostic boundary、`buy_rank` 映射、sample-only 标记；
- `buy_rank` 映射已定义并验证；
- `PortfolioState` 来源已标记为 `legacy_replay_snapshot_for_d1_sample_only`；
- D1 artifact 已标记 `not_used_for_replay_result=true`、`not_parity_evidence=true`；
- 未修改 replay execution 主体；
- 未触碰前端、API、daily orchestrator、provider accepted latest、monitor、broker、quick-trade、order；
- 未训练、未调参、未 score recompute、未 replay recompute；
- 未宣称 replay parity 或收益复现。

## 2. 审查对象

D1 handoff：

```text
docs/tw_modular_contracts/PHASED1_STRATEGY_DECISION_ENGINE_REVIEW_HANDOFF_CN.md
```

D1 执行报告：

```text
docs/tw_modular_contracts/PHASED1_STRATEGY_DECISION_ENGINE_EXECUTION_REPORT_CN.md
```

新增脚本：

```text
scripts/build_tw_modular_order_intent_artifact.py
scripts/validate_tw_modular_order_intent_artifact.py
```

新增测试：

```text
tests/unit/test_tw_modular_order_intent_artifact.py
```

样例 artifact：

```text
data_tw/artifacts/order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/d1_order_intent_20260507_20260617T040825Z/manifest.json
```

## 3. 复核结果

### 3.1 决策函数独立存在

`scripts/build_tw_modular_order_intent_artifact.py` 已实现：

```text
decide_original
decide_top50_exit_all
decide_top50_exit_one_worst_sell
decide_one_sell_one_buy_correct
decide_one_sell_one_buy_buggy_e8r
```

这些函数输入为：

```text
day_state
portfolio_state
strategy_config
```

输出为：

```text
sell / buy / hold / skip intent lists
```

未在函数中计算 execution price、quantity、fee、tax、cash、NAV、PnL。

### 3.2 D1 sample artifact 标记正确

样例 manifest：

```text
artifact_type: order_intent
schema_version: order_intent_d1_v1
artifact_stage: d1_decision_sample
model_name: e4_frozen_qlib_2023_2025_ltr
strategy_rule: top50_exit_one_worst_sell
signal_date: 2026-05-07
readonly_only: true
not_order: true
not_target_position: true
not_investment_advice: true
not_used_for_replay_result: true
not_parity_evidence: true
portfolio_state_source: legacy_replay_snapshot_for_d1_sample_only
not_d2_replay_execution_source: true
readonly_snapshot_not_portfolio_state: true
```

样例行数：

```text
buy=1
sell=1
hold=8
skip=0
```

### 3.3 `buy_rank` 映射通过

D1 定义：

```text
buy_rank == source_signal.score_rank when source signal row exists
```

validator 复核结果：

```text
buy_rank_mapping_defined: pass
buy_rank_mapping_validated: pass
```

outside-candidate 行使用：

```text
buy_rank=-1
buy_rank_source=outside_candidate_full_rank_sample_only
```

判断：该哨兵值仅用于 D1 sample 必填字段占位，不作为买入排序、产品展示排序或 replay 证据。D2/D3 不得把 `buy_rank=-1` 当作排序信号；正式 replay 的 exit 比较必须继续使用 `full_qlib_rank` 或规则明确定义字段。

### 3.4 `PortfolioState` 来源通过

D1 样例的 `PortfolioState` 来源：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_position_snapshots.csv
```

manifest 和每行 intent 均标记：

```text
portfolio_state_source=legacy_replay_snapshot_for_d1_sample_only
not_d2_replay_execution_source=true
readonly_snapshot_not_portfolio_state=true
```

未发现使用 readonly snapshot `hold_candidates` 作为 canonical portfolio state。

### 3.5 Validator 负面测试覆盖关键风险

单测覆盖：

```text
decision functions exist
default order intent artifact validates
diagnostic rule artifact keeps diagnostic boundary
forbidden execution_price field is rejected
broken buy_rank mapping is rejected
```

复核结果：

```text
5 passed
```

### 3.6 未修改 replay execution 主体

targeted diff 显示 D1 未修改：

```text
scripts/run_tw_modular_config_replay_matrix.py
```

因此 D1 未提前进入 D2。

## 4. 验证命令

复核命令：

```bash
python -m py_compile scripts/build_tw_modular_order_intent_artifact.py scripts/validate_tw_modular_order_intent_artifact.py
python scripts/build_tw_modular_order_intent_artifact.py --json
python scripts/validate_tw_modular_order_intent_artifact.py --artifact data_tw/artifacts/order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/d1_order_intent_20260507_20260617T040825Z/manifest.json --json
python -m pytest tests/unit/test_tw_modular_order_intent_artifact.py
python scripts/audit_tw_modular_decision_replay_d0.py --json
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

结果：

```text
py_compile: pass
builder: ok=true
OrderIntent validator: ok=true
D1 unit tests: 5 passed
D0 audit: ok=true
contract regression: ok=true
readonly snapshot validator: ok=true
```

说明：普通 sandbox 下部分 Python 命令仍可能出现 `bwrap: loopback: Failed RTM_NEWADDR`，复核时使用升级执行方式完成。

## 5. 非阻塞建议

### P2：D2 必须处理 `buy_rank=-1` 哨兵边界

D1 对 outside-candidate sell/hold 行使用 `buy_rank=-1` 是 sample-only 方案，D1 不阻塞。

D2 接入 replay execution 时必须满足：

```text
buy_rank=-1 不得作为买入排序；
buy_rank=-1 不得用于前端产品排序；
exit / hold 判断必须使用 full_qlib_rank 或规则明确字段；
D2 validator 或 execution audit 必须记录 outside-candidate handling。
```

### P2：D1 只生成主策略样例，D3 前仍需五规则 parity

D1 只证明 StrategyDecisionEngine 可以输出 contract-valid order intent。它不是五规则行为等价证明。

D3 仍必须完成：

```text
summary parity
daily_nav parity
actions parity
action key parity
```

## 6. D2 工作目标

D2 目标：

```text
ReplayExecutionEngine 只消费 OrderIntentArtifact。
```

D2 才允许修改 replay execution 主体，但必须保持行为语义不变。

D2 必须把当前 replay 中的决策逻辑依赖移出 replay 主循环：

```text
choose_sells(...)
buy_order
strategy_rule-specific sell/buy branching
```

改造后 replay execution 主体只能读取：

```text
OrderIntentArtifact
PriceStore
ExecutionConfig
InitialPortfolioState
```

## 7. D2 允许改动范围

允许修改：

```text
scripts/run_tw_modular_config_replay_matrix.py
```

允许新增：

```text
scripts/run_tw_modular_order_intent_replay.py
scripts/validate_tw_modular_order_intent_replay.py
tests/unit/test_tw_modular_order_intent_replay.py
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/
docs/tw_modular_contracts/PHASED2_REPLAY_ENGINE_DECOUPLING_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/PHASED2_REPLAY_ENGINE_DECOUPLING_REVIEW_HANDOFF_CN.md
```

如果执行者选择不直接改旧 replay 脚本，也可以新增 parallel D2 replay runner，但必须证明它只消费 `OrderIntentArtifact`。

D2 不得修改：

```text
frontend/
backend/
backend_api_python/
src/api/
scripts/run_daily_tw_stock_auto_update.py
configs/tw_modular_registry.yaml
configs/tw_modular_replay_matrix.yaml
configs/strategy_dependencies/
```

除非只是新增测试 fixture 或文档，且必须在执行报告中说明。

## 8. D2 必须实现

### 8.1 ReplayExecutionEngine 输入边界

Replay execution 必须只从 `OrderIntentArtifact` 读取决策意图：

```text
signal_date
instrument
intent_action
intent_reason
strategy_rule
model_name
```

Replay execution 可以读取 price / execution config：

```text
next-day execution price
commission
tax
cash
holdings
initial portfolio
```

Replay execution 不得读取 `ModelSignalArtifact` 来重新决定买卖。

### 8.2 ReplayExecutionEngine 输出边界

D2 输出必须仍符合 `ReplayResultArtifact` 合同：

```text
summary.csv
actions.csv
daily_nav.csv
position_snapshots.csv
coverage_audit.csv
position_integrity_audit.csv
forbidden_field_audit.csv
execution_audit.csv
manifest.json
```

新增 audit 建议：

```text
decision_source_audit.csv
```

必须能证明：

```text
decision_source=order_intent_artifact
no_inline_strategy_decision=true
no_choose_sells_call=true
no_model_signal_decision_read=true
```

### 8.3 行为保持

D2 必须保持：

- next-day execution；
- pending order 处理；
- coverage skip 行为；
- commission；
- tax；
- cash；
- holdings；
- daily NAV；
- return / drawdown / turnover；
- position integrity audit。

D2 不得借机修改：

- sizing；
- target holding count；
- fee/tax 参数；
- skip 逻辑；
- default model；
- default strategy；
- replay windows。

## 9. D2 验证要求

D2 至少验证一个主策略端到端：

```text
OrderIntentArtifact -> ReplayExecutionEngine -> ReplayResultArtifact
```

最低验证：

```bash
python -m py_compile scripts/run_tw_modular_order_intent_replay.py scripts/validate_tw_modular_order_intent_replay.py
python scripts/run_tw_modular_order_intent_replay.py --json
python scripts/validate_tw_modular_order_intent_replay.py --artifact <d2_replay_manifest> --json
python -m pytest tests/unit/test_tw_modular_order_intent_replay.py
python scripts/validate_tw_modular_order_intent_artifact.py --artifact <d1_or_d2_order_intent_manifest> --json
python scripts/run_tw_modular_contract_regression.py --json
```

D2 可以输出初步 replay artifact，但不得宣称五规则 parity 完成。五规则完整 parity 属于 D3。

## 10. D2 禁止事项

D2 禁止：

- 修改前端；
- 修改 API；
- 修改 daily orchestrator；
- provider publish；
- accepted latest switch；
- broker / quick-trade / order；
- monitor scan / config save / alerts write；
- 输出 target position / target weight；
- 训练；
- 调参；
- score recompute；
- 改默认模型；
- 改默认策略；
- 将 D2 初步 replay 结果作为产品化收益证据；
- 宣称 D3 parity 已完成。

## 11. D2 执行报告必须说明

D2 执行报告必须包含：

```text
修改文件清单
OrderIntentArtifact 输入路径
ReplayExecutionEngine 输入/输出合同
如何确认 replay 不再调用 choose_sells / buy_order 决策逻辑
execution / accounting 保持不变的证据
输出 ReplayResultArtifact 路径
validator 检查项
是否只完成主策略初步 replay
是否声明未完成 D3 parity
验证命令与结果
是否触碰前端/API/daily/provider/交易链路
```

## 12. D2 审查交接必须输出

执行者完成后必须输出：

```text
docs/tw_modular_contracts/PHASED2_REPLAY_ENGINE_DECOUPLING_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/PHASED2_REPLAY_ENGINE_DECOUPLING_REVIEW_HANDOFF_CN.md
```

审查者重点审查：

- replay execution 是否真的只消费 `OrderIntentArtifact`；
- 是否仍直接调用 `choose_sells()` 或内联策略规则；
- 是否重新读取 ModelSignalArtifact 做买卖决策；
- 是否改变 execution/accounting 语义；
- 输出是否符合 ReplayResultArtifact 合同；
- 是否未宣称 D3 parity；
- 是否没有前端/API/daily/provider/交易链路越界。

## 13. 最终结论

D1 通过。

可以进入 D2，但 D2 只能做 ReplayExecutionEngine 解耦，让 replay execution 消费 `OrderIntentArtifact`。D2 不得宣称五规则 parity；D3 才做完整 parity 验收。
