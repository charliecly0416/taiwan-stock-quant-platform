# Phase D2R 审查与 Phase D3 工作文档

生成日期：2026-06-17

## 1. D2R 审查结论

D2R 审查通过，可以关闭 D2 blocker，并允许进入 D3。

结论：

```text
D2R snapshot state repair: pass
D2 replay boundary: pass
next phase: D3 five-rule full-window parity
```

D2R 已修复上一轮发现的 `position_snapshots.csv` 使用最终 holdings 回填所有日期的问题。新的 replay runner 会在 `signal_date` 保存 initial holdings snapshot，并在每个 `execution_date` 完成 sell/buy 后保存当日 holdings snapshot。增强 validator 已能拒绝 future buy backfill、sell symbol execution date 残留、daily_nav holding_count 与 snapshot 行数不一致等同类错误。

D2R 仍未宣称 D3 parity，这一点正确。

## 2. 审查对象

handoff：

```text
docs/tw_modular_contracts/PHASED2R_REPLAY_SNAPSHOT_STATE_REPAIR_REVIEW_HANDOFF_CN.md
```

核心实现：

```text
scripts/run_tw_modular_order_intent_replay.py
scripts/validate_tw_modular_order_intent_replay.py
tests/unit/test_tw_modular_order_intent_replay.py
```

D2R replay artifact：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/d2_order_intent_replay_20260506_20260617T044813Z/manifest.json
```

D2R OrderIntent input：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/d2_order_intent_20260506_20260617T044813Z/manifest.json
```

## 3. Findings

未发现阻塞项。

### 3.1 上轮 High blocker 已修复

runner 修复点：

```text
scripts/run_tw_modular_order_intent_replay.py:138
scripts/run_tw_modular_order_intent_replay.py:187
scripts/run_tw_modular_order_intent_replay.py:322
```

当前实现：

- `snapshot_holdings(...)` 只从当前 `holdings` dict 生成指定日期的 snapshot；
- `signal_date` 初始化后立即生成 initial snapshot；
- 每个 `execution_date` 完成 sell/buy 和 NAV 计算后，追加当日 snapshot；
- 不再用最终 holdings 回填全部日期。

artifact spot check：

```text
actions.csv:
2026-05-06 -> 2026-05-07 TW2467 historical_risk_reduce quantity=280
2026-05-06 -> 2026-05-07 TW2337 historical_add quantity=820

position_snapshots.csv:
2026-05-06 contains TW2467 quantity=280
2026-05-06 does not contain TW2337
2026-05-07 contains TW2337 quantity=820
2026-05-07 does not contain TW2467
```

`daily_nav.csv` 的 `holding_count=9` 与两个日期 snapshot 正持仓行数一致。

### 3.2 Validator 已覆盖 snapshot state invariants

validator 增强点：

```text
scripts/validate_tw_modular_order_intent_replay.py:14
scripts/validate_tw_modular_order_intent_replay.py:93
scripts/validate_tw_modular_order_intent_replay.py:111
scripts/validate_tw_modular_order_intent_replay.py:166
scripts/validate_tw_modular_order_intent_replay.py:181
scripts/validate_tw_modular_order_intent_replay.py:204
```

新增/关键 checks：

```text
snapshots_required_columns
daily_nav_snapshot_dates_match
daily_nav_holding_count_matches_snapshots
initial_snapshot_matches_portfolio_state_or_manifest_initial_state
sell_action_removed_from_execution_snapshot
buy_action_present_in_execution_snapshot_with_quantity
no_future_buy_in_signal_date_snapshot
```

新 artifact validator 输出：

```text
ok=true
daily_nav_snapshot_dates_match=pass
daily_nav_holding_count_matches_snapshots=pass
initial_snapshot_matches_portfolio_state_or_manifest_initial_state=pass
sell_action_removed_from_execution_snapshot=pass
buy_action_present_in_execution_snapshot_with_quantity=pass
no_future_buy_in_signal_date_snapshot=pass
```

### 3.3 负面测试覆盖同类回归

测试增强点：

```text
tests/unit/test_tw_modular_order_intent_replay.py:103
tests/unit/test_tw_modular_order_intent_replay.py:116
tests/unit/test_tw_modular_order_intent_replay.py:125
tests/unit/test_tw_modular_order_intent_replay.py:146
tests/unit/test_tw_modular_order_intent_replay.py:167
```

覆盖：

- 正例：D2 snapshots 按日期区分；
- 正例：daily_nav holding_count 与 snapshot rows 一致；
- 负例：future buy 回填到 signal_date 会失败；
- 负例：sell symbol 在 execution date 残留会失败；
- 负例：daily_nav holding_count 与 snapshot rows 不一致会失败；
- 负例：D2/D2R 仍拒绝 parity claim。

## 4. 只读与解耦边界

静态审计：

```bash
rg -n "choose_sells|candidate_rank <=|buy_score|score_rank|target_position|target_weight|broker|quick_trade|provider_publish|accepted_latest|monitor/scan|monitor/config|monitor/alerts" scripts/run_tw_modular_order_intent_replay.py scripts/validate_tw_modular_order_intent_replay.py tests/unit/test_tw_modular_order_intent_replay.py
```

结果只命中 `no_choose_sells_call` 审计字段/说明文本。

未发现：

```text
choose_sells call
candidate_rank <= strategy decision
buy_score / score_rank replay decision
target_position / target_weight
provider publish
accepted latest switch
monitor config / scan / alerts write
broker / quick-trade / order
frontend/API/daily product path change
training / tuning / score recompute
```

判断：D2R 保持 `ReplayExecutionEngine` 从 `OrderIntentArtifact` 消费决策字段的边界，没有把策略决策重新塞回 replay runner。

## 5. 复核命令

已执行：

```bash
python -m py_compile scripts/run_tw_modular_order_intent_replay.py scripts/validate_tw_modular_order_intent_replay.py
python scripts/validate_tw_modular_order_intent_replay.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/d2_order_intent_replay_20260506_20260617T044813Z/manifest.json --json
python scripts/validate_tw_modular_order_intent_artifact.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/d2_order_intent_20260506_20260617T044813Z/manifest.json --json
python -m pytest tests/unit/test_tw_modular_order_intent_artifact.py tests/unit/test_tw_modular_order_intent_replay.py
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

结果：

```text
py_compile: pass
D2R replay validator: ok=true
D2R OrderIntent validator: ok=true
unit tests: 14 passed
contract regression: ok=true
readonly snapshot validator: ok=true
```

说明：普通 sandbox 下部分 Python 命令触发 `bwrap: loopback: Failed RTM_NEWADDR`，复核时使用升级执行方式完成。

## 6. D3 工作目标

D3 目标：

```text
把 D2R 的 OrderIntent -> ReplayExecution 路径扩展到五个规则和完整 2026_ytd 窗口，并与旧 replay matrix 做逐项 parity。
```

D3 不是产品接入阶段，不得改前端/API/daily/provider/accepted latest/monitor/broker/order。

## 7. D3 必做范围

D3 必须覆盖五个规则：

```text
original
top50_exit_all
top50_exit_one_worst_sell
one_sell_one_buy_correct
one_sell_one_buy_buggy_e8r
```

其中：

```text
one_sell_one_buy_buggy_e8r
```

只能作为 diagnostic parity 对象，不得作为有效策略、产品策略或收益证据。

D3 必须覆盖窗口：

```text
2026_ytd
```

D3 必须产出新的 parity artifact，至少包含：

```text
manifest.json
summary_parity.csv
daily_nav_parity.csv
actions_parity.csv
action_key_parity.csv
position_snapshot_parity.csv
coverage_audit.csv
forbidden_scope_audit.csv
decision_source_audit.csv
```

## 8. D3 Parity 验收标准

D3 与旧 replay matrix 比较时，至少检查：

```text
summary parity:
  final_equity
  total_return
  max_drawdown
  action_count
  buy_count
  sell_count
  skipped_action_count
  max_holding_count
  negative_cash_count
  missing_price_count

daily_nav parity:
  date
  cash
  market_value
  equity
  daily_return
  holding_count
  missing_price_count

actions parity:
  signal_date
  execution_date
  instrument
  action
  quantity
  execution_price
  commission
  tax
  cash_after
  position_after

action key parity:
  signal_date
  execution_date
  instrument
  action

position snapshot parity:
  date
  instrument
  quantity
  mark_price
  market_value
```

数值容差建议：

```text
cash / market_value / equity / fees / tax: abs diff <= 0.02
daily_return / total_return / max_drawdown: abs diff <= 1e-8
quantity / counts / action keys: exact match
dates / instruments / action labels: exact match
```

如旧 replay 与新 replay 在字段命名上不同，D3 可以做 adapter mapping，但必须在 parity manifest 中明示映射，不得用模糊字段绕过差异。

## 9. D3 实现边界

允许新增或修改：

```text
scripts/run_tw_modular_order_intent_replay.py
scripts/validate_tw_modular_order_intent_replay.py
tests/unit/test_tw_modular_order_intent_replay.py
scripts/run_tw_modular_order_intent_replay_parity.py
scripts/validate_tw_modular_order_intent_replay_parity.py
tests/unit/test_tw_modular_order_intent_replay_parity.py
docs/tw_modular_contracts/PHASED3_*.md
```

如需要让 D1/D2 builder 支持多日期、多规则 OrderIntentArtifact，可修改：

```text
scripts/build_tw_modular_order_intent_artifact.py
scripts/validate_tw_modular_order_intent_artifact.py
tests/unit/test_tw_modular_order_intent_artifact.py
```

禁止修改：

```text
frontend/**
backend/**
backend_api_python/src/api/**
scripts/run_daily_tw_stock_auto_update.py
scripts/publish_tw_modular_readonly_snapshot.py
provider / accepted latest / monitor / broker / quick-trade / order 相关路径
```

原则：

- 旧 `scripts/run_tw_modular_config_replay_matrix.py` 只能作为 parity baseline 读取或复跑；
- 若必须修改旧 replay baseline 脚本，必须先停下来说明原因，不得在 D3 中静默改变 baseline；
- D3 不得训练、调参、重算模型分数；
- D3 不得切换默认模型、默认策略、生产 latest 指针。

## 10. D3 Validator 要求

D3 必须提供 parity validator，至少检查：

```text
artifact_type / schema_version
five rules all present
window == 2026_ytd
baseline manifest exists
order_intent replay manifest exists
summary_parity all pass
daily_nav_parity all pass
actions_parity all pass
action_key_parity all pass
position_snapshot_parity all pass
diagnostic rule marked diagnostic_only
no D3 parity bypass / no missing-row ignored
forbidden_scope_audit pass
decision_source_audit pass
```

validator 必须在任何一项 parity fail 时返回非零退出码。

## 11. D3 测试要求

D3 至少增加：

```text
test_d3_parity_artifact_validates
test_d3_five_rules_present
test_d3_rejects_missing_rule
test_d3_rejects_summary_mismatch
test_d3_rejects_daily_nav_mismatch
test_d3_rejects_action_key_mismatch
test_d3_rejects_position_snapshot_mismatch
test_d3_rejects_diagnostic_rule_as_valid_strategy_evidence
```

负面测试必须 mutate parity artifact，证明 validator 不是只看 manifest flags。

## 12. D3 验证命令

D3 执行者完成后必须提供：

```bash
python -m py_compile scripts/build_tw_modular_order_intent_artifact.py scripts/validate_tw_modular_order_intent_artifact.py scripts/run_tw_modular_order_intent_replay.py scripts/validate_tw_modular_order_intent_replay.py scripts/run_tw_modular_order_intent_replay_parity.py scripts/validate_tw_modular_order_intent_replay_parity.py
python scripts/run_tw_modular_order_intent_replay_parity.py --json
python scripts/validate_tw_modular_order_intent_replay_parity.py --artifact <d3_parity_manifest> --json
python -m pytest tests/unit/test_tw_modular_order_intent_artifact.py tests/unit/test_tw_modular_order_intent_replay.py tests/unit/test_tw_modular_order_intent_replay_parity.py
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

并提供 static boundary audit：

```bash
rg -n "target_position|target_weight|broker|quick_trade|provider_publish|accepted_latest|monitor/scan|monitor/config|monitor/alerts|POST /api|PUT /api|PATCH /api|DELETE /api" scripts tests docs/tw_modular_contracts
```

预期：

```text
all validators ok=true
all parity checks pass
unit tests pass
contract regression ok=true
readonly snapshot validator ok=true
no production write / trading / monitor / provider boundary hit
```

## 13. D3 输出说明

D3 执行报告必须明确说明：

```text
baseline replay manifest
new order-intent replay manifest(s)
parity artifact path
five-rule row counts
window start/end
summary parity result
daily_nav parity result
actions parity result
action key parity result
position snapshot parity result
diagnostic rule boundary result
readonly boundary result
```

D3 通过后，下一阶段才可以考虑把标准 `OrderIntentArtifact` / `ReplayResultArtifact` 接入只读产品展示链路。
