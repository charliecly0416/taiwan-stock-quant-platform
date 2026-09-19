---
created_at: 2026-06-23
status: coordinator_mainline_trace_ledger_explicit_rule_discovery_v2
scope: after_policy_model_closure_and_ral2_no_hypothesis
base_signal_first: frozen_qlib_2018_2022
previous_closure_report: docs/tw_portfolio_decision_model/POLICY_RAL_POLICY_RESEARCH_EXTERNAL_CLOSURE_REPORT_CN.md
previous_ral2_review: docs/tw_portfolio_decision_model/POLICY_RAL2_EXISTING_PBA_ACTION_ATTRIBUTION_REVIEW_CN.md
policy_training_authorized: false
rule_experiment_authorized_initially: false
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

# RAL-ED Action Trace Ledger + Explicit Rule Discovery 主线

## 0. 统筹结论

当前已经完成：

```text
1. PAL / PBA / PBA-RC / RAL2 收尾；
2. 外部可读 closure report；
3. RAL2 existing PBA action attribution；
4. 结论：复杂 ML/RL policy 暂时不应继续，同线 PBA/RAL3 也没有 ready hypothesis。
```

但这不等于规则探索没有价值。

新的方向是：

```text
暂停机器学习；
把精力转向显式规则发现；
先补 Action Trace Ledger；
再做 score / rank / market / holding / cost 的 attribution diagnostic；
再从 attribution 中生成少量预声明规则；
最后用 rolling OOS / regime-isolated validation 严格验证。
```

本路线命名为：

```text
RAL-ED = Rule Attribution Ledger - Explicit Discovery
```

核心原则：

```text
先诊断，后规则；
先 trace，后 attribution；
先预声明，后验证；
先 rolling OOS，后 strict_test；
永远 return-first；
不训练模型。
```

## 1. 为什么现在转向显式规则

当前证据说明：

```text
1. baseline 已经吃掉主要 qlib ranking alpha；
2. ML/RL policy 学的是弱二阶 edge，样本少、regime 依赖强；
3. 复杂模型容易在 2025 validation 找到局部正收益，但 fold/seed/regime 不稳；
4. 强化稳定性后，模型又退化为 baseline clone / no_extra_action；
5. RAL2 证明既有 PBA 信号不能直接归因成 RAL3-ready rule。
```

因此更合理的下一步不是继续训练模型，而是先建立更透明的 trace 账本，再探索：

```text
score 是否存在显式阈值；
score gap / zscore 是否能过滤弱买入；
rank/score 的变化是否能决定买卖节奏；
大盘趋势或波动 regime 是否应该改变参与度；
持仓年龄、趋势、盈利/亏损状态是否影响卖出时点；
交易成本是否能定义最小调仓边际。
```

这些规则不一定正确，但它们是低维、可解释、可审计的假设，适合在当前阶段探索。

## 2. 目标

本主线要回答：

```text
在 frozen qlib baseline 下，
能否为每个偏离 baseline 的动作建立可追踪的 action_trace_id 和 baseline counterfactual；
是否存在少数显式、低维、可解释、非 baseline-clone 的规则，
可以在扣费税后收益上稳定超过 baseline？
```

第一阶段仍使用 qlib-only：

```text
input_signal_artifact =
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json

base qlib train = 2018-2022
rule diagnostic train = 2023-01-01..2024-12-31
rule validation = 2025-01-01..2025-12-31
strict_test = 2026-01-01..2026-05-07, declared only
```

## 3. 非目标

本主线不授权：

```text
1. 机器学习 / 深度学习 / 强化学习。
2. contextual bandit / supervised policy / offline RL。
3. free allocation / target weight。
4. strict_test。
5. qlib+orthogonal LTR。
6. provider publish / accepted latest switch。
7. monitor write / frontend default / Agent integration。
8. broker / quick-trade / real order。
9. 生产默认策略切换。
10. OrderIntent target_weight / target_position / quantity。
```

本路线也不允许：

```text
无界规则网格搜索；
用 validation 反复调阈值；
用低换手、低成本、低回撤替代收益；
cash/no-trade 通过；
baseline clone 通过；
gross return 通过；
单日/单股收益集中通过；
把规则诊断写成投资建议。
```

## 3.1 单日多买/多卖的统筹决策

规则探索不强制限制为：

```text
每天只买一支、只卖一支。
```

原因：

```text
如果规则是 score threshold / score zscore / score gap 导向，
同一天可能同时出现多只股票满足买入阈值，
也可能多只持仓同时跌破卖出或风险阈值。
```

因此 RAL-ED 允许研究：

```text
single_trade_per_day
multi_buy_multi_sell_threshold_driven
```

但多买/多卖只能作为 readonly research replay，不得无约束放开。必须受以下 hard gates 约束：

```text
max_buy_count_per_day
max_sell_count_per_day
max_total_trade_count_per_day
max_daily_turnover
max_period_turnover
max_fee_tax_drag
minimum_score_edge_vs_cost
minimum_position_holding_days, if relevant
cash_dominance_gate
participation_gate
symbol/date pnl concentration gate
```

审查口径：

```text
多买/多卖本身不是错误；
但如果收益主要来自过度换手、成本未被覆盖、或单日/单股集中，则必须失败。
```

通过条件仍然是：

```text
net_return_after_fee_tax > baseline
```

不能用：

```text
命中更多股票
更高 gross return
更高参与度
更低回撤
```

替代扣费税后收益。

## 4. 规则探索域

执行者和审查者不得把本路线局限于下列示例，但所有规则必须属于低维、可解释、PIT-safe 的显式机制。

### 4.1 Score 绝对/相对强度

候选诊断：

```text
score absolute threshold
score percentile / quantile
score zscore
score gap: top candidate 与 next candidate 或 cutoff candidate 的差距
score dispersion: 全市场 score 分化强弱
rank-to-score consistency
```

可能规则假设：

```text
score 不够强时不买；
score gap 不够大时减少买入；
score dispersion 低时降低参与；
score zscore 高才允许替换持仓。
```

### 4.2 Rank / Score 动量与变化

候选诊断：

```text
rank_delta_1d / 5d / rebalance_to_rebalance
score_delta_1d / 5d
rank_improvement_speed
rank_deterioration_speed
score_drop_from_entry
```

可能规则假设：

```text
排名快速上升才允许新买；
持仓排名轻微下降但 score 仍强时延后卖；
排名/score 急剧恶化时优先卖；
排名改善但 score gap 不足时不追。
```

### 4.3 Market / Regime

候选诊断：

```text
market trend: index MA / return / breadth
market volatility regime
risk_off / caution / normal
market drawdown state
score dispersion regime
```

可能规则假设：

```text
risk_off 提高买入 score threshold；
high_volatility 减少新买入；
market uptrend 恢复 baseline；
market downtrend 只允许最强 score candidate；
score dispersion 低时减少换仓。
```

### 4.4 Holding State

候选诊断：

```text
holding_age
entry_score
current_score_vs_entry_score
unrealized_pnl_diagnostic
trend_confirmed_hold
holding_rank_decay
```

可能规则假设：

```text
刚买入未满 N 天不因小幅排名下降卖出；
盈利持仓趋势未破时延后卖；
亏损且 score/rank 恶化时加速卖；
持仓 score 仍高于阈值时不强制换仓。
```

### 4.5 Cost / Turnover / Rebalance Friction

候选诊断：

```text
trade_cost_estimate
expected_score_edge_vs_cost
small_rank_change
same_symbol_reentry_cooldown
turnover_budget_by_period
```

可能规则假设：

```text
score edge 不足以覆盖交易成本时不换；
小幅 rank 变化不触发卖出/买入；
刚卖出股票短期内不重新买入；
高换手窗口提高换仓门槛。
```

## 5. Action Trace Ledger 前置要求

Gemini 外部意见中提出的 Action Trace Ledger 合理，应被吸收为 RAL-ED 的前置基础设施，而不是可选项。

RAL2 的关键限制是：

```text
active changed rows 多数只能做 opportunity proxy 或 summary-level partial attribution；
无法完整还原 active action 的 native trade PnL / cost / turnover。
```

因此 RAL-ED 必须先定义并尽量构建 trace-level ledger。

### 5.1 ActionTraceLedgerArtifact

用途：

```text
为每个偏离 baseline 的干预动作建立 trace，
并尽可能和 baseline counterfactual 对照，
计算该动作的 delta PnL / delta cost / delta turnover。
```

核心粒度：

```text
action_trace_id x date x symbol x intervention_action
```

必需字段：

```text
action_trace_id
baseline_counterfactual_trace_id
trace_source
trace_status
date
symbol
baseline_action_type
intervention_action_type
decision_reason_code
rule_id, if available
score
score_zscore
score_gap
rank
rank_delta
score_delta
holding_age
market_regime
volatility_regime
score_dispersion_regime
price_used
baseline_trade_notional_diagnostic
intervention_trade_notional_diagnostic
baseline_fee_tax_diagnostic
intervention_fee_tax_diagnostic
fee_tax_delta_diagnostic
baseline_turnover_diagnostic
intervention_turnover_diagnostic
turnover_delta_diagnostic
baseline_pnl_after_fee_tax_diagnostic
intervention_pnl_after_fee_tax_diagnostic
delta_pnl_after_fee_tax_diagnostic
attribution_horizon
simulation_only = true
readonly_research_only = true
production_allowed = false
```

`trace_status` 必须显式区分：

```text
native_trace
counterfactual_replay_trace
derived_proxy
summary_level_only
unavailable
```

严禁把 `derived_proxy` 或 `summary_level_only` 冒充为 native trace。

### 5.2 Trace 归因边界

动作级归因必须承认组合交互：

```text
一个 block_buy / delay_sell 会影响现金、后续持仓、后续买卖机会；
并非所有 PnL 都能完全独立隔离。
```

因此报告必须区分：

```text
native realized contribution
counterfactual delta contribution
proxy opportunity attribution
summary-level reconciliation
```

只有以下证据可以支持进入规则实验：

```text
native_trace
counterfactual_replay_trace
```

如果候选规则只依赖：

```text
derived_proxy
summary_level_only
```

则不得进入 RAL-ED2 规则 sanity。

## 6. 与 RAL 的衔接

RAL2 的限制是：

```text
existing PBA action 不能形成 RAL3-ready hypothesis；
部分 attribution 仍是 summary-level partial reconciliation。
```

RAL-ED 不直接复用 PBA3 模型结果，也不把 PBA3 validation signal 当规则。

RAL-ED 使用 RAL 的 ledger 思想，但新路线要先做：

```text
Action Trace Ledger contract / build feasibility
score / rank / regime / holding / cost attribution diagnostic
```

而不是直接跑规则。

## 7. 阶段计划

## RAL-ED0: Action Trace Ledger And Rule Discovery Contract

目标：

```text
冻结 Action Trace Ledger、显式规则发现诊断域、候选假设模板、rolling OOS 设计和禁止事项。
```

执行者必须：

```text
1. 阅读本主线、外部 closure report、RAL2 review。
2. 定义 ActionTraceLedgerArtifact schema。
3. 盘点现有 replay 是否支持 action_trace_id / counterfactual trace。
4. 定义 trace_status 与 native/proxy/unavailable 标记。
5. 定义 score / rank / market / holding / cost diagnostic schema。
6. 定义 rule hypothesis template。
7. 定义 multi-buy/multi-sell 的成本/换手/交易数 gate。
8. 定义 rolling OOS / regime validation 口径。
9. 定义 no-grid-search 约束。
10. 定义 validator / golden samples。
11. 不跑规则收益，不训练模型，不 strict_test。
```

输出：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/
  manifest.json
  action_trace_ledger_schema.json
  trace_status_policy.md
  existing_replay_trace_support_audit.csv
  diagnostic_feature_schema.json
  explicit_rule_hypothesis_template.md
  candidate_diagnostic_domains.md
  multi_trade_gate_design.md
  rolling_oos_design.md
  regime_validation_design.md
  no_grid_search_policy.md
  forbidden_consumer_audit.csv
  validator_design.md
  golden_sample_design.md

docs/tw_portfolio_decision_model/POLICY_RAL_ED0_EXPLICIT_RULE_DISCOVERY_CONTRACT_EXECUTION_REPORT_CN.md
```

通过条件：

```text
ActionTraceLedgerArtifact schema 完整；
trace_status 语义清楚；
existing replay 支持/不支持哪些 trace 字段被诚实盘点；
diagnostic domains 完整；
rule hypothesis template 可审查；
multi-trade gates 可执行；
rolling OOS 设计明确；
forbidden actions 完整；
reviewer 能据此写 RAL-ED1 工作文档。
```

## RAL-ED1: Score / Rank / Regime / Holding Attribution Diagnostic

只有 RAL-ED0 通过后允许。

目标：

```text
不跑新规则，只构建/审计 trace-level attribution，并做 score/rank/regime/holding/cost 归因诊断，
寻找是否存在值得预声明规则的显式规律。
```

必须输出：

```text
action_trace_ledger_sample.csv
trace_support_audit.csv
counterfactual_delta_attribution_audit.csv
score_bucket_return_attribution.csv
score_gap_bucket_attribution.csv
score_zscore_bucket_attribution.csv
rank_delta_attribution.csv
score_delta_attribution.csv
market_regime_action_attribution.csv
volatility_regime_action_attribution.csv
holding_age_sell_attribution.csv
entry_score_hold_attribution.csv
cost_edge_attribution.csv
candidate_rule_hypothesis_audit.csv
diagnostic_findings.md
validator_report.json
```

必须回答：

```text
1. 现有 replay 是否能生成 native action_trace_id？
2. 哪些动作只能 derived_proxy / summary_level_only？
3. score 绝对值或 zscore 与后续净贡献是否单调或分层明显？
4. score gap 小的 baseline buy 是否贡献负收益？
5. rank/score 快速下降是否对应卖出收益改善？
6. rank 下降但 score 仍强的持仓，延后卖是否可能有利？
7. risk_off/high_vol 中 baseline buy 是否集中亏损？
8. holding age 是否影响卖出时点？
9. trade cost 是否能定义最小 score edge？
10. threshold-driven multi-buy/multi-sell 是否可能提高收益，还是主要增加成本？
11. 是否存在至少一个可预声明、低维、非模型化 rule hypothesis？
```

通过条件：

```text
至少一个候选 hypothesis 满足：
  attribution evidence clear；
  train/validation 或 subwindow 方向不明显反转；
  trace evidence 至少达到 counterfactual_replay_trace；
  非 no_extra_action / 非 baseline clone；
  可预声明；
  不需要 ML 模型；
  不需要 target_weight / quantity。
```

如果没有，STOP 回统筹，不得进入 RAL-ED2。

## RAL-ED2: Predeclared Explicit Rule Sanity

只有 RAL-ED1 通过后允许。

目标：

```text
只测试少量由 RAL-ED1 attribution 支持的预声明规则。
```

规则数量限制：

```text
最多 6 个 rule candidates。
每个 rule candidate 最多 2 个预声明阈值版本。
不得无界网格搜索。
```

交易数量限制必须预声明：

```text
max_buy_count_per_day
max_sell_count_per_day
max_total_trade_count_per_day
max_daily_turnover
max_period_turnover
max_fee_tax_drag
```

允许规则族：

```text
score_threshold_buy_filter
score_zscore_buy_filter
score_gap_buy_filter
rank_delta_buy_confirmation
rank_score_deterioration_sell
score_still_strong_sell_delay
high_vol_no_new_buy
risk_off_raise_buy_threshold
small_rank_change_no_rebalance
same_symbol_reentry_cooldown
threshold_multi_buy_filter
threshold_multi_sell_filter
```

每个 rule 必须包含：

```text
rule_id
rule_family
predeclared_thresholds
attribution_evidence_from_RAL_ED1
expected_positive_effect
expected_failure_mode
allowed_action_types
max_trade_count_per_day
turnover_budget
fee_tax_budget
forbidden_outputs
```

通过条件：

```text
validation net_return_after_fee_tax > baseline
train/validation direction 不明显反转
rolling OOS average excess > 0
participation pass
cash dominance pass
not baseline clone
active decision change rate pass
symbol/date PnL concentration pass
cost/turnover not pathological
multi-trade cost budget pass, if applicable
strict_test_used=false
```

若通过，仅表示：

```text
ready_for_coordinator_to_consider_RAL_ED3_final_only_strict_test
```

不得自动 strict_test。

## RAL-ED3: Optional Final-only Strict-test Rule Replay

只有 RAL-ED2 通过，且统筹另行授权后才允许。

规则：

```text
strict_test final-only；
不得根据 strict_test 改规则；
strict_test 失败则 closure；
strict_test 通过也只进入 readonly research acceptance，不自动 production。
```

## 8. Rolling OOS 要求

RAL-ED2 起必须使用 rolling OOS，而不是只用单一 2025 validation。

建议最小设计：

```text
train window: 12 months
validation/test window: next 3 months
step: 3 months
coverage: 2023-2025
```

如果数据不足，执行者必须报告：

```text
rolling_oos_insufficient_data
```

不得用单一窗口冒充 rolling OOS。

## 9. 通过/失败解释标准

成功必须是：

```text
after-fee-tax return improvement；
active rule contribution；
non-clone；
non-cash/no-trade；
not concentrated in one date/symbol；
multi-window direction acceptable。
multi-buy/multi-sell, if enabled, improves net return after cost。
```

失败包括：

```text
只降低换手但收益低；
只在 validation 有效；
只来自 no_extra_action；
只来自 baseline clone；
只来自单日/单股；
阈值靠 validation 反复调出来；
需要模型才能解释；
需要 target_weight / quantity。
多买/多卖只提高 gross return 但 after-cost 失败；
多买/多卖导致 turnover 或 fee/tax drag 失控。
```

## 10. 审查者总则

审查者必须严格执行：

```text
1. 没有 RAL-ED0，不得 RAL-ED1。
2. 没有 RAL-ED1 明确 hypothesis，不得 RAL-ED2。
3. 没有 RAL-ED2 validation + rolling OOS 通过，不得 RAL-ED3。
4. 审查者不得擅自授权 strict_test。
5. 审查者不得把“看起来有趣的规则”改写成工作文档。
6. 审查者必须阻止无界阈值搜索。
7. 审查者必须检查所有字段 PIT-safe。
8. 审查者必须检查没有 target_weight / quantity / OrderIntent。
9. 审查者必须检查 trace_status，禁止把 proxy 当 native trace。
10. 审查者必须检查 multi-trade gates，禁止无约束多买/多卖。
```

## 11. 停止条件

必须停止并回统筹：

```text
1. diagnostic feature 无法 PIT-safe 构造。
2. Action Trace Ledger 无法区分 native/counterfactual/proxy/summary。
3. 候选规则只能依赖 summary-level proxy。
4. score/rank/regime/holding attribution 没有明确 rule hypothesis。
5. candidate hypothesis 需要 validation 反复调参。
6. rule sanity 不超过 baseline。
7. rolling OOS 方向反转。
8. active decision change rate 太低。
9. 收益集中在单日/单股。
10. 规则退化为 cash/no-trade 或 baseline clone。
11. multi-buy/multi-sell 导致 turnover/cost 失控。
12. 执行者请求训练模型、strict_test、qlib+LTR 或 production。
```

## 12. RAL-ED0 执行者命令

```text
你是执行者。请启动 RAL-ED Explicit Rule Discovery 主线 RAL-ED0。

必须读取：
1. docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
2. docs/tw_portfolio_decision_model/POLICY_RAL_POLICY_RESEARCH_EXTERNAL_CLOSURE_REPORT_CN.md
3. docs/tw_portfolio_decision_model/POLICY_RAL2_EXISTING_PBA_ACTION_ATTRIBUTION_REVIEW_CN.md
4. docs/tw_portfolio_decision_model/POLICY_RAL_ACTION_LEDGER_RULE_ATTRIBUTION_MAINLINE_CN.md
5. docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
6. docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
7. docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
8. docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
9. docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
10. docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md

本轮只做 RAL-ED0：
- 定义 ActionTraceLedgerArtifact schema；
- 盘点现有 replay 是否支持 action_trace_id / baseline_counterfactual_trace_id；
- 定义 native / counterfactual / proxy / summary / unavailable 的 trace_status policy；
- 定义 score / rank / market / holding / cost diagnostic schema；
- 定义 explicit rule hypothesis template；
- 定义 candidate diagnostic domains；
- 定义 threshold-driven multi-buy/multi-sell 的交易数、换手、成本 gate；
- 定义 rolling OOS / regime validation 设计；
- 定义 no-grid-search policy；
- 设计 validator / golden samples；
- 写 RAL-ED0 execution report。

本轮禁止：
- 跑规则收益；
- 训练模型；
- 运行或读取 strict_test；
- 输出 OrderIntent；
- 输出 target_weight / target_position / quantity / broker order；
- provider/latest/monitor/frontend/Agent/broker/production 扩权。

artifact root:
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/

执行报告：
docs/tw_portfolio_decision_model/POLICY_RAL_ED0_EXPLICIT_RULE_DISCOVERY_CONTRACT_EXECUTION_REPORT_CN.md
```

## 13. RAL-ED0 审查者命令

```text
你是审查者。请审查 RAL-ED0 执行报告是否符合 RAL-ED 主线。

必须检查：
1. action_trace_ledger_schema 是否覆盖 action_trace_id / baseline_counterfactual_trace_id；
2. trace_status_policy 是否能区分 native / counterfactual / proxy / summary / unavailable；
3. existing_replay_trace_support_audit 是否诚实说明现有 replay 支持边界；
4. diagnostic_feature_schema 是否覆盖 score/rank/regime/holding/cost；
5. explicit_rule_hypothesis_template 是否能阻止事后编规则；
6. multi_trade_gate_design 是否能约束单日多买/多卖的换手和成本；
7. rolling_oos_design 是否明确；
8. no_grid_search_policy 是否可执行；
9. validator / golden samples 是否覆盖 negative cases；
10. 是否未训练、未跑规则收益、未 strict_test；
11. 是否没有 target_weight / target_position / quantity / OrderIntent。

审查输出：
docs/tw_portfolio_decision_model/POLICY_RAL_ED0_EXPLICIT_RULE_DISCOVERY_CONTRACT_REVIEW_CN.md

如果 RAL-ED0 通过，请写 RAL-ED1 attribution diagnostic 工作文档。
如果合同或 PIT-safe 设计不清楚，请 STOP 回统筹。
```
