---
created_at: 2026-07-10
status: execution_report
phase: PBPR3_V_RERUN_WITH_CONTAINED_ADAPTER
target_asof: 2026-07-08
verdict: BLOCKED_AFTER_GATE_LEGACY_REAL_BUILD_SCORING_NOT_CONTAINED
production_allowed: false
provider_pull_allowed: false
network_command_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
qlib_refresh_allowed: false
real_qlib_scoring_executed: false
model_inference_input_real_build_executed: false
score_job_real_build_executed: false
model_signal_artifact_real_build_executed: false
validator_on_contained_artifacts_executed: false
readonly_latest_publish_allowed: false
agent_prompt_publish_allowed: false
monitor_write_allowed: false
order_or_target_output_allowed: false
---

# PBPR3_V Rerun With Contained Adapter 执行报告

## 1. Scope

Assigned phase:

```text
PBPR3_V_RERUN_WITH_CONTAINED_ADAPTER
```

Mainline document:

```text
docs/tw_portfolio_decision_model/POLICY_PBPR_PROVIDER_BRIDGE_PRODUCTIONIZATION_MAINLINE_CN.md
```

Work document:

```text
docs/tw_portfolio_decision_model/POLICY_PBPR3_V_RERUN_WITH_CONTAINED_ADAPTER_WORK_CN.md
```

本次按 PBPR3_V 单一步骤执行：先运行 contained adapter contract gate。Gate 通过后检查真实 build/scoring 脚本是否能把输入/输出严格约束到 PBPR3_V isolated root。检查结果显示 legacy scripts 仍不能满足约束，因此停止，未执行真实 qlib scoring/build/validation。

## 2. Documents / Contracts / Skills Read

已读取：

```text
docs/tw_portfolio_decision_model/POLICY_PBPR_PROVIDER_BRIDGE_PRODUCTIONIZATION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PBPR3_V_RERUN_WITH_CONTAINED_ADAPTER_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_PBPR3_U_CONTAINED_MODELA_SCORING_BUILD_ADAPTER_REPAIR_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_PBPR3_U_CONTAINED_MODELA_SCORING_BUILD_ADAPTER_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PBPR3_U_CONTAINED_MODELA_SCORING_BUILD_ADAPTER_REPAIR_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBPR3_T_RERUN_WITH_SAFE_SCORING_ADAPTER_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md
```

已检查：

```text
scripts/run_tw_pbpr3_modela_no_publish_dry_run.py
scripts/build_tw_model_inference_input.py
scripts/run_tw_model_score_job.py
scripts/validate_tw_score_job.py
scripts/tw_modela_score_common.py
tests/unit/test_pbpr3_modela_no_publish_entrypoint.py
```

使用的 workflow / skill：

```text
coordinator-executor-reviewer-workflow
tw-stock-new-model-onboarding
```

## 3. Gate Result

Mandatory contained adapter contract gate 已运行并写入：

```text
data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3u/contained_adapter_contract_gate.json
```

Gate result:

```text
status=pass
target_asof=2026-07-08
provider_root=PBPR2A-AC accepted staged_qlib_bin
normalized_root=PBPR2A-AC accepted candidate_normalized
output_root=data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3u
no_publish=true
no_catalog=true
no_latest=true
no_target_output=true
preflight_only=true
```

但 gate payload 同时声明当前 runtime reachability 仍为：

```text
real_qlib_scoring_reachable=false
build_tw_model_inference_input_reachable=false
run_tw_model_score_job_reachable=false
validate_tw_score_job_on_real_artifacts_reachable=false
fixture_or_mock_only=true
```

## 4. Stop Condition / Blocker

Gate pass 后检查真实 build/scoring scripts，确认 blocker 仍成立：

```text
scripts/tw_modela_score_common.py
  INPUT_BASE=data_tw/canonical/model_inference_input/{MODEL_ID}
  SCORE_BASE=data_tw/artifacts/score_jobs/{MODEL_ID}
  SIGNAL_BASE=data_tw/artifacts/signals/{MODEL_ID}
  CATALOG_VALIDATION_PATH=data_tw/catalog/dng7_modela_score_pipeline_validation.json
  QLIB_PROVIDER=qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin
  QLIB_NORMALIZED=qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized

scripts/run_tw_model_score_job.py
  subprocess.run(...) reaches qlib scoring
  writes SCORE_BASE / SIGNAL_BASE / CATALOG_VALIDATION_PATH
```

这些路径违反 PBPR3_V 要求：所有真实输出必须只落在

```text
data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3u/
```

真实 artifact payload 必须只落在：

```text
data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3u/planned_future_outputs/
```

因此按 work doc stop condition 停止，未运行 legacy real build/scoring/validator。

Blocker:

```text
BLOCKED_AFTER_GATE_LEGACY_REAL_BUILD_SCORING_NOT_CONTAINED
```

## 5. Evidence Produced

PBPR3_V evidence root:

```text
data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3u/
```

写入：

```text
contained_adapter_contract_gate.json
model_inference_input_manifest.json
score_job_manifest.json
model_signal_artifact_no_publish_manifest.json
validator_report.json
static_safety_audit.json
forbidden_action_audit.json
execution_report_supporting_summary.json
artifact_manifest.json
blocker.json
```

Evidence status:

```text
contained_adapter_contract_gate.status=pass
model_inference_input_manifest.status=blocked_not_built
score_job_manifest.status=blocked_not_built
model_signal_artifact_no_publish_manifest.status=blocked_not_built
validator_report.status=blocked_not_run
static_safety_audit.status=blocker_found_before_real_build
forbidden_action_audit.status=pass_no_forbidden_action_observed
artifact_manifest.status=blocked_manifest_complete
```

## 6. Commands Run

```text
sed -n ... required docs/contracts/scripts
rg -n "PBPR3|contained|output_root|INPUT_BASE|SCORE_BASE|SIGNAL_BASE|CATALOG_VALIDATION_PATH|QLIB_PROVIDER|QLIB_NORMALIZED|subprocess\\.run|write_json|to_csv|data_tw/canonical|data_tw/artifacts|data_tw/catalog" scripts/...
python scripts/run_tw_pbpr3_modela_no_publish_dry_run.py --target-asof 2026-07-08 --accepted-readiness data_tw/experiments/provider_bridge_productionization/pbpr2a_ac_provider_candidate_readiness_review/provider_candidate_readiness_accepted.json --provider-root data_tw/experiments/provider_bridge_productionization/pbpr2a_w_proxy_provider_only_rerun/pbpr2a_w_yahoo_proxy_provider_only_20260708/staged_qlib_bin --normalized-root data_tw/experiments/provider_bridge_productionization/pbpr2a_w_proxy_provider_only_rerun/pbpr2a_w_yahoo_proxy_provider_only_20260708/candidate_normalized --output-root data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3u --contained-adapter-contract-only --contained-adapter-contract-report data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3u/contained_adapter_contract_gate.json --no-publish --no-catalog --no-latest --no-target-output --preflight-only --json
python -m py_compile scripts/run_tw_pbpr3_modela_no_publish_dry_run.py scripts/build_tw_model_inference_input.py scripts/run_tw_model_score_job.py scripts/validate_tw_score_job.py scripts/tw_modela_score_common.py tests/unit/test_pbpr3_modela_no_publish_entrypoint.py
python -m pytest tests/unit/test_pbpr3_modela_no_publish_entrypoint.py -q
python -m py_compile scripts/build_tw_pbpr3v_rerun_evidence.py
python scripts/build_tw_pbpr3v_rerun_evidence.py --py-compile-status pass --pytest-status pass --pytest-summary '13 passed in 0.23s' --json
python -m json.tool <PBPR3_V evidence json files>
```

Results:

```text
contained_adapter_contract_gate=pass
py_compile=pass
focused pytest=13 passed in 0.23s
PBPR3_V evidence_builder=blocked_manifest_complete
```

Commands intentionally not run:

```text
python scripts/build_tw_model_inference_input.py ...
python scripts/run_tw_model_score_job.py ...
python scripts/validate_tw_score_job.py ...
```

Skip reason:

```text
legacy scripts still cannot constrain all inputs/outputs to PBPR3_V isolated roots and would write formal legacy paths.
```

## 7. Runtime Executed Flags

```text
real_qlib_scoring_executed=false
model_inference_input_real_build_executed=false
score_job_real_build_executed=false
model_signal_artifact_real_build_executed=false
validator_on_contained_artifacts_executed=false
```

## 8. Forbidden Actions Audit

未执行：

```text
provider/network pull
Yahoo/Scrapling/FinMind live request
yfinance
provider fallback
mixed-provider fill
cached prior-asof fill
network probe
provider publish
latest/catalog/publish/published writes
latest pointer creation or switch
accepted/latest switch
formal normalized source mutation
formal qlib provider/calendar mutation
qlib accepted latest refresh
qlib refresh
model training/retraining/tuning
readonly latest publish
Agent prompt build or publish
production/default/frontend/monitor behavior change
monitor write
broker / quick-trade / real order
OrderIntentArtifact generation
target_position / target_weight / quantity / shares / lots / target output
```

## 9. Compliance With Mainline

PBPR readiness separation 保持成立：

```text
raw-ready != provider-ready
provider/bridge-ready != signal-ready
signal-ready != accepted/latest publish-ready
readonly context-ready != readonly latest published
Agent context-ready != Agent prompt latest published
```

PBPR3_V 没有产生 no-publish real signal artifact，因此不能进入 PBPR4 readonly/Agent source-context readiness。Publish/latest、readonly/Agent latest、monitor、broker/order、target output 仍未授权。

## 10. Files Changed

```text
scripts/build_tw_pbpr3v_rerun_evidence.py
docs/tw_portfolio_decision_model/POLICY_PBPR3_V_RERUN_WITH_CONTAINED_ADAPTER_EXECUTION_REPORT_CN.md
data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3u/contained_adapter_contract_gate.json
data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3u/model_inference_input_manifest.json
data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3u/score_job_manifest.json
data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3u/model_signal_artifact_no_publish_manifest.json
data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3u/validator_report.json
data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3u/static_safety_audit.json
data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3u/forbidden_action_audit.json
data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3u/execution_report_supporting_summary.json
data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3u/artifact_manifest.json
data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3u/blocker.json
```

## 11. Recommendation For Reviewer

Recommended reviewer gate:

```text
FAIL_NEEDS_REPAIR
```

下一步应是一个 repair work doc：实现真正 contained real build/scoring runtime，而不仅是 contract gate。该 repair 必须参数化或新增 isolated runtime，使 `provider_root`、`normalized_root`、`output_root` 显式传入，并让 ModelInferenceInput、ScoreJob、ModelSignalArtifact、validator report 全部只写入 PBPR3 isolated `planned_future_outputs/`。仍不得授权 provider/network、publish/latest、accepted/latest、qlib refresh、readonly/Agent publish、monitor、broker/order、OrderIntentArtifact 或 target output。
