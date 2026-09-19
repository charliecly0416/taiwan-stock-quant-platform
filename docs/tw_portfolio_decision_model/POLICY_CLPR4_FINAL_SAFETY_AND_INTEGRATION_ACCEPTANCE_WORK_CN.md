---
created_at: 2026-07-10T06:31:07+00:00
status: work_document
route: CLPR_CONTROLLED_LATEST_PUBLISH_ROUTE
phase: CLPR4_FINAL_SAFETY_AND_INTEGRATION_ACCEPTANCE
target_asof: 2026-07-08
provider_pull_allowed: false
network_command_allowed: false
provider_publish_allowed: false
provider_accepted_latest_switch_allowed: false
qlib_accepted_latest_switch_allowed: false
legacy_option_c_latest_signal_switch_allowed: false
readonly_snapshot_publish_allowed: false
agent_prompt_build_allowed: false
agent_prompt_publish_allowed: false
model_scoring_allowed: false
strategy_replay_allowed: false
openai_call_allowed: false
monitor_write_allowed: false
order_or_trade_target_output_allowed: false
production_default_switch_allowed: false
---

# CLPR4 Final Safety And Integration Acceptance Work

## 1. Objective

CLPR4 的目标是最终只读审查 CLPR0-CLPR3 证据，确认 CLPR 路线可以关闭：

```text
controlled ModelSignalArtifact latest 已发布并校验通过
readonly snapshot latest 未变更
Agent latest 未变更
legacy option_c latest_signal 未变更
provider/qlib accepted latest 未变更
CLPR3 snapshot blocker 被明确记录
```

CLPR4 不发布 snapshot，不构建 snapshot，不运行 strategy replay，不生成 OrderIntent、
ReplayResult/NAV 或 Agent prompt。

## 2. Required Inputs

Executor 必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_CLPR_CONTROLLED_LATEST_PUBLISH_ROUTE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR0_CONTRACT_INVENTORY_AND_PROMOTION_PLAN_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR1_CANONICAL_SIGNAL_PROMOTION_DRY_RUN_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR2_CONTROLLED_SIGNAL_LATEST_PUBLISH_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR3_READONLY_SNAPSHOT_CANDIDATE_OR_BLOCKER_EXECUTION_REPORT_CN.md
data_tw/experiments/controlled_latest_publish_route/clpr3_readonly_snapshot_candidate_or_blocker/blocker_report.json
data_tw/experiments/controlled_latest_publish_route/clpr3_readonly_snapshot_candidate_or_blocker/artifact_manifest.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
```

## 3. Allowed Writes

CLPR4 只允许写：

```text
data_tw/experiments/controlled_latest_publish_route/clpr4_final_safety_and_integration_acceptance/*.json
scripts/build_tw_clpr4_final_safety_and_integration_acceptance.py
docs/tw_portfolio_decision_model/POLICY_CLPR4_FINAL_SAFETY_AND_INTEGRATION_ACCEPTANCE_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR_FINAL_ROUTE_CLOSURE_REVIEW_CN.md
```

## 4. Required Checks

必须证明：

```text
CLPR0 reviewer PASS
CLPR1 reviewer PASS or accepted PASS_WITH_CONDITIONS
CLPR2 reviewer PASS
CLPR3 verdict PASS_RECOMMEND_CLPR4_FINAL_ACCEPTANCE_WITH_SNAPSHOT_BLOCKER
controlled signal latest exists and checksum matches canonical manifest/signals
readonly_strategy_snapshot/latest.json unchanged from CLPR2/CLPR3 fingerprint
Agent daily prompt latest unchanged
legacy option_c latest_signal unchanged
provider/qlib accepted latest not switched
no monitor/broker/order/trade target output
artifact manifests checksum recompute pass
```

## 5. Pass Gate

CLPR4 可输出：

```text
PASS_CLOSE_CLPR_CONTROLLED_SIGNAL_LATEST_ONLY_WITH_SNAPSHOT_BLOCKER
FAIL_NEEDS_REPAIR
STOP_NEEDS_COORDINATOR_CONFIRMATION
```

PASS 表示 CLPR 路线关闭在 controlled signal latest 层；readonly snapshot 和 Agent prompt
latest 均未进入本路线发布范围。若用户要继续，应另开独立 readonly snapshot builder/publish
route 或 Agent prompt latest route。
