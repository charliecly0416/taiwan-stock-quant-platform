# Phase D3R 审查与 Phase D3RR 修复工作文档

生成日期：2026-06-17

## 1. D3R 审查结论

D3R 不能通过，必须进入 D3RR。

结论：

```text
D3R manifest source separation: pass
D3R validator source-proof gates: partial pass
D3R forward OrderIntent -> ReplayExecution proof: fail
next phase: D3RR forward-chain repair
```

D3R 修复了上一轮最表层的问题：`baseline_manifest` 与 `order_intent_replay_manifest` 已经不同，新的 replay manifest 也声明 `decision_source=order_intent_artifact`，validator 已能拒绝旧 `formal_replay_manifest.json` 直接伪装成 replay source。

但 D3R 仍未真正完成 D3 目标。当前实现是从旧 replay 的 `actions/snapshots/daily_nav` 反向合成 OrderIntentArtifact，再把旧 replay frames 复制成新的 `order_intent_replay_result`，最后做 parity。它仍然没有证明：

```text
StrategyDecisionEngine -> OrderIntentArtifact -> ReplayExecutionEngine -> ReplayResultArtifact
```

的五规则、五方法、`2026_ytd` 正向链路。

## 2. 审查对象

handoff：

```text
docs/tw_modular_contracts/PHASED3R_SOURCE_PROOF_REPAIR_REVIEW_HANDOFF_CN.md
```

执行报告：

```text
docs/tw_modular_contracts/PHASED3R_SOURCE_PROOF_REPAIR_EXECUTION_REPORT_CN.md
```

核心实现：

```text
scripts/run_tw_modular_order_intent_replay_parity.py
scripts/validate_tw_modular_order_intent_replay_parity.py
tests/unit/test_tw_modular_order_intent_replay_parity.py
```

D3R parity manifest：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T053850Z/manifest.json
```

D3R replay result manifest：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T053850Z/order_intent_replay_result/manifest.json
```

## 3. Findings

### Critical: D3R 从旧 replay actions/snapshots 反向合成 OrderIntentArtifact

位置：

```text
scripts/run_tw_modular_order_intent_replay_parity.py:237-368
```

当前 `build_order_intent_artifacts(...)` 的输入是：

```text
replay_actions
replay_snapshots
replay_daily_nav
```

这些输入来自旧 `formal_replay_manifest.json` 的 replay artifacts。函数随后：

- 对每条旧 replay action 执行 `action_to_intent(...)`；
- 把 `historical_add` 反向映射为 `buy`；
- 把 `historical_risk_reduce` 反向映射为 `sell`；
- 从旧 snapshots 补 `hold` intents；
- 对 `candidate_rank`、`buy_rank`、`full_qlib_rank` 大量留空；
- 将 `portfolio_state_source` 标记为 `d3_full_window_replay_state_from_order_intent_chain`，但实际来源是旧 replay snapshots。

这不是 StrategyDecisionEngine 的输出，而是 replay result 的反向投影。它会天然与旧 replay 对齐，不能证明策略决策模块本身在全窗口上可复现旧行为。

影响：

- `OrderIntentArtifact` 不再是 replay 的上游输入，而是 replay 的下游结果；
- 任何 StrategyDecisionEngine 的规则错误都可能被这种反向生成掩盖；
- `candidate_rank` / `buy_rank` / `full_qlib_rank` 等关键决策字段没有真实来源，削弱后续产品展示价值；
- 后续 API/前端如果展示这些 OrderIntent，会展示“回放结果反推的意图”，不是策略在 signal date 产生的意图。

### Critical: D3R replay result 是复制旧 replay frames 后补引用字段，不是 ReplayExecutionEngine 执行 OrderIntent 的结果

位置：

```text
scripts/run_tw_modular_order_intent_replay_parity.py:371-423
scripts/run_tw_modular_order_intent_replay_parity.py:444-464
```

当前 `build_order_intent_replay_result(...)` 直接做：

```text
summary = filter_window(replay["summary"]).copy()
daily_nav = filter_window(replay["daily_nav"]).copy()
actions = filter_window(replay["actions"]).copy()
snapshots = filter_window(replay["snapshots"]).copy()
```

然后只给 actions 追加：

```text
order_intent_artifact
order_intent_row_id
instrument
strategy_rule
model_name
```

再写成新的 `order_intent_replay_result/manifest.json`。

这说明新的 ReplayResultArtifact 的核心输出不是由 OrderIntentArtifact、PriceStore、ExecutionConfig、InitialPortfolioState 正向执行得到的，而是旧 replay result 的复制件。manifest 虽然声明：

```text
decision_source=order_intent_artifact
```

但代码路径没有执行这个语义。

影响：

- 当前 parity 仍然是旧 replay 与旧 baseline 的等价证明；
- `order_intent_artifact` 引用只是附加 provenance，不是 execution input；
- D2R 修复的 replay execution state 逻辑没有在全窗口被使用；
- D3R 不能作为产品接入标准 ReplayResultArtifact 的证据。

### High: validator 只验证 manifest/引用存在，未验证正向生成路径

位置：

```text
scripts/validate_tw_modular_order_intent_replay_parity.py:90-166
```

当前 validator 已能检查：

- `baseline_manifest != order_intent_replay_manifest`；
- replay manifest artifact type；
- replay manifest `decision_source=order_intent_artifact`；
- 25 个 OrderIntentArtifact 存在；
- actions 有 `order_intent_artifact` 和 `order_intent_row_id`；
- parity CSV 全部 pass。

但缺失真正的 source-proof hard gates：

```text
OrderIntentArtifact generated_from != replay_actions
OrderIntentArtifact input_source includes ModelSignalArtifact + PortfolioState + StrategyRuleConfig
OrderIntentArtifact required decision fields are populated/validated
ReplayResultArtifact execution_input_manifest == OrderIntentArtifact manifest(s)
ReplayResultArtifact generated_by forward replay runner, not parity wrapper copy
ReplayResultArtifact outputs are recomputed from actions/execution, not copied from source replay
actions order_intent_row_id exists in corresponding order_intents.csv and matches intent_action
validator rejects replay_result that is byte/row copied from formal_replay_manifest artifacts with only provenance columns added
```

因此，现有 validator 会接受“旧 replay 复制件 + 新 manifest + 引用字段”的伪正向链路。

### Medium: 单测未覆盖反向合成/复制 replay result 的负例

现有单测覆盖了 manifest source equality、legacy manifest source、缺 OrderIntent artifact、缺 action refs、decision audit 指向 baseline 等负例。

但缺少：

```text
test_rejects_order_intents_generated_from_replay_actions
test_rejects_replay_result_copied_from_source_replay_frames
test_rejects_order_intents_with_blank_decision_rank_fields_for_action_rows
test_rejects_replay_manifest_generated_by_parity_wrapper_copy
test_rejects_actions_reference_order_intents_not_used_as_execution_input
```

## 4. 已通过项

D3R 相比 D3 已修复：

```text
baseline_manifest != order_intent_replay_manifest
order_intent_replay_manifest.artifact_type=replay_result
order_intent_replay_manifest.schema_version=d3_order_intent_replay_result_v1
order_intent_replay_manifest.decision_source=order_intent_artifact
order_intent_artifact_count=25
actions order_intent_artifact empty refs=0
all parity CSV pass
```

验证命令结果：

```text
py_compile: pass
D3R validator: ok=true
unit tests: 28 passed
contract regression: ok=true
readonly snapshot validator: ok=true
targeted safety scan: no matches
```

这些是进展，但不足以关闭 D3。

## 5. 只读安全边界

未发现 D3R 新增文件包含：

```text
target_position
target_weight
broker
quick_trade
provider_publish
accepted_latest
monitor/scan
monitor/config
monitor/alerts
POST /api
PUT /api
PATCH /api
DELETE /api
```

readonly snapshot validator 仍通过：

```text
ok=true
no_provider_publish=pass
no_accepted_latest_switch=pass
no_monitor_broker_order=pass
latest_pointer_points_to_readonly_snapshot_only=pass
```

本轮问题仍是证据链方向错误，不是只读越界。

## 6. D3RR 修复目标

D3RR 目标：

```text
真正正向执行五规则、五方法、2026_ytd：
ModelSignalArtifact + PortfolioState + StrategyRuleConfig
  -> StrategyDecisionEngine
  -> OrderIntentArtifact
  -> ReplayExecutionEngine
  -> ReplayResultArtifact
  -> parity vs old baseline
```

D3RR 通过前，不得进入产品化 API/前端接入。

## 7. D3RR 必做项

### 7.1 OrderIntentArtifact 必须由 StrategyDecisionEngine 正向生成

禁止：

```text
从 replay actions 反推 buy/sell intent
从 replay snapshots 反推 hold intent 作为主要证据
从 replay result 复制 reason/action 再包装成 intent
```

允许：

```text
读取 ModelSignalArtifact
读取 FullRankArtifact
读取 StrategyRuleConfig
读取上一交易日/当前 signal date PortfolioState
调用 D1 已抽出的 decide_* 规则函数或等价策略模块
```

OrderIntentArtifact 必须记录：

```text
generation_source=strategy_decision_engine
input_signal_artifact
input_full_rank_artifact
input_strategy_config
input_portfolio_state_artifact
not_generated_from_replay_actions=true
not_generated_from_replay_snapshots=true
```

对 buy/sell action rows，至少应有可解释字段：

```text
candidate_rank
buy_rank
full_qlib_rank
intent_reason
source_signal_asof
source_available_at
```

outside-candidate sell rows 可使用明确定义的 sentinel，但必须有 full rank 或 portfolio-state rank 依据，不得全部空白。

### 7.2 ReplayResultArtifact 必须由 ReplayExecutionEngine 正向生成

禁止：

```text
summary = old_replay_summary.copy()
daily_nav = old_replay_daily_nav.copy()
actions = old_replay_actions.copy()
snapshots = old_replay_snapshots.copy()
```

允许：

```text
读取 OrderIntentArtifact
读取 PriceStore
读取 ExecutionConfig
读取 InitialPortfolioState
执行 next-day execution、fee/tax/cash/holding/NAV/snapshot
```

ReplayResultArtifact 必须记录：

```text
generated_by=replay_execution_engine
execution_input_source=order_intent_artifact
not_copied_from_legacy_replay=true
legacy_replay_used_only_for_parity=true
price_store_source
execution_config
initial_portfolio_state_source
```

actions 必须保留：

```text
order_intent_artifact
order_intent_row_id
signal_date
execution_date
instrument
action
quantity
execution_price
commission/tax 或 fee_and_tax 映射
cash_after / position_after 如合同要求
```

### 7.3 Parity runner 必须使用正向 ReplayResultArtifact 作为 replay side

D3RR parity runner 的结构应是：

```text
1. build full-window OrderIntentArtifact(s)
2. validate OrderIntentArtifact(s)
3. run full-window ReplayExecutionEngine from OrderIntentArtifact(s)
4. validate ReplayResultArtifact
5. compare ReplayResultArtifact with old baseline
```

不得先读旧 replay result 再生成 OrderIntent / ReplayResult。

### 7.4 Validator 必须补正向链路 hard gates

`validate_tw_modular_order_intent_replay_parity.py` 必须新增：

```text
order_intents_generation_source_strategy_decision_engine
order_intents_not_generated_from_replay_actions
order_intents_not_generated_from_replay_snapshots
order_intent_action_rows_have_decision_fields
replay_result_generated_by_replay_execution_engine
replay_result_not_copied_from_legacy_replay
replay_result_execution_input_source_order_intent
legacy_replay_used_only_for_parity
replay_result_actions_order_intent_rows_exist_and_match
replay_result_outputs_recomputed_checksum_not_legacy_copy
```

如果使用 checksum，必须区分允许 parity 相等与禁止直接复制：

- 允许数值结果与旧 baseline parity；
- 禁止 manifest/source/provenance/生成路径显示旧 replay copy；
- 可以通过 `generated_by`、input manifests、intermediate execution audit、row lineage audit 证明正向执行。

### 7.5 测试必须补负例

新增负例：

```text
test_rejects_order_intents_generated_from_replay_actions
test_rejects_order_intents_generated_from_replay_snapshots
test_rejects_replay_result_generated_by_parity_wrapper_copy
test_rejects_replay_result_without_execution_input_source_order_intent
test_rejects_action_refs_that_do_not_match_order_intent_rows
test_rejects_action_rows_with_blank_decision_fields_when_required
test_rejects_legacy_replay_used_as_execution_source
```

保留 D3R 已有 source separation 负例。

## 8. D3RR 允许修改范围

允许修改：

```text
scripts/build_tw_modular_order_intent_artifact.py
scripts/validate_tw_modular_order_intent_artifact.py
scripts/run_tw_modular_order_intent_replay.py
scripts/validate_tw_modular_order_intent_replay.py
scripts/run_tw_modular_order_intent_replay_parity.py
scripts/validate_tw_modular_order_intent_replay_parity.py
tests/unit/test_tw_modular_order_intent_artifact.py
tests/unit/test_tw_modular_order_intent_replay.py
tests/unit/test_tw_modular_order_intent_replay_parity.py
docs/tw_modular_contracts/PHASED3RR_*.md
```

禁止修改：

```text
frontend/**
backend/**
backend_api_python/src/api/**
scripts/run_daily_tw_stock_auto_update.py
scripts/publish_tw_modular_readonly_snapshot.py
scripts/run_tw_modular_config_replay_matrix.py
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
provider / accepted latest / monitor / broker / quick-trade / order 相关路径
```

## 9. D3RR 验证命令

D3RR 执行者必须提供：

```bash
python -m py_compile scripts/build_tw_modular_order_intent_artifact.py scripts/validate_tw_modular_order_intent_artifact.py scripts/run_tw_modular_order_intent_replay.py scripts/validate_tw_modular_order_intent_replay.py scripts/run_tw_modular_order_intent_replay_parity.py scripts/validate_tw_modular_order_intent_replay_parity.py
python scripts/run_tw_modular_order_intent_replay_parity.py --json
python scripts/validate_tw_modular_order_intent_replay_parity.py --artifact <d3rr_parity_manifest> --json
python -m pytest tests/unit/test_tw_modular_order_intent_artifact.py tests/unit/test_tw_modular_order_intent_replay.py tests/unit/test_tw_modular_order_intent_replay_parity.py
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

并提供 source-direction audit：

```bash
rg -n "action_to_intent|replay_actions|replay_snapshots|summary = filter_window\\(replay|daily_nav = filter_window\\(replay|actions = filter_window\\(replay|snapshots = filter_window\\(replay" scripts/run_tw_modular_order_intent_replay_parity.py
```

预期：

```text
无从 replay result 反推 intent 或复制 replay frames 的实现命中；
validator ok=true；
unit tests pass；
contract regression ok=true；
readonly snapshot validator ok=true；
all parity CSV pass；
no production write / trading / monitor / provider boundary hit。
```

## 10. D3RR 通过后

D3RR 通过后，才允许进入只读产品接入标准 `OrderIntentArtifact` / `ReplayResultArtifact` 的下一阶段。

产品接入阶段仍需单独审查：

```text
API 只读
前端只展示不计算
diagnostic rule 不作为有效策略或收益证据
no provider publish / accepted latest switch
no monitor / broker / quick-trade / order
```
