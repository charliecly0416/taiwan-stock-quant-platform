---
created_at: 2026-06-28
status: review
phase: MTRP3_SAME_WINDOW_REPLAY_COMPARISON_REVIEW
reviewer: MTRP3
strategy_candidate: top50_hold_rank_buffer_100
baseline_strategy: top50_exit_one_worst_sell
review_root: data_tw/artifacts/replays/top50_hold_rank_buffer_100/mtrp3_same_window_replay_comparison/
readonly_only: true
simulation_only: true
production_allowed: false
verdict: PASS_CANDIDATE_OUTPERFORMS_READY_FOR_P4_SHADOW_READINESS
can_enter_p4: true
---

# POLICY_MTRP3_SAME_WINDOW_REPLAY_COMPARISON_REVIEW_CN

## 1. Verdict

```text
PASS_CANDIDATE_OUTPERFORMS_READY_FOR_P4_SHADOW_READINESS
```

是否可以进入 P4 shadow/readiness：

```text
true
```

审查结论：

```text
MTRP3 same-window baseline-vs-candidate readonly replay 比较同口径、会计检查通过，且真实显示 candidate 收益更高、回撤更低。
可以进入 P4 readonly shadow/readiness。
```

但该 PASS 不是 production-ready / default switch 授权：

```text
P2_R lineage warning 必须继续保留。
当前 bridge 仍是 existing audited broad reference repackaged for production-candidate readiness，不等同 production-ready ModelSignalArtifact。
不得切 production default、不得发布 latest、不得接入 broker、不得输出 target_weight/target_position。
```

## 2. 已审查材料

必读文件已审查：

- `docs/tw_portfolio_decision_model/POLICY_MTRC6_COORDINATOR_DECISION_AND_PRODUCTION_GATE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP2_R_FULL_RANK_VISIBILITY_BRIDGE_AND_ORDER_INTENT_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP3_SAME_WINDOW_REPLAY_COMPARISON_EXECUTION_REPORT_CN.md`
- `scripts/build_tw_policy_mtrp3_same_window_replay_comparison.py`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`

按新策略接入审查技能补充阅读：

- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`

审查 root：

```text
data_tw/artifacts/replays/top50_hold_rank_buffer_100/mtrp3_same_window_replay_comparison/
```

## 3. 同口径检查

通过。

root manifest 与两侧 replay manifest 均固定：

```text
signal_window = 2026-01-02..2026-05-07
bridge = data_tw/artifacts/signals/top50_hold_rank_buffer_100_full_rank_visibility_bridge/mtrp2_r_20260628T181347Z/manifest.json
initial_equity = 1000000
target_holdings = 10
fee_rate = 0.001425
sell_tax_rate = 0.003
lot_size = 10
execution_price = next_open
execution_date_policy = next_tradeable_day_after_signal_date
cash_policy = no_negative_cash
mark_price = close
mark_policy = same_day_required_fallback_audited
```

`scripts/build_tw_policy_mtrp3_same_window_replay_comparison.py` 中 baseline 与 candidate 使用同一个 `EXECUTION_CONFIG`、同一批允许本地 OHLCV price sources、同一 `run_replay()` 记账逻辑、同一 `build_summary()` 与 validator 口径。

价格源审计通过：

```text
allowed source priority 1: rcpt15_r3_x_r_real_model_a_top50_bridge_coverage_repair/stock_price_bridge
allowed source priority 2: rcpt15_r1_option_c_yahoo_scrapling_refresh_20260625/candidate_normalized
allowed source priority 3: rcpt15_r3_t_isolated_price_twii_source_repair/stock_price_bridge
self_contained_demo: forbidden_not_used
```

## 4. Baseline OrderIntent 来源

通过。

baseline OrderIntent 不是 production pending no-trade artifact。脚本直接读取同一个 P2_R bridge：

```text
BRIDGE_MANIFEST = data_tw/artifacts/signals/top50_hold_rank_buffer_100_full_rank_visibility_bridge/mtrp2_r_20260628T181347Z/manifest.json
BRIDGE_SIGNALS = .../signals.csv
BASELINE_ORDER_DIR = .../mtrp3_same_window_replay_comparison/baseline_order_intent
```

baseline manifest 也指向同一 bridge：

```text
signal_artifact = data_tw/artifacts/signals/top50_hold_rank_buffer_100_full_rank_visibility_bridge/mtrp2_r_20260628T181347Z/manifest.json
source_lineage = existing_audited_broad_reference_repackaged_for_production_candidate_readiness
order_intent_count = 144
buy_intent_count = 77
sell_intent_count = 67
validator_status = pass
```

独立 CSV 检查：

```text
baseline order_intents rows = 144
signal_date range = 2026-01-02..2026-05-07
actions = buy 77 / sell 67
forbidden OrderIntent fields = []
```

## 5. Candidate OrderIntent 来源

通过。

candidate replay manifest 固定使用 P2_R OrderIntent：

```text
order_intent_artifact = data_tw/artifacts/strategies/top50_hold_rank_buffer_100/mtrp2_r_20260628T181347Z/manifest.json
signal_artifact = data_tw/artifacts/signals/top50_hold_rank_buffer_100_full_rank_visibility_bridge/mtrp2_r_20260628T181347Z/manifest.json
```

P2_R candidate OrderIntent manifest：

```text
strategy_rule = top50_hold_rank_buffer_100
phase = MTRP2_R_FULL_RANK_VISIBILITY_BRIDGE_AND_ORDER_INTENT
run_id = mtrp2_r_20260628T181347Z
order_intent_count = 76
buy_intent_count = 43
sell_intent_count = 33
readiness_pass = true
production_allowed = false
not_default_candidate = true
not_published_latest = true
not_order = true
not_target_position = true
```

独立 CSV 检查：

```text
candidate order_intents rows = 76
intent rows date range = 2026-01-02..2026-05-05
strategy_decision_audit covers = 2026-01-02..2026-05-07
2026-05-06 and 2026-05-07 are audited as no buy/sell intent days
forbidden OrderIntent fields = []
```

未发现重新调参、重算模型分数、读取 replay return 作为策略输入或修改 candidate OrderIntent 的证据。

## 6. Accounting 与 Validator

通过。

root validator：

```text
status = pass
baseline_order_intent_validator_pass = true
baseline_replay_validator_pass = true
candidate_replay_validator_pass = true
same_window_signal_dates = true
same_execution_config = true
same_price_source_policy = true
lineage_warning_preserved = true
mark_quality_gate_pass = true
execution_price_gate_pass = true
forbidden_scope_clean = true
```

两侧 execution audit：

```text
execution_next_open_available = pass / 0 missing
execution_date_after_signal_date = pass / 0 violation
cash_never_negative = pass / 0 violation
```

两侧 mark coverage：

| strategy | same_day_mark_coverage_ratio | final_date_same_day_mark_coverage_ratio | fallback_mark_count | max_mark_lag_days | status |
| --- | ---: | ---: | ---: | ---: | --- |
| top50_exit_one_worst_sell | 1.0 | 1.0 | 0 | 0 | pass |
| top50_hold_rank_buffer_100 | 1.0 | 1.0 | 0 | 0 | pass |

ReplayResult 中 `execution_price`、`commission`、`tax`、`cash_after` 属于回放合同允许的记账输出，不存在于 OrderIntent，也未作为策略 ranking 输入。

## 7. Comparison 结果

通过，candidate 真实 outperform 且回撤更低。

| metric | baseline | candidate | delta |
| --- | ---: | ---: | ---: |
| final_equity | 1889481.157718 | 1960582.833712 | +71101.675994 |
| total_return | 0.8894811577 | 0.9605828337 | +0.0711016760 |
| max_drawdown | -0.1369660506 | -0.1104340101 | +0.0265320405 |
| action_count | 137 | 66 | -71 |
| buy_count | 73 | 37 | -36 |
| sell_count | 64 | 29 | -35 |
| skipped_action_count | 7 | 10 | +3 |

审查判断：

```text
candidate final_equity 更高；
candidate total_return 更高；
candidate max_drawdown 数值更接近 0，回撤更低；
candidate 交易动作显著更少；
candidate skipped actions 多 3 个，但未伴随 negative cash、missing price、execution price 或 mark coverage fail。
```

## 8. Lineage 与生产边界

通过，但必须保留 warning。

root manifest 明确：

```text
p2_r_lineage_warning = existing_audited_broad_reference_repackaged_for_production_candidate_readiness
readonly_only = true
simulation_only = true
production_allowed = false
not_default_switch = true
not_published_latest = true
production_ready = false
```

forbidden scope audit 全部 pass：

```text
production_registry_default_change = false
frontend_api_agent_daily_change = false
provider_refresh_or_publish = false
accepted_latest_switch = false
formal_price_store_write = false
broker_connection = false
quick_trade = false
real_order = false
target_weight_instruction = false
target_position_instruction = false
production_ready_claim = false
model_training = false
model_score_recompute = false
strategy_tuning = false
self_contained_demo_price_source = false
```

定向配置检查：

```text
configs/tw_product_artifact_registry.yaml:
  default_strategy_rule = top50_exit_one_worst_sell

configs/tw_replay_window_policy.yaml:
  default_strategy_rule = top50_exit_one_worst_sell

configs/strategy_dependencies/top50_hold_rank_buffer_100.yaml:
  frontend_selectable = false
  production_default = false
```

`configs/tw_product_artifact_registry.yaml`、`configs/tw_replay_window_policy.yaml`、`configs/tw_modular_registry.yaml` 在本次定向 diff 中无改动。

注意：当前工作树存在其他未提交改动，包含 frontend/API/daily/Agent 相关文件。该状态不能证明仓库全局未改这些文件；本审查只能确认 MTRP3 script/artifact 记录未执行这些生产链路动作，且 registry/default 定向检查未切换。进入 P4 前应隔离或单独审查这些非 MTRP3 改动，避免把 P4 shadow/readiness 与其他产品化改动混在同一证据包。

## 9. 风险与 P4 条件

主要风险：

```text
1. Lineage 风险：bridge 仍来自 research-only/broad reference repackaged lineage，只能支持 P4 readonly shadow/readiness，不能支持 production default。
2. 工作树隔离风险：仓库存在其他 frontend/API/daily/Agent 改动，P4 证据包应要求隔离或重新确认 forbidden scope。
3. skipped action 风险：candidate skipped_action_count = 10，高于 baseline 的 7；虽然 accounting gate 通过，但 P4 应跟踪 skip reason 分布。
4. window 风险：本次窗口为 2026-01-02..2026-05-07，仍是单一 same-window replay；P4 需要连续 readonly shadow/readiness 证据，不应把本 PASS 解读为生产稳定性证明。
```

P4 进入条件：

```text
允许进入 P4 readonly shadow/readiness；
继续 production_allowed=false；
继续 frontend_selectable=false / production_default=false；
继续不发布 latest、不改 provider/PriceStore、不接 broker、不输出 target_weight/target_position；
P4 报告必须继承 P2_R lineage warning，并单独审查当前工作树的非 MTRP3 改动隔离情况。
```
