---
created_at: 2026-08-25
route: MODEL_B_2026_ONLY_PIT_SOURCE_FEASIBILITY
phase: MB26R_2026_SOURCE_PIT_TRAINING_PURGE_CONTRACT_REPAIR_NO_SCORING
status: active
training_allowed: false
scoring_allowed: false
---

# MB26R 2026 Source/PIT 与 Training-Purge Contract Repair 主线

## 1. 目标

在不训练、不评分和不修改旧 artifact 的前提下，判断 2026-only Model B 是否能闭合：
37 条 `margin_short_available_at` 缺口，以及 E3 训练标签 maturity/purge 证据。

## 2. 允许范围

- 只读检查现有本地 E2/E3 manifest、source lineage、available_at、label maturity、fold
  ledger 和既有审计；
- 只允许从同一行已有 PIT 字段确定性恢复，禁止跨行或后见推断；
- 生成 isolated repair feasibility evidence 和 contract decision；
- 如需真实 source、新数据或修改旧 payload，必须停止并报告，不得自行修复。

## 3. 阶段

| 阶段 | 目标 | 训练/评分 |
|---|---|---|
| MB26R0 | 缺口身份、source 与 purge 合同复核 | 否 |
| MB26R1 | 独立审查并作 repair/stop 决策 | 否 |
| MB26R2 | 若完全闭合，另行申请 scoring gate | 需明确授权 |

## 4. 通过条件

37 条缺口必须具备 sample-date 可证明的 `available_at`、source lineage 和唯一恢复规则；
训练 labels 必须证明严格早于 2026 score 起点并满足 10 trading-day maturity/purge。
任一条无法证明即保持 unknown/quarantine，输出 STOP。

## 5. 禁止

- 不补零、不用 later/current 数据、不跨行猜测、不静默删行；
- 不修改 E1/E2/E3、旧模型、旧 score、runner、frozen window 或生产链路；
- 不训练、不评分、不 replay、不生成 ModelSignal/OrderIntent；
- 不访问 network、DB、OpenAI 或 provider。

## 6. 第一阶段

```text
执行 MB26R0_2026_SOURCE_PIT_AND_TRAINING_PURGE_REPAIR_FEASIBILITY_NO_SCORING
```
