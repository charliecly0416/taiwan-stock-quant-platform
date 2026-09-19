---
created_at: 2026-08-25
route: MODEL_B_2026_ONLY_PIT_SOURCE_FEASIBILITY
status: active
training_allowed: false
scoring_allowed: false
production_allowed: false
---

# Model B 2026-only PIT/Source Feasibility 主线

## 1. 目标

判断现有冻结 Model B 在 2026 年评测窗口是否具备当前合同要求的可复现、PIT-safe
输入。该路线不重训、不评分，不把结果接入生产。

## 2. 范围

- 评测候选窗口：旧 Model B 严格 OOS 记录覆盖的 `2026-01-02..2026-05-07`；
- 核验 Model B 的固定模型、78 特征、Qlib Top50 输入、available_at、source lineage、
  label maturity、purge、逐日完整性和未知缺口；
- 旧 Model B 结果只作为待核验输入，不自动视为当前规范 OOS。

## 3. 阶段

| 阶段 | 目标 | 训练/评分 |
|---|---|---|
| MB26F0 | 合同、模型和 2026 输入盘点 | 否 |
| MB26F1 | 逐日 PIT/source/coverage feasibility | 否 |
| MB26F2 | 独立审查并作 GO/STOP 决策 | 否 |
| MB26F3 | 若 GO，另行申请受控 2026 scoring | 需明确授权 |

## 4. 通过条件

只有当每个纳入评测日的 78 特征、Qlib Top50、availability、lineage、标签隔离和
完整性均可机械验证，且窗口和排除规则预先冻结，才可输出 `READY_FOR_MB26_SCORING_GATE`。
任何未知 source coverage、后见数据或不足 Top50 都必须 quarantine 并输出 STOP。

## 5. 禁止

- 不补零、不用 later/current 数据、不跨行推断、不静默跳过缺失行；
- 不修改旧 E1/E2/E3、旧模型、旧 score、窗口、runner 或生产 artifact；
- 不训练、不评分、不 replay、不生成 ModelSignal/OrderIntent；
- 不修改 provider、Qlib、latest、cron、frontend、backend 或 Agent。

## 6. 第一阶段

```text
执行 MB26F0_2026_ONLY_MODEL_B_CONTRACT_AND_INPUT_INVENTORY_NO_TRAINING
```
