---
created_at: 2026-07-10T06:17:24+00:00
status: work_document
route: CLPR_CONTROLLED_LATEST_PUBLISH_ROUTE
phase: CLPR3_READONLY_SNAPSHOT_CANDIDATE_OR_BLOCKER
target_asof: 2026-07-08
provider_pull_allowed: false
network_command_allowed: false
provider_publish_allowed: false
provider_accepted_latest_switch_allowed: false
qlib_accepted_latest_switch_allowed: false
legacy_option_c_latest_signal_switch_allowed: false
canonical_signal_latest_required: true
readonly_snapshot_publish_allowed: false
agent_prompt_build_allowed: false
agent_prompt_publish_allowed: false
model_scoring_allowed: false
strategy_replay_allowed: false
openai_call_allowed: false
monitor_write_allowed: false
order_or_target_output_allowed: false
production_default_switch_allowed: false
---

# CLPR3 Readonly Snapshot Candidate Or Blocker Work

## 1. Objective

CLPR3 的目标是只读检查 CLPR2 controlled signal latest 是否足以进入 readonly
snapshot publish 的候选阶段，或输出 blocker。

CLPR3 默认不发布 readonly snapshot latest。若发现 snapshot 需要 strategy replay、
OrderIntent、ReplayResult/NAV、provider/qlib accepted latest 或 Agent prompt build，必须输出
blocker，不得伪造 snapshot payload。

## 2. Required Inputs

Executor 必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_CLPR_CONTROLLED_LATEST_PUBLISH_ROUTE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR3_READONLY_SNAPSHOT_CANDIDATE_OR_BLOCKER_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR2_CONTROLLED_SIGNAL_LATEST_PUBLISH_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR2_CONTROLLED_SIGNAL_LATEST_PUBLISH_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/READONLY_STRATEGY_SNAPSHOT_CONTRACT_CN.md
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/manifest.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/signals.csv
```

## 3. Allowed Writes

CLPR3 只允许写：

```text
data_tw/experiments/controlled_latest_publish_route/clpr3_readonly_snapshot_candidate_or_blocker/*.json
scripts/build_tw_clpr3_readonly_snapshot_candidate_or_blocker.py
docs/tw_portfolio_decision_model/POLICY_CLPR3_READONLY_SNAPSHOT_CANDIDATE_OR_BLOCKER_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR4_FINAL_SAFETY_AND_INTEGRATION_ACCEPTANCE_WORK_CN.md
```

## 4. Required Checks

必须证明：

```text
CLPR2 reviewer PASS
controlled signal latest exists and matches CLPR2 plan
canonical manifest/signals checksums match CLPR2 evidence
readonly_strategy_snapshot/latest.json pre-state fingerprinted only
snapshot input contract can or cannot be satisfied without strategy replay
no legacy option_c latest_signal change
no Agent latest change
no provider/qlib accepted latest switch
no monitor/broker/order/target output
```

## 5. Stop Conditions

必须 STOP 或输出 blocker：

```text
CLPR2 review missing or not PASS
controlled signal latest missing or checksum mismatch
readonly snapshot would require strategy replay
readonly snapshot would require OrderIntentArtifact
readonly snapshot would require ReplayResult/NAV generation
readonly snapshot would require provider/qlib accepted latest switch
Agent prompt latest is requested
frontend/default switch is requested
monitor/broker/order/target output is requested
```

## 6. Pass Gate

CLPR3 PASS 可以是以下之一：

```text
PASS_RECOMMEND_CLPR4_FINAL_ACCEPTANCE_WITH_SNAPSHOT_BLOCKER
PASS_RECOMMEND_SEPARATE_READONLY_SNAPSHOT_PUBLISH_ROUTE
STOP_NEEDS_COORDINATOR_CONFIRMATION
```

CLPR3 不得自行扩大为 snapshot publish。
