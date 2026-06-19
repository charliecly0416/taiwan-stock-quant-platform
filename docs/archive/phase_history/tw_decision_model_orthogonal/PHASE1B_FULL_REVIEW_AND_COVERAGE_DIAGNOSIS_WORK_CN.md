# Phase 1B Full 审查结论与覆盖缺口诊断工作文档

审查日期：2026-06-11

审查入口：

- `docs/tw_decision_model_orthogonal/PHASE1B_FULL_EXECUTION_REPORT_CN.md`

关联依据：

- `docs/tw_decision_model_orthogonal/PHASE0E_SCRAPLING_EXPLANATION_REVIEW_AND_PHASE1B_WORK_CN.md`
- `docs/tw_decision_model_orthogonal/REVIEWER_PROMPT_CN.md`
- `docs/TW_STOCK_DECISION_ORTHOGONAL_DATA_MODEL_PLAN_CN.md`

审查产物：

- `scripts/analyze_tw_decision_orthogonal_phase1b.py`
- `docs/tw_decision_model_orthogonal/PHASE1B_FULL_EXECUTION_REPORT_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE1B_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/decision_orthogonal/phase1b_full_*`
- `data_tw/experiments/decision_orthogonal/phase1b_*`

## 1. 本步审核结论

Phase 1B Full 的只读边界和主线范围基本通过，但不接受 `request_phase2_rules_baseline=true` 作为进入 Phase 2 的充分依据。

原因：

- 执行者没有联网、没有使用 token、没有重拉 Phase0E、没有写入 Qlib provider、没有训练模型、没有构建规则 baseline、没有自动进入 Phase2。
- 产物均在 Phase1B 或 Phase1B Full 实验命名空间内，未发现生产目录写入。
- 泄露审计显示 `available_at <= asof`、同日不可见、forward label date 等检查均为 0 bad rows。
- 但 Phase1B Full 样本覆盖不连续：月度样本只覆盖 2022-01 至 2022-12、2025-01 至 2026-05，缺少 2023 全年和 2024 全年。
- 报告写了 asof 范围为 2022-01-04 至 2026-05-29，容易让人误解为连续覆盖整个区间；实际证据不是完整 2022-2026 扩展窗口。
- 候选 RankIC 绝对值多在 0.02 至 0.034 左右，信号幅度不强；在缺两整年样本的情况下，不能直接进入规则 baseline。

因此：

- Phase1B Full 审查结论：`request_more_data_or_repair=true`。
- 暂不允许 Phase2 rules baseline。
- 下一步必须先做只读覆盖缺口诊断，解释为什么 2023-2024 没有样本，并给出是否可修复的方案。

## 2. 主线一致性审查

通过项：

- 使用 Phase0E normalized PIT archive。
- 使用本地已有 qlib ranking/score、价格与 TWII。
- 未使用 Phase0E excluded tail rows。
- 未启用月营收。
- 未新增外部数据源。
- 未联网。
- 未重拉 Phase0E。
- 未写入 Qlib bin/provider。
- 未 provider refresh/publish。
- 未 accepted latest switching。
- 未训练模型。
- 未构建规则 baseline。
- 未进入 Phase2。
- 未触碰前端/API 或交易路径。

注意项：

- 执行者新增了 `phase1b_full_*` 产物和 `PHASE1B_FULL_EXECUTION_REPORT_CN.md`。这属于 Phase1B 内的完整指标输出，不构成新分支。
- 脚本内同时支持 fast/full 两种指标模式，当前仍限定在 Phase1B 只读分析边界内，不构成模型分支。

未发现偏离主线或新增研究分支。

## 3. 样本与覆盖审查

报告给出的关键事实：

- Phase0E archive：150 symbols。
- Phase1B Full 样本：103 symbols，58354 rows。
- qlib prediction rows：59766。
- prediction file count：633。
- Top50 rows：28320。
- Top150 rows：58354。
- 泄露审计：pass。

月度样本覆盖：

- 2022-01 至 2022-12：有样本。
- 2023-01 至 2024-12：无样本。
- 2025-01 至 2026-05：有样本。

审查判断：

- 这是当前 Phase1B Full 最大问题。
- Phase0E PIT archive 本身覆盖到 2026-05-29，不足以解释 2023-2024 缺失；更可能是本地 qlib prediction artifact 在 2023-2024 缺失或命名/扫描范围未覆盖。
- 在缺 2023-2024 的情况下，年度、季度、月度稳定性都只能代表已覆盖片段，不能代表完整扩展窗口。
- 不能把当前结果作为 Phase2 规则 baseline 的准入证据。

## 4. 指标与 Gate 审查

正向证据：

- 多个 dealer/margin 相关特征 RankIC 为正。
- 与 qlib score 的 Spearman 相关大多处于低到中等水平。
- 泄露审计为 0 bad rows。

不足：

- RankIC 幅度偏小，Top 值约 0.034。
- 稳定性判断混合了年度和季度分段，不能替代完整年度覆盖。
- 缺少 2023 和 2024，使 market regime 覆盖明显不足。
- 当前报告没有解释为什么 2023-2024 没有样本，也没有证明缺失不会影响结论。

审查裁决：

- 不接受当前 `request_phase2_rules_baseline=true`。
- 改判为 `request_more_data_or_repair=true`。
- 必须先完成 Phase1B Coverage Diagnosis。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：报告中存在覆盖表述不够清楚的问题，但不是安全边界问题。

### Network Audit

Phase1B Full 报告声明未联网。脚本未发现 `requests`、Scrapling、Fetcher 或外部下载路径；输入来自本地 Phase0E archive、本地 qlib prediction、本地价格文件。

### Console Audit

未发现 provider refresh/publish、accepted latest switching、monitor config save、monitor scan、alerts write、broker、quick-trade、orders、target position 或 target weight 证据。

### Text / Agent Semantics

报告中 hit-rate 明确作为历史统计，不代表未来胜率或收益承诺。未发现真实买入/卖出建议、目标仓位、收益承诺或上涨概率承诺。

### Verdict

只读研究边界通过。

## 6. 是否需要停下来讨论的问题

当前问题不需要立即做交易或生产侧决策，但需要阻止进入 Phase2。

需要执行者先回答：

- 2023-2024 为什么完全没有样本？
- 是本地 qlib prediction artifact 缺失，还是脚本扫描路径、日期解析、文件命名或 join 逻辑导致遗漏？
- 如果缺失来自 qlib artifact，是否已有本地可用 artifact 可以补齐？
- 如果不能补齐，当前方向是否只能退回为“片段窗口证据”，并继续停在 Phase1B？

在这些问题回答前，不授权 Phase2。

## 7. 给执行者的下一步工作文档：Phase 1B Coverage Diagnosis

### 7.1 目标

对 Phase1B Full 的样本覆盖缺口做只读诊断，解释 2023-2024 缺失原因，并给出是否可以在不联网、不训练、不写 provider 的前提下补齐。

### 7.2 允许产物

允许新增：

- `docs/tw_decision_model_orthogonal/PHASE1B_COVERAGE_DIAGNOSIS_REPORT_CN.md`
- `data_tw/experiments/decision_orthogonal/phase1b_coverage_diagnosis_*`

如确有必要，可以新增只读诊断脚本：

- `scripts/diagnose_tw_decision_orthogonal_phase1b_coverage.py`

脚本只能读本地文件，只能写 `data_tw/experiments/decision_orthogonal/phase1b_coverage_diagnosis_*`。

### 7.3 必做诊断

执行者必须检查并报告：

1. Phase0E archive 覆盖
   - institutional/margin normalized rows 的 year/month 覆盖。
   - 证明 2023-2024 是否在 Phase0E archive 中存在。

2. 本地价格覆盖
   - `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/*.csv` 对样本 symbols 的 year/month 覆盖。
   - TWII 覆盖。
   - 判断标签是否导致 2023-2024 缺失。

3. qlib prediction 覆盖
   - `qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill/*/*/prediction.csv`
   - `qlib_pipeline/data_tw/experiments/option_c_daily_signal/*/prediction.csv`
   - 按 year/month 列出 prediction file count、prediction rows、symbols。
   - 明确 2023-2024 是否缺本地 qlib prediction。

4. join drop-off
   - 从 prediction rows 到 PIT join 再到 final sample 的逐步 row count。
   - 按 year/month 输出 drop reason：
     - no_prediction
     - no_price
     - no_twii_label
     - no_institutional_pit
     - no_margin_pit
     - label_horizon_missing

5. 当前 Gate 重判
   - 如果 2023-2024 可以用本地已有 artifact 补齐，提出 Phase1B Repair 方案，但不得直接执行。
   - 如果不能补齐，明确当前结果只能作为 2022 + 2025-2026 片段窗口验证，不得请求 Phase2。

### 7.4 禁止事项

- 禁止联网。
- 禁止下载或重拉任何数据。
- 禁止使用 token。
- 禁止 Scrapling。
- 禁止新增数据源。
- 禁止月营收。
- 禁止训练模型。
- 禁止生成新的 qlib predictions。
- 禁止规则 baseline。
- 禁止 Phase2。
- 禁止 Qlib bin/provider 写入。
- 禁止 provider refresh/publish。
- 禁止 accepted latest switching。
- 禁止前端/API。
- 禁止 monitor config save、monitor scan、alerts write。
- 禁止 broker、orders、quick-trade、target position、target weight。
- 禁止买入/卖出建议、收益承诺、上涨概率承诺。

### 7.5 完成标准

报告必须给出以下结论之一：

- `phase1b_repair_possible_with_local_artifacts=true`：仅当本地已有 qlib/price/PIT artifacts 能补齐 2023-2024，且不需要联网、不需要训练、不需要 provider 写入。
- `phase1b_repair_requires_new_artifacts=true`：若需要新 qlib predictions、重新训练、联网下载或生产 artifact，必须停下来等待用户确认。
- `phase1b_evidence_fragmentary_stop_phase2=true`：若无法补齐，则当前方向停在 Phase1B，不进入 Phase2。

任何结论都不得自动进入 Phase2。

## 8. 审查者最终裁决

- 主线范围：通过。
- 新增分支：未发现。
- 只读安全边界：通过。
- 泄露审计：通过。
- Phase1B Full 数据覆盖：不通过，缺 2023-2024。
- `request_phase2_rules_baseline=true`：不接受。
- 下一步：执行 Phase1B Coverage Diagnosis。
