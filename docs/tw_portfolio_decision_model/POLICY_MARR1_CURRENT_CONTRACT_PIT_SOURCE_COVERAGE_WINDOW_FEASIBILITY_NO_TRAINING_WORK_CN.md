---
route: MODEL_AB_RERUN_CURRENT_CONTRACT_MAINLINE
phase: MARR1_CURRENT_CONTRACT_PIT_SOURCE_COVERAGE_WINDOW_FEASIBILITY_NO_TRAINING
training_allowed: false
scoring_allowed: false
replay_allowed: false
production_allowed: false
---

# MARR1 当前合同 PIT、Source Coverage 与共同窗口 Feasibility 工作单

## 1. 目标

只读评估 Model A/B 在当前合同下是否存在合法、可复现、可共同比较的候选窗口，为后续
MARR2 冻结提供证据。不得训练、评分、回放或修改任何既有/生产 artifact。

## 2. 允许范围

- 读取本地既有 metadata、manifest、feature schema、calendar、lineage 和已封存统计；
- 使用流式统计核验日期、instrument、行数、Top50 完整性、`available_at`、label maturity、
  purge 和候选连续窗口；
- 仅在 `data_tw/experiments/model_ab_current_contract_rerun/` 下写入 MARR1 isolated
  evidence、manifest、统计报告、forbidden-scope audit 和 execution report；
- 如需 synthetic fixture，只能使用 `SYNTHETIC_*` 标识，不能混入真实结果。

## 3. 必须回答的问题

1. Model A 与 Model B 各自的 feature/source/date coverage 是否满足当前 PIT 合同。
2. `available_at <= decision_cutoff`、label maturity 和 purge 是否可逐日证明。
3. 1,297 条 margin-short gaps 能否由既有本地证据合法重建；不能时必须保持
   `unknown/quarantine`，不得转为 absent、neutral 或 zero-fill。
4. 是否存在足够长、连续、完整、A/B 共同使用的候选窗口。
5. 候选窗口的 exact fit/validation/score 日期、行数、Top50 数量和 coverage 统计。
6. 哪些 Model A/B 参数和比较指标可以在 MARR2 中冻结。

## 4. 严格禁止

- 禁止读取新外部 source、network、DB 或 OpenAI；
- 禁止修改 legacy artifact、E1/E2/E3、frozen window、runner、latest、provider、Qlib、
  cron、frontend、backend、Agent；
- 禁止训练、评分、回放、ModelSignal、OrderIntent、absence/zero-fill 或任何生产写入；
- 禁止删除不完整日期后宣称 full-window OOS；禁止为兼容旧结果放宽 PIT 或 coverage。

## 5. 必须输出

- exact input inventory 与 aggregate SHA-256；
- PIT/source/coverage/label/purge audit；
- 按日期和 instrument 的流式统计及完整性结果；
- candidate window ledger，含 blocked/eligible 原因；
- protected8 before/after fingerprints；
- forbidden-scope audit、execution report 和明确结论：
  `READY_FOR_MARR2_FREEZE` 或 `STOP_MARR1_NO_LEGAL_COMMON_WINDOW`。

任何关键证据无法证明时必须 STOP，不得推断或补齐。
