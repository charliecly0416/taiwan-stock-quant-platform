# Phase 2C Manual Rule Freeze 审查结论与 Phase 2D Closure 工作文档

审查日期：2026-06-11

审查入口：

- `docs/tw_decision_model_orthogonal/PHASE2C_MANUAL_RULE_FREEZE_EXECUTION_REPORT_CN.md`

关联依据：

- `docs/tw_decision_model_orthogonal/PHASE2B_RULE_REPAIR_REVIEW_AND_PHASE2C_WORK_CN.md`
- `docs/tw_decision_model_orthogonal/REVIEWER_PROMPT_CN.md`
- `docs/TW_STOCK_DECISION_ORTHOGONAL_DATA_MODEL_PLAN_CN.md`

审查产物：

- `scripts/freeze_tw_decision_orthogonal_phase2c_manual_rules.py`
- `data_tw/experiments/decision_orthogonal/phase2c_manual_rule_cards.json`
- `data_tw/experiments/decision_orthogonal/phase2c_manual_rule_freeze_summary.json`
- `docs/tw_decision_model_orthogonal/PHASE2C_MANUAL_RULE_FREEZE_EXECUTION_REPORT_CN.md`

## 1. 本步审核结论

Phase 2C Manual Rule Freeze 主线范围通过，只读安全边界通过。

执行者没有偏离主线，也没有新增分支：

- 只读取 Phase2B 产物。
- 未读取样本 parquet 重新计算样本。
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
- 未 monitor 写入。
- 未触碰交易路径。

Phase2C gate 结论接受：

- `manual_rules_ready_for_later_review=true`
- `stop_before_phase3=true`

不允许进入 Phase3。

理由：

- Phase2B 已确认 `pass_count=0`，规则证据不足以进入模型训练。
- Phase2C 只是把人工解释价值固化为规则卡，没有产生新的训练证据。
- 当前阶段应结束规则探索，进入收尾归档，而不是继续修参数、训练模型或接入系统。

## 2. 主线一致性审查

通过项：

- Phase2C 严格执行了上一轮要求的 Manual Rule Freeze。
- 输出了 4 张规则卡，对应上一轮要求的 caution、review、explanation、auxiliary 四类。
- 每张规则卡包含 `rule_id`、`status`、`condition`、`baseline_group`、`intended_use`、`not_intended_use`、`key_metrics`、`known_caveats`、`pit_note`、`readonly_safety_note`。
- 报告和 summary 均显式写入：
  - `phase3_allowed=false`
  - `risk_filter_model_training_allowed=false`
  - `provider_write_allowed=false`
  - `accepted_latest_switching_allowed=false`
  - `trading_or_order_allowed=false`
  - `manual_rules_ready_for_later_review=true`
  - `stop_before_phase3=true`

未发现偏离主线或新增分支。

## 3. 规则卡审查

### 3.1 `margin_crowding_top50_p85_caution`

冻结状态：

- `manual_caution_explanation`

审查判断：

- 与上一轮要求一致。
- 已写明用于人工解释 Top50 中融资余额相对拥挤。
- 已写明 2025 年分段方向反向。
- 已写明 selected downside q10 未优于 baseline Top50。
- 已写明不能作为模型训练通过证据。

通过。

### 3.2 `flow_crowding_conflict_top50_p80_weak30_review`

冻结状态：

- `manual_review_explanation`

审查判断：

- 与上一轮要求一致。
- 已写明用于人工解释融资拥挤但外资/自营商 20 日流向偏弱的冲突状态。
- 已写明 2025 年分段方向反向。
- 已写明 coverage 只有 `797` days。
- 已写明不能单独作为模型 gate。

通过。

### 3.3 `foreign_flow_non_crowded_top150_explanation`

冻结状态：

- `manual_explanation_feature`

审查判断：

- 与上一轮要求一致。
- 已写明只解释非拥挤条件下外资流入背景。
- 已写明不得恢复为 confirmed watch。
- 已写明不得作为风险过滤或买卖含义。

通过。

### 3.4 `margin_change_non_crowded_top150_auxiliary`

冻结状态：

- `manual_auxiliary_feature`

审查判断：

- 与上一轮要求一致。
- 已写明只作为非拥挤条件下融资变化的辅助确认。
- 已写明不能独立支撑 Phase3。
- 已写明只能作为 auxiliary feature。

通过。

## 4. 数据与 PIT 审查

通过项：

- Phase2C 不新增 PIT 逻辑。
- Phase2C 未重新计算样本。
- Phase2C 继承 Phase1B repaired full 与 Phase2B 的只读产物。
- 报告和规则卡均保留 `available_at = next_trading_day(trade_date)` 是 conservative visibility proxy 的说明。
- 未将该 proxy 包装为官方发布时间证明。

继续注意：

- 后续任何使用规则卡的环节，都必须保留这个 PIT caveat。

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

规则卡和报告均明确：

- 不是交易建议。
- 不是买入/卖出信号。
- 不是目标仓位。
- 不是收益承诺。
- 不是上涨概率承诺。
- 不触发订单、broker、quick-trade 或 monitor 写入。

这些表述是安全边界声明，不是交易动作。

### Verdict

只读研究边界通过。

## 6. 是否需要停下来讨论

当前不需要停下来要求用户确认。

理由：

- Phase2C 已按审查要求完成。
- 没有发现偏离主线或新增分支。
- 没有触发需要用户选择的风险动作。

但本轮必须停止在 Phase2C 之后，不能默认进入 Phase3。

如果后续希望训练模型、接入前端/API、写 provider、切换 accepted latest、引入新数据源或使用规则卡生成交易含义，必须作为新方向单独提交给用户确认。

## 7. 给执行者的下一步工作文档：Phase 2D Closure

### 7.1 目标

对正交特征规则探索做收尾归档，形成一个最终 closure 包，明确：

- 本轮正交特征规则探索到 Phase2C 结束。
- 当前结果只支持人工研究解释规则卡。
- 不支持 Phase3。
- 不支持 Risk Filter Model 训练。
- 不支持前端/API 接入。
- 不支持 provider 写入或 accepted latest switching。
- 不支持任何交易路径。

Phase2D 是归档阶段，不是继续探索阶段。

### 7.2 输入

只允许使用：

- `docs/tw_decision_model_orthogonal/PHASE2C_MANUAL_RULE_FREEZE_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/decision_orthogonal/phase2c_manual_rule_cards.json`
- `data_tw/experiments/decision_orthogonal/phase2c_manual_rule_freeze_summary.json`
- `docs/tw_decision_model_orthogonal/PHASE2C_MANUAL_RULE_FREEZE_REVIEW_AND_PHASE2D_CLOSURE_WORK_CN.md`

可引用但不得改写历史事实：

- Phase1B repaired full 审查结论。
- Phase2 baseline 审查结论。
- Phase2B rule repair 审查结论。

### 7.3 允许产物

必须新增：

- `docs/tw_decision_model_orthogonal/PHASE2D_ORTHOGONAL_RULE_CLOSURE_REPORT_CN.md`
- `data_tw/experiments/decision_orthogonal/phase2d_orthogonal_rule_closure_summary.json`

如确有必要，可新增只读整理脚本：

- `scripts/summarize_tw_decision_orthogonal_phase2d_closure.py`

脚本只能读 Phase2C 及审查文档，只能写 Phase2D closure 专用输出。

### 7.4 必须写入的 closure 结论

Phase2D closure report 必须明确写：

- `orthogonal_rule_exploration_closed=true`
- `manual_rule_cards_frozen=true`
- `phase3_allowed=false`
- `risk_filter_model_training_allowed=false`
- `frontend_api_integration_allowed=false`
- `provider_write_allowed=false`
- `accepted_latest_switching_allowed=false`
- `trading_or_order_allowed=false`
- `requires_user_decision_for_new_direction=true`

### 7.5 必须总结的内容

Closure report 至少包含：

1. 最终冻结规则清单
   - `margin_crowding_top50_p85_caution`
   - `flow_crowding_conflict_top50_p80_weak30_review`
   - `foreign_flow_non_crowded_top150_explanation`
   - `margin_change_non_crowded_top150_auxiliary`

2. 每条规则的最终状态
   - `manual_caution_explanation`
   - `manual_review_explanation`
   - `manual_explanation_feature`
   - `manual_auxiliary_feature`

3. 不能进入 Phase3 的原因
   - Phase2B `pass_count=0`。
   - 主 caution 规则存在 2025 反向且 downside q10 未优于 baseline。
   - 主 review 规则 coverage 较窄且 2025 反向。
   - explanation/auxiliary 规则不计入模型 gate。

4. PIT caveat
   - `available_at = next_trading_day(trade_date)` 是 conservative visibility proxy，不是官方发布时间证明。

5. 只读安全边界
   - 不是交易建议。
   - 不是买入/卖出信号。
   - 不是目标仓位。
   - 不是收益承诺。
   - 不是上涨概率承诺。
   - 不触发订单、broker、quick-trade、monitor config save、monitor scan 或 alerts write。

### 7.6 禁止事项

Phase2D 禁止：

- 继续调参。
- 重新计算规则样本。
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

### 7.7 完成标准

Phase2D 完成后，执行者只提交：

- Phase2D closure report。
- Phase2D closure summary JSON。
- 如有脚本，提交只读整理脚本。

完成后等待审查者审核，不得自动开启 Phase3 或任何新方向。
