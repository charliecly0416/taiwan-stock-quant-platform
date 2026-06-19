# Phase D0 决策与回放解耦审查交接

生成日期：2026-06-17

## 1. 审查入口

工作冻结文档：

```text
docs/tw_modular_contracts/PHASED0_DECISION_REPLAY_DECOUPLING_WORK_CN.md
```

执行报告：

```text
docs/tw_modular_contracts/PHASED0_DECISION_REPLAY_DECOUPLING_EXECUTION_REPORT_CN.md
```

D0 审计脚本：

```text
scripts/audit_tw_modular_decision_replay_d0.py
```

D0 审计输出：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/decision_replay_decoupling_d0/d0_summary.json
```

## 2. 建议复核命令

```bash
python -m py_compile scripts/audit_tw_modular_decision_replay_d0.py
python scripts/audit_tw_modular_decision_replay_d0.py --json
cat data_tw/experiments/extended_oos_qlib_orthogonal_ltr/decision_replay_decoupling_d0/rule_expressibility_audit.csv
cat data_tw/experiments/extended_oos_qlib_orthogonal_ltr/decision_replay_decoupling_d0/replay_decoupling_feasibility_audit.csv
cat data_tw/experiments/extended_oos_qlib_orthogonal_ltr/decision_replay_decoupling_d0/readonly_snapshot_boundary_audit.csv
```

预期：

```text
d0_summary.ok=true
d0_conclusion=feasible_to_enter_d1
rule_expressibility_audit.csv 五规则 status=pass
replay_decoupling_feasibility_audit.csv 全部 status=pass
readonly_snapshot_boundary_audit.csv 全部 status=pass
```

## 3. 审查重点

请重点确认：

1. D0 是否只做合同冻结与审计，没有提前做 D1/D2 实现；
2. 五种规则是否都能映射到 `OrderIntentArtifact`；
3. `one_sell_one_buy_buggy_e8r` 是否保持 diagnostic only；
4. 当前耦合点是否被准确定位在 replay loop 中的 `choose_sells()` 与 `buy_order`；
5. D1/D2 拆分边界是否明确：决策只输出意图，回放负责成交/记账/NAV；
6. readonly snapshot 是否明确不是 canonical 决策输入；
7. 是否没有训练、调参、重算 score/replay、provider publish、accepted latest、monitor、broker/order 越界。

## 4. D1 放行建议

若 D0 审查通过，建议进入 D1。

D1 允许做：

```text
scripts/build_tw_modular_order_intent_artifact.py
scripts/validate_tw_modular_order_intent_artifact.py
StrategyDecisionEngine 五规则决策函数
OrderIntentArtifact 样例产物
D1 执行报告与审查交接
```

D1 不应做：

```text
修改前端/API
修改日更
修改 provider accepted latest
改默认策略
训练/调参/score recompute
把 replay 记账主体重构为只吃 OrderIntent
```

最后一项属于 D2。
