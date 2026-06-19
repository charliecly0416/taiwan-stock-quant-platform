# Phase D2R Replay Snapshot State Repair 审查交接

生成日期：2026-06-17

## 1. 审查结论建议

请审查 D2R 是否可以关闭以下 D2 blocker：

```text
position_snapshots.csv 使用最终 holdings 回填所有日期
```

执行侧结论：该 blocker 已修复，增强 validator 已能拒绝同类错误，新的 D2R artifact 可作为后续 D3 parity 工作的输入候选。但 D2R 仍未、也不应宣称 D3 parity。

## 2. 审查重点

建议审查者重点看 3 个文件：

```text
scripts/run_tw_modular_order_intent_replay.py
scripts/validate_tw_modular_order_intent_replay.py
tests/unit/test_tw_modular_order_intent_replay.py
```

关键实现点：

- runner 在 `signal_date` 立即 snapshot initial holdings；
- runner 在每个 `execution_date` 完成 sell/buy 后 snapshot 当日 holdings；
- runner 已删除最终 holdings 回填所有日期的逻辑；
- validator 新增 snapshot schema、daily_nav/snapshot 日期一致性、holding_count 一致性、initial state 一致性、sell/buy 状态转移、future buy backfill 拒绝；
- tests 包含正例和 mutated artifact 负例。

## 3. 新产物

Replay manifest：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/d2_order_intent_replay_20260506_20260617T044813Z/manifest.json
```

OrderIntent manifest：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/d2_order_intent_20260506_20260617T044813Z/manifest.json
```

必要 spot check：

```text
position_snapshots.csv:
2026-05-06,TW2467,280
2026-05-07,TW2337,820
```

语义：`TW2337` 不再出现在 `2026-05-06` signal-date snapshot；`TW2467` 不再残留在 `2026-05-07` execution-date snapshot。

## 4. Validator 新增检查

增强 validator 的新增 check 名称如下，审查时可直接在 validation JSON 中定位：

```text
snapshots_required_columns
daily_nav_snapshot_dates_match
daily_nav_holding_count_matches_snapshots
initial_snapshot_matches_portfolio_state_or_manifest_initial_state
sell_action_removed_from_execution_snapshot
buy_action_present_in_execution_snapshot_with_quantity
no_future_buy_in_signal_date_snapshot
```

当前新 artifact 上述 checks 全部 pass。

## 5. 复核命令

建议审查者复跑：

```bash
python -m py_compile scripts/run_tw_modular_order_intent_replay.py scripts/validate_tw_modular_order_intent_replay.py
python scripts/validate_tw_modular_order_intent_replay.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/d2_order_intent_replay_20260506_20260617T044813Z/manifest.json --json
python scripts/validate_tw_modular_order_intent_artifact.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/d2_order_intent_20260506_20260617T044813Z/manifest.json --json
python -m pytest tests/unit/test_tw_modular_order_intent_artifact.py tests/unit/test_tw_modular_order_intent_replay.py
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

执行者已跑结果：

```text
py_compile: pass
D2R replay validator: ok=true
D2R OrderIntent validator: ok=true
unit tests: 14 passed
contract regression: ok=true
readonly snapshot validator: ok=true
```

## 6. Static Audit 说明

执行命令：

```bash
rg -n "choose_sells|candidate_rank <=|buy_score|score_rank|target_position|target_weight|broker|quick_trade|provider_publish|accepted_latest|monitor/scan|monitor/config|monitor/alerts" scripts/run_tw_modular_order_intent_replay.py scripts/validate_tw_modular_order_intent_replay.py tests/unit/test_tw_modular_order_intent_replay.py
```

结果仅命中 `no_choose_sells_call` 审计字段/说明文本。这些命中用于证明 runner 没有调用旧策略选择函数，不是 replay 决策逻辑。未发现 `candidate_rank <=`、score 排名字段、target position/weight 或任何交易/生产写路径命中。

## 7. 边界复核

D2R 未修改：

```text
scripts/run_tw_modular_config_replay_matrix.py
frontend/**
backend/**
backend_api_python/src/api/**
scripts/run_daily_tw_stock_auto_update.py
provider / accepted latest / monitor / broker / quick-trade / order 相关路径
```

D2R 未做：

```text
D3 five-rule parity
full 2026_ytd replay parity
training / tuning / score recompute
default model or default strategy switch
production publish or accepted latest switch
```

## 8. 建议下一步

若审查通过，下一阶段可进入 D3：five strategy rules、full 2026_ytd window、summary/daily_nav/actions/action key/position snapshot parity。D3 前提是继续保持只读边界，不改生产 API、前端、daily、provider、accepted latest、monitor、broker、quick-trade、order 链路。
