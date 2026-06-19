# Phase D3 Five-rule Full-window Parity 审查交接

生成日期：2026-06-17

## 1. 审查结论建议

执行侧建议：D3 可进入审查。D3 已生成五规则、`2026_ytd` 全窗口 parity artifact，并由独立 validator 验证通过。

```text
D3 parity_status: pass
summary parity: pass
daily_nav parity: pass
actions parity: pass
action key parity: pass
position snapshot parity: pass
diagnostic rule boundary: pass
```

## 2. 审查对象

新增实现：

```text
scripts/run_tw_modular_order_intent_replay_parity.py
scripts/validate_tw_modular_order_intent_replay_parity.py
tests/unit/test_tw_modular_order_intent_replay_parity.py
```

执行报告：

```text
docs/tw_modular_contracts/PHASED3_FIVE_RULE_FULL_WINDOW_PARITY_EXECUTION_REPORT_CN.md
```

D3 parity artifact：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T052126Z/manifest.json
```

## 3. 核心复核点

请重点复核：

- 是否覆盖五个规则：`original`、`top50_exit_all`、`top50_exit_one_worst_sell`、`one_sell_one_buy_correct`、`one_sell_one_buy_buggy_e8r`；
- 是否覆盖 `2026_ytd` 全窗口：`2026-01-01 -> 2026-05-07`；
- 是否覆盖 5 个 method x 5 个 rule，总计 25 条 summary；
- 是否生成并验证 `summary_parity.csv`、`daily_nav_parity.csv`、`actions_parity.csv`、`action_key_parity.csv`、`position_snapshot_parity.csv`；
- validator 是否读取 parity CSV 和 audit CSV，而不是只看 manifest flags；
- `one_sell_one_buy_buggy_e8r` 是否仅作为 diagnostic parity 对象，不作为有效策略或产品策略证据；
- 是否未修改 production/frontend/API/daily/provider/accepted latest/monitor/trading 链路。

## 4. Artifact 摘要

D3 manifest 记录：

```text
parity_status=pass
window=2026_ytd
window_start=2026-01-01
window_end=2026-05-07
```

row counts：

```text
summary=25
daily_nav=1975
actions=3651
action_key=3651
position_snapshot=11512
```

rules_present：

```text
one_sell_one_buy_buggy_e8r
one_sell_one_buy_correct
original
top50_exit_all
top50_exit_one_worst_sell
```

methods_present：

```text
e4_frozen_qlib_2023_2025_ltr
fresh_qlib_2025_ltr
fresh_qlib_adaptive
frozen_qlib_2018_2022
frozen_qlib_2025_ltr
```

## 5. Baseline 映射

D3 使用 baseline manifest：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
```

D3 明示映射：

```text
summary / daily_nav / actions:
  data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix_windowed

position snapshots:
  data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix
```

原因：`formal_replay_matrix_windowed` 没有 snapshot copy；原始 snapshot 文件已有 `window` 字段，可直接过滤 `2026_ytd`。D3 没有修改旧 baseline 脚本或 baseline 文件。

## 6. 复核命令

建议审查者复跑：

```bash
python -m py_compile scripts/build_tw_modular_order_intent_artifact.py scripts/validate_tw_modular_order_intent_artifact.py scripts/run_tw_modular_order_intent_replay.py scripts/validate_tw_modular_order_intent_replay.py scripts/run_tw_modular_order_intent_replay_parity.py scripts/validate_tw_modular_order_intent_replay_parity.py
python scripts/validate_tw_modular_order_intent_replay_parity.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T052126Z/manifest.json --json
python -m pytest tests/unit/test_tw_modular_order_intent_artifact.py tests/unit/test_tw_modular_order_intent_replay.py tests/unit/test_tw_modular_order_intent_replay_parity.py
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

执行者结果：

```text
py_compile: pass
D3 runner: ok=true, parity_status=pass
D3 validator: ok=true
unit tests: 22 passed
contract regression: ok=true
readonly snapshot validator: ok=true
```

## 7. Static Boundary Audit

文档要求的全仓扫描会命中大量既有合同说明、禁止项清单和历史脚本说明文本。为了隔离 D3 新增代码风险，D3 新增文件定向扫描结果为零命中：

```bash
rg -n "target_position|target_weight|broker|quick_trade|provider_publish|accepted_latest|monitor/scan|monitor/config|monitor/alerts|POST /api|PUT /api|PATCH /api|DELETE /api" scripts/run_tw_modular_order_intent_replay_parity.py scripts/validate_tw_modular_order_intent_replay_parity.py tests/unit/test_tw_modular_order_intent_replay_parity.py
```

结果：无匹配。

## 8. 建议下一步

若 D3 审查通过，后续才可以考虑产品化接入标准 `OrderIntentArtifact` / `ReplayResultArtifact` 到只读展示链路。进入产品接入前仍需单独审查 readonly/product boundary，不能把 diagnostic rule 当成有效策略或收益证据。
