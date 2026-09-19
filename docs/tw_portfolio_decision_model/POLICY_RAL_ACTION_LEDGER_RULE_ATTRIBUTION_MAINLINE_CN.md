---
created_at: 2026-06-23
status: coordinator_mainline_action_ledger_rule_attribution_v1
scope: after_policy_model_research_route_closure
previous_work_doc: docs/tw_portfolio_decision_model/POLICY_MODEL_RESEARCH_ROUTE_CLOSURE_WORK_CN.md
base_signal_first: frozen_qlib_2018_2022
policy_training_authorized: false
rule_exploration_authorized_after_attribution_only: true
strict_test_authorized_initially: false
readonly_only: true
simulation_only: true
not_order: true
not_investment_advice: true
production_allowed: false
provider_publish_authorized: false
accepted_latest_switch_authorized: false
monitor_write_authorized: false
broker_authorized: false
frontend_default_switch_authorized: false
order_intent_target_weight_allowed: false
---

# RAL Action-level Ledger + Rule Attribution 主线

## 0. 统筹结论

PAL / PBA / PBA-RC policy model research 已经足够说明：

```text
在当前 qlib-only signal、当前 2023-2025 policy window、当前 action space 下，
复杂 ML / RL policy 的稳定超额收益证据不足。
```

但这不等于 policy 层完全没有价值。更合理的下一步不是继续训练模型，而是先补齐：

```text
action-level / symbol-level / daily replay ledger
```

再做：

```text
rule attribution
```

目的：

```text
用细粒度账本回答具体动作到底有没有贡献，
再决定是否值得探索少量可解释规则。
```

本路线命名为：

```text
RAL = Rule Attribution Ledger
```

## 1. 目标

本主线要回答：

```text
在 frozen qlib baseline 下，
每天、每只股票、每个 baseline/action overlay 动作分别贡献了多少收益、成本、换手和风险？

能否从这些细粒度 attribution 中找到少数稳定、可解释、非 baseline-clone 的规则 edge？
```

第一阶段仍使用 qlib-only：

```text
input_signal_artifact =
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json

base qlib train = 2018-2022
analysis train = 2023-01-01..2024-12-31
analysis validation = 2025-01-01..2025-12-31
strict_test = 2026-01-01..2026-05-07, declared only
```

注意：

```text
RAL0/RAL1/RAL2 不训练模型。
RAL3 只允许预声明 rule sanity，不允许机器学习。
strict_test 初始不授权。
```

## 2. 非目标

本主线不授权：

```text
1. 机器学习 / 深度学习 / 强化学习 policy training。
2. PAL / PBA / PBA-RC 同线 repair。
3. strict_test。
4. qlib+orthogonal LTR。
5. provider publish / accepted latest switch。
6. monitor write / frontend default / Agent integration。
7. broker / quick-trade / real order。
8. 生产默认策略切换。
9. OrderIntent target_weight / target_position / quantity。
10. free allocation vector。
```

本路线也不允许：

```text
把低换手、低成本、低回撤当成成功；
把 cash/no-trade 当成成功；
把 gross return 当成成功；
用 validation 反复调规则；
用 strict_test 选规则；
把 attribution 结论直接写成投资建议。
```

## 3. 是否需要新数据

初始阶段不需要引入新外部数据。

RAL 要补的是：

```text
内部 readonly replay 过程中的账本粒度。
```

数据来源应优先使用现有：

```text
1. frozen qlib ModelSignalArtifact。
2. 现有价格 / OHLCV / adjusted price 数据。
3. baseline replay ledger / holdings / cash / trade events。
4. PBA1 baseline snapshot。
5. PBA2/PBA3/PBA-RC 既有 diagnostic action artifact。
6. 现有 fee / sell tax / cost model。
```

只有当现有 replay 无法还原某字段时，才允许标记为：

```text
not_available_in_current_replay
derived_proxy
requires_future_data_contract
```

但不得为本阶段抓取新外部数据、切换 provider、publish latest 或改变生产数据源。

## 4. 核心 Artifact：ActionSymbolDailyLedgerArtifact

RAL 的核心合同是：

```text
ActionSymbolDailyLedgerArtifact
```

用途：

```text
记录每个交易日、每只股票、每个 baseline/policy/rule action 对组合收益、成本、换手和风险的贡献。
```

粒度：

```text
date x symbol x action_source x action_type
```

其中：

```text
action_source:
  baseline
  pba2_rule
  pba3_model_diagnostic
  pba3_r_model_diagnostic
  pba_rc_gate_diagnostic
  ral_rule_candidate_diagnostic

action_type:
  buy
  sell
  hold
  skip_buy
  block_buy
  allow_buy
  allow_sell
  delay_sell
  no_extra_action
  reduce_participation_diagnostic
  active_tilt_diagnostic
```

必需字段建议：

```text
date
symbol
action_source
action_type
baseline_action_type
policy_or_rule_action_type
rank
score
score_gap
score_zscore
holding_before_diagnostic
holding_after_diagnostic
position_value_before_diagnostic
position_value_after_diagnostic
cash_before_diagnostic
cash_after_diagnostic
price_used
price_source
shares_diagnostic
notional_diagnostic
trade_notional_diagnostic
turnover_contribution
fee_contribution
sell_tax_contribution
gross_pnl_contribution
realized_pnl_contribution
unrealized_pnl_contribution
net_pnl_after_fee_tax_contribution
nav_contribution
holding_age
market_regime
volatility_regime
score_dispersion_regime
baseline_state
reason_code
source_signal_artifact
source_replay_artifact
simulation_only = true
readonly_research_only = true
production_allowed = false
```

禁止字段：

```text
target_weight
target_position
quantity
order_size
broker_order
production_order_id
```

如果需要“股数/金额”来还原 replay，只能使用：

```text
shares_diagnostic
notional_diagnostic
trade_notional_diagnostic
```

不得映射为 OrderIntent quantity。

## 5. 为什么要补这个 Ledger

现有模型路线失败后，组合级 summary 不足以回答：

```text
1. block_buy 到底挡掉亏损，还是错过上涨？
2. delay_sell 是延长赢家，还是拖住输家？
3. score_gap_buy_filter 的收益来自少数日期还是多数日期？
4. 成本主要来自 buy、sell、switch 还是无效小额 rebalance？
5. PBA3 的 validation edge 是否集中在少数股票？
6. PBA-RC 的 regime edge 是否只是 no_extra_action / baseline clone？
7. 哪些 symbol / sector / rank bucket 贡献了收益或亏损？
```

Action-level ledger 的目的不是继续训练模型，而是先把这些问题变成可审计事实。

## 6. 阶段计划

## RAL0: Ledger Contract And Replay Mapping Freeze

目标：

```text
冻结 ActionSymbolDailyLedgerArtifact 合同，映射现有 replay/snapshot/action artifact 到 ledger 字段。
```

执行者必须：

```text
1. 阅读本主线和 policy model closure work doc。
2. 盘点现有 baseline / PBA artifacts 能提供哪些字段。
3. 定义 ActionSymbolDailyLedgerArtifact schema。
4. 定义 action_type / action_source / reason_code 枚举。
5. 定义 PnL / cost / turnover attribution 口径。
6. 定义缺失字段标记策略。
7. 设计 validator / golden samples。
8. 不生成大规模 ledger，不跑收益实验。
```

输出：

```text
data_tw/experiments/rule_attribution_ledger/ral0_contract_mapping/
  manifest.json
  source_artifact_inventory.csv
  action_symbol_daily_ledger_schema.json
  action_enum_design.md
  pnl_cost_turnover_attribution_design.md
  missing_field_policy.md
  forbidden_consumer_audit.csv
  validator_design.md
  golden_sample_design.md

docs/tw_portfolio_decision_model/POLICY_RAL0_LEDGER_CONTRACT_MAPPING_EXECUTION_REPORT_CN.md
```

通过条件：

```text
schema 完整；
字段来源清楚；
缺失字段不被伪造；
禁止字段不出现；
reviewer 能据此写 RAL1 ledger build 工作文档。
```

## RAL1: Baseline Action Ledger Build And Parity

只有 RAL0 通过后允许。

目标：

```text
先只构建 baseline 的 action-level / symbol-level / daily ledger，并证明能复现 baseline replay。
```

必须输出：

```text
baseline_action_symbol_daily_ledger.csv
baseline_ledger_parity_metrics.csv
daily_nav_reconciliation.csv
symbol_pnl_reconciliation.csv
cost_turnover_reconciliation.csv
feature_available_at_audit.csv
forbidden_consumer_audit.csv
validator_report.json
golden_samples_report.json
```

关键 parity：

```text
sum(symbol/date net_pnl_after_fee_tax_contribution) ~= baseline replay net PnL
sum(fee_contribution + sell_tax_contribution) ~= replay cost
sum(turnover_contribution) ~= replay turnover
daily NAV path ~= baseline replay NAV path
```

RAL1 不允许：

```text
训练模型；
新增规则；
validation 选规则；
strict_test；
production / OrderIntent。
```

## RAL2: Action Attribution For Existing PBA Evidence

只有 RAL1 通过后允许。

目标：

```text
把 PBA2/PBA3/PBA3-R/PBA-RC 已有 diagnostic actions 映射到 action ledger，
做动作归因，而不是训练或新规则搜索。
```

必须回答：

```text
1. PBA2 score_gap_buy_filter 的 excess 来自哪些 action_type / symbol / date / regime？
2. PBA3 shallow_mlp seed_23 的 validation edge 是否集中在少数 symbol/date？
3. PBA3-R contextual bandit 的 +0.07789642 是否有稳定 action attribution？
4. PBA-RC mid_vol no_extra_action 是否只是 baseline clone？
5. buy_filter / delay_sell / no_extra_action 各自的 net contribution 如何？
6. 成本主要由哪些 action source 和 action type 造成？
```

输出：

```text
data_tw/experiments/rule_attribution_ledger/ral2_existing_pba_action_attribution/
  manifest.json
  pba_action_symbol_daily_ledger.csv
  action_type_contribution_summary.csv
  symbol_contribution_summary.csv
  date_contribution_summary.csv
  regime_action_contribution_summary.csv
  cost_by_action_type.csv
  turnover_by_action_type.csv
  pnl_concentration_by_action.csv
  baseline_clone_action_audit.csv
  attribution_findings.md
  validator_report.json

docs/tw_portfolio_decision_model/POLICY_RAL2_EXISTING_PBA_ACTION_ATTRIBUTION_EXECUTION_REPORT_CN.md
```

通过条件：

```text
attribution 可复现既有 PBA summary；
能解释主要正/负贡献来源；
能明确是否存在值得进入 RAL3 的 rule hypothesis。
```

如果没有明确 rule hypothesis，应 STOP 回到统筹。

## RAL3: Predeclared Rule Attribution Sanity

只有 RAL2 找到明确 rule hypothesis 后允许。

目标：

```text
只测试少量预声明、可解释、由 attribution 支持的规则。
```

候选规则仅限：

```text
score_gap_buy_filter
score_zscore_buy_filter
weak_score_skip_buy
holding_age_sell_delay
trend_confirmed_hold
high_volatility_reduce_new_buy
regime_fallback_to_baseline
```

RAL3 必须先写 rule hypothesis：

```text
rule_id
attribution_evidence
expected_positive_action_type
expected_negative_action_type_to_avoid
expected_cost_effect
expected_failure_mode
```

选择规则：

```text
1. 规则必须预声明。
2. 不得超过 6 个 rule candidates。
3. train/validation 分离。
4. validation 只能一次 selection。
5. primary metric = net_return_after_fee_tax。
6. 不能因为 turnover/cost/drawdown 改善而通过。
```

RAL3 通过条件：

```text
validation net_return_after_fee_tax > baseline
train/validation direction 不显著反转
participation pass
cash dominance pass
not baseline clone
active decision change rate pass
pnl concentration pass
cost/turnover not pathological
strict_test_used=false
```

若 RAL3 通过，也只是：

```text
ready_for_coordinator_to_consider_final-only strict_test work doc
```

不得自动 strict_test。

## RAL4: Optional Final-only Strict-test Rule Replay

只有 RAL3 validation 通过，且统筹另行授权后才允许。

规则：

```text
strict_test final-only；
不得根据 strict_test 改规则；
strict_test 失败则 rule route closure；
strict_test 通过也只进入 readonly research acceptance，不自动 production。
```

## 7. Attribution 指标与 Gate

每轮必须使用 return-first：

```text
primary = net_return_after_fee_tax
```

同时审计：

```text
gross_return
cost_drag
turnover
fee
sell_tax
drawdown
participation_rate
risk_asset_exposure
cash_dominance_rate
active_decision_change_rate
baseline_clone_rate
symbol_pnl_concentration
date_pnl_concentration
action_pnl_concentration
regime_stability
```

不允许通过：

```text
低交易但低收益；
cash/no-trade；
baseline clone；
单日/单股收益集中；
只在 validation 有效、train/fold 方向反转；
成本 proxy 不可还原；
缺失字段被默认填 0 后冒充真实 ledger。
```

## 8. 审查重点

审查者每轮必须检查：

```text
1. 是否没有训练模型。
2. 是否没有 strict_test。
3. 是否没有 OrderIntent / target_weight / target_position / quantity。
4. Ledger 是否能 reconciliation 到 replay summary。
5. 缺失字段是否诚实标记，而不是伪造。
6. attribution 是否区分 baseline contribution 和 active rule contribution。
7. 是否没有把 no_extra_action / baseline clone 解释成 active edge。
8. 是否没有因为低成本或低换手而忽略收益不足。
9. 是否没有用 validation 反复调规则。
10. 是否所有产物仍是 readonly research artifact。
```

## 9. 停止条件

必须停止并回到统筹：

```text
1. RAL0 无法定义安全 ledger 合同。
2. RAL1 ledger 无法复现 baseline replay。
3. action attribution 需要的关键字段无法从现有 replay 还原，且只能靠伪造或外部数据补。
4. attribution 只说明 no_extra_action / baseline clone 有收益。
5. 没有任何明确 rule hypothesis。
6. RAL3 validation 不超过 baseline。
7. 执行者请求 strict_test、训练模型、qlib+LTR 或 production。
```

## 10. RAL0 执行者命令

```text
你是执行者。请启动 RAL Action-level Ledger + Rule Attribution 主线 RAL0。

必须读取：
1. docs/tw_portfolio_decision_model/POLICY_RAL_ACTION_LEDGER_RULE_ATTRIBUTION_MAINLINE_CN.md
2. docs/tw_portfolio_decision_model/POLICY_MODEL_RESEARCH_ROUTE_CLOSURE_WORK_CN.md
3. docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
4. docs/tw_portfolio_decision_model/POLICY_PBA_RC_REGIME_CONDITIONED_ACTIVE_POLICY_DIAGNOSTIC_REVIEW_CN.md
5. docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
6. docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
7. docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
8. docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
9. docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
10. docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md

本轮只做 RAL0：
- 盘点现有 replay / baseline / PBA artifacts 能提供哪些 ledger 字段；
- 定义 ActionSymbolDailyLedgerArtifact schema；
- 定义 action_type / action_source / reason_code 枚举；
- 定义 PnL / cost / turnover attribution 口径；
- 定义缺失字段标记策略；
- 设计 forbidden consumer audit、validator、golden samples；
- 写 RAL0 execution report。

本轮禁止：
- 训练模型；
- 运行收益规则实验；
- 运行或读取 strict_test；
- 输出 OrderIntent；
- 输出 target_weight / target_position / quantity / broker order；
- provider/latest/monitor/frontend/Agent/broker/production 扩权。

artifact root:
data_tw/experiments/rule_attribution_ledger/ral0_contract_mapping/

执行报告：
docs/tw_portfolio_decision_model/POLICY_RAL0_LEDGER_CONTRACT_MAPPING_EXECUTION_REPORT_CN.md
```

## 11. RAL0 审查者命令

```text
你是审查者。请审查 RAL0 执行报告是否符合 RAL 主线。

必须检查：
1. source_artifact_inventory 是否完整；
2. ActionSymbolDailyLedgerArtifact schema 是否覆盖 date/symbol/action/pnl/cost/turnover/regime；
3. 是否明确哪些字段来自现有 replay，哪些是 proxy，哪些缺失；
4. 是否没有 target_weight / target_position / quantity / OrderIntent；
5. attribution 口径是否能支持 RAL1 reconciliation；
6. validator / golden samples 是否覆盖负样本；
7. 是否未训练、未 replay 规则收益、未 strict_test。

审查输出：
docs/tw_portfolio_decision_model/POLICY_RAL0_LEDGER_CONTRACT_MAPPING_REVIEW_CN.md

如果 RAL0 通过，请写 RAL1 baseline ledger build 工作文档。
如果 ledger 合同无法安全定义，请 STOP 回到统筹。
```
