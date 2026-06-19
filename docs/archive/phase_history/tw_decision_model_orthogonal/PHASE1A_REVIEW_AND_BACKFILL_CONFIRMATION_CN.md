# 正交数据 Decision Model Phase 1A 审查结论与扩展补齐确认事项

审查日期：2026-06-10

审查入口：

- `docs/tw_decision_model_orthogonal/PHASE1A_EXECUTION_REPORT_CN.md`

审查依据：

- `docs/tw_decision_model_orthogonal/REVIEWER_PROMPT_CN.md`
- `docs/TW_STOCK_DECISION_ORTHOGONAL_DATA_MODEL_PLAN_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE0D_REVIEW_AND_PHASE1A_WORK_CN.md`

审查产物：

- `scripts/build_tw_decision_orthogonal_phase1a_poc_samples.py`
- `data_tw/experiments/decision_orthogonal/phase1a_poc_samples.parquet`
- `data_tw/experiments/decision_orthogonal/phase1a_poc_samples_preview.csv`
- `data_tw/experiments/decision_orthogonal/phase1a_schema.json`
- `data_tw/experiments/decision_orthogonal/phase1a_factor_increment_report.md`
- `data_tw/experiments/decision_orthogonal/phase1a_leakage_audit_report.md`
- `data_tw/experiments/decision_orthogonal/phase1a_factor_metrics.csv`

## 1. 本步审核结论

Phase 1A 执行范围通过。执行者没有偏离主线，也没有新增未授权分支。

Phase 1A 只构建了受限 POC PIT 样本，并对法人筹码、融资融券做单因子 sanity check。未联网、未重跑 FinMind、未新增数据源、未扩大时间范围或 symbol universe、未启用月营收、未写 Qlib bin/provider、未切换 accepted latest、未训练模型、未进入规则 baseline、未接前端/API，也未触碰交易路径。

Phase 1A 的结论是：

- `request_larger_backfill=true`
- `stop_orthogonal_poc=false`
- `phase1a_incomplete=false`
- `enter_phase2=false`
- `train_model=false`
- `phase1_gate_pass=false`

审查者同意该结论。

当前不能进入 Phase 2，也不能视为完整 Phase 1 通过。下一步如继续，必须先由用户确认是否允许更长历史/更多 symbols 的 raw archive backfill。

## 2. 主线一致性审查

通过项：

- 仍处于正交数据主线。
- 只使用 Phase 0D cleaned archive。
- 样本范围为 2025-05 到 2025-09。
- 实际样本为 3536 rows、34 symbols、104 asof days。
- leakage audit 通过，`institutional_available_at > asof` 与 `margin_available_at > asof` 均为 0。
- 没有输出 `enter_phase2=true`、`train_model=true` 或 `phase1_gate_pass=true`。
- 明确承认当前 POC 不足以证明跨年度稳定性。

未发现项：

- 未发现联网或新下载。
- 未发现月营收启用。
- 未发现 materialize/Qlib bin/provider。
- 未发现规则型 baseline。
- 未发现模型训练。
- 未发现前端/API。
- 未发现 broker、orders、quick-trade、target position/target weight。

## 3. 数据与 PIT 审查

Phase 1A 的 PIT join 规则符合要求：

- 只使用 `available_at <= asof` 的法人筹码与融资融券记录。
- 不使用 `trade_date == asof` 且 `available_at > asof` 的记录。
- label 从 asof 后第 N 个交易日计算。
- leakage audit 全部通过。

审查者复核样本：

- rows：3536。
- symbols：34。
- asof days：104。
- asof range：2025-05-05 到 2025-09-30。
- bad institutional PIT rows：0。
- bad margin PIT rows：0。
- months：2025-05、2025-06、2025-07、2025-08、2025-09。

限制：

- 34 symbols 是 qlib prediction 与 POC universe 的交集，不是 50 档完整样本。
- 只有 5 个月，不能证明跨年度或跨市场状态稳定性。
- T+1 仍是 conservative visibility proxy，不是官方发布时间声明。

## 4. 模型/指标/样本审查

Phase 1A 没有训练模型，只有单因子 sanity metrics。

POC 中观察到的迹象：

- `margin_balance_change_20d_sum` 对 `fwd_20d_excess_return` 的 daily mean Spearman 约 0.153。
- `institutional_total_net_buy_*` 的 high-minus-low 分组对 20d excess return 有正差异。
- 若干法人筹码 rolling sum 与 qlib score/rank 有中低相关性，说明并非完全独立，但也不是完全重复。

审查判断：

- 这些迹象足以支持“申请更大范围 backfill 后再验证”。
- 这些迹象不足以支持 Phase 2 规则 baseline。
- 当前不应训练模型，也不应做规则型风险过滤。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：安全关键词仅出现在禁止范围或未执行声明中。

### Network Audit

Phase 1A 未联网，未重跑 FinMind。

### Console Audit

未发现 provider refresh/publish、accepted latest switching、monitor 写入、broker、quick-trade 或订单路径证据。

### Text / Agent Semantics

报告没有买入/卖出建议、目标仓位、收益承诺或上涨概率承诺。单因子结果只是研究信号 sanity check。

### Verdict

只读研究边界通过。

## 6. 必须修复项

当前无必须返工项。

但下一阶段必须避免以下误用：

- 不得把 Phase 1A 结果当作完整 Phase 1 通过。
- 不得进入 Phase 2。
- 不得训练模型。
- 不得把 5 个月 POC 结果写成稳定收益结论。
- 不得扩大 backfill，除非用户明确授权。

## 7. 可暂缓项

继续暂缓：

- 月营收。
- Phase 2 规则 baseline。
- Risk Filter Model。
- 持仓风险验证。
- 前端/API。

## 8. 是否需要用户确认的问题

需要用户确认。

Phase 1A 已证明 POC 有继续验证价值，但下一步需要更长历史和更多 symbols 的 backfill。这会涉及联网调用 FinMind 与写入新的 raw archive，超出 Phase 1A 当前授权，必须由用户确认。

审查者建议：

- 允许进入 Phase 0E：法人筹码与融资融券扩展 raw archive backfill。
- 月营收继续暂缓。
- 不进入 Phase 2。
- 不训练模型。

## 9. 给执行者的下一步工作文档

当前不给执行者可立即执行的扩展 backfill 任务。必须等待用户确认。

如果用户确认“允许 Phase 0E 扩展 raw archive backfill”，执行者才可按以下边界执行。

### 9.1 Phase 0E 目标

扩大法人筹码与融资融券 raw archive 覆盖范围，为完整 Phase 1 单因子/分组检验准备可审计 PIT 数据。

Phase 0E 仍不是完整 Phase 1，不做单因子检验，不做模型，不做规则 baseline。

### 9.2 推荐范围

数据类别：

- 法人筹码。
- 融资融券。

暂缓：

- 月营收。

时间范围：

- 推荐 2022-01-01 至 2026-06-10。
- 若 API 限额不足，最低应覆盖 2024-01-01 至 2026-06-10。

股票范围：

- 推荐 qlib / tw_liquid_dyn Top150 historical universe。
- 不允许全市场。

### 9.3 允许产物

建议新增：

- `scripts/build_tw_decision_orthogonal_phase0e_raw_archive.py`
- `data_tw/experiments/decision_orthogonal/phase0e_raw_archive/`
- `data_tw/experiments/decision_orthogonal/phase0e_download_status.csv`
- `data_tw/experiments/decision_orthogonal/phase0e_pit_snapshot_manifest.csv`
- `data_tw/experiments/decision_orthogonal/phase0e_coverage_report.csv`
- `data_tw/experiments/decision_orthogonal/phase0e_pit_validation_samples.csv`
- `docs/tw_decision_model_orthogonal/PHASE0E_EXECUTION_REPORT_CN.md`

### 9.4 禁止事项

- 禁止月营收。
- 禁止全市场补齐。
- 禁止 materialize derived features。
- 禁止 Qlib bin/provider 写入。
- 禁止 accepted latest switching。
- 禁止 Phase 2。
- 禁止模型训练。
- 禁止前端/API。
- 禁止 broker、orders、quick-trade、target position/target weight。

### 9.5 Phase 0E Gate

Phase 0E 通过后，仍需审查者确认才能进入完整 Phase 1B。

Phase 0E 最低要求：

- 两类数据均有非零 raw archive。
- row-level `available_at` 完整。
- 有 coverage、缺失、失败、重复、quality flags。
- 有 PIT validation samples。
- 没有 provider/accepted/latest/Phase2/model/front-end 越界。

## 10. 审查者最终裁决

- Phase 1A 执行范围：通过。
- Phase 1A 安全边界：通过。
- 是否偏离主线：否。
- 是否新增未授权分支：否。
- 是否允许进入 Phase 2：否。
- 是否允许训练模型：否。
- 是否建议更大 backfill：是。
- 是否需要用户确认：是。
- 当前给执行者的指令：停止等待；若用户确认，最多执行 Phase 0E 扩展 raw archive backfill。
