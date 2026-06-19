# Phase 1B Coverage Diagnosis 审查结论与预测层修复工作文档

审查日期：2026-06-11

审查入口：

- `docs/tw_decision_model_orthogonal/PHASE1B_COVERAGE_DIAGNOSIS_REPORT_CN.md`

关联依据：

- `docs/tw_decision_model_orthogonal/PHASE1B_FULL_REVIEW_AND_COVERAGE_DIAGNOSIS_WORK_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE0E_SCRAPLING_EXPLANATION_REVIEW_AND_PHASE1B_WORK_CN.md`
- `docs/tw_decision_model_orthogonal/REVIEWER_PROMPT_CN.md`
- `docs/TW_STOCK_DECISION_ORTHOGONAL_DATA_MODEL_PLAN_CN.md`

审查产物：

- `scripts/diagnose_tw_decision_orthogonal_phase1b_coverage.py`
- `data_tw/experiments/decision_orthogonal/phase1b_coverage_diagnosis_phase0e_monthly_coverage.csv`
- `data_tw/experiments/decision_orthogonal/phase1b_coverage_diagnosis_price_monthly_coverage.csv`
- `data_tw/experiments/decision_orthogonal/phase1b_coverage_diagnosis_prediction_monthly_coverage.csv`
- `data_tw/experiments/decision_orthogonal/phase1b_coverage_diagnosis_join_dropoff_monthly.csv`
- `data_tw/experiments/decision_orthogonal/phase1b_coverage_diagnosis_summary.json`

## 1. 本步审核结论

Coverage Diagnosis 本身通过，未发现偏离主线或新增研究分支。

诊断结论成立：

- Phase0E institutional/margin normalized archive 在 2023-2024 均有数据。
- 本地价格与 TWII 在 2023-2024 均有覆盖。
- 2023-2024 缺样本不是正交数据层缺失，也不是价格标签层缺失。
- 直接缺口是本地 qlib prediction artifact 在 2023-2024 没有 prediction rows。
- Join drop-off 显示 2023-2024 从第一步就是 `no_prediction=1`，后续 PIT/price/label join 没有机会形成样本。

审查裁决：

- `phase1b_repair_requires_new_artifacts=true` 接受。
- 当前 Phase1B Full 仍只能作为 2022 + 2025-2026 片段窗口证据。
- 仍不允许进入 Phase2 rules baseline。
- 需要补的是预测层，不是数据层。
- 为了完成正交特征相对 qlib rank 的完整 Phase1B 验证，允许进入受限 Phase1B Prediction Repair。

## 2. 是否需要补预测

需要补预测。

理由：

- 正交数据主线不是单独证明法人/融资融券因子有效，而是验证它们相对 qlib rank/score 是否有独立增量。
- Phase1 计划明确要求检查 Top50/Top150、qlib rank 相关性、qlib TopN 内外的增量表现。
- 若 2023-2024 没有 qlib predictions，就无法判断这些年份里正交特征是否稳定地补充 qlib baseline。
- 直接跳过 qlib prediction，把 Phase1B 改成纯因子检验，会改变问题定义，属于新分支。

但补预测必须严格受限：

- 只能补 2023-2024 历史 qlib prediction artifact。
- 只能使用本地已有模型/recorder/配置和本地已有数据。
- 不允许训练新模型。
- 不允许联网下载。
- 不允许刷新或发布 provider。
- 不允许切换 accepted latest。
- 不允许进入 Phase2。

如果本地没有可复用的历史推理入口、模型或 recorder，则执行者必须停下报告，不得临时训练模型或改用新模型。

## 3. 主线一致性审查

通过项：

- 本阶段只做覆盖缺口诊断。
- 未联网。
- 未使用 token。
- 未重拉 Phase0E。
- 未新增数据源。
- 未生成 qlib predictions。
- 未训练模型。
- 未写 Qlib bin/provider。
- 未 provider refresh/publish。
- 未 accepted latest switching。
- 未构建规则 baseline。
- 未进入 Phase2。
- 未触碰前端/API 或交易路径。

未发现新增分支。

## 4. 数据与 PIT 审查

确认：

- 2023-2024 Phase0E PIT archive 有 institutional 与 margin 数据。
- 2023-2024 本地价格与 TWII 有覆盖。
- 当前缺口在 qlib prediction 层。

PIT 风险点：

- 补预测必须使用对应 asof 的历史可见数据。
- 不得用 2026 或当前可见的未来特征生成 2023-2024 prediction。
- 若现有预测脚本无法证明 point-in-time inference，应停止补预测。
- 生成的 prediction 必须标明 source model、asof、input data latest allowed date、output path。

## 5. 模型/指标/样本审查

Coverage Diagnosis 没有做模型训练、单因子指标或规则 baseline，符合阶段限制。

对下一步的判断：

- 补 prediction 只是为 Phase1B 样本完整性服务，不是进入模型训练阶段。
- 补完后必须重新跑 Phase1B Full，并重新审查独立年份稳定性。
- 只有补齐 2023-2024 后，Phase1B 才能重新提出是否进入 Phase2。

## 6. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：无。

### Network Audit

本阶段报告声明未联网，脚本也限定为本地覆盖诊断。未发现下载、刷新、发布或外部请求证据。

### Console Audit

未发现 provider refresh/publish、accepted latest switching、monitor config save、monitor scan、alerts write、broker、quick-trade、orders、target position 或 target weight 证据。

### Text / Agent Semantics

未发现买入/卖出建议、目标仓位、收益承诺或上涨概率承诺。

### Verdict

只读研究边界通过。

## 7. 必须修复项

必须先修复预测层覆盖：

- 2023-2024 qlib prediction rows 为 0。
- 当前 Phase1B Full 不具备完整扩展窗口证据。
- 不得基于当前片段窗口进入 Phase2。

## 8. 可暂缓项

继续暂缓：

- 月营收。
- 新数据源。
- 重新拉取 Phase0E 数据。
- Scrapling。
- 全市场补齐。
- 模型训练。
- 规则 baseline。
- Phase2。
- provider refresh/publish。
- accepted latest switching。
- 前端/API。

## 9. 是否需要用户确认的问题

用户已明确指出“数据没有缺失，缺失的是预测层”，并允许审查者判断是否需要补预测。

审查者判断：需要补预测。

但执行者只能在下方受限范围内行动；若发现必须训练模型、联网、刷新 provider、生成生产 artifact 或改变 qlib baseline 定义，则必须停止并回报，不能自行继续。

## 10. 给执行者的下一步工作文档：Phase 1B Prediction Repair

### 10.1 目标

补齐 2023-01-01 至 2024-12-31 的本地 qlib prediction artifact，使 Phase1B Full 能在 2022、2023、2024、2025、2026 片段上重新验证正交特征相对 qlib rank/score 的增量。

本步骤不是训练阶段，不是规则 baseline，不是 Phase2。

### 10.2 允许输入

只允许使用：

- 本地已有 qlib/Option C 历史推理脚本。
- 本地已有模型、recorder、配置或 inference artifact。
- 本地已有价格、特征、universe、calendar。
- Phase0E normalized PIT archive。
- 当前已有 `option_c_historical_signal_backfill` 与 `option_c_daily_signal` 的目录结构作为输出格式参考。

### 10.3 允许产物

允许新增：

- `docs/tw_decision_model_orthogonal/PHASE1B_PREDICTION_REPAIR_REPORT_CN.md`
- `data_tw/experiments/decision_orthogonal/phase1b_prediction_repair_*`
- 若必须新建胶水脚本，允许：
  - `scripts/repair_tw_decision_orthogonal_phase1b_predictions.py`

允许写入的 prediction artifact 必须是实验/回填目录，不得写生产 provider：

- 推荐写入 `qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill/option_c_historical_backfill_20230101_20241231_research_only/.../prediction.csv`

如果执行者认为不能写入 qlib_pipeline 实验目录，则可写入：

- `data_tw/experiments/decision_orthogonal/phase1b_prediction_repair_predictions/`

但后续 Phase1B Full 重跑脚本必须明确读取这些 repaired predictions，且不得改变 qlib score 含义。

### 10.4 必做步骤

1. Inventory
   - 找出当前生成 2022、2025、2026 prediction 的脚本、配置、模型/recorder 来源。
   - 说明是否能复用同一 qlib baseline。
   - 输出 inventory 表：script、config、model/recorder、input data path、output path、是否只读、是否需要联网、是否需要训练。

2. Feasibility Gate
   - 若能用本地已有模型/recorder做历史 inference，则继续。
   - 若需要训练模型、联网下载、刷新 provider 或切换 accepted latest，则停止并写报告，不得执行补预测。

3. Repair
   - 只生成 2023-01-01 至 2024-12-31 的 prediction。
   - 每个 prediction.csv 至少包含 `datetime`、`instrument`、`score`。
   - 每个 asof 的 input latest date 必须不晚于 asof。
   - 不得读取 Phase0E 正交特征来生成 qlib prediction；qlib baseline 必须保持原定义。

4. Coverage Audit
   - 重新输出 2023-2024 prediction coverage：
     - month
     - prediction_file_count
     - prediction_rows
     - prediction_symbols
     - prediction_days
   - 重新检查 join drop-off。
   - 证明不再是 `no_prediction=1`。

5. Rerun Phase1B Full
   - 在补齐 prediction 后，重跑 Phase1B Full。
   - 输出新的报告：
     - `docs/tw_decision_model_orthogonal/PHASE1B_REPAIRED_FULL_EXECUTION_REPORT_CN.md`
   - 输出新的产物前缀：
     - `data_tw/experiments/decision_orthogonal/phase1b_repaired_full_*`

### 10.5 Repaired Phase1B Full 必须报告

必须包含：

- 2022-2026 每月样本量。
- 2023-2024 是否有样本。
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

### 10.6 明确禁止事项

- 禁止联网。
- 禁止使用 token。
- 禁止重拉数据。
- 禁止 Scrapling。
- 禁止新增数据源。
- 禁止训练模型。
- 禁止改变 qlib baseline 模型定义。
- 禁止用 Phase0E 正交特征生成 qlib prediction。
- 禁止写 Qlib bin/provider。
- 禁止 provider refresh/publish。
- 禁止 accepted latest switching。
- 禁止规则 baseline。
- 禁止 Phase2。
- 禁止前端/API。
- 禁止 monitor config save、monitor scan、alerts write。
- 禁止 broker、orders、quick-trade、target position、target weight。
- 禁止买入/卖出建议、收益承诺、上涨概率承诺。

## 11. 审查者最终裁决

- Coverage Diagnosis：通过。
- 主线范围：通过。
- 新增分支：未发现。
- 只读安全边界：通过。
- 数据层是否缺失：否。
- 预测层是否缺失：是，2023-2024 qlib prediction 缺失。
- 是否需要补预测：是。
- 是否允许进入 Phase2：否。
- 下一步：执行受限 Phase1B Prediction Repair。
