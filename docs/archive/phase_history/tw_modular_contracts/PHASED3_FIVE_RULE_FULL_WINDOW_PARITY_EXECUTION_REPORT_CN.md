# Phase D3 Five-rule Full-window Parity 执行报告

生成日期：2026-06-17

## 1. 执行结论

D3 已完成五规则、`2026_ytd` 全窗口 replay parity artifact 生成与独立 validator。新的 D3 parity artifact 对 summary、daily_nav、actions、action_key、position_snapshot 五类输出均为 pass。

结论：

```text
D3 five-rule full-window parity: pass
summary parity: pass
daily_nav parity: pass
actions parity: pass
action key parity: pass
position snapshot parity: pass
diagnostic rule boundary: pass
readonly / production boundary: pass
```

## 2. 修改范围

新增：

```text
scripts/run_tw_modular_order_intent_replay_parity.py
scripts/validate_tw_modular_order_intent_replay_parity.py
tests/unit/test_tw_modular_order_intent_replay_parity.py
docs/tw_modular_contracts/PHASED3_FIVE_RULE_FULL_WINDOW_PARITY_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/PHASED3_FIVE_RULE_FULL_WINDOW_PARITY_REVIEW_HANDOFF_CN.md
```

未修改、未触碰：

```text
frontend/**
backend/**
backend_api_python/src/api/**
scripts/run_daily_tw_stock_auto_update.py
scripts/publish_tw_modular_readonly_snapshot.py
provider / accepted latest / monitor / broker / quick-trade / order 相关路径
```

没有训练、调参、重算模型分数、切换默认模型、切换默认策略或发布 production latest。

## 3. D3 产物

D3 parity manifest：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T052126Z/manifest.json
```

baseline replay manifest：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
```

baseline 数据映射：

```text
summary / daily_nav / actions baseline:
  data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix_windowed

position snapshot baseline:
  data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix
```

说明：`formal_replay_matrix_windowed` 没有 snapshot 文件；原始 `formal_replay_matrix/formal_replay_position_snapshots.csv` 已带 `window` 字段，因此 D3 manifest 明示 `baseline_snapshot_dir`，没有修改 baseline 脚本或 baseline 文件。

order-intent replay source：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
```

## 4. 覆盖范围

窗口：

```text
2026_ytd: 2026-01-01 -> 2026-05-07
```

五个规则全部覆盖：

```text
original
top50_exit_all
top50_exit_one_worst_sell
one_sell_one_buy_correct
one_sell_one_buy_buggy_e8r
```

`one_sell_one_buy_buggy_e8r` 仅作为 diagnostic parity 对象：

```text
diagnostic_rule_only_for_parity=true
diagnostic_rule_not_valid_strategy_evidence=true
```

实际矩阵覆盖 5 个 method x 5 个 rule：

```text
e4_frozen_qlib_2023_2025_ltr
fresh_qlib_2025_ltr
fresh_qlib_adaptive
frozen_qlib_2018_2022
frozen_qlib_2025_ltr
```

## 5. Parity 结果

D3 row counts：

```text
summary: 25
daily_nav: 1975
actions: 3651
action_key: 3651
position_snapshot: 11512
```

各 parity CSV：

```text
summary_parity.csv: baseline_rows=25, replay_rows=25, status=pass
daily_nav_parity.csv: baseline_rows=1975, replay_rows=1975, status=pass
actions_parity.csv: baseline_rows=3651, replay_rows=3651, status=pass
action_key_parity.csv: baseline_rows=3651, replay_rows=3651, status=pass
position_snapshot_parity.csv: baseline_rows=11512, replay_rows=11512, status=pass
```

输出文件：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T052126Z/summary_parity.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T052126Z/daily_nav_parity.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T052126Z/actions_parity.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T052126Z/action_key_parity.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T052126Z/position_snapshot_parity.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T052126Z/coverage_audit.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T052126Z/forbidden_scope_audit.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T052126Z/decision_source_audit.csv
```

## 6. Validator 与测试

新增 validator：

```text
scripts/validate_tw_modular_order_intent_replay_parity.py
```

validator 覆盖：

```text
artifact_type / schema_version
five rules all present
window == 2026_ytd
baseline manifest exists
order intent replay manifest exists
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

新增测试：

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

负面测试通过 mutated artifact 证明 validator 会真实读取 parity CSV 与 manifest 边界字段，不只是看 manifest flags。

## 7. 验证结果

已执行：

```bash
python -m py_compile scripts/build_tw_modular_order_intent_artifact.py scripts/validate_tw_modular_order_intent_artifact.py scripts/run_tw_modular_order_intent_replay.py scripts/validate_tw_modular_order_intent_replay.py scripts/run_tw_modular_order_intent_replay_parity.py scripts/validate_tw_modular_order_intent_replay_parity.py
```

结果：pass。

```bash
python scripts/run_tw_modular_order_intent_replay_parity.py --json
```

结果：`ok=true`, `parity_status=pass`, manifest 为 `d3_order_intent_replay_parity_20260617T052126Z/manifest.json`。

```bash
python scripts/validate_tw_modular_order_intent_replay_parity.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T052126Z/manifest.json --json
```

结果：`ok=true`。

```bash
python -m pytest tests/unit/test_tw_modular_order_intent_artifact.py tests/unit/test_tw_modular_order_intent_replay.py tests/unit/test_tw_modular_order_intent_replay_parity.py
```

结果：`22 passed in 79.00s`。

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

结果：`ok=true`。

```bash
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

结果：`ok=true`。

Static boundary audit：

```bash
rg -n "target_position|target_weight|broker|quick_trade|provider_publish|accepted_latest|monitor/scan|monitor/config|monitor/alerts|POST /api|PUT /api|PATCH /api|DELETE /api" scripts tests docs/tw_modular_contracts
```

全仓扫描命中大量既有合同文档、历史脚本和禁止项说明文本；这些不是 D3 新增生产写路径。为隔离 D3 变更风险，已对 D3 新增文件执行定向扫描：

```bash
rg -n "target_position|target_weight|broker|quick_trade|provider_publish|accepted_latest|monitor/scan|monitor/config|monitor/alerts|POST /api|PUT /api|PATCH /api|DELETE /api" scripts/run_tw_modular_order_intent_replay_parity.py scripts/validate_tw_modular_order_intent_replay_parity.py tests/unit/test_tw_modular_order_intent_replay_parity.py
```

结果：零命中。

## 8. 边界声明

D3 只生成并验证 replay parity artifact；没有进入产品接入阶段，没有修改前端/API/daily/provider/accepted latest/monitor/broker/quick-trade/order 链路；没有训练、调参、score 重算、默认模型或默认策略切换。
