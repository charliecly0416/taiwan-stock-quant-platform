# Phase 2D Orthogonal Rule Closure 执行报告

- 生成时间：`2026-06-11T11:14:37+00:00`
- 执行范围：只读汇总 Phase2C 冻结规则卡与审查工作文档，对正交特征规则探索做收尾归档。
- 禁止范围：未继续调参、未重新计算规则样本、未联网、未使用 token、未重拉数据、未新增数据源、未月营收、未训练模型、未 Risk Filter Model、未写 provider、未 refresh/publish、未 accepted latest switching、未前端/API、未 monitor 写入、未交易相关操作。
- orthogonal_rule_exploration_closed=true
- manual_rule_cards_frozen=true
- phase3_allowed=false
- risk_filter_model_training_allowed=false
- frontend_api_integration_allowed=false
- provider_write_allowed=false
- accepted_latest_switching_allowed=false
- trading_or_order_allowed=false
- requires_user_decision_for_new_direction=true

## 1. 输入与边界

- 输入只使用：
  - `docs/tw_decision_model_orthogonal/PHASE2C_MANUAL_RULE_FREEZE_EXECUTION_REPORT_CN.md`
  - `data_tw/experiments/decision_orthogonal/phase2c_manual_rule_cards.json`
  - `data_tw/experiments/decision_orthogonal/phase2c_manual_rule_freeze_summary.json`
  - `docs/tw_decision_model_orthogonal/PHASE2C_MANUAL_RULE_FREEZE_REVIEW_AND_PHASE2D_CLOSURE_WORK_CN.md`
- 本阶段没有读取样本 parquet，没有重新计算规则样本，没有新增字段、数据源或参数搜索。
- Phase2D 是 closure 阶段，不是继续探索阶段。

## 2. 最终冻结规则清单

| rule_id | final_status | baseline_group | selected_20d_mean | baseline_20d_mean | selected_20d_downside_q10 | baseline_20d_downside_q10 | coverage_days | reverse_years |
|---|---|---|---|---|---|---|---|---|
| margin_crowding_top50_p85_caution | manual_caution_explanation | baseline_top50 | 0.013156 | 0.025458 | -0.116822 | -0.114664 | 1063.000000 | ['2025'] |
| flow_crowding_conflict_top50_p80_weak30_review | manual_review_explanation | baseline_top50 | 0.008129 | 0.025458 | -0.107884 | -0.114664 | 797.000000 | ['2025'] |
| foreign_flow_non_crowded_top150_explanation | manual_explanation_feature | baseline_top150 | 0.025422 | 0.020705 | -0.105842 | -0.113525 | 1063.000000 | [] |
| margin_change_non_crowded_top150_auxiliary | manual_auxiliary_feature | baseline_top150 | 0.033365 | 0.020705 | -0.113039 | -0.113525 | 1063.000000 | [] |

## 3. 不能进入 Phase3 的原因

- Phase2B `pass_count=0`。
- 主 caution 规则 `margin_crowding_top50_p85_caution` 存在 2025 反向，且 downside q10 未优于 baseline。
- 主 review 规则 `flow_crowding_conflict_top50_p80_weak30_review` coverage 较窄，只有 797 days，且存在 2025 反向。
- `foreign_flow_non_crowded_top150_explanation` 和 `margin_change_non_crowded_top150_auxiliary` 不计入模型 gate。
- 当前结果只支持人工研究解释规则卡，不支持 Risk Filter Model 训练。

## 4. PIT Caveat

- `available_at = next_trading_day(trade_date)` 是 conservative visibility proxy，不是官方发布时间证明。
- 后续任何引用这些规则卡的环节，都必须保留该 caveat。
- 本阶段没有重新解释该 proxy，也没有将其包装为官方公告时间。

## 5. 只读安全边界

- 不是交易建议。
- 不是买入/卖出信号。
- 不是目标仓位。
- 不是收益承诺。
- 不是上涨概率承诺。
- 不触发订单、broker、quick-trade、monitor config save、monitor scan 或 alerts write。
- 不支持 provider 写入、accepted latest switching、前端/API 接入或任何交易路径。

## 6. 产物

- Closure report：`docs/tw_decision_model_orthogonal/PHASE2D_ORTHOGONAL_RULE_CLOSURE_REPORT_CN.md`
- Closure summary JSON：`data_tw/experiments/decision_orthogonal/phase2d_orthogonal_rule_closure_summary.json`
- 只读整理脚本：`scripts/summarize_tw_decision_orthogonal_phase2d_closure.py`

## 7. 结论

- `orthogonal_rule_exploration_closed=true`
- `manual_rule_cards_frozen=true`
- `requires_user_decision_for_new_direction=true`
- 本轮正交特征规则探索到 Phase2C/Phase2D 收尾为止，不得自动开启 Phase3 或任何新方向。

## 8. 风险与待审查问题

- 规则卡可用于后续人工复盘引用，但不能被误用为自动模型训练证据。
- 后续若要训练模型、接入前端/API、写 provider、切换 accepted latest、引入新数据源或输出交易含义，必须作为新方向提交用户确认。
