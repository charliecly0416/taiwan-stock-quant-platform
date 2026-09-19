---
created_at: 2026-08-24
status: coordinator_mainline
route: MODEL_B_SAME_WINDOW_READONLY_INPUT_READINESS
current_phase: MB0_LINEAGE_WINDOW_AND_INPUT_READINESS
readonly_only: true
simulation_only: true
production_allowed: false
default_switch_allowed: false
replay_allowed: false
---

# Model B Same-Window Readonly Input Readiness 主线

## 1. 目标

判断 Model B/LTR 是否能够在 Model A baseline 的同一历史窗口 `2023-01-03..2026-05-07`、同一 `option_c_150` universe、同一 PIT/available_at 规则下，形成标准 `ModelSignalArtifact`，供后续只读策略比较使用。

## 2. 非目标

- 不训练、重训或调优 LTR；
- 不拼接 `2026-01-02..2026-05-07` 短窗口与 Model A 长窗口；
- 不把 broad research artifact 冒充 production lineage；
- 不运行 OrderIntent/replay；
- 不修改 Model B registry、default、latest、provider、qlib、cron、前后端或 Agent；
- 不访问 network/DB/OpenAI，不读取 future return/label/realized PnL；
- 不进入 optional-source/core registry 路线。

## 3. 冻结输入要求

- model id：`e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`；
- base dependency：同一 `e4_frozen_qlib_2018_2022` qlib lineage；
- requested window：`2023-01-03..2026-05-07`；
- universe：`option_c_150`，每天 coverage 必须可审计；
- LTR semantics：只在 qlib top50 内提供 `buy_score`/买入顺序，不改变 qlib candidate/sell boundary；
- PIT：每条 signal 的 `available_at <= signal_asof`，训练/OOS 分界和 feature lineage 必须有 manifest 证据；
- output：research-only standard `ModelSignalArtifact` candidate 或明确 `BLOCKED`。

## 4. 阶段计划

| phase | 目标 | 输出 | 放行 |
| --- | --- | --- | --- |
| MB0 | 盘点 lineage、窗口、universe、PIT、模型/特征 artifact 与标准 adapter 可行性 | readiness manifest、coverage/PIT audit、execution report | 独立审查 |
| MB1 | 若 MB0 可行，生成 research-only standard ModelSignalArtifact candidate | candidate artifact、validator、golden sample | 独立审查 |
| MB2 | 只读输入链路验收 | integration report | 通过后才可另开 replay route |

## 5. 停止条件

- 长窗口缺少可追溯 LTR score/model/feature lineage；
- 只能依赖短窗口或不同 universe；
- 需要网络/DB 临时补历史数据；
- PIT/available_at 无法证明；
- 需要修改生产 registry/default/latest；
- 发现 Model B 语义会改变 qlib top50 boundary。

## 6. 关闭条件

MB0 只能输出 `READY_FOR_MB1_RESEARCH_ONLY_ARTIFACT_BUILD` 或 `BLOCKED_MISSING_LONG_WINDOW_LTR_LINEAGE`。即使 READY，也不授权 replay、default/latest 或生产接入。
