# Phase 2 Rules Baseline 审查结论与 Phase 2B Rule Repair 工作文档

审查日期：2026-06-11

审查入口：

- `docs/tw_decision_model_orthogonal/PHASE2_RULES_BASELINE_EXECUTION_REPORT_CN.md`

关联依据：

- `docs/tw_decision_model_orthogonal/PHASE1B_REPAIRED_FULL_REVIEW_AND_PHASE2_RULES_WORK_CN.md`
- `docs/tw_decision_model_orthogonal/REVIEWER_PROMPT_CN.md`
- `docs/TW_STOCK_DECISION_ORTHOGONAL_DATA_MODEL_PLAN_CN.md`

审查产物：

- `scripts/run_tw_decision_orthogonal_phase2_rules_baseline.py`
- `data_tw/experiments/decision_orthogonal/phase2_rules_definitions.json`
- `data_tw/experiments/decision_orthogonal/phase2_rules_group_metrics.csv`
- `data_tw/experiments/decision_orthogonal/phase2_rules_segment_metrics.csv`
- `data_tw/experiments/decision_orthogonal/phase2_rules_daily_membership.csv`
- `data_tw/experiments/decision_orthogonal/phase2_rules_turnover_summary.csv`
- `data_tw/experiments/decision_orthogonal/phase2_rules_gate_summary.json`

## 1. 本步审核结论

Phase 2 Rules Baseline 主线范围和只读安全边界通过。

执行者没有偏离主线，也没有新增分支：

- 只读取 repaired Phase1B Full 样本。
- 未联网。
- 未使用 token。
- 未重拉数据。
- 未新增数据源。
- 未训练模型。
- 未写 provider。
- 未 provider refresh/publish。
- 未 accepted latest switching。
- 未前端/API。
- 未触碰交易路径。

Gate 结论接受：

- `request_phase2b_rule_repair=true`

不允许进入 Phase3。

理由：

- 当前只有 `margin_crowding_caution_top50` 一条非辅助规则通过 rule baseline check。
- `margin_change_confirmation_top150` 只是辅助确认规则，不能支撑 Phase3。
- `foreign_flow_confirmed_candidate_top150` 年度方向不稳定，不能作为 confirmed watch 规则。
- `flow_crowding_conflict_top50` 覆盖偏窄且未通过 gate。
- 2025 年存在明确反向风险，Phase2B 必须解释或缩小规则适用范围。

## 2. 主线一致性审查

通过项：

- Phase2 仅做规则型风险过滤 baseline。
- 规则输出是 research status，不是交易动作。
- 对照了裸 qlib Top50 与 Top150。
- 输出了 rule-selected / rule-excluded 对照。
- 输出了年度、季度、turnover proxy 与 gate summary。
- 未训练 Risk Filter Model。
- 未请求 Phase3 直接执行。

未发现偏离主线或新增分支。

## 3. 数据与 PIT 审查

通过项：

- 输入沿用 `phase1b_repaired_full_samples.parquet`。
- Phase2 未新增字段。
- 法人/融资字段仍按 `available_at <= asof` 使用。
- repaired qlib prediction 已在 Phase1B 修复阶段通过 asof-aware 审查。

继续注意：

- `available_at = next_trading_day(trade_date)` 仍是 conservative visibility proxy，不是官方发布时间证明。

## 4. 规则与指标审查

### 4.1 通过但需修正规则

`margin_crowding_caution_top50`：

- selected 20d mean：`0.0162`
- excluded 20d mean：`0.0276`
- baseline Top50 20d mean：`0.0255`
- historical positive rate：selected `0.4592`，低于 baseline Top50 `0.5151`
- 年度方向 share：`0.8`
- 反向年份：`2025`

审查判断：

- 该规则有风险过滤价值。
- 但 downside q10 并未明显优于 baseline，且 2025 反向。
- Phase2B 应缩小适用范围，而不是直接进入模型训练。

### 4.2 辅助规则

`margin_change_confirmation_top150`：

- selected 20d mean 高于 excluded 与 baseline Top150。
- 年度方向 share：`0.8`。
- 反向年份：`2022`。
- 但状态为 `confirmation_auxiliary`，不能独立支撑 Phase3。

审查判断：

- 可保留为辅助确认。
- 不得单独输出强研究状态。

### 4.3 未通过规则

`foreign_flow_confirmed_candidate_top150`：

- selected 20d mean 低于 excluded 与 baseline。
- 年度方向 share：`0.4`。
- 反向年份：`2022`、`2023`、`2026`。

审查判断：

- 当前不应作为 confirmed watch 规则。
- Phase2B 只能尝试缩小 scope，例如限制到特定 qlib rank band、排除融资拥挤或仅作为解释字段。

`flow_crowding_conflict_top50`：

- selected 20d mean 明显低于 excluded 与 baseline。
- 但 selected downside q10 反而不差于 baseline，且覆盖仅 835 days。
- 年度方向 share：`0.8`，反向年份 `2025`。

审查判断：

- 有研究价值，但定义过窄或指标目标不一致。
- Phase2B 可尝试修正为 review/caution 解释规则，但不能进入 Phase3。

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

报告明确说明 positive-rate 仅为历史样本统计，不代表未来胜率或收益承诺。规则状态如 `confirmed_watch_candidate` 也说明不是买入建议。

### Verdict

只读研究边界通过。

## 6. 必须修复项

Phase2B 必须解决：

- `margin_crowding_caution_top50` 的 2025 反向问题。
- `margin_crowding_caution_top50` downside q10 未明显改善的问题。
- `foreign_flow_confirmed_candidate_top150` 年度不稳定问题。
- `flow_crowding_conflict_top50` 覆盖窄且 gate 未通过的问题。
- 明确规则目标是风险过滤、确认辅助，还是解释标签，不能混用。

## 7. 可暂缓项

继续暂缓：

- 月营收。
- 新数据源。
- 数据重拉。
- 模型训练。
- Risk Filter Model。
- Phase3。
- 前端/API。
- provider refresh/publish。
- accepted latest switching。
- 交易路径。

## 8. 是否需要用户确认的问题

当前不需要停下来要求用户确认。

理由：

- Phase2B rule repair 是 Phase2 gate 允许的修复路径。
- 不需要联网、训练、provider 操作、accepted latest switching 或新增数据源。
- 不改变主目标。

若执行者在 Phase2B 中需要训练模型、参数搜索到复杂模型、接入前端/API、写 provider 或新增数据源，必须停止并回报。

## 9. 给执行者的下一步工作文档：Phase 2B Rule Repair

### 9.1 目标

在不训练模型的前提下，对 Phase2 规则做最小范围修正，判断规则型风险过滤 baseline 是否能达到进入 Phase3 的门槛。

Phase2B 不是模型阶段，不得训练 Risk Filter Model。

### 9.2 输入

只允许使用：

- `data_tw/experiments/decision_orthogonal/phase1b_repaired_full_samples.parquet`
- `data_tw/experiments/decision_orthogonal/phase2_rules_*`
- `data_tw/experiments/decision_orthogonal/phase1b_repaired_full_*`

### 9.3 允许产物

允许新增：

- `docs/tw_decision_model_orthogonal/PHASE2B_RULE_REPAIR_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/decision_orthogonal/phase2b_rules_*`

如确有必要，可新增只读分析脚本：

- `scripts/run_tw_decision_orthogonal_phase2b_rule_repair.py`

脚本只能读 Phase1B/Phase2 产物，只能写 Phase2B 专用输出。

### 9.4 允许修正规则范围

只允许做小范围、可解释的规则修正：

1. Margin crowding risk refinement
   - 尝试把 threshold 从 `>=0.80` 调整为 `>=0.85` 或 `>=0.90`。
   - 尝试增加 qlib rank band，例如只在 Top20/Top30/Top50 中比较。
   - 尝试增加 margin balance change 或 short balance 条件作为确认。
   - 必须单独报告 2025 年效果。

2. Flow/crowding conflict refinement
   - 可调整 foreign/dealer weak threshold，例如 `<=0.30`、`<=0.40`。
   - 可增加 minimum coverage constraint。
   - 必须报告 coverage 是否过低。

3. Foreign flow rule downgrade
   - 若无法稳定改善，只能降级为 explanation feature，不得保留为 `confirmed_watch_candidate`。

4. Margin change confirmation
   - 只能作为 auxiliary。
   - 可以测试是否在非拥挤或非 2022 区间更稳定，但不得作为强规则。

### 9.5 禁止过度搜索

禁止做大规模参数搜索或隐性模型训练。

允许的阈值候选必须少量、固定、可解释，例如：

- `0.75`
- `0.80`
- `0.85`
- `0.90`

不得为了指标最优进行网格爆搜。

### 9.6 必做验证

每条修正规则必须报告：

- selected / excluded / baseline Top50 / baseline Top150。
- 5d / 10d / 20d mean、median、downside q10、worst decile。
- historical positive-rate，只能作为历史统计。
- coverage rows/days/symbols。
- turnover proxy。
- 年度分段。
- 季度分段。
- 2025 单独分段。
- 相对 Phase2 原规则是否改善。

### 9.7 Gate

Phase2B 完成后只能给出：

- `request_phase3_risk_filter_model=true`：至少两条非辅助规则稳定通过，或一条风险过滤规则非常稳定且解释价值强，同时多年度/季度优于 baseline。
- `stop_orthogonal_direction=true`：规则修正后仍不足以稳定改善或解释价值不足。
- `request_phase2c_manual_rule_freeze=true`：若只有一条规则可用，但适合冻结为人工解释规则，不适合进入模型训练。

即使请求 Phase3，也必须等待审查者审查，不得自行训练模型。

### 9.8 明确禁止事项

- 禁止联网。
- 禁止使用 token。
- 禁止重拉数据。
- 禁止新增数据源。
- 禁止月营收。
- 禁止训练模型。
- 禁止 Risk Filter Model。
- 禁止大规模参数搜索。
- 禁止写 Qlib bin/provider。
- 禁止 provider refresh/publish。
- 禁止 accepted latest switching。
- 禁止前端/API。
- 禁止 monitor config save、monitor scan、alerts write。
- 禁止 broker、orders、quick-trade、target position、target weight。
- 禁止买入/卖出建议、收益承诺、上涨概率承诺。

## 10. 审查者最终裁决

- Phase2 主线范围：通过。
- 新增分支：未发现。
- 只读安全边界：通过。
- 是否允许进入 Phase3：否。
- 是否允许训练模型：否。
- 是否允许 Phase2B：是。
- 下一步：执行 Phase2B Rule Repair。
