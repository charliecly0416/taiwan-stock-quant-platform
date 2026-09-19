---
created_at: 2026-07-10T10:02:22+00:00
status: review
route: ADOR_AUTOMATIC_DAILY_ORCHESTRATION_ROUTE
phase: ADOR1_R_ARTIFACT_MANIFEST_SELF_CHECK_REPAIR
reviewer: ADOR1_R
target_reference_asof: 2026-07-08
verdict: PASS_RECOMMEND_ADOR1_REVIEW_REOPEN_AND_ADOR2_GATE
ador1_review_reopen_allowed: true
ador2_allowed: true
ador2_scope: explicit_non_default_gate_only
provider_pull_allowed: false
network_command_allowed: false
provider_publish_allowed: false
provider_accepted_latest_switch_allowed: false
qlib_accepted_latest_switch_allowed: false
legacy_option_c_latest_signal_switch_allowed: false
model_scoring_allowed: false
strategy_replay_allowed: false
order_intent_allowed: false
replay_result_allowed: false
readonly_snapshot_latest_write_allowed: false
agent_prompt_latest_write_allowed: false
openai_call_allowed: false
monitor_write_allowed: false
order_or_trade_target_output_allowed: false
production_default_switch_allowed: false
daily_automation_default_switch_allowed: false
cron_switch_allowed: false
---

# ADOR1_R Artifact Manifest Self-Check Repair Review

## 1. Verdict

```text
PASS_RECOMMEND_ADOR1_REVIEW_REOPEN_AND_ADOR2_GATE
```

允许重新提交 ADOR1 review，并允许进入 ADOR2，但 ADOR2 仅限实现显式非默认、默认 dry-run、默认不写 latest 的 gate。仍不得触发 provider/network pull、provider publish、accepted latest switch、模型打分、策略回放、OpenAI、monitor、broker、order、target position/weight、production default 或 cron/default 切换。

## 2. Materials Reviewed

已阅读和复核：

```text
docs/tw_portfolio_decision_model/POLICY_ADOR1_NO_PUBLISH_ORCHESTRATION_DRY_RUN_DESIGN_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_ADOR1_R_ARTIFACT_MANIFEST_SELF_CHECK_REPAIR_EXECUTION_REPORT_CN.md
scripts/build_tw_ador1_no_publish_orchestration_dry_run_design.py
data_tw/experiments/automatic_daily_orchestration_route/ador1_no_publish_orchestration_dry_run_design/artifact_manifest.json
data_tw/experiments/automatic_daily_orchestration_route/ador1_r_manifest_self_check_repair/manifest_self_check_repair_evidence.json
data_tw/experiments/automatic_daily_orchestration_route/ador1_no_publish_orchestration_dry_run_design/protected_paths_fingerprint.json
data_tw/experiments/automatic_daily_orchestration_route/ador1_no_publish_orchestration_dry_run_design/forbidden_action_audit.json
```

## 3. Reviewer Finding Closure

原 ADOR1 reviewer 阻塞点是 `artifact_manifest.json` 在 `outputs` 中记录自身 placeholder sha/size，导致最终 manifest 无法按记录复算。

本次修复已关闭该问题：

```text
artifact_manifest.status=pass
artifact_manifest.outputs contains artifact_manifest.json=false
manifest_self_checksum_policy.self_entry_excluded_from_checksum=true
manifest_self_checksum_policy.excluded_path=data_tw/experiments/automatic_daily_orchestration_route/ador1_no_publish_orchestration_dry_run_design/artifact_manifest.json
manifest_self_checksum_policy.self_validation.checksum_recorded_in_outputs=false
manifest_self_checksum_policy.self_validation.size_recorded_in_outputs=false
manifest_self_checksum_policy.self_validation.json_parse_required=true
manifest_self_checksum_policy.self_validation.non_self_outputs_checksum_required=true
```

`scripts/build_tw_ador1_no_publish_orchestration_dry_run_design.py` 中的修复策略是：

```text
output_paths = [path for path in EVIDENCE_FILES.values() if path != manifest_path] + [EXECUTION_REPORT, ADOR2_WORK_DOC, SCRIPT_PATH]
manifest_self_checksum_policy()
build_manifest_self_check_repair_evidence(...)
```

该策略显式排除 self-entry，并用 JSON parse、自身实际 fingerprint 记录、required inputs 与非自引用 outputs 复算作为替代自检。

## 4. Independent Recompute

独立复算当前工作区文件：

```text
required_inputs_total=15
required_inputs_mismatch_count=0
non_self_outputs_total=10
non_self_outputs_mismatch_count=0
manifest_in_outputs=false
```

repair evidence 复核：

```text
repair_evidence.status=pass
required_inputs_check.total=15
required_inputs_check.mismatch_count=0
non_self_outputs_check.total=10
non_self_outputs_check.mismatch_count=0
manifest_self_policy_check.all_match=true
manifest_actual_sha256=81790d421f04d5f89c4c6401ea4720c3eab6b21b41642abac9ab4ffb9478afc4
manifest_actual_size_bytes=14551
```

`manifest_self_check_repair_evidence.json` 中记录的 manifest 实际 sha/size 与当前文件一致。

## 5. Protected Paths And Boundary

`protected_paths_fingerprint.json` before/after 一致：

```text
all_protected_paths_unchanged=true
orchestrator_unchanged=true
readonly_latest_unchanged=true
agent_latest_unchanged=true
provider_accepted_latest_unchanged=true
```

受保护路径覆盖：

```text
scripts/run_daily_tw_stock_auto_update.py
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
data_tw/artifacts/agent_daily_prompt/latest.json
qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json
data_tw/experiments/option_c_daily_signal/latest_signal.json
```

`forbidden_action_audit.json` 通过：

```text
status=pass
all_false=true
latest_pointer_write=false
artifact_publish=false
provider_or_network_pull=false
provider_publish=false
accepted_latest_switch=false
legacy_latest_switch=false
model_scoring_or_training=false
strategy_replay=false
order_intent_generation=false
replay_or_nav_generation=false
openai_call=false
daily_automation_default_switch=false
monitor_or_broker_or_order_path=false
trade_size_or_allocation_output=false
```

静态搜索确认 `scripts/run_daily_tw_stock_auto_update.py` 中未出现 ADOR2 gate 名称：

```text
ENABLE_TW_ADOR_NO_PUBLISH_ORCHESTRATION_DRY_RUN
--enable-ador-no-publish-orchestration-dry-run
ador_no_publish_orchestration_dry_run
ENABLE_TW_AGENT_DAILY_PROMPT_PUBLISH
TW_AGENT_DAILY_PROMPT_DRY_RUN
TW_AGENT_DAILY_PROMPT_PUBLISH_LATEST
```

这些标识仅出现在 ADOR1 设计/ADOR2 work doc/schema 中，未落入 daily orchestrator 实现。

## 6. Dirty Worktree Note

当前仓库不是干净工作区，`scripts/run_daily_tw_stock_auto_update.py` 相对 git HEAD 已有大量修改。本审查不回滚、不归因这些已有改动；只基于本次 ADOR1_R repair 证据、protected before/after fingerprint、当前 sha/size 复算和 ADOR gate 静态搜索判断。

在该限定下，repair 没有证据显示修改 orchestrator、写 readonly/agent latest、实现 ADOR2 gate、触发 provider/OpenAI/default/order 行为。

## 7. Decision

```text
ador1_review_reopen_allowed=true
ador2_allowed=true
ador2_scope=explicit_non_default_gate_only
```

ADOR2 开始前仍需继承 ADOR2 work doc 的限制：默认关闭 gate、dry-run 默认 true、latest 写入默认 false，并用测试证明默认不写 latest、不触发 provider/OpenAI/order/default/cron 行为。
