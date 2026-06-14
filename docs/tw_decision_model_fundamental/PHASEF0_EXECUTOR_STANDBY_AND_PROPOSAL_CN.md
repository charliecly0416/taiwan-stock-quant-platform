# Phase F0 执行者待命与 Proposal 报告

- 生成日期：`2026-06-11`
- 当前主线：台股 Decision Model 基本面 PIT 新主线
- 当前状态：等待审查者给出 Phase F0 工作文档

## 1. 已读取文档

- `docs/tw_decision_model_fundamental/EXECUTOR_PROMPT_CN.md`
- `docs/TW_STOCK_DECISION_FUNDAMENTAL_PIT_NEW_MAINLINE_PLAN_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE2D_CLOSURE_REVIEW_AND_STANDBY_WORK_CN.md`

## 2. 当前判断

fundamental 新主线已经由用户明确开启，但当前仓库中尚未存在审查者给出的：

- `docs/tw_decision_model_fundamental/PHASEF0_REVIEW_BASELINE_AND_NEXT_WORK_CN.md`

根据执行者 prompt 和旧主线 standby 文档，执行者不能在缺少审查者工作文档的情况下直接执行 Phase F0 数据源审计、脚本修改、联网、下载、样本构建或模型训练。

## 3. 建议的 Phase F0 工作范围

建议审查者下一步授权 Phase F0，只允许执行者做只读可行性审计：

- 盘点仓库内是否已有月营收/基本面相关脚本、数据目录、schema 或历史产物。
- 盘点是否已有 FinMind / Scrapling / 其他 provider 的月营收字段引用。
- 判断候选数据源是否可能提供 `announcement_date` 或等价可见时间。
- 设计 raw archive schema 草案。
- 明确是否需要用户授权联网和 token 才能进入 F0B POC。

Phase F0 不应：

- 联网。
- 使用 token。
- 下载新数据。
- 构建 Phase F1 样本。
- 训练模型。
- materialize 到 qlib。
- 写 provider。
- provider refresh/publish。
- accepted latest switching。
- 接入前端/API。
- 触碰 monitor、alerts、broker、quick-trade、orders。
- 输出买入/卖出建议、目标仓位、收益承诺或上涨概率承诺。

## 4. Phase F0 建议产物

建议审查者授权后，执行者生成：

- `docs/tw_decision_model_fundamental/PHASEF0_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/decision_fundamental/phasef0_data_source_inventory.csv`
- `data_tw/experiments/decision_fundamental/phasef0_pit_schema_proposal.json`
- `data_tw/experiments/decision_fundamental/phasef0_feasibility_summary.json`

如确有必要，可新增只读审计脚本：

- `scripts/audit_tw_decision_fundamental_phasef0.py`

## 5. 必须等待的审查者文档

请审查者先给出：

- `docs/tw_decision_model_fundamental/PHASEF0_REVIEW_BASELINE_AND_NEXT_WORK_CN.md`

执行者收到该文档后，才能继续执行 Phase F0。

## 6. 安全边界

本次只生成待命与 proposal 文档：

- 未联网。
- 未使用 token。
- 未下载数据。
- 未新增数据源。
- 未构建样本。
- 未训练模型。
- 未写 provider。
- 未 provider refresh/publish。
- 未 accepted latest switching。
- 未接前端/API。
- 未 monitor 写入。
- 未触碰交易路径。

## 7. 结论

- `phasef0_work_document_present=false`
- `phasef0_execution_started=false`
- `requires_reviewer_phasef0_work_document=true`
- `stop_and_wait_for_review=true`

当前必须停止，等待审查者给出 Phase F0 工作文档。
