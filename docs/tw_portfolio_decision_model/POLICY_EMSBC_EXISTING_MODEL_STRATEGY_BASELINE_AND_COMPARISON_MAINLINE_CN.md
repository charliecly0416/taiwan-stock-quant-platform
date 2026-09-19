---
created_at: 2026-08-24
status: coordinator_mainline
route: EXISTING_MODEL_STRATEGY_BASELINE_AND_COMPARISON
current_phase: EMSBC0_BASELINE_CONTRACT_AND_READONLY_EVIDENCE
readonly_only: true
simulation_only: true
production_allowed: false
default_switch_allowed: false
daily_auto_change_allowed: false
---

# Existing Model Strategy Baseline And Comparison 主线

## 1. 目标

在当前 150 股票、已验收的 Model A / Model B 和既有策略证据基础上，冻结一套统一的模型-策略比较口径，形成可复现的只读 baseline evidence。第一阶段只回答：

```text
Model A + default strategy
Model A + hold-rank-buffer-100 anchor
Model B/LTR + default strategy
Model B/LTR + hold-rank-buffer-100 anchor
```

在同一窗口、同一执行价、同一费用税费、同一初始组合状态下，哪些差异来自模型，哪些差异来自策略。

## 2. 非目标

- 不训练或重训模型；
- 不新增策略机制、不调阈值、不做网格搜索；
- 不修改 provider、qlib、accepted latest、legacy latest、DAPR18、cron、前后端或 Agent；
- 不修改 production default，不发布任何 latest；
- 不连接 broker/order/target，不生成真实交易；
- 不使用 future return、label、realized PnL 作为策略输入；
- 不把单日 2026-08-21 freshness artifact 当作历史绩效证据；
- 不启动 optional-source/core registry 路线。

## 3. 冻结基线

- universe：当前 `option_c_150`，必须证明 150 支覆盖；
- Model A：`e4_frozen_qlib_2018_2022`；
- Model B：`e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`，LTR 只在 qlib top50 内重排；
- default strategy：`top50_exit_one_worst_sell`；
- comparison anchor：`top50_hold_rank_buffer_100`，只读 research candidate，不是 default；
- execution：signal date 后下一可交易日 `next_open`；
- costs：commission `0.001425`、sell tax `0.003`、研究 lot policy `10`；
- initial equity：`1,000,000`，cash-only；
- required metrics：net return、max drawdown、turnover、fee、tax、buy/sell/skip count、holding concentration、coverage 和 baseline delta；
-首选历史窗口：同 lineage、PIT-safe、可追溯的既有 OOS window；窗口不以结果后验选择。

## 4. 阶段计划

| phase | 目标 | 输出 | 放行 |
| --- | --- | --- | --- |
| EMSBC0 | 冻结口径并生成四组合只读 baseline evidence | contract、comparison manifest、metrics、coverage/forbidden audit、执行报告 | 独立审查通过 |
| EMSBC1 | 分离模型效应与策略效应 | 对照分析、机制归因、下一工作单 | baseline 输入同 lineage 且无口径冲突 |
| EMSBC2 | 单一新策略候选 readiness | strategy dependency、PIT/input contract | 候选可证伪且不重复已关闭机制 |
| EMSBC3+ | readonly OrderIntent、replay、稳健性和收口 | 标准 artifacts 与独立 reviews | 仅研究 GO/NO-GO，不自动生产化 |

## 5. EMSBC0 执行边界

执行者只能读取已有 standard ModelSignalArtifact、strategy dependency、OrderIntent/Replay artifacts、PriceStore manifest 和 registry；输出只能落在本路线独立 research 目录和本路线文档。不得重写历史 artifact，不得读取模型私有训练输出，不得把 replay 输出反向作为策略输入。

## 6. 审查要求

审查者必须核对四组合是否使用同一窗口和成本口径、Model A/B 是否通过标准 artifact、anchor 是否仍标记 research-only、指标是否包含收益之外的风险与覆盖指标，并审查 forbidden scope。发现窗口漂移、模型/策略混淆或结果不可复现时必须 FAIL_NEEDS_REPAIR。

## 7. 关闭条件

EMSBC0 只有在 comparison evidence 可重放、四组合边界清晰、没有 production/latest mutation、且独立审查通过后，才能进入 EMSBC1。EMSBC0 不授权策略默认切换、latest 发布或交易动作。
