# 正交数据 Decision Model Phase 0C 审查结论与 Phase 0D 工作文档

审查日期：2026-06-10

审查入口：

- `docs/tw_decision_model_orthogonal/PHASE0C_EXECUTION_REPORT_CN.md`

审查依据：

- `docs/tw_decision_model_orthogonal/REVIEWER_PROMPT_CN.md`
- `docs/TW_STOCK_DECISION_ORTHOGONAL_DATA_MODEL_PLAN_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE0C_USER_APPROVED_POC_WORK_CN.md`

审查产物：

- `scripts/build_tw_decision_orthogonal_phase0c_raw_archive.py`
- `data_tw/experiments/decision_orthogonal/phase0c_raw_archive/`
- `data_tw/experiments/decision_orthogonal/phase0c_download_status.csv`
- `data_tw/experiments/decision_orthogonal/phase0c_pit_snapshot_manifest.csv`
- `data_tw/experiments/decision_orthogonal/phase0c_coverage_report.csv`
- `data_tw/experiments/decision_orthogonal/phase0c_pit_validation_samples.csv`

## 1. 本步审核结论

Phase 0C 执行范围通过，但 Phase 1 暂不准入。

执行者没有偏离主线，也没有新增未授权分支。Phase 0C 仅对法人筹码与融资融券做受限 FinMind POC raw archive，未执行月营收、materialize derived features、Qlib bin/provider、accepted latest switching、Phase 1 样本、单因子检验、模型训练、规则 baseline、组合回放、前端/API 或交易路径。

Phase 0C 成功生成非零 raw archive：

- 法人筹码：50 symbols，5291 normalized rows。
- 融资融券：50 symbols，5300 normalized rows。

但是当前 raw archive 仍有 PIT 质量缺口：

- 法人筹码有 50 行缺失 `available_at`。
- 融资融券有 50 行缺失 `available_at`。
- 缺失集中在区间尾部 `2025-09-30`，原因是脚本只在 `start/end` 区间内加载交易日历，无法为最后一个 raw trade date 找到下一交易日。
- 覆盖率报告中 `observed_rows` 可大于 `expected_trading_days`，但没有单独报告 extra dates / PIT-valid rows。

因此，Phase 0C 不能直接进入 Phase 1。需要先执行 Phase 0D：不联网的 PIT 修复与 gate confirmation。

## 2. 主线一致性审查

通过项：

- 只执行用户授权的法人筹码与融资融券 POC。
- 时间范围为 `2025-05-01` 到 `2025-09-30`，小于原授权上限。
- symbol 数量为 50，符合小 universe POC。
- 月营收未执行，符合暂缓要求。
- 产物写入 `data_tw/experiments/decision_orthogonal/phase0c_*` 与专用 raw archive 目录。
- 没有写 Qlib bin、provider、accepted latest 或前端/API。
- 没有构建 Phase 1 样本或训练模型。

未发现项：

- 未发现全市场补齐。
- 未发现无限期历史回填。
- 未发现计划外数据源。
- 未发现 materialize/screen/ablation。
- 未发现真实交易相关路径。

## 3. 数据与 PIT 审查

Phase 0C 证明了两类数据可以通过 FinMind 取得非零行级原始数据，但当前只达到 POC raw archive 级别，尚未达到 Phase 1 样本准入级别。

已满足：

- 每类数据有非零 row-level archive。
- 每类数据有 `symbol`、`stock_id`、`trade_date`、`data_source`、`raw_snapshot_id`、`fetched_at`。
- 大部分行有保守 T+1 `available_at`。
- 有 raw snapshot manifest、download status、coverage report、PIT validation samples。

未满足：

- 不是所有行都有 `available_at`。
- 覆盖率没有区分 raw observed rows 与 PIT-valid rows。
- 对 `2025-09-30` 尾部行的处理未闭合。
- T+1 规则仍需在 Phase 0D 报告中明确作为保守可见性规则，不能被解释为官方发布时间。

审查者接受保守 T+1 作为 Phase 0D 继续验证口径，前提是：

- 任何进入 Phase 1 的行必须满足 `available_at` 非空。
- Phase 1 构样本时只能使用 `available_at <= asof` 的行。
- 对无法生成下一交易日的尾部行必须修复或排除，不得静默进入样本。

## 4. 模型/指标/样本审查

本阶段未涉及模型、指标回测或样本构建，符合 Phase 0C 限制。

未发现：

- Phase 1 samples。
- 单因子 IC。
- 分组收益检验。
- 规则 baseline。
- Risk Filter Model。
- 组合回放。

验证：

- 已执行 `python -m py_compile scripts/build_tw_decision_orthogonal_phase0c_raw_archive.py`，通过。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：安全关键词仅出现在禁止范围或未执行声明中。

### Network Audit

Phase 0C 已按用户授权联网调用 FinMind endpoint：`https://api.finmindtrade.com/api/v4/data`。未发现超出授权范围的数据类别；只调用法人筹码与融资融券 dataset。

### Console Audit

未发现 provider refresh/publish、accepted latest switching、monitor 写入、broker、quick-trade 或订单路径证据。

### Text / Agent Semantics

报告没有给出买入/卖出建议、目标仓位、收益承诺或上涨概率承诺。

### Verdict

只读研究边界通过。

## 6. 必须修复项

Phase 1 前必须修复：

- `available_at` 缺失：两类数据各 50 行缺失，必须修复或标记为不可进入 Phase 1。
- coverage 口径：必须新增 PIT-valid coverage，不得只报告 raw observed coverage。
- 尾部交易日：必须加载 `end` 之后的交易日历窗口，或明确过滤最后无法生成 `available_at` 的 raw rows。
- quality flags：必须汇总每类每 symbol 的 `quality_flags` 原因，不能只给 count。
- Phase 0C Gate：必须重新以 PIT-valid rows 而非 raw rows 判断。

这些修复不需要用户新增授权，因为不要求联网、不下载新数据、不扩大数据范围。

## 7. 可暂缓项

继续暂缓：

- 月营收。
- 扩大时间范围。
- 扩大 symbol universe。
- materialize derived features。
- Qlib bin/provider。
- Phase 1 样本。
- 单因子/分组检验。
- 模型训练。
- 前端/API。

## 8. 是否需要用户确认的问题

当前不需要用户确认。

Phase 0D 只允许基于已有 Phase 0C raw archive 做不联网修复与 gate confirmation，不新增数据源、不下载、不 materialize、不进入 Phase 1。

如果执行者想扩大时间范围、增加 symbol、重跑 FinMind、补月营收或进入 Phase 1，必须再次等待用户确认。

## 9. 给执行者的 Phase 0D 工作文档

### 9.1 目标

修复 Phase 0C POC raw archive 的 PIT 质量问题，并给出是否具备进入 Phase 1 数据前提的确认报告。

Phase 0D 不是新数据补齐阶段，不允许联网或下载。

### 9.2 允许范围

允许：

- 读取 Phase 0C raw archive。
- 读取本地 qlib/价格交易日历。
- 使用 `end` 之后的本地交易日历为尾部 row 生成下一交易日 `available_at`。
- 或者明确过滤无法生成 `available_at` 的尾部 row。
- 生成 PIT-valid cleaned view。
- 重新计算 coverage、missing、extra dates、quality flags。
- 写中文执行报告。

禁止：

- 禁止联网。
- 禁止重新调用 FinMind。
- 禁止新增数据源。
- 禁止扩大时间范围或 symbol universe。
- 禁止月营收。
- 禁止 materialize derived features。
- 禁止写 Qlib bin/provider。
- 禁止 accepted latest switching。
- 禁止 Phase 1 样本。
- 禁止单因子检验。
- 禁止模型训练。
- 禁止前端/API。
- 禁止 broker/orders/quick-trade/target position/target weight。

### 9.3 建议新增文件

建议新增：

- `scripts/confirm_tw_decision_orthogonal_phase0d_pit_gate.py`
- `data_tw/experiments/decision_orthogonal/phase0d_pit_clean_manifest.csv`
- `data_tw/experiments/decision_orthogonal/phase0d_pit_valid_coverage_report.csv`
- `data_tw/experiments/decision_orthogonal/phase0d_quality_flags_summary.csv`
- `data_tw/experiments/decision_orthogonal/phase0d_phase1_allowed_fields.csv`
- `docs/tw_decision_model_orthogonal/PHASE0D_EXECUTION_REPORT_CN.md`

如生成 cleaned CSV，必须放在：

- `data_tw/experiments/decision_orthogonal/phase0d_pit_clean/`

### 9.4 修复规则

执行者必须二选一处理尾部缺失 `available_at`：

1. 首选：从本地价格/qlib calendar 加载 `end` 之后至少 10 个自然日的交易日，补出下一交易日 `available_at`。
2. 若无法获得下一交易日：保留 raw row，但在 cleaned view 中排除，并标记 `phase1_allowed=false`。

不得把 `available_at` 填成 `trade_date`。

不得把 `fetched_at` 作为历史 `available_at`。

### 9.5 输出指标要求

Phase 0D 报告必须包含：

- raw rows。
- rows with non-empty `available_at`。
- rows excluded due to missing `available_at`。
- PIT-valid coverage rate。
- raw observed coverage rate。
- extra dates count。
- missing dates count。
- duplicate rows count。
- quality flag reason counts。
- per-category and per-symbol summary。

### 9.6 Phase 0D Gate

允许进入 Phase 1 的最低数据前提：

- 至少一类数据有非零 PIT-valid rows。
- PIT-valid rows 都有 `symbol`、`trade_date`、`available_at`、`data_source`、`raw_snapshot_id`。
- `available_at > trade_date` 或至少不早于保守可见规则。
- coverage report 明确分开 raw rows 与 PIT-valid rows。
- quality flags 不影响核心字段可用性，或已明确排除。
- 未发生任何联网、materialize、Phase 1 样本或模型越界。

如果 Phase 0D 通过，也只能建议进入 Phase 1 审查，不得自行构建 Phase 1 样本。

## 10. 审查者最终裁决

- Phase 0C 执行范围：通过。
- Phase 0C 安全边界：通过。
- 是否偏离主线：否。
- 是否新增未授权分支：否。
- Phase 0C Gate：条件性通过，但存在 PIT 尾部质量缺口。
- 是否允许进入 Phase 1：否。
- 下一步：执行 Phase 0D，不联网修复/确认 PIT gate。
