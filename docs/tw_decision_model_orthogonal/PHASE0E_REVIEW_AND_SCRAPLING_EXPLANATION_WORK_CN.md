# 正交数据 Decision Model Phase 0E 审查结论与 Scrapling 说明要求

审查日期：2026-06-10

审查入口：

- `docs/tw_decision_model_orthogonal/PHASE0E_EXECUTION_REPORT_CN.md`

审查依据：

- `docs/tw_decision_model_orthogonal/REVIEWER_PROMPT_CN.md`
- `docs/TW_STOCK_DECISION_ORTHOGONAL_DATA_MODEL_PLAN_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE0E_USER_APPROVED_BACKFILL_WORK_CN.md`

审查产物：

- `scripts/build_tw_decision_orthogonal_phase0e_raw_archive.py`
- `data_tw/experiments/decision_orthogonal/phase0e_raw_archive/`
- `data_tw/experiments/decision_orthogonal/phase0e_download_status.csv`
- `data_tw/experiments/decision_orthogonal/phase0e_pit_snapshot_manifest.csv`
- `data_tw/experiments/decision_orthogonal/phase0e_coverage_report.csv`
- `data_tw/experiments/decision_orthogonal/phase0e_pit_validation_samples.csv`
- `data_tw/experiments/decision_orthogonal/phase0e_quality_flags_summary.csv`

## 1. 本步审核结论

Phase 0E 数据范围、PIT archive 和安全边界通过。当前已拉取数据可以作为后续 Phase 1B 审查的候选输入，不要求重新用 Scrapling 拉取。

但执行者没有使用 Scrapling，报告写明 `scrapling_used=false`。用户已明确表示：如果数据已经拉好且可用，不需要为了 Scrapling 重新拉取；但执行者必须回答为什么没有使用 Scrapling，是不知道如何使用，还是判断该 endpoint 不适合 Scrapling，或是其他原因。

因此，下一步不是重拉数据，而是要求执行者补充一份 Scrapling 未使用原因说明。

## 2. 主线一致性审查

通过项：

- 数据类别限定为法人筹码与融资融券。
- 月营收未触碰。
- universe 为 `tw_liquid_dyn` 窗口内 active days Top150，不是全市场。
- 时间范围为 2022-01-01 至 2026-06-10。
- 没有 materialize derived features。
- 没有 Qlib bin/provider 写入。
- 没有 provider refresh/publish。
- 没有 accepted latest switching。
- 没有 Phase 1 样本、单因子检验、模型训练、Phase 2、前端/API 或交易路径。

需要解释项：

- 未使用 Scrapling，与用户的偏好要求不一致；但按用户最新指示，不要求重拉，只要求说明原因。

## 3. Token 与泄露审查

审查结果：

- 未在审查范围内发现 token 原文。
- 下载命令为脱敏命令。
- download status 只记录 `token_used=True`。
- 脚本支持 `--token-stdin`，未把 token 写入报告。

token 处理方式通过。

## 4. 数据与 PIT 审查

Phase 0E 生成了可用的 PIT-normalized archive：

- 法人筹码：158834 PIT-normalized rows，150 symbols。
- 融资融券：156021 PIT-normalized rows，150 symbols。
- 两类数据 `available_at` 均非空。
- 实际 PIT-valid trade date 范围为 2022-01-03 至 2026-05-29。
- 两类各有 1529 raw rows 因无法生成下一交易日 `available_at` 被排除。

审查判断：

- 当前 archive 有后续 Phase 1B 审查价值。
- 后续 Phase 1B 必须使用 normalized PIT-valid rows，不得使用 excluded tail rows。
- T+1 conservative visibility proxy 可以继续作为审查口径，但仍须在 Phase 1B 报告中明确它不是官方发布时间声明。

## 5. 模型/指标/样本审查

Phase 0E 未涉及模型、指标回测或样本构建，符合阶段限制。

验证：

- 已执行 `python -m py_compile scripts/build_tw_decision_orthogonal_phase0e_raw_archive.py`，通过。

## 6. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：安全关键词仅出现在禁止范围或未执行声明中。

### Network Audit

Phase 0E 已按授权联网调用 FinMind endpoint。未发现月营收、全市场、provider refresh/publish、accepted latest switching 或交易路径。

### Console Audit

未发现 provider refresh/publish、accepted latest switching、monitor 写入、broker、quick-trade 或订单路径证据。

### Text / Agent Semantics

报告没有买入/卖出建议、目标仓位、收益承诺或上涨概率承诺。

### Verdict

只读研究边界通过。

## 7. 必须补充项

执行者必须补充说明：

- 为什么 Phase 0E 没有使用 Scrapling。
- 是不知道如何使用 Scrapling，还是判断 FinMind API endpoint 用 `requests` 更合适。
- 当时是否检查过 Scrapling 可用性。
- 如果未来再次要求使用 Scrapling，执行者会如何实现。
- 为什么这次未使用 Scrapling 不影响当前已拉取数据的可用性。

补充说明不得包含 token 原文。

## 8. 可暂缓项

继续暂缓：

- 月营收。
- 重拉 Phase 0E 数据。
- Scrapling parity backfill。
- Phase 2。
- 模型训练。
- materialize / Qlib bin/provider。
- 前端/API。

## 9. 是否需要用户确认的问题

当前不需要用户确认是否重拉。用户已明确表示：数据已拉好且可用时，不需要为了 Scrapling 重拉。

若执行者后续想重新拉取、扩大范围、启用月营收或进入 Phase 2，仍需另行确认。

## 10. 给执行者的下一步工作文档

### 10.1 目标

补充一份 Phase 0E 未使用 Scrapling 的原因说明，不重拉数据，不新增数据，不进入 Phase 1B。

### 10.2 允许产物

新增：

- `docs/tw_decision_model_orthogonal/PHASE0E_SCRAPLING_EXPLANATION_CN.md`

### 10.3 内容要求

该说明必须回答：

1. Phase 0E 为什么没有使用 Scrapling。
2. 是执行者不知道如何使用 Scrapling，还是认为 FinMind API 不需要 Scrapling。
3. 是否检查过 Scrapling 在当前环境中的可用性。
4. 如果未来强制要求 Scrapling，应采用什么实现方式。
5. 为什么本次 requests + API token 拉取的数据仍可用于后续审查。
6. 如何保证 token 没有泄露。

### 10.4 禁止事项

- 禁止重拉数据。
- 禁止联网。
- 禁止新增数据源。
- 禁止月营收。
- 禁止 Phase 1B 样本。
- 禁止单因子检验。
- 禁止模型训练。
- 禁止 Phase 2。
- 禁止 provider refresh/publish。
- 禁止 accepted latest switching。
- 禁止前端/API。
- 禁止 broker、orders、quick-trade、target position/target weight。

## 11. 审查者最终裁决

- Phase 0E 数据范围：通过。
- Phase 0E PIT archive：通过，实际 PIT-valid 至 2026-05-29。
- Phase 0E token 处理：通过。
- Phase 0E 安全边界：通过。
- 是否要求重拉 Scrapling 数据：否。
- 是否需要执行者补充说明：是。
- 是否允许进入 Phase 1B：暂缓，等待 Scrapling 未使用原因说明后再放行。
