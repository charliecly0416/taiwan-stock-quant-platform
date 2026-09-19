---
created_at: 2026-08-24
route: MODEL_AB_RERUN_CURRENT_CONTRACT_MAINLINE
status: active
production_allowed: false
training_allowed: false
---

# Model A/B 当前合同规范化重跑主线

## 1. 目标

在不改写 legacy 结果的前提下，使用当前 PIT、source completeness、lineage、hash
和 OOS 合同，重新建立 Model A 与 Model B 的可复现共同评测基线。

## 2. Legacy 保全

既有训练、score、replay 和报告原样保留，标记为 `legacy_exploratory`。不得删除、覆盖、
补写缺失 lineage，或将其直接作为当前标准下的 OOS 证据。

## 3. 新主线非目标

- 不修订旧 payload；
- 不用 later/current 数据倒灌历史；
- 不零填补或静默跳过不完整日期；
- 不接入 production/latest、frontend、Agent、strategy replay、OrderIntent；
- feasibility 未通过前不训练 Model A/B。

## 4. 阶段

| 阶段 | 目标 | 训练 |
|---|---|---|
| MARR0 | legacy 保全、当前合同和输入盘点 | 否 |
| MARR1 | PIT/source coverage/窗口 feasibility | 否 |
| MARR2 | 冻结合法共同窗口与 exact input bundle | 否 |
| MARR3 | Model A/B 受控 OOS 训练评分 | 需独立审查及明确授权 |
| MARR4 | Model A/B 对比与策略只读评估 | 另行放行 |

## 5. 当前决策门

MARR1 必须回答：

- 哪些特征和日期具备完整 `available_at` 与 source lineage；
- 是否存在可供 A/B 共同使用的连续窗口；
- Model B 的 margin-short 缺口是否必须排除该特征族；
- 不能满足 coverage 的日期如何整体 quarantine；
- 固定 Model A/B 参数、fold、purge 和比较指标。

若没有合法共同窗口，输出 `STOP_MARR1_NO_LEGAL_COMMON_WINDOW`，不训练。

## 6. 证据要求

每阶段必须输出 exact input manifest、SHA-256、PIT/coverage audit、fold ledger、
forbidden-scope audit 和独立 reviewer report。所有新结果写入 isolated research root，
`production_allowed=false`。

## 7. 保护边界

protected latest、provider、Qlib、cron、frontend、backend、Agent、strategy、
monitor/broker/order/target 均不得修改。旧 artifact 只读。

## 8. 第一条执行命令

```text
执行 MARR0_LEGACY_PRESERVATION_AND_CURRENT_CONTRACT_INVENTORY_NO_TRAINING
```
