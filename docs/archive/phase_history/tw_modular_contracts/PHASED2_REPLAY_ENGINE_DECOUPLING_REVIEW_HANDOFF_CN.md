# Phase D2 ReplayExecutionEngine 解耦审查交接

生成日期：2026-06-17

## 1. 审查入口

执行报告：

```text
docs/tw_modular_contracts/PHASED2_REPLAY_ENGINE_DECOUPLING_EXECUTION_REPORT_CN.md
```

核心新增文件：

```text
scripts/run_tw_modular_order_intent_replay.py
scripts/validate_tw_modular_order_intent_replay.py
tests/unit/test_tw_modular_order_intent_replay.py
```

D2 replay artifact：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/d2_order_intent_replay_20260506_20260617T042642Z/manifest.json
```

D2 OrderIntent input：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/d2_order_intent_20260506_20260617T042642Z/manifest.json
```

## 2. 建议复核命令

```bash
python -m py_compile scripts/build_tw_modular_order_intent_artifact.py scripts/validate_tw_modular_order_intent_artifact.py scripts/run_tw_modular_order_intent_replay.py scripts/validate_tw_modular_order_intent_replay.py
python scripts/run_tw_modular_order_intent_replay.py --json
python scripts/validate_tw_modular_order_intent_replay.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/d2_order_intent_replay_20260506_20260617T042642Z/manifest.json --json
python scripts/validate_tw_modular_order_intent_artifact.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d2/order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/d2_order_intent_20260506_20260617T042642Z/manifest.json --json
python -m pytest tests/unit/test_tw_modular_order_intent_artifact.py tests/unit/test_tw_modular_order_intent_replay.py
python scripts/run_tw_modular_contract_regression.py --json
```

预期：全部通过。

## 3. 审查重点

请重点审查：

1. `scripts/run_tw_modular_order_intent_replay.py` 是否只消费 OrderIntentArtifact 的决策字段；
2. D2 runner 是否没有 `choose_sells()`、`candidate_rank <=`、`buy_score`、`score_rank` 等策略决策逻辑；
3. `decision_source_audit.csv` 是否声明并通过：`decision_source=order_intent_artifact`、`no_choose_sells_call=true`、`no_model_signal_decision_read=true`；
4. execution/accounting 是否只处理 next-day 成交、费用、税费、现金、持仓、NAV；
5. 输出是否包含 ReplayResultArtifact 必需文件；
6. D2 是否没有宣称 D3 parity；
7. 是否没有前端/API/daily/provider/交易链路越界。

## 4. 已知边界

D2 是单日主策略初步 replay：

```text
model=e4_frozen_qlib_2023_2025_ltr
strategy=top50_exit_one_worst_sell
signal_date=2026-05-06
```

D2 不等于 D3 parity。D3 仍需完成五规则全窗口：

```text
summary parity
daily_nav parity
actions parity
action key parity
```

## 5. D3 建议入口

若 D2 审查通过，D3 应将 D2 runner 扩展到五规则和完整 2026_ytd 窗口，并与旧 replay 逐项做 parity。
