---
created_at: 2026-06-28
phase: MTRP0_P2_PRODUCTION_CANDIDATE_ORDER_INTENT_REVIEW
reviewer: MTRP0-P2
strategy_rule: top50_hold_rank_buffer_100
reviewed_run_id: mtrp0_p2_20260628T180138Z
readonly_only: true
simulation_only: true
production_allowed: false
verdict: PASS_STOP_CORRECT_NEEDS_PRODUCTION_FULL_RANK_VISIBILITY_BRIDGE
can_enter_p3: false
---

# POLICY_MTRP0_P2_PRODUCTION_CANDIDATE_ORDER_INTENT_REVIEW_CN

## 1. Verdict

```text
PASS_STOP_CORRECT_NEEDS_PRODUCTION_FULL_RANK_VISIBILITY_BRIDGE
```

结论：

```text
MTRP0-P2 的 STOP 是正确的。
当前 production ModelSignalArtifact 只有 qlib top50 可见性，不能支持 top50_hold_rank_buffer_100 对持仓跌出 top50 后、但仍在 rank<=100 缓冲区内的判断。
因此不得生成 OrderIntentArtifact，也不得进入 P3 same-window baseline replay。
```

P3：

```text
can_enter_p3 = false
```

## 2. 已审查输入

已阅读指定政策、合同、dependency、执行脚本与执行报告：

- `docs/tw_portfolio_decision_model/POLICY_MTRC6_COORDINATOR_DECISION_AND_PRODUCTION_GATE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP0_P2_PRODUCTION_CANDIDATE_ORDER_INTENT_EXECUTION_REPORT_CN.md`
- `configs/strategy_dependencies/top50_hold_rank_buffer_100.yaml`
- `scripts/build_tw_policy_mtrp0_p2_production_candidate_order_intent.py`
- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/STRATEGY_DEPENDENCY_CONTRACT_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`

审查 artifact：

```text
data_tw/artifacts/strategies/top50_hold_rank_buffer_100/mtrp0_p2_20260628T180138Z/
```

## 3. STOP 合理性审查

执行报告与 artifact 一致显示：

```text
production signal manifest = data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/2026-06-17/model_b_yz2/manifest.json
signal rows = 50
top50 rows = 50
non-top50 rows = 0
max full_qlib_rank visible = 50
visibility_columns = []
```

`top50_hold_rank_buffer_100` 的 dependency 明确要求：

```text
candidate_k = 50
hold_rank_buffer = 100
minimum_full_qlib_rank_visible = 100
non_top50_visibility_required = true
holding_visibility_required = true
stop_if_only_top50_visible = true
```

`readiness_audit.csv` 中四个失败项合理且必要：

```text
full_rank_visibility_min_rank_100: observed=50 expected=>=100
non_top50_visibility_rows_present: observed=0 expected=>0
not_only_top50_visible: observed=row_count=50;top50_count=50 expected=not exactly top50-only
holding_visibility_bridge_present: observed= expected=full-rank rows or explicit holding visibility bridge
```

审查判断：

```text
STOP_PRODUCTION_SIGNAL_FULL_RANK_VISIBILITY_MISSING 合理。
当前 production signal 不能证明一个已持仓标的在 top50 外但 rank<=100 时应继续持有，也不能证明 rank>100 时应卖出。
在这种可见性缺口下生成买卖意图会违反 StrategyRule / ModelSignal / OrderIntent 边界。
```

## 4. 六项重点结论

### 4.1 Full-rank visibility

通过。

当前 production signal 确实只有 top50：源 `signals.csv` 为 51 行含表头，即 50 条信号；manifest `row_count=50`、`candidate_k=50`；artifact 统计 `max_full_qlib_rank=50`、`non_top50_count=0`。这不足以支持 `hold_rank_buffer=100`。

### 4.2 未伪造非 top50 / full-rank visibility

通过。

未发现 artifact 伪造 rank>50 行、非 top50 行或 holding visibility bridge。`stop_artifact.json` 明确声明 blocker 为 production signal lacks full-rank/holding visibility。执行脚本只从 product registry 指向的 production ModelSignalArtifact 读取 signal，并显式检查路径不属于 `policy_mtr_research_only_continuation` 或 `mtrc1d`。

注意：生产 signal manifest 中有 `source_model_artifact` 指向历史训练模型文件，这是 ModelSignal 溯源字段；本阶段脚本没有把该模型私有文件作为 runtime input 读取。

### 4.3 Dependency 生产候选边界

通过。

`configs/strategy_dependencies/top50_hold_rank_buffer_100.yaml` 与 readiness audit 均显示：

```text
diagnostic_only = false
research_only = false
production_candidate = true
production_allowed = false
frontend_selectable = false
production_default = false
```

新策略被定义为 production-candidate，但没有打开 production allowed、frontend selectable 或 production default。

### 4.4 未生成 OrderIntentArtifact

通过。

artifact 目录中没有 `order_intents.csv`。`manifest.json` 的 `artifact_type` 是：

```text
production_candidate_order_intent_readiness
```

不是 `order_intent`。`validator_report.json` 中 `stop_has_no_order_intents_csv` 为 pass，`order_intent_generated=false`。STOP artifact 没有冒充 OrderIntentArtifact。

### 4.5 未改生产 registry/default/frontend/API/Agent/daily/latest/provider/PriceStore

有条件通过。

本阶段相关证据显示：

```text
product_default_strategy_unchanged = pass
replay_policy_default_strategy_unchanged = pass
new_strategy_not_production_selectable = pass
forbidden_action_audit.frontend_or_api_or_agent_change = false
forbidden_action_audit.daily_auto_latest_pointer_switch = false
forbidden_action_audit.formal_pricestore_write = false
forbidden_action_audit.provider_publish = false
forbidden_action_audit.accepted_latest_switch = false
```

关键词检索未发现 `top50_hold_rank_buffer_100` 或 MTRP0-P2 被接入 frontend/API/Agent/daily 链路。当前仓库存在大量其他已修改或未跟踪文件，包含 frontend/API/daily 相关改动；本审查不将这些非 MTRP0-P2 变更归因给本阶段，但要求后续合并前由对应阶段单独审查。

### 4.6 无 broker/order/target_weight/target_position

通过。

STOP artifact、manifest、forbidden action audit 均未输出 broker/order/target_weight/target_position。dependency 与 schema 将 execution、quantity、cash、NAV、broker、target position/weight 等字段列为 forbidden。当前阶段没有 `order_intents.csv`，因此也不存在数量、权重、目标仓位或真实订单语义。

## 5. 合同一致性

本阶段符合：

```text
ModelSignalArtifact -> StrategyRule -> OrderIntentArtifact
```

的模块边界要求，因为在 ModelSignal 可见性不满足策略 dependency 时停止，没有跨层读取 MTRC research-only private signals，也没有从 replay return、future label、future price 或 private model CSV 推导策略动作。

本阶段也符合 MTRC6 Gate P2 的精神：P2 只能在正式 StrategyRule + production ModelSignalArtifact + PortfolioState 满足条件后生成标准 OrderIntentArtifact。现在条件不满足，因此 STOP 是正确输出。

## 6. Blocker 与下一步

当前 blocker：

```text
production ModelSignalArtifact only exposes top50; full-rank/holding visibility for hold_rank_buffer_100 is missing
```

进入 P2 OrderIntent build / P3 replay 前，必须先完成以下二选一：

```text
1. 生产 ModelSignalArtifact 输出 full-rank rows 至少覆盖 full_qlib_rank <= 100，并保持买入 universe 仍只限 candidate_rank <= 50；
2. 生产 ModelSignalArtifact 增加明确的 holding visibility bridge，仅用于当前持仓卖出边界审计，不得扩大买入 top50 universe。
```

完成 bridge 后，需要重新运行 MTRP0-P2 readiness/order-intent builder，并要求：

```text
readiness_pass = true
order_intent_generated = true
order_intents.csv 符合 ORDER_INTENT_CONTRACT_CN.md
无 broker/order/target_weight/target_position/quantity/execution/cash/NAV 字段
```

只有上述条件满足后，才可考虑进入 P3 same-window production baseline replay。
