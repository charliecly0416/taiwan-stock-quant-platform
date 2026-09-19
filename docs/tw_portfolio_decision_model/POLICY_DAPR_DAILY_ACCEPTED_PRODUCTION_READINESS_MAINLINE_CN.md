# DAPR Daily Accepted Production Readiness No-Publish Route 主线

创建时间：2026-07-17

## 目标

DAPR 用来把 daily auto 的自然证据整理成可审查的 accepted production readiness 判断：区分 raw-ready、provider/bridge-ready、Model A input-ready、signal-ready、latest-ready。

本路线 DAPR0-DAPR2 仅授权 no-publish evidence / contract / isolated candidate-or-blocker，不授权任何实际推进。

## 禁止边界

- 不触发 provider pull、provider refresh、provider publish。
- 不修改 formal qlib provider、calendar、instruments、features。
- 不执行 accepted latest switch、legacy latest switch、qlib refresh。
- 不构建或发布 readonly snapshot latest、Agent prompt latest。
- 不调用 OpenAI。
- 不写 monitor、broker、order、target_position、target_weight、quantity。

## 阶段

### DAPR0 Inventory

读取最新 daily auto 观察和最近 raw-ready target job。

本轮最新观察 job 为 `2026-07-18`，状态 `RAW_NOT_READY`，属于周末/非交易日观察；readiness target job 选择最近 raw-ready 交易日 `2026-07-17`。

输出：`data_tw/experiments/daily_accepted_production_readiness/dapr0_inventory/`

### DAPR1 Canonical Bridge Contract

定义 daily auto 从 `RAW_READY_PROVIDER_STALE` 进入 Model A input-ready 前必须满足的 accepted input 类型：

- formal provider/calendar 覆盖 target_asof；
- exact target_asof 的 validated same-lineage provider candidate；
- exact target_asof 的 validated canonical same-lineage local immutable bridge。

FinMind raw alone 不可作为 Model A canonical bridge。

输出：`data_tw/experiments/daily_accepted_production_readiness/dapr1_canonical_bridge_contract/`

### DAPR2 Isolated Candidate-Or-Blocker

按 DAPR1 合约检查当前 target_asof=`2026-07-17` 是否已有 accepted isolated input。

本轮结论：`BLOCKED_NEEDS_VALIDATED_EXACT_TARGET_PROVIDER_OR_BRIDGE`。

输出：`data_tw/experiments/daily_accepted_production_readiness/dapr2_isolated_bridge_candidate_or_blocker/`

### DAPR3 Exact-Target Provider/Bridge Candidate-Or-Blocker

接续 DAPR2 blocker，执行 no-pull exact-target local readiness 搜索与合约映射。

本轮结论：`BLOCKED_NO_EXACT_TARGET_PROVIDER_OR_BRIDGE`。

输出：`data_tw/experiments/daily_accepted_production_readiness/dapr3_exact_target_provider_bridge_candidate_or_blocker/`

## 当前结论

DAPR0-DAPR2 no-publish route 已完成。当前系统 raw 已覆盖 2026-07-17，但 formal provider/calendar 仍停在 2026-06-25，qlib accepted latest 仍停在 2026-07-08，PBPR2A-AC candidate 也只覆盖 2026-07-08。

因此，真正 latest 自动推进的当前阻塞不是 cron 没跑，而是缺少 exact-target validated canonical bridge/provider candidate。

DAPR3 已确认：本地没有 `2026-07-17` exact-target provider_candidate_readiness 或 canonical_bridge_readiness；FinMind raw 覆盖目标日，但 raw alone 不能解除 Model A canonical bridge readiness blocker。
