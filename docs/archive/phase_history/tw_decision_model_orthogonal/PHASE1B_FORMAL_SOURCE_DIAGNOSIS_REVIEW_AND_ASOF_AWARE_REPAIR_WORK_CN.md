# Phase 1B Formal Source Diagnosis 审查结论与 Asof-aware Prediction Repair 工作文档

审查日期：2026-06-11

审查入口：

- `docs/tw_decision_model_orthogonal/PHASE1B_FORMAL_SOURCE_DIAGNOSIS_REPORT_CN.md`

关联依据：

- `docs/tw_decision_model_orthogonal/PHASE1B_PREDICTION_REPAIR_REVIEW_AND_FORMAL_SOURCE_WORK_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE1B_COVERAGE_DIAGNOSIS_REVIEW_AND_PREDICTION_REPAIR_WORK_CN.md`
- `docs/tw_decision_model_orthogonal/REVIEWER_PROMPT_CN.md`
- `docs/TW_STOCK_DECISION_ORTHOGONAL_DATA_MODEL_PLAN_CN.md`

审查产物：

- `scripts/diagnose_tw_decision_orthogonal_phase1b_formal_source.py`
- `data_tw/experiments/decision_orthogonal/phase1b_formal_source_diagnosis_validation.csv`
- `data_tw/experiments/decision_orthogonal/phase1b_formal_source_diagnosis_source_coverage.csv`
- `data_tw/experiments/decision_orthogonal/phase1b_formal_source_diagnosis_symbol_gaps.csv`
- `data_tw/experiments/decision_orthogonal/phase1b_formal_source_diagnosis_pred_fast_inventory.csv`
- `data_tw/experiments/decision_orthogonal/phase1b_formal_source_diagnosis_summary.json`

## 1. 本步审核结论

Phase 1B Formal Source Diagnosis 通过。

执行者没有偏离主线，也没有新增研究分支。诊断结论可信：

- formal validation 失败不是 provider calendar 问题，calendar 覆盖至 `2026-06-10`。
- 失败不是 provider field inventory 问题，`open/high/low/close/volume/vwap/factor` 字段检查通过。
- 失败不是全体数据缺失，150 个 expected symbol 的 CSV 文件均存在。
- 失败集中在 `TW7769`：该 symbol 在 static accepted universe 中，但 `option_c_150_normalized/TW7769.csv` 的覆盖从 `2024-11-01` 才开始。
- `2023-01-03`、`2024-01-02`、`2024-01-03` 三个 formal validation 目标日均只有 `TW7769` 缺 exact asof，其他 149 个 symbols 可用。
- `pred_fast` provenance 仍不足，不能直接混入 Phase1B。

审查裁决：

- 接受 `formal_source_fix_possible_without_mutation=true`。
- 不需要 provider rebuild。
- 不需要训练模型。
- 不需要 formal validation bypass。
- 不接受 `pred_fast` 标准化混入。
- 允许进入受限的 Asof-aware Prediction Repair。
- 仍不允许进入 Phase2。

## 2. 主线一致性审查

通过项：

- 本阶段只做只读诊断。
- 未联网。
- 未使用 token。
- 未重拉数据。
- 未生成全量 2023-2024 prediction。
- 未训练模型。
- 未写入或重建 Qlib provider。
- 未执行 formal validation bypass。
- 未进入 Phase2。
- 未触碰前端/API 或交易路径。

未发现偏离主线或新增分支。

## 3. 数据与 PIT 审查

本次诊断把 PIT 风险从“无法证明”收敛为“静态 universe 与历史 asof 不匹配”。

审查判断：

- 对历史 asof，prediction universe 应只包含该 asof 在 dedicated Option C source 中有记录、且 provider/instrument 有效的 symbols。
- 在 `TW7769` 于 `2024-11-01` 才进入 source 覆盖的情况下，2023-2024 早期 asof 不应强制要求它存在。
- 使用 asof-aware universe 排除尚未可见 symbols，是 PIT 更严格的做法，不是降低标准。
- 该修复不需要用未来数据补历史，也不需要绕过 validation。

必须保持：

- 每个 asof 的 formal validation 必须在 asof-aware universe 下通过。
- 每个 asof 的 prediction symbols 必须与当日 validated universe 一致。
- 不得用 Phase0E 正交特征生成 qlib prediction。
- qlib baseline 模型定义不得改变。

## 4. 模型/指标/样本审查

本阶段没有训练模型或重跑 Phase1B Full，符合限制。

下一步可以做的是预测层修复和 repaired Phase1B Full 重跑：

- 只使用 frozen recorder/model。
- 只修复 2023-2024 prediction artifact。
- 修复后重新跑 Phase1B Full。
- repaired Full 仍只能提出请求，不能自动进入 Phase2。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：无。

### Network Audit

报告声明未联网。诊断脚本只读取本地文件并写入本阶段诊断产物。

### Console Audit

未发现 provider refresh/publish、accepted latest switching、monitor config save、monitor scan、alerts write、broker、quick-trade、orders、target position 或 target weight 证据。

### Text / Agent Semantics

未发现买入/卖出建议、目标仓位、收益承诺或上涨概率承诺。

### Verdict

只读研究边界通过。

## 6. 必须修复项

必须实现 asof-aware universe prediction repair：

- historical formal validation 不能再使用 static 150 symbols 强制覆盖所有历史 asof。
- 对每个 asof，应以 dedicated Option C source 当日可见 symbol 集合作为 prediction universe。
- `TW7769` 在 `2024-11-01` 前不得进入该日 prediction universe。

## 7. 可暂缓项

继续暂缓：

- 月营收。
- 新数据源。
- 重新拉取 Phase0E 数据。
- Scrapling。
- provider rebuild。
- 模型训练。
- 规则 baseline。
- Phase2。
- 前端/API。

## 8. 是否需要用户确认的问题

当前不需要停下来要求用户确认。

原因：

- 诊断已经证明不需要绕过 formal validation。
- 也不需要训练、联网、provider rebuild、accepted latest switching 或新增数据源。
- Asof-aware universe 是对 PIT 约束的加强，不是改变主目标。

若执行者在修复中发现必须重建 provider、训练模型、联网下载或使用 bypass，则必须停止并回报。

## 9. 给执行者的下一步工作文档：Phase 1B Asof-aware Prediction Repair

### 9.1 目标

实现并执行 2023-2024 qlib prediction 的 asof-aware repair，然后重跑 repaired Phase1B Full。

本步骤仍属于 Phase1B 修复，不是 Phase2。

### 9.2 允许修改

允许执行者在最小范围内修改或新增脚本：

- 修改 `scripts/backfill_tw_option_c_historical_signals.py`，增加 historical asof-aware universe 模式；或
- 新增 `scripts/repair_tw_decision_orthogonal_phase1b_asof_aware_predictions.py`。

允许新增报告：

- `docs/tw_decision_model_orthogonal/PHASE1B_ASOF_AWARE_PREDICTION_REPAIR_REPORT_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE1B_REPAIRED_FULL_EXECUTION_REPORT_CN.md`

允许新增产物：

- `data_tw/experiments/decision_orthogonal/phase1b_asof_aware_prediction_repair_*`
- `data_tw/experiments/decision_orthogonal/phase1b_repaired_full_*`
- `qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill/option_c_historical_backfill_20230101_20241231_asof_aware_research_only/.../prediction.csv`

### 9.3 Asof-aware universe 要求

对每个 asof：

1. 从 static accepted universe 作为候选池开始。
2. 只保留在 `option_c_150_normalized/{symbol}.csv` 中存在该 asof 日期的 symbol。
3. 只保留 provider feature inventory 完整的 symbol。
4. 记录 excluded symbols 及原因，例如：
   - `missing_source_asof`
   - `missing_provider_feature`
   - `outside_instrument_date_range`
5. formal validation 必须在过滤后的 universe 上通过。
6. prediction.csv 只包含过滤后的 universe。

`TW7769` 的处理必须在报告中单独说明：

- `2024-11-01` 前应因 `missing_source_asof/outside_instrument_date_range` 排除。
- `2024-11-01` 起如 source/provider 均具备，应可进入 universe。

### 9.4 必做步骤

1. Smoke
   - 对 `2023-01-03`、`2024-01-02`、`2024-11-01` 各跑一个 asof-aware formal validation smoke。
   - 不允许使用 `--research-only-skip-formal-validation`。
   - 报告 universe size、excluded symbols、validation status。

2. Full Repair
   - 生成 `2023-01-01` 至 `2024-12-31` 的 standard prediction artifacts。
   - 每个 prediction.csv 至少包含 `datetime`、`instrument`、`score`。
   - 使用 frozen recorder/model。
   - 不训练模型。
   - 不写 provider。
   - 不更新 latest signal。

3. Coverage Audit
   - 输出每月 prediction file count、rows、symbols、days。
   - 输出每月 excluded symbols summary。
   - 证明 2023-2024 不再 `no_prediction=1`。

4. Repaired Phase1B Full
   - 重跑 Phase1B Full。
   - 输出 `docs/tw_decision_model_orthogonal/PHASE1B_REPAIRED_FULL_EXECUTION_REPORT_CN.md`。
   - 输出 `data_tw/experiments/decision_orthogonal/phase1b_repaired_full_*`。

### 9.5 Repaired Full 报告必须包含

- 2022-2026 每月样本量。
- 2023-2024 每月样本量。
- 2023-2024 prediction coverage。
- asof-aware universe exclusion summary。
- 每年 RankIC/IC。
- 每季度 RankIC/IC。
- qlib score 相关性。
- Top50/Top150 内外表现。
- 泄露审计。
- prediction repair provenance。
- 是否仍请求 Phase2。

Gate 只能给出：

- `request_phase2_rules_baseline=true`
- `request_more_data_or_repair=true`
- `stop_orthogonal_direction=true`

即使重新提出 `request_phase2_rules_baseline=true`，也必须等待审查者审查，不得自行进入 Phase2。

### 9.6 明确禁止事项

- 禁止联网。
- 禁止使用 token。
- 禁止重拉数据。
- 禁止新增数据源。
- 禁止使用 `--research-only-skip-formal-validation` 做 full repair。
- 禁止标准化或混入 2023 `pred_fast` artifact。
- 禁止训练模型。
- 禁止改变 qlib baseline 模型定义。
- 禁止用 Phase0E 正交特征生成 qlib prediction。
- 禁止写入或重建 Qlib bin/provider。
- 禁止 provider refresh/publish。
- 禁止 accepted latest switching。
- 禁止规则 baseline。
- 禁止 Phase2。
- 禁止前端/API。
- 禁止 monitor config save、monitor scan、alerts write。
- 禁止 broker、orders、quick-trade、target position、target weight。
- 禁止买入/卖出建议、收益承诺、上涨概率承诺。

## 10. 审查者最终裁决

- Formal Source Diagnosis：通过。
- 主线范围：通过。
- 新增分支：未发现。
- 只读安全边界：通过。
- 是否接受 bypass：否。
- 是否接受 pred_fast 混入：否。
- 是否需要 provider rebuild：否。
- 是否允许 asof-aware prediction repair：是。
- 是否允许进入 Phase2：否。
- 下一步：执行 Phase1B Asof-aware Prediction Repair，并重跑 repaired Phase1B Full。
