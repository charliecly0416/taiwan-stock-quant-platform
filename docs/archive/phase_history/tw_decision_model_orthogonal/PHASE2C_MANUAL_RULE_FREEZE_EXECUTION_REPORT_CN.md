# Phase 2C Manual Rule Freeze 执行报告

- 生成时间：`2026-06-11T11:06:06+00:00`
- 执行范围：只读整理 Phase2B 规则产物，冻结人工研究解释规则卡。
- 禁止范围：未联网、未使用 token、未重拉数据、未新增数据源、未月营收、未训练模型、未 Risk Filter Model、未写 provider、未 refresh/publish、未 accepted latest switching、未前端/API、未 monitor 写入、未交易相关操作。
- phase3_allowed=false
- risk_filter_model_training_allowed=false
- provider_write_allowed=false
- accepted_latest_switching_allowed=false
- trading_or_order_allowed=false
- manual_rules_ready_for_later_review=true
- stop_before_phase3=true

## 1. 输入与边界

- 输入只使用 Phase2B 产物：
  - `data_tw/experiments/decision_orthogonal/phase2b_rules_definitions.json`
  - `data_tw/experiments/decision_orthogonal/phase2b_rules_group_metrics.csv`
  - `data_tw/experiments/decision_orthogonal/phase2b_rules_turnover_summary.csv`
  - `data_tw/experiments/decision_orthogonal/phase2b_rules_candidate_comparison.csv`
  - `data_tw/experiments/decision_orthogonal/phase2b_rules_gate_summary.json`
- 本阶段没有读取样本 parquet，没有重新计算规则样本，没有新增字段或数据源。
- Phase2B gate：`request_phase2c_manual_rule_freeze=true`。
- Phase2C 只冻结人工解释规则，不进入 Phase3。

## 2. 冻结规则卡

| rule_id | status | baseline_group | selected_20d_mean | baseline_20d_mean | selected_20d_downside_q10 | baseline_20d_downside_q10 | coverage_days | reverse_years |
|---|---|---|---|---|---|---|---|---|
| margin_crowding_top50_p85_caution | manual_caution_explanation | baseline_top50 | 0.013156 | 0.025458 | -0.116822 | -0.114664 | 1063.000000 | ['2025'] |
| flow_crowding_conflict_top50_p80_weak30_review | manual_review_explanation | baseline_top50 | 0.008129 | 0.025458 | -0.107884 | -0.114664 | 797.000000 | ['2025'] |
| foreign_flow_non_crowded_top150_explanation | manual_explanation_feature | baseline_top150 | 0.025422 | 0.020705 | -0.105842 | -0.113525 | 1063.000000 | [] |
| margin_change_non_crowded_top150_auxiliary | manual_auxiliary_feature | baseline_top150 | 0.033365 | 0.020705 | -0.113039 | -0.113525 | 1063.000000 | [] |

## 3. 规则用途与禁止用途

- `margin_crowding_top50_p85_caution`：冻结为 `manual_caution_explanation`，用于人工解释 Top50 中融资余额相对拥挤。必须同时提示 2025 反向，以及 downside q10 未优于 baseline。
- `flow_crowding_conflict_top50_p80_weak30_review`：冻结为 `manual_review_explanation`，用于人工解释融资拥挤但外资/自营商流向偏弱的冲突状态。必须同时提示 2025 反向、coverage 只有 797 days，不能单独作为模型 gate。
- `foreign_flow_non_crowded_top150_explanation`：冻结为 `manual_explanation_feature`，只解释非拥挤条件下外资流入背景，不得升级为 confirmed watch。
- `margin_change_non_crowded_top150_auxiliary`：冻结为 `manual_auxiliary_feature`，只作为辅助确认，不得单独输出强研究状态。

每张规则卡均明确：不是交易建议、不是买入/卖出信号、不是目标仓位、不是收益承诺、不是上涨概率承诺，不触发订单、broker、quick-trade 或 monitor 写入。

## 4. Point-in-Time 说明

- Phase2C 不新增 PIT 逻辑，只继承 Phase1B repaired full 与 Phase2B 的只读产物。
- `available_at = next_trading_day(trade_date)` 仍是 conservative visibility proxy，不是官方发布时间证明。
- 本阶段没有重新解释该 proxy，也没有把它包装为官方公告时间。

## 5. 产物

- 规则卡：`data_tw/experiments/decision_orthogonal/phase2c_manual_rule_cards.json`
- freeze summary：`data_tw/experiments/decision_orthogonal/phase2c_manual_rule_freeze_summary.json`
- 执行报告：`docs/tw_decision_model_orthogonal/PHASE2C_MANUAL_RULE_FREEZE_EXECUTION_REPORT_CN.md`
- 只读整理脚本：`scripts/freeze_tw_decision_orthogonal_phase2c_manual_rules.py`

## 6. 结论

- `manual_rules_ready_for_later_review=true`
- `stop_before_phase3=true`
- 当前证据只支持人工研究解释规则卡，不支持 Phase3、Risk Filter Model 训练、前端/API 接入、provider 写入或任何交易路径。

## 7. 风险与待审查问题

- 主 caution 规则仍存在 2025 反向，且 downside q10 未优于 baseline。
- 主 review 规则 coverage 较窄，不能单独作为模型 gate。
- explanation/auxiliary 两类字段不得被后续误升级为 confirmed watch 或强研究状态。
