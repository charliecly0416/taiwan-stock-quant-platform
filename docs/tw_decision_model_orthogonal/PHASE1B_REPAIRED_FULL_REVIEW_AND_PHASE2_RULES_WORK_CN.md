# Phase 1B Repaired Full 审查结论与 Phase 2 Rules Baseline 工作文档

审查日期：2026-06-11

审查入口：

- `docs/tw_decision_model_orthogonal/PHASE1B_ASOF_AWARE_PREDICTION_REPAIR_REPORT_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE1B_REPAIRED_FULL_EXECUTION_REPORT_CN.md`

关联依据：

- `docs/tw_decision_model_orthogonal/PHASE1B_FORMAL_SOURCE_DIAGNOSIS_REVIEW_AND_ASOF_AWARE_REPAIR_WORK_CN.md`
- `docs/tw_decision_model_orthogonal/REVIEWER_PROMPT_CN.md`
- `docs/TW_STOCK_DECISION_ORTHOGONAL_DATA_MODEL_PLAN_CN.md`

审查产物：

- `scripts/audit_tw_decision_orthogonal_phase1b_asof_aware_repair.py`
- `qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill/option_c_historical_backfill_20230101_20241231_asof_aware_research_only/`
- `data_tw/experiments/decision_orthogonal/phase1b_asof_aware_prediction_repair_*`
- `data_tw/experiments/decision_orthogonal/phase1b_repaired_full_*`

## 1. 本步审核结论

Phase1B Asof-aware Prediction Repair 与 Repaired Full 通过。

审查结论：

- 未发现偏离主线。
- 未发现新增研究分支。
- asof-aware prediction repair 没有使用 formal validation bypass。
- 2023-2024 prediction 覆盖已修复。
- repaired Phase1B Full 已形成 2022-01 至 2026-05 连续月度样本。
- 泄露审计通过。
- 允许进入受限 Phase2：规则型风险过滤 baseline。

但 Phase2 只能做可解释规则 baseline，不允许训练模型、不允许前端/API、不允许 provider/accepted latest 操作。

## 2. 主线一致性审查

通过项：

- 修复范围限定为 2023-2024 qlib prediction artifact。
- 使用 asof-aware universe，而不是绕过 formal validation。
- `formal_validation_bypass_count=0`。
- `refresh_triggered_count=0`。
- `publish_triggered_count=0`。
- `provider_mutation_triggered_count=0`。
- `model_retraining_count=0`。
- 未联网。
- 未使用 token。
- 未重拉 Phase0E。
- 未训练模型。
- 未写入或重建 provider。
- 未 provider refresh/publish。
- 未 accepted latest switching。
- 未进入 Phase2 执行规则 baseline。
- 未触碰前端/API 或交易路径。

未发现偏离主线或新增分支。

## 3. 数据与 PIT 审查

Asof-aware repair 通过：

- 2023-2024 provider calendar days：481。
- repaired prediction files：481。
- missing prediction days：0。
- prediction columns：`datetime,instrument,score`。
- 2023 prediction rows：35611，symbols 149。
- 2024 prediction rows：36101，symbols 149 至 150。
- `TW7769` 在 `2024-11-01` 前因 `missing_source_asof` 与 `outside_instrument_date_range` 排除，符合 PIT。
- `TW7769` 在 `2024-11-01` 起 source/provider 可用后进入 universe，符合 asof-aware 口径。

Repaired Full 样本覆盖通过：

- 样本行数：106440。
- qlib prediction rows：109309。
- prediction file count：1118。
- 2023-2024 每月均有样本。
- 2022-2026 年度样本均存在。
- `available_at <= asof` 泄露审计为 0 bad rows。
- same-day trade date 不可见检查为 0 bad rows。
- forward label date 均晚于 asof。

继续注意：

- `available_at = next_trading_day(trade_date)` 仍是 conservative visibility proxy，不是官方发布时间证明。

## 4. 模型/指标/样本审查

Phase1B Repaired Full 支持进入 Phase2 规则 baseline，但只能从风险过滤角度进入。

支持证据：

- margin balance 水平类特征在全样本上对 20d excess return 呈稳定负向 RankIC：
  - `margin_balance_20d_mean` RankIC 约 `-0.04146`。
  - `margin_balance_10d_mean` RankIC 约 `-0.04065`。
  - `margin_balance` RankIC 约 `-0.03927`。
- 年度分段中，margin balance 水平类在 5 个年份中 4 年为负向，2025 为反向，需要在 Phase2 中作为规则边界重点审计。
- `margin_balance_change_20d_sum` 对 20d excess return 在 2022-2026 五个年份均为正向，但幅度较小，适合做辅助确认，不适合单独做强规则。
- foreign net buy 10/20d 与 qlib score 的相关性约 `0.15-0.18`，与 qlib 有中低相关，可作为增量候选，但年度方向有不稳定，需要规则 baseline 中做分段检验。
- qlib score 相关性没有高到完全重复 qlib rank。
- Top50/Top150 内外 high-low 表现有一定正向证据，但幅度不大，应作为辅助指标。

Phase2 设计方向：

- 优先做 `caution_watch` / `defer_watch` 风险过滤规则。
- 不要先做“confirmed_watch 强买入增强”。
- 第一批规则应围绕融资余额拥挤、融资变化、外资连续买超确认、qlib Top50 内风险识别。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：无。

### Network Audit

报告声明未联网。产物为本地 repaired prediction 与本地 Phase1B 分析输出。

### Console Audit

未发现 provider refresh/publish、accepted latest switching、monitor config save、monitor scan、alerts write、broker、quick-trade、orders、target position 或 target weight 证据。

### Text / Agent Semantics

报告中 hit-rate/positive-rate 仅作为历史统计。未发现真实买入/卖出建议、目标仓位、收益承诺或上涨概率承诺。

### Verdict

只读研究边界通过。

## 6. 必须修复项

当前没有阻塞 Phase2 rules baseline 的必须修复项。

Phase2 必须处理的风险：

- 2025 年 margin balance 方向与 2022/2023/2024/2026 不一致，规则不能简单写死。
- 外资/自营商类信号有年度和季度波动，不能单独作为强规则。
- Phase2 必须以裸 qlib rank 为基线对照，证明规则能降低风险或改善 top bucket，不得只展示规则组自身表现。

## 7. 可暂缓项

继续暂缓：

- 月营收。
- 新数据源。
- 数据重拉。
- 模型训练。
- Risk Filter Model。
- 前端/API。
- provider refresh/publish。
- accepted latest switching。
- 交易路径。

## 8. 是否需要用户确认的问题

当前不需要停下来要求用户确认。

理由：

- Phase2 rules baseline 是主计划中的下一阶段。
- 本次不需要联网、训练、provider 操作、accepted latest switching 或前端/API。
- Phase2 仍是只读历史规则验证。

若执行者在 Phase2 中发现需要训练模型、接入前端/API、写 provider、切换 accepted latest 或新增数据源，必须停止并回报。

## 9. 给执行者的下一步工作文档：Phase 2 Rules Baseline

### 9.1 目标

基于 repaired Phase1B Full 样本，构建可解释、只读、历史规则型风险过滤 baseline。

目标不是训练模型，也不是给交易建议，而是验证规则是否比裸 qlib Top50/Top150 更清晰地降低风险或改善分组表现。

### 9.2 输入

只允许使用：

- `data_tw/experiments/decision_orthogonal/phase1b_repaired_full_samples.parquet`
- `data_tw/experiments/decision_orthogonal/phase1b_repaired_full_factor_metrics.csv`
- `data_tw/experiments/decision_orthogonal/phase1b_repaired_full_segment_metrics.csv`
- `data_tw/experiments/decision_orthogonal/phase1b_repaired_full_schema.json`
- `data_tw/experiments/decision_orthogonal/phase1b_asof_aware_prediction_repair_*`

### 9.3 允许产物

允许新增：

- `docs/tw_decision_model_orthogonal/PHASE2_RULES_BASELINE_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/decision_orthogonal/phase2_rules_*`

如确有必要，可新增只读分析脚本：

- `scripts/run_tw_decision_orthogonal_phase2_rules_baseline.py`

脚本只能读取 Phase1B repaired outputs，只能写 Phase2 专用实验输出。

### 9.4 规则候选

第一批规则必须从简单、可解释、风险过滤优先开始：

1. 融资拥挤风险
   - qlib Top50。
   - margin balance / margin_balance_20d_mean 高分位。
   - 输出研究状态：`caution_watch` 或 `defer_watch`。

2. 融资变化确认
   - qlib Top50 或 Top150。
   - margin_balance_change_20d_sum 高分位。
   - 只作为辅助确认，不得单独给强结论。

3. 外资连续买超确认
   - qlib Top50/Top150。
   - foreign_net_buy_10d_sum / 20d_sum 高分位。
   - 输出研究状态：`confirmed_watch_candidate`，不得写成买入建议。

4. 法人/融资冲突
   - qlib Top50。
   - qlib score 高但 margin crowding 高、foreign/dealer flow 弱。
   - 输出研究状态：`review_watch` 或 `caution_watch`。

### 9.5 必做对照

每条规则必须对照：

- 裸 qlib Top50。
- 裸 qlib Top150。
- rule-selected group。
- rule-excluded group。

指标至少包括：

- 5d / 10d / 20d forward excess return。
- mean / median。
- downside quantile。
- worst decile。
- historical positive-rate 只作为历史统计，不得写成胜率承诺。
- coverage。
- turnover proxy 或 daily membership change。
- 年度分段。
- 季度分段。
- 2025 反向年份单独解释。

### 9.6 Gate

Phase2 完成后只能给出以下结论之一：

- `request_phase3_risk_filter_model=true`：仅当规则 baseline 在多个年份/季度比裸 qlib rank 更清晰地降低风险或改善 top bucket，且规则解释简单。
- `request_phase2b_rule_repair=true`：若规则有方向但不稳定，需要修规则或缩小适用范围。
- `stop_orthogonal_direction=true`：若规则无法稳定改善或解释价值不足。

即使请求 Phase3，也必须等待审查者审查，不得自行训练模型。

### 9.7 明确禁止事项

- 禁止联网。
- 禁止使用 token。
- 禁止重拉数据。
- 禁止新增数据源。
- 禁止月营收。
- 禁止训练模型。
- 禁止 Risk Filter Model。
- 禁止写 Qlib bin/provider。
- 禁止 provider refresh/publish。
- 禁止 accepted latest switching。
- 禁止前端/API。
- 禁止 monitor config save、monitor scan、alerts write。
- 禁止 broker、orders、quick-trade、target position、target weight。
- 禁止买入/卖出建议、收益承诺、上涨概率承诺。

## 10. 审查者最终裁决

- Asof-aware Prediction Repair：通过。
- Repaired Phase1B Full：通过。
- 主线范围：通过。
- 新增分支：未发现。
- 只读安全边界：通过。
- 是否允许进入 Phase2：是，仅限规则型风险过滤 baseline。
- 是否允许训练模型：否。
- 下一步：执行 Phase2 Rules Baseline。
