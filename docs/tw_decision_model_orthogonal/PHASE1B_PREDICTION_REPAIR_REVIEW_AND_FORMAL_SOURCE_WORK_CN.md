# Phase 1B Prediction Repair 审查结论与 Formal Source 诊断工作文档

审查日期：2026-06-11

审查入口：

- `docs/tw_decision_model_orthogonal/PHASE1B_PREDICTION_REPAIR_REPORT_CN.md`

关联依据：

- `docs/tw_decision_model_orthogonal/PHASE1B_COVERAGE_DIAGNOSIS_REVIEW_AND_PREDICTION_REPAIR_WORK_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE1B_COVERAGE_DIAGNOSIS_REPORT_CN.md`
- `docs/tw_decision_model_orthogonal/REVIEWER_PROMPT_CN.md`
- `docs/TW_STOCK_DECISION_ORTHOGONAL_DATA_MODEL_PLAN_CN.md`

审查产物：

- `scripts/backfill_tw_option_c_historical_signals.py`
- `data_tw/experiments/decision_orthogonal/phase1b_prediction_repair_inventory.csv`
- `data_tw/experiments/decision_orthogonal/phase1b_prediction_repair_feasibility_smoke.csv`
- `data_tw/experiments/decision_orthogonal/phase1b_prediction_repair_feasibility_summary.json`

## 1. 本步审核结论

Prediction Repair 可行性检查没有偏离主线，也没有新增研究分支；执行者在 formal validation 失败后停止，没有全量生成 2023-2024 prediction，这是正确的。

但不接受直接使用 `--research-only-skip-formal-validation` 做 2023-2024 全量 repair。

原因：

- 工作文档明确要求：如果现有预测脚本无法证明 point-in-time inference，应停止补预测。
- 当前 2023 与 2024 formal smoke 均失败，错误为 `option_c_formal_source_missing_asof`。
- 2024 单日 smoke 只是在 `--research-only-skip-formal-validation` 下成功，语义上就是绕过 formal source asof validation。
- 该 bypass 可作为压力测试或调试证据，但不能作为 Phase1B repaired qlib baseline 的正式 PIT 证据。
- 现有 2023 `pred_fast` artifact 缺少明确脚本、配置、模型/recorder、输入路径和标准列格式，不能直接标准化混入 Phase1B repaired baseline。

因此：

- 不允许进入 Phase2。
- 不允许执行 2023-2024 全量 bypass backfill。
- 不允许把 2023 `pred_fast` 直接纳入 Phase1B。
- 下一步应做只读 Formal Source Diagnosis，确认 formal validation 失败的具体原因以及是否存在不绕过 validation 的修复路径。

## 2. 主线一致性审查

通过项：

- 未联网。
- 未使用 token。
- 未重拉 Phase0E。
- 未新增数据源。
- 未训练模型。
- 未写 Qlib bin/provider。
- 未 provider refresh/publish。
- 未 accepted latest switching。
- 未进入 Phase2。
- 未构建规则 baseline。
- 未触碰前端/API 或交易路径。
- 已在 formal validation 失败后停止，没有执行全量 repair。

注意项：

- `--research-only-skip-formal-validation` 是已存在脚本能力，但它改变了 PIT 证据强度。不能在当前主线中作为正式修复依据。
- 2023 `pred_fast` artifact 是潜在线索，不是可直接使用的 repaired qlib baseline。

未发现偏离主线或新增分支。

## 3. 数据与 PIT 审查

已确认：

- 数据层不缺：Phase0E archive 与价格/TWII 覆盖 2023-2024。
- 预测层缺口仍未修复。
- formal validation 失败原因是 `option_c_formal_source_missing_asof`。

PIT 审查裁决：

- 不能绕过 formal source asof validation 生成正式 repaired prediction。
- 不能使用 provenance 不完整的 2023 `pred_fast` artifact。
- 若要继续修复，必须先证明 dedicated Option C normalized source / provider / universe 对 2023-2024 asof 的 PIT 可用性，或证明缺失只是 validation 逻辑与历史回填场景不匹配。

## 4. 模型/指标/样本审查

本阶段没有训练模型，也没有重跑 Phase1B Full，符合停止条件。

不接受项：

- 当前没有生成完整 2023-2024 standard predictions。
- 当前没有 repaired full sample。
- 当前没有新的年度稳定性证据。
- 当前不能提出 Phase2 rules baseline。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：存在 research-only bypass 能力，但执行者未全量使用；需要继续禁止其作为正式 PIT 修复路径。

### Network Audit

报告声明未联网。审查范围内没有 FinMind/Scrapling/download 请求证据。

### Console Audit

未发现 provider refresh/publish、accepted latest switching、monitor config save、monitor scan、alerts write、broker、quick-trade、orders、target position 或 target weight 证据。

### Text / Agent Semantics

未发现买入/卖出建议、目标仓位、收益承诺或上涨概率承诺。

### Verdict

只读研究边界通过。

## 6. 必须停下讨论的问题

当前不应由执行者自行选择 bypass。

审查者裁决是：不接受 bypass 作为正式 Phase1B repaired prediction 来源。

如果后续确实要接受 bypass，只能在用户明确降低 PIT 证据标准后另行授权；但这会削弱 Phase1B 对“独立年份稳定增量”的可信度，不建议这样做。

## 7. 给执行者的下一步工作文档：Phase 1B Formal Source Diagnosis

### 7.1 目标

只读诊断 `option_c_formal_source_missing_asof` 的真实原因，判断是否存在不绕过 formal validation 的预测层修复路径。

本步骤仍不是 Phase2，不生成全量 prediction，不训练模型。

### 7.2 允许产物

允许新增：

- `docs/tw_decision_model_orthogonal/PHASE1B_FORMAL_SOURCE_DIAGNOSIS_REPORT_CN.md`
- `data_tw/experiments/decision_orthogonal/phase1b_formal_source_diagnosis_*`

如确有必要，可新增只读诊断脚本：

- `scripts/diagnose_tw_decision_orthogonal_phase1b_formal_source.py`

脚本只能读本地文件，只能写 `data_tw/experiments/decision_orthogonal/phase1b_formal_source_diagnosis_*`。

### 7.3 必做诊断

执行者必须报告：

1. Formal validation 失败明细
   - 对 2023-01-03、2024-01-03、2024-01-02 分别运行只读 formal validation。
   - 输出 `symbols_expected`、`symbols_found`、`symbols_with_asof`、`missing_files`、`missing_asof`。
   - 输出 provider calendar max 与 field inventory 状态。

2. Dedicated Option C source 覆盖
   - `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized` 的月度覆盖。
   - `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin` 的 calendar 覆盖。
   - 与 `normalized_nonempty`、Phase0E archive 的 2023-2024 覆盖对比。

3. Universe 与 symbols 对齐
   - accepted prediction universe 在 2023-2024 的 symbol 集合。
   - Option C source 缺失是否集中在特定 symbols，还是所有 symbols 都缺 asof。
   - 是否因当前 universe 定义使用了不适合历史 asof 的成员导致 validation 失败。

4. 2023 `pred_fast` artifact provenance
   - 列出该 artifact 的目录结构、文件数量、日期解析问题、列格式问题。
   - 查找是否存在 run metadata、script command、model recorder、config、input source 记录。
   - 判断是否可证明它与当前 qlib baseline 同源。
   - 如果不能证明，必须继续标记为 unusable。

5. 修复路径判断
   - `formal_source_fix_possible_without_provider_write=true/false`
   - `requires_provider_or_qlib_bin_rebuild=true/false`
   - `requires_model_training=true/false`
   - `requires_bypass=true/false`

### 7.4 禁止事项

- 禁止联网。
- 禁止使用 token。
- 禁止重拉数据。
- 禁止生成全量 2023-2024 prediction。
- 禁止使用 `--research-only-skip-formal-validation` 做全量 backfill。
- 禁止标准化或混入 2023 `pred_fast` artifact。
- 禁止训练模型。
- 禁止重建或写入 Qlib bin/provider。
- 禁止 provider refresh/publish。
- 禁止 accepted latest switching。
- 禁止规则 baseline。
- 禁止 Phase2。
- 禁止前端/API。
- 禁止 monitor config save、monitor scan、alerts write。
- 禁止 broker、orders、quick-trade、target position、target weight。
- 禁止买入/卖出建议、收益承诺、上涨概率承诺。

### 7.5 完成标准

报告必须给出以下结论之一：

- `formal_source_fix_possible_without_mutation=true`：仅当只需修正读取路径、日期解析或 universe 对齐，且不写 provider、不训练、不绕过 validation。
- `formal_source_repair_requires_provider_rebuild=true`：若必须重建或写入 Option C provider/qlib bin，必须停下等待用户确认。
- `prediction_repair_requires_bypass_stop=true`：若唯一可行路径是 `--research-only-skip-formal-validation`，则停止 repaired Phase1B，不进入 Phase2。
- `pred_fast_provenance_sufficient_for_standardization=true`：仅当能证明 2023 pred_fast 与当前 qlib baseline 同源、PIT 合法、列格式可无损标准化；否则不得使用。

任何结论都不得自动进入 Phase2。

## 8. 审查者最终裁决

- Prediction Repair feasibility：通过，执行者正确停止。
- 主线范围：通过。
- 新增分支：未发现。
- 只读安全边界：通过。
- 是否接受 bypass 全量 repair：否。
- 是否接受 2023 pred_fast 直接混入：否。
- 是否允许进入 Phase2：否。
- 下一步：执行 Phase1B Formal Source Diagnosis。
