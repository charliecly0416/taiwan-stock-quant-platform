# Phase D2R Replay Snapshot State Repair 执行报告

生成日期：2026-06-17

## 1. 执行结论

D2R 已完成 `position_snapshots.csv` 按日状态修复，并补齐 replay validator 与负面测试。新的 D2R replay artifact 已通过增强 validator、OrderIntent validator、D1+D2 单测、modular contract regression 与 readonly snapshot validator。

结论：

```text
D2R snapshot repair: pass
D2R validator hardening: pass
D2R readonly boundary: pass
D3 parity: not claimed
next eligible phase: D3 review/work only after reviewer approval
```

## 2. 修改范围

本次只修改 D2R 允许范围：

```text
scripts/run_tw_modular_order_intent_replay.py
scripts/validate_tw_modular_order_intent_replay.py
tests/unit/test_tw_modular_order_intent_replay.py
docs/tw_modular_contracts/PHASED2R_REPLAY_SNAPSHOT_STATE_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/PHASED2R_REPLAY_SNAPSHOT_STATE_REPAIR_REVIEW_HANDOFF_CN.md
```

未修改、未触碰：

```text
scripts/run_tw_modular_config_replay_matrix.py
frontend/**
backend/**
backend_api_python/src/api/**
scripts/run_daily_tw_stock_auto_update.py
provider / accepted latest / monitor / broker / quick-trade / order 路径
```

## 3. Runner 修复

`scripts/run_tw_modular_order_intent_replay.py` 新增 `snapshot_holdings()`，并将 snapshot 写入时机改为 replay 状态推进时同步写入：

- 加载 initial state 并计算 `signal_date` NAV 后，立即保存 `signal_date` snapshot；
- 每个 `execution_date` 完成 sell/buy 记账、更新 `daily_nav` 后，立即保存该 execution date snapshot；
- 删除旧逻辑中“所有 orders 完成后用最终 holdings 遍历所有 daily_nav 日期”的回填路径；
- `summary.max_holding_count` 仍来自真实 `daily_nav.holding_count`。

D2R 验收样例已满足：

```text
2026-05-06 snapshot: TW2467 quantity=280; no TW2337
2026-05-07 snapshot: TW2337 quantity=820; no TW2467
```

抽查输出：

```text
      date instrument  quantity
2026-05-06     TW2467       280
2026-05-07     TW2337       820
```

## 4. Validator 加固

`scripts/validate_tw_modular_order_intent_replay.py` 保留原 D2 边界检查，并新增 D2R 要求的状态检查：

```text
snapshots_required_columns
daily_nav_snapshot_dates_match
daily_nav_holding_count_matches_snapshots
initial_snapshot_matches_portfolio_state_or_manifest_initial_state
sell_action_removed_from_execution_snapshot
buy_action_present_in_execution_snapshot_with_quantity
no_future_buy_in_signal_date_snapshot
```

说明：validator 读取 OrderIntent manifest 的 `portfolio_state_artifact` 只用于核对 initial snapshot，不用于重新选股、排序、训练、调参或信号重算。

## 5. 测试补充

`tests/unit/test_tw_modular_order_intent_replay.py` 增加并通过以下 D2R 用例：

```text
test_d2_position_snapshots_are_date_specific
test_validator_rejects_future_buy_backfilled_into_signal_date_snapshot
test_validator_rejects_sell_symbol_remaining_after_execution_date
test_daily_nav_holding_count_matches_snapshot_rows
test_validator_rejects_daily_nav_holding_count_snapshot_mismatch
```

负面测试会复制 replay artifact 后构造 mutated artifact，确认 validator 能拒绝：

- 将未来买入的 `TW2337` 回填到 signal date snapshot；
- 将已卖出的 `TW2467` 残留到 execution date snapshot；
- 删除 execution date 买入持仓导致 `daily_nav.holding_count` 与 snapshot 行数不一致。

## 6. 新产物

D2R replay artifact：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/d2_order_intent_replay_20260506_20260617T044813Z/manifest.json
```

配套 OrderIntent artifact：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/d2_order_intent_20260506_20260617T044813Z/manifest.json
```

Runner 输出：

```json
{
  "ok": true,
  "manifest": "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/d2_order_intent_replay_20260506_20260617T044813Z/manifest.json",
  "order_intent_artifact": "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/d2_order_intent_20260506_20260617T044813Z/manifest.json",
  "action_count": 2,
  "skipped_action_count": 0
}
```

## 7. 验证结果

已执行并通过：

```bash
python -m py_compile scripts/run_tw_modular_order_intent_replay.py scripts/validate_tw_modular_order_intent_replay.py
```

结果：pass。

```bash
python scripts/run_tw_modular_order_intent_replay.py --json
```

结果：`ok=true`, `action_count=2`, `skipped_action_count=0`。

```bash
python scripts/validate_tw_modular_order_intent_replay.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/d2_order_intent_replay_20260506_20260617T044813Z/manifest.json --json
```

结果：`ok=true`，新增 D2R checks 全部 pass。

```bash
python scripts/validate_tw_modular_order_intent_artifact.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/d2_order_intent_20260506_20260617T044813Z/manifest.json --json
```

结果：`ok=true`, `row_count=10`, `artifact_stage=d2_replay_input`。

```bash
python -m pytest tests/unit/test_tw_modular_order_intent_artifact.py tests/unit/test_tw_modular_order_intent_replay.py
```

结果：`14 passed in 28.75s`。

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

结果：`ok=true`。

```bash
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

结果：`ok=true`。

Targeted static audit：

```bash
rg -n "choose_sells|candidate_rank <=|buy_score|score_rank|target_position|target_weight|broker|quick_trade|provider_publish|accepted_latest|monitor/scan|monitor/config|monitor/alerts" scripts/run_tw_modular_order_intent_replay.py scripts/validate_tw_modular_order_intent_replay.py tests/unit/test_tw_modular_order_intent_replay.py
```

结果有 4 个命中，均为 `no_choose_sells_call` 审计字段或说明文本，不是 `choose_sells()` 调用、实现或策略决策逻辑；未命中 `candidate_rank <=`、`buy_score`、`score_rank`、`target_position`、`target_weight`、broker、quick_trade、provider_publish、accepted_latest、monitor scan/config/alerts。

## 8. 边界声明

D2R 没有进入 D3 full-window/five-rule parity；没有修改生产 API、前端、daily auto update、provider publish、accepted latest、monitor、broker、quick-trade 或 order 链路；没有训练、调参、score 重算、默认模型或默认策略切换。
