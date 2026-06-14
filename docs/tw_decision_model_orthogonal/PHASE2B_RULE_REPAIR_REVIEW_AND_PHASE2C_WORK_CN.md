# Phase 2B Rule Repair 审查结论与 Phase 2C Manual Rule Freeze 工作文档

审查日期：2026-06-11

审查入口：

- `docs/tw_decision_model_orthogonal/PHASE2B_RULE_REPAIR_EXECUTION_REPORT_CN.md`

关联依据：

- `docs/tw_decision_model_orthogonal/PHASE2_RULES_BASELINE_REVIEW_AND_PHASE2B_WORK_CN.md`
- `docs/tw_decision_model_orthogonal/REVIEWER_PROMPT_CN.md`
- `docs/TW_STOCK_DECISION_ORTHOGONAL_DATA_MODEL_PLAN_CN.md`

审查产物：

- `scripts/run_tw_decision_orthogonal_phase2b_rule_repair.py`
- `data_tw/experiments/decision_orthogonal/phase2b_rules_definitions.json`
- `data_tw/experiments/decision_orthogonal/phase2b_rules_group_metrics.csv`
- `data_tw/experiments/decision_orthogonal/phase2b_rules_segment_metrics.csv`
- `data_tw/experiments/decision_orthogonal/phase2b_rules_turnover_summary.csv`
- `data_tw/experiments/decision_orthogonal/phase2b_rules_candidate_comparison.csv`
- `data_tw/experiments/decision_orthogonal/phase2b_rules_gate_summary.json`

## 1. 本步审核结论

Phase 2B Rule Repair 主线范围通过，只读安全边界通过。

执行者没有偏离主线，也没有新增分支：

- 只读取 Phase1B repaired full 与 Phase2 rules 产物。
- 未联网。
- 未使用 token。
- 未重拉数据。
- 未新增数据源。
- 未月营收。
- 未训练模型。
- 未执行 Risk Filter Model。
- 未写 provider。
- 未 provider refresh/publish。
- 未 accepted latest switching。
- 未前端/API。
- 未触碰交易路径。

Gate 结论接受：

- `request_phase2c_manual_rule_freeze=true`

不允许进入 Phase3。

理由：

- Phase2B 没有任何规则通过进入模型训练所需的 gate，`pass_count=0`。
- 若干规则具备人工解释价值，但仍存在 2025 反向或 coverage 偏窄问题。
- 当前证据只能支持冻结为人工研究解释规则，不能支持自动模型训练或上线。

## 2. 主线一致性审查

通过项：

- Phase2B 沿用 Phase2B 工作文档限定的“小范围、可解释规则修正”。
- 候选阈值固定且少量：融资拥挤 `0.85/0.90`、Top20/30/50、弱流向 `0.30`。
- 没有大规模参数搜索。
- 没有把规则修复伪装成模型训练。
- 输出仍然是 research status，不是交易动作。
- 报告明确说明 historical positive rate 只是历史样本统计，不代表未来胜率或收益承诺。

未发现偏离主线或新增分支。

## 3. 关键规则审查

### 3.1 可冻结为人工 caution 的风险规则

`margin_crowding_top50_p85_caution`：

- selected 20d mean：`0.013156`
- excluded 20d mean：`0.027508`
- baseline Top50 20d mean：`0.025458`
- selected downside q10：`-0.116822`
- baseline downside q10：`-0.114664`
- coverage days：`1063`
- year direction share：`0.8`
- reverse years：`2025`
- `passes_phase2b_gate_check=false`
- `eligible_manual_freeze=true`

审查判断：

- 可以作为人工 caution 解释规则候选。
- 不能作为模型训练 gate 通过证据。
- 必须在规则卡中写明 2025 反向，以及 downside q10 未优于 baseline。

`margin_crowding_top50_p90_caution`：

- selected 20d mean 与 p85 接近。
- downside q10 更差：`-0.119976`。
- 同样存在 2025 反向。

审查判断：

- 可作为 p85 的严阈值对照，不建议作为主冻结规则。

Top30/Top20 融资拥挤版本：

- coverage 更窄。
- downside q10 更差。
- 仍存在 2025 反向。

审查判断：

- 不建议作为主冻结规则，只可作为附录对照。

### 3.2 可冻结为人工 review 的冲突规则

`flow_crowding_conflict_top50_p80_weak30_review`：

- selected 20d mean：`0.008129`
- excluded 20d mean：`0.026088`
- baseline Top50 20d mean：`0.025458`
- selected downside q10：`-0.107884`
- baseline downside q10：`-0.114664`
- coverage days：`797`
- reverse years：`2025`
- `passes_phase2b_gate_check=false`
- `eligible_manual_freeze=true`

审查判断：

- 有人工 review 价值，尤其适合表达“融资拥挤且外资/自营商流向偏弱”的冲突标签。
- coverage 窄于 margin crowding，不能作为单独模型 gate。
- 必须写明 2025 反向和 coverage 限制。

`flow_crowding_conflict_top50_p85_weak30_review`：

- coverage 更窄，selected mean 略高于 p80 版本。
- downside q10 略优。

审查判断：

- 可作为 p80 版本的严阈值对照，不建议优先冻结为主规则。

### 3.3 仅保留解释或辅助

`foreign_flow_non_crowded_top150_explanation`：

- selected 20d mean：`0.025422`
- baseline Top150 20d mean：`0.020705`
- year direction share：`1.0`
- `counts_for_gate=false`
- `eligible_manual_freeze=false`

审查判断：

- 降级为 explanation feature 是正确的。
- 不得恢复为 confirmed watch。
- 可解释为“非拥挤条件下外资流入背景”，不能作为风险过滤或买卖含义。

`margin_change_non_crowded_top150_auxiliary`：

- selected 20d mean：`0.033365`
- baseline Top150 20d mean：`0.020705`
- year direction share：`1.0`
- `counts_for_gate=false`
- `eligible_manual_freeze=false`

审查判断：

- 只能作为辅助确认。
- 不能独立支撑 Phase3。

## 4. 数据与 PIT 审查

通过项：

- 输入沿用 `phase1b_repaired_full_samples.parquet`。
- Phase2B 未新增字段。
- 法人/融资字段仍沿用 Phase1B 的 PIT 可见性约束。
- repaired qlib prediction 已在 Phase1B 修复阶段通过 asof-aware 审查。

继续注意：

- `available_at = next_trading_day(trade_date)` 仍是 conservative visibility proxy，不是官方发布时间证明。
- Phase2C 不得重新解释为官方发布时间证明。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：无。

### Network Audit

未联网，未下载，未调用外部 API。

### Console Audit

未发现 provider refresh/publish、accepted latest switching、monitor config save、monitor scan、alerts write、broker、quick-trade、orders、target position 或 target weight 证据。

### Text / Agent Semantics

报告中的 `watch`、`review`、`caution` 均用于研究解释状态；报告明确写明 historical positive rate 不是未来胜率或收益承诺。

### Verdict

只读研究边界通过。

## 6. 是否需要停下来讨论

当前不需要停下来要求用户确认。

理由：

- Phase2C Manual Rule Freeze 是 Phase2B gate 给出的保守下一步。
- Phase2C 不涉及联网、数据重拉、新数据源、模型训练、provider 写入、accepted latest switching、前端/API 或交易路径。
- Phase2C 的目标是冻结人工解释规则，并明确停止 Phase3，不改变主目标。

若执行者希望进入模型训练、引入新数据、做月营收、接前端/API、写 provider、切换 accepted latest 或输出交易含义，必须停止并回报。

## 7. 给执行者的下一步工作文档：Phase 2C Manual Rule Freeze

### 7.1 目标

将 Phase2B 中有人工解释价值的规则冻结为只读研究规则卡，形成后续人工复盘可引用的解释标签。

Phase2C 不是模型阶段，不得训练 Risk Filter Model，不得进入 Phase3。

### 7.2 输入

只允许使用：

- `docs/tw_decision_model_orthogonal/PHASE2B_RULE_REPAIR_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/decision_orthogonal/phase2b_rules_definitions.json`
- `data_tw/experiments/decision_orthogonal/phase2b_rules_group_metrics.csv`
- `data_tw/experiments/decision_orthogonal/phase2b_rules_segment_metrics.csv`
- `data_tw/experiments/decision_orthogonal/phase2b_rules_turnover_summary.csv`
- `data_tw/experiments/decision_orthogonal/phase2b_rules_candidate_comparison.csv`
- `data_tw/experiments/decision_orthogonal/phase2b_rules_gate_summary.json`

不得新增数据源，不得重新拉取数据。

### 7.3 允许产物

必须新增：

- `docs/tw_decision_model_orthogonal/PHASE2C_MANUAL_RULE_FREEZE_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/decision_orthogonal/phase2c_manual_rule_cards.json`
- `data_tw/experiments/decision_orthogonal/phase2c_manual_rule_freeze_summary.json`

如确有必要，可新增只读整理脚本：

- `scripts/freeze_tw_decision_orthogonal_phase2c_manual_rules.py`

脚本只能读 Phase2B 产物，只能写 Phase2C 专用输出。

### 7.4 必须冻结的内容

至少输出以下规则卡：

1. 主 caution 规则候选
   - rule_id：`margin_crowding_top50_p85_caution`
   - status：`manual_caution_explanation`
   - condition：`top50_flag and margin_balance_20d_mean_cs_rank_pct >= 0.85`
   - 用途：人工解释“Top50 中融资余额相对拥挤”。
   - 必须 caveat：2025 反向，downside q10 未优于 baseline。

2. 主 review 规则候选
   - rule_id：`flow_crowding_conflict_top50_p80_weak30_review`
   - status：`manual_review_explanation`
   - condition：`top50_flag and margin_balance_20d_mean_cs_rank_pct >= 0.80 and foreign_net_buy_20d_sum_cs_rank_pct <= 0.30 and dealer_net_buy_20d_sum_cs_rank_pct <= 0.30`
   - 用途：人工解释“融资拥挤但法人/自营商流向偏弱的冲突状态”。
   - 必须 caveat：2025 反向，coverage 只有 `797` days，不能单独作为模型 gate。

3. explanation feature
   - rule_id：`foreign_flow_non_crowded_top150_explanation`
   - status：`manual_explanation_feature`
   - 用途：只解释非拥挤条件下外资流入背景。
   - 禁止：不得升级为 confirmed watch。

4. auxiliary feature
   - rule_id：`margin_change_non_crowded_top150_auxiliary`
   - status：`manual_auxiliary_feature`
   - 用途：只作为辅助确认。
   - 禁止：不得单独输出强研究状态。

### 7.5 规则卡字段要求

每条规则卡至少包含：

- `rule_id`
- `status`
- `condition`
- `baseline_group`
- `intended_use`
- `not_intended_use`
- `key_metrics`
- `known_caveats`
- `pit_note`
- `readonly_safety_note`

`not_intended_use` 必须明确写：

- 不是交易建议。
- 不是买入/卖出信号。
- 不是目标仓位。
- 不是收益承诺。
- 不是上涨概率承诺。
- 不触发订单、broker、quick-trade 或 monitor 写入。

### 7.6 必须写入报告的审查结论

Phase2C 报告必须明确写：

- `phase3_allowed=false`
- `risk_filter_model_training_allowed=false`
- `provider_write_allowed=false`
- `accepted_latest_switching_allowed=false`
- `trading_or_order_allowed=false`
- `manual_rules_ready_for_later_review=true`
- `stop_before_phase3=true`

### 7.7 禁止事项

Phase2C 禁止：

- 训练模型。
- 执行 Risk Filter Model。
- 新增特征或新数据源。
- 月营收。
- 联网或使用 token。
- provider refresh/publish。
- accepted latest switching。
- 前端/API 接入。
- monitor config save。
- monitor scan。
- alerts write。
- broker、quick-trade、orders。
- target position 或 target weight。
- 输出买入/卖出建议。
- 输出收益承诺或上涨概率承诺。

### 7.8 完成标准

Phase2C 完成后，执行者只提交：

- Phase2C 执行报告。
- Phase2C rule cards JSON。
- Phase2C freeze summary JSON。
- 如有脚本，提交只读整理脚本。

完成后等待审查者审核，不得自动进入 Phase3。
