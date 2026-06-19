# Phase D0 决策与回放解耦执行报告

生成日期：2026-06-17

## 1. 执行内容

本轮执行 `TW_MODULAR_DECISION_REPLAY_DECOUPLING_WORK_CN.md` 的 D0：合同冻结与可行性审计。

新增文件：

```text
scripts/audit_tw_modular_decision_replay_d0.py
docs/tw_modular_contracts/PHASED0_DECISION_REPLAY_DECOUPLING_WORK_CN.md
docs/tw_modular_contracts/PHASED0_DECISION_REPLAY_DECOUPLING_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/PHASED0_DECISION_REPLAY_DECOUPLING_REVIEW_HANDOFF_CN.md
```

新增审计产物：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/decision_replay_decoupling_d0/d0_summary.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/decision_replay_decoupling_d0/signal_input_audit.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/decision_replay_decoupling_d0/rule_expressibility_audit.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/decision_replay_decoupling_d0/replay_decoupling_feasibility_audit.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/decision_replay_decoupling_d0/readonly_snapshot_boundary_audit.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/decision_replay_decoupling_d0/d1_d5_acceptance_checklist.csv
```

D0 未修改 replay 结果、前端、API、日更、默认策略、provider accepted latest 或交易链路。

## 2. 审计脚本

新增只读审计脚本：

```text
scripts/audit_tw_modular_decision_replay_d0.py
```

脚本只读取：

```text
configs/tw_modular_replay_matrix.yaml
configs/tw_modular_registry.yaml
configs/strategy_dependencies/*.yaml
scripts/run_tw_modular_config_replay_matrix.py
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
data_tw/artifacts/shadow_modular_daily/2026-06-16/manifest.json
ModelSignalArtifact manifests/signals.csv
```

脚本不训练、不调参、不重算 score、不重算 replay、不触发 publish、不写生产 latest。

## 3. D0 审计结果

执行命令：

```bash
python scripts/audit_tw_modular_decision_replay_d0.py --json
```

结果：

```text
ok=true
phase=D0
signal_input_models=5
rule_count=5
d0_conclusion=feasible_to_enter_d1
```

输出目录：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/decision_replay_decoupling_d0/
```

## 4. ModelSignalArtifact 输入可行性

`signal_input_audit.csv` 结果：5 个模型输入全部 pass。

覆盖模型：

```text
fresh_qlib_adaptive
fresh_qlib_2025_ltr
frozen_qlib_2025_ltr
e4_frozen_qlib_2023_2025_ltr
frozen_qlib_2018_2022
```

检查结论：

- `date/instrument/candidate_rank/buy_score/score_rank/full_qlib_rank/signal_asof/available_at` 均可用；
- quality_status 均为 pass；
- 未发现 D0 禁止的 future label / future return / 成交 / 现金 / 净值 / broker 字段；
- 决策不需要 readonly snapshot 作为 canonical 输入。

## 5. 五规则 OrderIntent 表达性

`rule_expressibility_audit.csv` 结果：五种规则全部 pass。

```text
original: pass
top50_exit_all: pass
top50_exit_one_worst_sell: pass
one_sell_one_buy_correct: pass
one_sell_one_buy_buggy_e8r: pass
```

五规则均可映射到标准意图字段：

```text
signal_date
instrument
intent_action
intent_reason
strategy_rule
candidate_rank
buy_rank
full_qlib_rank
max_buy_count
max_sell_count
model_name
signal_artifact
```

其中 `one_sell_one_buy_buggy_e8r` 已确认：

```text
diagnostic_only=True
not_valid_strategy_evidence=True
```

## 6. 当前耦合点与 D1/D2 拆分可行性

`replay_decoupling_feasibility_audit.csv` 关键结论：

```text
current_decision_replay_coupling: pass
  evidence: choose_sells and buy_order are called inside replay_strategy

legacy_replay_parity_baseline_available: pass
  summary/daily_nav/action parity are available for later D3 checks

replay_can_consume_order_intent: pass
  OrderIntent can carry buy/sell/hold/skip intent; ReplayExecution computes quantity, execution date, price, fees, tax, cash and NAV

readonly_snapshot_not_canonical_decision_input: pass
  replay manifest links ModelSignalArtifact and FullRankArtifact directly; shadow/readonly snapshot is display layer
```

当前耦合位置：

```text
scripts/run_tw_modular_config_replay_matrix.py
  choose_sells(rule, holdings, state)
  for symbol in buy_order:
```

D1 应抽出上述决策逻辑；D2 应让 replay loop 只消费 `OrderIntentArtifact`。

## 7. Legacy Parity 基线

现有 replay manifest：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/formal_replay_manifest.json
```

已有 parity：

```text
r2_parity_audit.csv:
  summary: pass, 25 vs 25
  daily_nav: pass, 1975 vs 1975
  actions: pass, 3651 vs 3651

r2_action_key_parity_audit.csv:
  baseline_not_modular_count=0
  modular_not_baseline_count=0
  duplicate_baseline_action_key_count=0
  duplicate_modular_action_key_count=0
  value_mismatch_count=0
  status=pass
```

D3 必须继续以这组 legacy parity 为验收基线。

## 8. Readonly Snapshot 边界

`readonly_snapshot_boundary_audit.csv` 结果全部 pass。

确认：

- shadow modular daily manifest 是 readonly only；
- shadow manifest 链接标准 `model_signal_manifest` 与 `replay_result_manifest`；
- readonly snapshot 只能作为展示层，不得成为 `StrategyDecisionEngine` 的 canonical 输入。

## 9. 验证命令

已执行：

```bash
python -m py_compile scripts/audit_tw_modular_decision_replay_d0.py
python scripts/audit_tw_modular_decision_replay_d0.py --json
```

结果：

```text
py_compile: pass
audit: ok=true, d0_conclusion=feasible_to_enter_d1
```

## 10. 禁止事项确认

D0 未执行：

- 训练；
- 调参；
- score recompute；
- replay recompute；
- 修改默认模型；
- 修改默认策略；
- 修改前端；
- 修改 API；
- 修改日更主链路；
- provider publish；
- accepted latest switch；
- monitor scan/config/alerts write；
- broker / quick-trade / order。

## 11. D0 结论

D0 通过，结论为：

```text
feasible_to_enter_d1
```

建议下一阶段 D1 只做：

```text
StrategyDecisionEngine
OrderIntentArtifact builder
OrderIntentArtifact validator
```

D1 不应改 ReplayExecution 记账主体；D2 再处理 replay 只消费 OrderIntent。
