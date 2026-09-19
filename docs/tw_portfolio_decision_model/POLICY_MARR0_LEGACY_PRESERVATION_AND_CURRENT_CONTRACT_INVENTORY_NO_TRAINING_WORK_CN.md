---
route: MODEL_AB_RERUN_CURRENT_CONTRACT_MAINLINE
phase: MARR0_LEGACY_PRESERVATION_AND_CURRENT_CONTRACT_INVENTORY_NO_TRAINING
training_allowed: false
production_allowed: false
---

# MARR0 Legacy 保全与当前合同盘点工作单

## 目标

建立 legacy artifact 的只读清单和当前 Model A/B 合同盘点，确认新重跑不能继承哪些旧
假设。不得训练、评分、修改旧 artifact 或生产链路。

## 必须输出

- legacy artifact path/type/size/SHA-256/status；
- 已知训练、验证、评分窗口与 in-sample/OOS 分类；
- Model A/B 特征、source、available_at、lineage、coverage 缺口；
- 当前可合法重跑的候选窗口，以及明确 blocker；
- protected-scope audit 和 execution report。

## 禁止

不得读取新外部 source，不得修改 E1/E2/E3、旧结果、frozen window、runner、latest、
provider、Qlib、cron、frontend、backend、Agent，不得训练、评分、回放或生成交易 artifact。

## 结果

只能输出 `READY_FOR_MARR1_FEASIBILITY` 或 `STOP_MARR0_INVENTORY_BLOCKED`。
