# Phase D1 StrategyDecisionEngine 审查交接

生成日期：2026-06-17

## 1. 审查入口

D1 执行报告：

```text
docs/tw_modular_contracts/PHASED1_STRATEGY_DECISION_ENGINE_EXECUTION_REPORT_CN.md
```

核心新增文件：

```text
scripts/build_tw_modular_order_intent_artifact.py
scripts/validate_tw_modular_order_intent_artifact.py
tests/unit/test_tw_modular_order_intent_artifact.py
```

样例 artifact：

```text
data_tw/artifacts/order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/d1_order_intent_20260507_20260617T040825Z/manifest.json
```

## 2. 建议复核命令

```bash
python -m py_compile scripts/build_tw_modular_order_intent_artifact.py scripts/validate_tw_modular_order_intent_artifact.py
python scripts/build_tw_modular_order_intent_artifact.py --json
python scripts/validate_tw_modular_order_intent_artifact.py --artifact data_tw/artifacts/order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/d1_order_intent_20260507_20260617T040825Z/manifest.json --json
python -m pytest tests/unit/test_tw_modular_order_intent_artifact.py
python scripts/audit_tw_modular_decision_replay_d0.py --json
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

预期：全部通过，其中 D1 validator 返回 `ok=true`。

## 3. 审查重点

请重点审查：

1. 五个 `decide_*` 函数是否独立存在；
2. 决策函数是否只消费 signal rows、PortfolioState、StrategyRuleConfig；
3. 是否没有修改 replay execution 主体；
4. `OrderIntentArtifact` 是否不含 execution/accounting/broker/target position 字段；
5. `buy_rank` 映射是否定义清楚并由 validator 检查；
6. outside-candidate 行的 `buy_rank=-1` 是否仅为 D1 sample-only 哨兵，未作为排序或 replay 证据；
7. PortfolioState 是否来自 `legacy_replay_snapshot_for_d1_sample_only`，且声明 `not_d2_replay_execution_source=true`；
8. 是否没有把 readonly snapshot 当作 canonical PortfolioState；
9. artifact 是否声明 `artifact_stage=d1_decision_sample`、`not_used_for_replay_result=true`、`not_parity_evidence=true`；
10. diagnostic 规则是否仍为 `diagnostic_only=true` / `not_valid_strategy_evidence=true`；
11. D1 报告是否没有宣称 replay parity 或收益复现。

## 4. Validator 负面测试

单测覆盖：

```text
forbidden execution_price 字段会被拒绝
buy_rank 与 source signal score_rank 不一致会被拒绝
diagnostic rule 边界必须成立
```

## 5. D2 建议入口

若 D1 审查通过，D2 可以开始：

```text
ReplayExecutionEngine 只消费 OrderIntentArtifact
```

D2 才允许改 replay execution 主体。D2 应保持 next-day execution、费用、税费、现金、持仓、NAV 逻辑不变，并准备 D3 parity。
