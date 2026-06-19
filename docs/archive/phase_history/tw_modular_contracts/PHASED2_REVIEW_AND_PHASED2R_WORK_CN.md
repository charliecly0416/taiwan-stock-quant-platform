# Phase D2 审查与 Phase D2R 修复工作文档

生成日期：2026-06-17

## 1. 审查结论

D2 未发现只读安全边界越界，也未发现 replay runner 重新读取模型信号做策略决策；但 D2 不能直接进入 D3。

结论：

```text
D2 boundary: pass
D2 replay output integrity: fail
next phase: D2R repair
```

D2 已完成 parallel replay runner 的基本解耦证明：

- 新增 `scripts/run_tw_modular_order_intent_replay.py`；
- 新增 `scripts/validate_tw_modular_order_intent_replay.py`；
- 新增 `tests/unit/test_tw_modular_order_intent_replay.py`；
- D2 runner 消费 `OrderIntentArtifact`，未在 runner 内嵌 `choose_sells()` / `buy_score` / `score_rank` / `candidate_rank <=` 策略决策；
- D2 manifest 与 `decision_source_audit.csv` 声明 `decision_source=order_intent_artifact`；
- D2 未宣称 D3 parity；
- 未触碰前端、API、daily、provider、accepted latest、monitor、broker、quick-trade、order。

阻塞项是 replay output 中 `position_snapshots.csv` 的按日状态错误。该问题会直接污染 D3 的 full-window parity，所以必须先做 D2R。

## 2. 审查对象

handoff：

```text
docs/tw_modular_contracts/PHASED2_REPLAY_ENGINE_DECOUPLING_REVIEW_HANDOFF_CN.md
```

执行报告：

```text
docs/tw_modular_contracts/PHASED2_REPLAY_ENGINE_DECOUPLING_EXECUTION_REPORT_CN.md
```

核心实现：

```text
scripts/run_tw_modular_order_intent_replay.py
scripts/validate_tw_modular_order_intent_replay.py
tests/unit/test_tw_modular_order_intent_replay.py
scripts/build_tw_modular_order_intent_artifact.py
scripts/validate_tw_modular_order_intent_artifact.py
```

D2 artifact：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/d2_order_intent_replay_20260506_20260617T042642Z/manifest.json
```

## 3. Findings

### High: `position_snapshots.csv` 使用最终持仓回填所有日期

位置：

```text
scripts/run_tw_modular_order_intent_replay.py:302-317
```

当前代码在执行完所有 orders 后才生成 `snapshot_rows`，并对 `daily_nav` 的每个日期都遍历同一个最终 `holdings` dict：

```text
for nav_row in daily_nav:
    for symbol, qty in sorted(holdings.items()):
```

这导致 `position_snapshots.csv` 的历史日期不是该日期的真实持仓，而是最终持仓在所有日期上的回填。

实证：

```text
D2 actions:
2026-05-06 -> 2026-05-07 TW2467 historical_risk_reduce
2026-05-06 -> 2026-05-07 TW2337 historical_add
```

但 D2 snapshot 在 `2026-05-06` 已包含次日才买入的 `TW2337`：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/d2_order_intent_replay_20260506_20260617T042642Z/position_snapshots.csv
2026-05-06,TW2337,820
```

同时，旧 replay 初始持仓证明 `2026-05-06` 对 `e4_frozen_qlib_2023_2025_ltr + top50_exit_one_worst_sell` 持有的是 `TW2467`：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_position_snapshots.csv
2026-05-06,e4_frozen_qlib_2023_2025_ltr,top50_exit_one_worst_sell,TW2467,280
```

影响：

- 单日 D2 的 `actions.csv` 和 `daily_nav.csv` 可作为执行路径 smoke，但 `position_snapshots.csv` 不能作为正确 replay result；
- D3 扩展到全窗口后，所有中间日期持仓都会被最终持仓污染；
- position parity、daily holdings parity、后续 API/前端展示都会被误导；
- 当前 validator 未覆盖该 invariant，因此会出现 `ok=true` 但产物语义错误。

修复要求：

- replay 过程中必须在每个 `daily_nav` 日期同步保存当日收盘后的 holdings snapshot；
- `signal_date` snapshot 必须等于 initial portfolio state；
- 每个 execution date snapshot 必须反映当天 sell/buy 后的 holdings；
- 不得用最终 `holdings` dict 回填历史日期；
- validator 必须检查 snapshot 与 actions 的状态转移一致性。

### Medium: D2 validator 缺少 snapshot/action 状态转移校验

位置：

```text
scripts/validate_tw_modular_order_intent_replay.py:43-83
tests/unit/test_tw_modular_order_intent_replay.py:38-85
```

当前 validator 只检查：

- required artifacts 存在；
- active action 的 `execution_date > signal_date`；
- active quantity > 0；
- active action 引用同一个 `OrderIntentArtifact`；
- audit CSV 没有 fail；
- decision source flags 为 true。

缺失检查：

```text
initial snapshot == initial portfolio state
sell 后该 symbol 不再出现在 execution date snapshot
buy 后该 symbol 出现在 execution date snapshot 且 quantity 匹配
每个 daily_nav.holding_count == 同日 snapshot 非零持仓数
snapshot 不允许包含未来才买入的 symbol
snapshot 不允许缺失当日仍持有的 symbol
```

影响：

当前错误产物仍通过：

```text
python scripts/validate_tw_modular_order_intent_replay.py --artifact ... --json
ok=true
```

D2R 必须补 validator 和单测，否则 D3 parity 失败时无法区分是策略差异还是 replay state 输出错误。

## 4. 已通过项

### 4.1 决策源边界通过

静态检查：

```text
rg -n "choose_sells|candidate_rank <=|buy_score|score_rank|ModelSignalArtifact|signal_artifact|target_position|target_weight|broker|quick_trade|provider_publish|accepted_latest|monitor/scan|monitor/config|monitor/alerts" scripts/run_tw_modular_order_intent_replay.py scripts/validate_tw_modular_order_intent_replay.py tests/unit/test_tw_modular_order_intent_replay.py
```

结果显示 D2 runner 中没有 `choose_sells`、`candidate_rank <=`、`buy_score`、`score_rank` 决策逻辑；`ModelSignalArtifact` 只出现在 audit 说明文本中。

### 4.2 OrderIntent 输入通过

D2 input：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/d2_order_intent_20260506_20260617T042642Z/manifest.json
```

复核结果：

```text
ok=true
row_count=10
artifact_stage=d2_replay_input
buy_rank_mapping_validated=pass
forbidden_action_audit_pass=pass
```

### 4.3 Replay validator 当前检查通过但不足

复核结果：

```text
ok=true
decision_source=pass
no_choose_sells_call=pass
no_model_signal_decision_read=pass
actions_reference_order_intent=pass
coverage_status=pass
integrity_status=pass
forbidden_status=pass
```

该结果只能说明当前 validator 范围内通过，不能覆盖本次发现的 snapshot 状态错误。

### 4.4 只读安全边界通过

未发现：

```text
provider publish
accepted latest switch
monitor config save
monitor scan
alerts write
broker
quick-trade
order
target_position / target_weight
frontend/API/daily product path change
training/tuning/score recompute
```

readonly snapshot validator 仍通过：

```text
ok=true
latest_pointer_points_to_readonly_snapshot_only=pass
no_provider_publish=pass
no_accepted_latest_switch=pass
no_monitor_broker_order=pass
```

## 5. 复核命令

已执行：

```bash
python -m py_compile scripts/build_tw_modular_order_intent_artifact.py scripts/validate_tw_modular_order_intent_artifact.py scripts/run_tw_modular_order_intent_replay.py scripts/validate_tw_modular_order_intent_replay.py
python scripts/run_tw_modular_order_intent_replay.py --json
python scripts/validate_tw_modular_order_intent_replay.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/d2_order_intent_replay_20260506_20260617T042642Z/manifest.json --json
python scripts/validate_tw_modular_order_intent_artifact.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/d2_order_intent_20260506_20260617T042642Z/manifest.json --json
python -m pytest tests/unit/test_tw_modular_order_intent_artifact.py tests/unit/test_tw_modular_order_intent_replay.py
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

结果：

```text
py_compile: pass
D2 runner: ok=true, action_count=2, skipped_action_count=0
D2 replay validator: ok=true
D2 OrderIntent validator: ok=true
unit tests: 9 passed
contract regression: ok=true
readonly snapshot validator: ok=true
```

说明：部分 Python 命令在普通 sandbox 下触发 `bwrap: loopback: Failed RTM_NEWADDR`，复核时使用升级执行方式完成。

## 6. Phase D2R 修复目标

D2R 目标：

```text
修复 ReplayResultArtifact 的按日持仓状态输出，并补齐 validator/test，使 D2 产物能作为 D3 parity 的可靠输入。
```

D2R 仍然只允许修复新增 D2 parallel runner / validator / tests，不得进入五规则全窗口 parity。

允许修改：

```text
scripts/run_tw_modular_order_intent_replay.py
scripts/validate_tw_modular_order_intent_replay.py
tests/unit/test_tw_modular_order_intent_replay.py
docs/tw_modular_contracts/PHASED2R_*.md
```

如确实需要小幅补充 D1 `OrderIntentArtifact` validator 以支持 D2R 检查，可以修改：

```text
scripts/validate_tw_modular_order_intent_artifact.py
tests/unit/test_tw_modular_order_intent_artifact.py
```

禁止修改：

```text
scripts/run_tw_modular_config_replay_matrix.py
frontend/**
backend/**
scripts/run_daily_tw_stock_auto_update.py
scripts/publish_tw_modular_readonly_snapshot.py
provider / accepted latest / monitor / broker / quick-trade / order 相关路径
```

## 7. D2R 必做项

### 7.1 修复 daily position snapshots

实现要求：

- 加载 initial state 后立即保存 `signal_date` 的 snapshot；
- 每个 execution date 完成 sell/buy 记账后保存该日期 snapshot；
- snapshots 必须来自当日状态副本，不得在所有日期复用最终 holdings；
- `daily_nav.holding_count` 必须等于同日 snapshot 非零持仓数；
- `summary.max_holding_count` 应由真实 daily snapshots 或真实 daily holdings count 计算。

验收样例：

```text
2026-05-06 snapshot:
  must contain TW2467 quantity=280
  must not contain TW2337

2026-05-07 snapshot:
  must contain TW2337 quantity=820
  must not contain TW2467
```

### 7.2 补 validator 状态转移检查

`validate_tw_modular_order_intent_replay.py` 至少增加：

```text
snapshots_required_columns
daily_nav_snapshot_dates_match
daily_nav_holding_count_matches_snapshots
initial_snapshot_matches_portfolio_state_or_manifest_initial_state
sell_action_removed_from_execution_snapshot
buy_action_present_in_execution_snapshot_with_quantity
no_future_buy_in_signal_date_snapshot
```

如果 validator 需要读取 OrderIntent manifest 的 `portfolio_state_artifact`，必须只用于核对 initial state，不得用于重新决策。

### 7.3 补单测和负面测试

`tests/unit/test_tw_modular_order_intent_replay.py` 至少增加：

```text
test_d2_position_snapshots_are_date_specific
test_validator_rejects_future_buy_backfilled_into_signal_date_snapshot
test_validator_rejects_sell_symbol_remaining_after_execution_date
test_daily_nav_holding_count_matches_snapshot_rows
```

负面测试必须构造 mutated artifact，让当前这类错误能够被 validator 拒绝。

### 7.4 重新生成 D2 artifact

D2R 修复后重新运行：

```bash
python scripts/run_tw_modular_order_intent_replay.py --json
```

新的 artifact 必须：

```text
decision_source=order_intent_artifact
not_d3_parity_evidence=true
parity_status=not_claimed_d2_single_strategy_sample
no_inline_strategy_decision=true
no_choose_sells_call=true
no_model_signal_decision_read=true
```

并通过增强 validator。

## 8. D2R 验证命令

D2R 执行者完成后必须提供以下命令结果：

```bash
python -m py_compile scripts/run_tw_modular_order_intent_replay.py scripts/validate_tw_modular_order_intent_replay.py
python scripts/run_tw_modular_order_intent_replay.py --json
python scripts/validate_tw_modular_order_intent_replay.py --artifact <new_d2r_replay_manifest> --json
python scripts/validate_tw_modular_order_intent_artifact.py --artifact <new_d2r_order_intent_manifest> --json
python -m pytest tests/unit/test_tw_modular_order_intent_artifact.py tests/unit/test_tw_modular_order_intent_replay.py
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

同时提供 targeted static audit：

```bash
rg -n "choose_sells|candidate_rank <=|buy_score|score_rank|target_position|target_weight|broker|quick_trade|provider_publish|accepted_latest|monitor/scan|monitor/config|monitor/alerts" scripts/run_tw_modular_order_intent_replay.py scripts/validate_tw_modular_order_intent_replay.py tests/unit/test_tw_modular_order_intent_replay.py
```

预期：

```text
所有验证命令通过；
static audit 不出现 replay 决策逻辑或危险只读边界调用；
validator 能拒绝 snapshot backfill 类错误；
D2R 仍不宣称 D3 parity。
```

## 9. D2R 通过后才能进入 D3

D2R 通过后，D3 才能扩展到：

```text
five strategy rules
full 2026_ytd window
summary parity
daily_nav parity
actions parity
action key parity
position snapshot parity
```

D3 仍不得修改前端、API、daily、provider、accepted latest、monitor、broker、quick-trade、order 链路。
