---
route: MODEL_AB_RERUN_CURRENT_CONTRACT_MAINLINE
phase: MARR0_LEGACY_PRESERVATION_AND_CURRENT_CONTRACT_INVENTORY_NO_TRAINING
review_status: PASS_MARR0
training_allowed: false
production_allowed: false
---

# MARR0 Legacy 保全与当前合同盘点独立审查

## 1. 审查范围

本审查只读取以下本地材料：主线文档、MARR0 工作单、隔离目录中的
`legacy_inventory.csv`、`contract_gap_matrix.csv`、`manifest.json`、
`forbidden_scope_audit.json` 和 `execution_report.md`。未读取新外部 source，未执行训练、
评分或回放。

## 2. 结论

```text
PASS_MARR0
```

MARR0 的盘点证据与主线和工作单一致，可以进入 MARR1 feasibility。MARR1 仍严格限定为
metadata、流式统计和候选窗口 feasibility，不得训练或评分。

## 3. 独立核对结果

### 3.1 Legacy 保全

- legacy inventory 登记了 Model A/Model B 的 manifest、model、score 和 lineage/audit 文件，
  并记录 path、类型、窗口、规模、分类和 SHA-256 状态。
- execution report 与 forbidden-scope audit 均声明旧 artifact 未修改；本轮没有把旧结果
  重新标记成 current-contract 结果，也没有覆盖旧文件。
- 旧结果仍可作为 exploratory reference，但不能直接升级为正式 OOS、ModelSignal、
  OrderIntent 或 production/default 输入。

### 3.2 Model A 分类

- Model A 记录的 Qlib 训练窗口为 `2018-01-01..2022-12-31`，score 窗口为
  `2023-01-01..2026-05-07`，旧 score 记录为 40,100 行。
- 该日期和 artifact identity 已被登记，但逐行 `available_at`、source completeness、
  immutable lineage 和当前 fold 合同尚未完成，因此必须标为“待当前合同重验”，不能直接
  作为新主线正式证据。

### 3.3 Model B 分类

- Model B 的训练窗口为 `2023-01-01..2025-12-31`；对应训练分数是 in-sample，不能作为
  OOS 证据。
- 明确的测试/OOS 记录为 `2026-01-01..2026-05-07`，共 79 日、11,822 行，属于部分
  OOS，不代表 full-window OOS。
- 既有审计识别出 top50 中 1,297 条 margin-short source/PIT key 缺失；这些记录不能被
  当作 structural absent、neutral、零值或以 later/current 数据补齐。

### 3.4 当前合同缺口

`contract_gap_matrix.csv` 正确列出 input identity、窗口、feature schema、`available_at`、
coverage、labels、lineage 和 reproducibility 等 OPEN 项。尤其是完整共同窗口尚未证明，
不得为了兼容旧结果而放宽 PIT 或 coverage 合同。

### 3.5 保护边界

`forbidden_scope_audit.json` 报告：

- protected entries 共 8 个，且 `protected_unchanged=true`；
- 未修改 E1/E2/E3、runner、production latest、provider、Qlib、cron、frontend、backend
  或 Agent；
- 未访问 network、DB 或 OpenAI；
- 未训练、评分、回放、生成交易 artifact 或 absence/zero-fill payload。

当前 worktree 存在其他既有 dirty changes；这些变更不归因于 MARR0，本审查不回滚也不纳入
本阶段变更判断。

## 4. 放行边界

仅放行以下下一步：MARR1 当前合同 PIT/source coverage/window feasibility。MARR1 必须只
产生 isolated evidence/report，核验候选窗口和逐日统计；不能修改 legacy、E1/E2/E3、
frozen window、runner 或生产路径，不能训练、评分或回放。
