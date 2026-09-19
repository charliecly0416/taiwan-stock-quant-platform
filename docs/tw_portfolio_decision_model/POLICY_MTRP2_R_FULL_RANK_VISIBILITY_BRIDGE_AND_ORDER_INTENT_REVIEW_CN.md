---
created_at: 2026-06-28
phase: MTRP2_R_FULL_RANK_VISIBILITY_BRIDGE_AND_ORDER_INTENT_REVIEW
reviewer: MTRP2_R
strategy_rule: top50_hold_rank_buffer_100
reviewed_run_id: mtrp2_r_20260628T181347Z
readonly_only: true
simulation_only: true
production_candidate: true
production_allowed: false
verdict: PASS_READY_FOR_P3_SAME_WINDOW_REPLAY_WITH_LINEAGE_WARNING
can_enter_p3: true
---

# POLICY_MTRP2_R_FULL_RANK_VISIBILITY_BRIDGE_AND_ORDER_INTENT_REVIEW_CN

## 1. Verdict

```text
PASS_READY_FOR_P3_SAME_WINDOW_REPLAY_WITH_LINEAGE_WARNING
```

结论：

```text
MTRP2_R full-rank visibility bridge 与 top50_hold_rank_buffer_100 OrderIntent 构建通过本阶段合规审查。
可以进入 P3 same-window baseline readonly replay。
```

但该 PASS 带 lineage warning：

```text
bridge 来源是 existing audited broad reference repackaged for production-candidate readiness。
它可以用于 P3 same-window readonly replay 的可见性补桥，不等同于 production-ready ModelSignalArtifact，
不得发布 latest、不得切 production default、不得接入 frontend/API/Agent/daily/provider/PriceStore。
```

## 2. 已审查输入

已阅读：

- `docs/tw_portfolio_decision_model/POLICY_MTRC6_COORDINATOR_DECISION_AND_PRODUCTION_GATE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP0_P2_PRODUCTION_CANDIDATE_ORDER_INTENT_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRP2_R_FULL_RANK_VISIBILITY_BRIDGE_AND_ORDER_INTENT_EXECUTION_REPORT_CN.md`
- `scripts/build_tw_policy_mtrp2_r_full_rank_visibility_bridge_and_order_intent.py`
- `configs/strategy_dependencies/top50_hold_rank_buffer_100.yaml`
- `docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`

补充按新策略接入审查要求阅读：

- `docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`

审查 artifact：

```text
data_tw/artifacts/signals/top50_hold_rank_buffer_100_full_rank_visibility_bridge/mtrp2_r_20260628T181347Z/
data_tw/artifacts/strategies/top50_hold_rank_buffer_100/mtrp2_r_20260628T181347Z/
```

## 3. Bridge 覆盖与语义

通过。

CSV 复核结果：

```text
row_count = 11837
date_range = 2026-01-02..2026-05-07
date_count = 79
daily_row_count = 149..150
top50_row_count = 3950
non_top50_row_count = 7887
top50_daily_count = 50..50
duplicate_date_instrument = 0
```

`coverage_audit.csv` 与独立 CSV 统计一致：

```text
daily_row_count_min = 149 >= 100
daily_full_rank_visibility_min = 150 >= 100
top50_daily_row_count = 50..50
```

语义审查：

```text
top50 rows:
  buy_score/raw_score/score_rank 可用
  ext_ltr_top50_flag = true
  ext_buy_ranking_allowed = true

non-top50 visibility rows:
  buy_score/raw_score/score_rank 置空
  ext_broad_rank_visibility_only = true
  ext_buy_ranking_allowed = false
  只提供 full_qlib_rank visibility，不扩大买入 universe
```

独立统计确认：

```text
non_top50_buy_score_present = 0
non_top50_buy_allowed_true = 0
top50_buy_score_blank = 0
top50_buy_allowed_not_true = 0
```

因此，bridge 满足 MTRP0-P2 blocker 的修复目标：支持 `hold_rank_buffer=100` 的持仓 rank 可见性，同时仍把买入边界限制在 top50。

## 4. Source Lineage

有条件通过，必须保留 warning。

bridge manifest 诚实标注：

```text
source_lineage = existing_audited_broad_reference_repackaged_for_production_candidate_readiness
source_research_only = true
source_diagnostic_only = true
production_ready = false
production_allowed = false
not_published_latest = true
not_default_candidate = true
```

`lineage_audit.csv` 明确说明：

```text
bridge is production-candidate readonly readiness only and is not declared production-ready
source remains research_only lineage
```

源 manifest 也明确：

```text
research_only = true
diagnostic_only = true
production_allowed = false
no_provider_publish = true
no_accepted_latest_switch = true
quality_status = pass
window = 2026-01-02..2026-05-07
row_count = 11837
```

审查判断：

```text
source_lineage 未被伪装为 production-ready。
当前 lineage 可接受范围仅限 P3 same-window readonly replay 的 production-candidate readiness 验证。
后续若要进入生产 default / latest / daily shadow，必须另建正式 production artifact lineage 或取得 coordinator 决策。
```

## 5. OrderIntent 合同边界

通过。

OrderIntent manifest：

```text
artifact_type = order_intent
order_intent_count = 76
buy_intent_count = 43
sell_intent_count = 33
readiness_pass = true
can_enter_p3_same_window_baseline_replay = true
readonly_only = true
simulation_only = true
production_allowed = false
not_order = true
not_target_position = true
not_investment_advice = true
```

`order_intents.csv` 字段集合不含以下禁用语义：

```text
execution_price
cash
equity
quantity
target_weight
target_position
broker
execution_date
execution_quantity
shares
lots
nav
position
order_id
broker_order_id
```

独立 CSV 统计确认：

```text
forbidden_fields_present = []
readonly_not_order_bad = 0
source_lineage = existing_audited_broad_reference_repackaged_for_production_candidate_readiness
```

因此，本阶段产物只表达策略意图，不表达成交、数量、资金、权益、目标仓位、broker 或真实订单。

## 6. 策略规则一致性

通过。

`configs/strategy_dependencies/top50_hold_rank_buffer_100.yaml` 与 OrderIntent schema/validator 一致：

```text
strategy_rule = top50_hold_rank_buffer_100
hold_rank_buffer = 100
candidate_k = 50
target_holding_count = 10
max_buy_count = 1
max_sell_count = 1
sell_boundary = full_qlib_rank_gt_100
buy_order = buy_score_desc_full_qlib_rank_asc_instrument_asc
production_allowed = false
frontend_selectable = false
production_default = false
```

OrderIntent 独立统计：

```text
max_daily_buy = 1
max_daily_sell = 1
non_top50_buys = 0
sell_rank_lte_100 = 0
```

规则语义成立：

```text
买入只允许 candidate_rank <= 50 且 ext_buy_ranking_allowed=true。
卖出只针对当前持仓且 full_qlib_rank > 100。
每日最多一买一卖。
```

## 7. 未改生产链路

通过，但保留仓库脏状态说明。

定向检查结果：

```text
configs/tw_product_artifact_registry.yaml:
  default_strategy_rule = top50_exit_one_worst_sell

configs/tw_replay_window_policy.yaml:
  default_strategy_rule = top50_exit_one_worst_sell

configs/tw_modular_registry.yaml:
  production_selectable 仅包含 top50_exit_one_worst_sell
  未加入 top50_hold_rank_buffer_100

backend/frontend/scripts/run_daily_tw_stock_auto_update.py:
  未发现 mtrp2_r_20260628T181347Z
  未发现 top50_hold_rank_buffer_100_full_rank_visibility_bridge
  未发现 top50_hold_rank_buffer_100 接入痕迹
```

artifact 自带 forbidden action audit 也显示：

```text
provider_publish = false
accepted_latest_switch = false
frontend_or_api_or_agent_change = false
daily_auto_latest_pointer_switch = false
formal_pricestore_write = false
broker_connection = false
quick_trade = false
real_order = false
target_weight_or_target_position_output = false
quantity_output = false
```

注意：

```text
当前工作树存在大量既有 modified/untracked 文件，包含 frontend/API/daily 相关改动。
本审查只确认未发现本阶段 run_id、bridge artifact 或策略名被接入 production registry/default/frontend/API/Agent/daily/latest/provider/PriceStore。
这些无关脏改动不归因于 MTRP2_R，但合并前仍需由对应阶段单独审查。
```

## 8. Validator 与脚本审查

通过。

MTRP2_R builder 的关键安全实现：

```text
source_lineage_checks 要求源 artifact name、quality_status、window、research_only=true、production_allowed=false 均匹配。
bridge 对 non-top50 行清空 buy_score/raw_score/score_rank，并设置 ext_buy_ranking_allowed=false。
OrderIntent 字段白名单不含 execution/cash/equity/quantity/target_weight/target_position/broker。
validate_order_intents 检查每日 buy/sell <= 1、buy top50 only、sell rank > 100、holding visibility 不缺失。
forbidden_action_audit 明确禁止 publish/latest/default/frontend/API/Agent/daily/PriceStore/broker/order/quantity。
```

产物 validator：

```text
bridge_ready = true
order_intent_ready = true
ok = true
verdict = PASS_FULL_RANK_VISIBILITY_BRIDGE_AND_ORDER_INTENT_READY_FOR_P3_REPLAY
```

## 9. P3 准入判断

```text
can_enter_p3 = true
```

准入范围限定为：

```text
P3 same-window baseline readonly replay
window = 2026-01-02..2026-05-07
input_order_intent = data_tw/artifacts/strategies/top50_hold_rank_buffer_100/mtrp2_r_20260628T181347Z/manifest.json
input_signal_bridge = data_tw/artifacts/signals/top50_hold_rank_buffer_100_full_rank_visibility_bridge/mtrp2_r_20260628T181347Z/manifest.json
```

P3 必须继续遵守：

```text
readonly_only = true
simulation_only = true
不得训练、调参、重算分数
不得修改 OrderIntent
不得读取 future return / future label / replay return 作为策略输入
不得 provider publish / accepted latest switch / default switch
不得接 broker / quick-trade / real order
```

## 10. 主要风险

1. Lineage 风险：

```text
bridge 仍来自 existing audited broad reference 的 repackaging，源头标记 research_only/diagnostic_only。
本审查只允许它进入 P3 same-window readonly replay，不允许把它解释为 production-ready signal lineage。
```

2. 窗口风险：

```text
当前覆盖只验证 2026-01-02..2026-05-07。
P3 之外的更长窗口、日更 shadow 或未来交易日不能沿用本结论。
```

3. 生产接入风险：

```text
若 P3 通过，也只能得到 same-window replay 证据。
进入 production selectable/default/latest/daily/Agent/frontend 仍需后续 gate、正式 lineage 和 coordinator decision。
```

## 11. 最终结论

```text
verdict = PASS_READY_FOR_P3_SAME_WINDOW_REPLAY_WITH_LINEAGE_WARNING
can_enter_p3 = true
```

MTRP2_R bridge 与 OrderIntent 符合本阶段合同与安全边界，可进入 P3 same-window baseline readonly replay。唯一必须显式带入 P3 的条件是 lineage warning：当前 bridge 是已审计 broad reference 的 production-candidate readiness repackaging，不是 production-ready artifact。
