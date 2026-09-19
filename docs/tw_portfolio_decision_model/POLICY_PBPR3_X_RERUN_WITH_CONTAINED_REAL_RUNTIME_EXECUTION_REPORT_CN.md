---
created_at: 2026-07-10
status: execution_report
phase: PBPR3_X_RERUN_WITH_CONTAINED_REAL_RUNTIME
target_asof: 2026-07-08
verdict: REAL_CONTAINED_RERUN_PASS
production_allowed: false
provider_pull_allowed: false
network_command_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
qlib_refresh_allowed: false
real_qlib_scoring_executed: true
model_inference_input_real_build_executed: true
score_job_real_build_executed: true
model_signal_artifact_real_build_executed: true
validator_on_contained_artifacts_executed: true
readonly_latest_publish_allowed: false
agent_prompt_publish_allowed: false
monitor_write_allowed: false
order_or_target_output_allowed: false
target_output_allowed: false
---

# PBPR3_X Rerun With Contained Real Runtime 执行报告

## 1. Scope

Assigned phase:

```text
PBPR3_X_RERUN_WITH_CONTAINED_REAL_RUNTIME
```

Mainline:

```text
docs/tw_portfolio_decision_model/POLICY_PBPR_PROVIDER_BRIDGE_PRODUCTIONIZATION_MAINLINE_CN.md
```

Work document:

```text
docs/tw_portfolio_decision_model/POLICY_PBPR3_X_RERUN_WITH_CONTAINED_REAL_RUNTIME_WORK_CN.md
```

本轮目标是在 PBPR3_W 修复后的 contained runtime 中，对固定 `target_asof=2026-07-08` 执行真实 no-publish Model A rerun。所有真实 payload 均限定在：

```text
data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3w/planned_future_outputs/
```

未执行 provider/network pull、provider publish、accepted/latest switch、qlib accepted latest refresh、latest/catalog publish、readonly/Agent publish、monitor、broker/order、OrderIntentArtifact 或 target_position/target_weight/quantity/shares/lots/target 输出。

## 2. Documents / Contracts / Skills Read

已读取：

```text
docs/tw_portfolio_decision_model/POLICY_PBPR_PROVIDER_BRIDGE_PRODUCTIONIZATION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PBPR3_W_CONTAINED_REAL_RUNTIME_REPAIR_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_PBPR3_W_CONTAINED_REAL_RUNTIME_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PBPR3_W_CONTAINED_REAL_RUNTIME_REPAIR_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBPR3_V_RERUN_WITH_CONTAINED_ADAPTER_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBPR3_X_RERUN_WITH_CONTAINED_REAL_RUNTIME_WORK_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md
```

使用 workflow / skill：

```text
coordinator-executor-reviewer-workflow
tw-stock-new-model-onboarding
```

## 3. Changes Made

新增：

```text
scripts/build_tw_pbpr3x_contained_rerun_evidence.py
docs/tw_portfolio_decision_model/POLICY_PBPR3_X_RERUN_WITH_CONTAINED_REAL_RUNTIME_EXECUTION_REPORT_CN.md
```

修改：

```text
scripts/run_tw_model_score_job.py
```

修改内容仅限修复 PBPR3_X 证据歧义：将 contained/non-2026-06-25 run 的 pipeline validation 改为写 `target_asof_score_generated=true`，并让 legacy `true_20260625_score_generated` 仅在 `asof == 2026-06-25` 时为 true；报告文案也改为动态 asof。未改变 provider、publish/latest、readonly/Agent、monitor/broker/order 或生产默认行为。

## 4. Mandatory Gates Before Real Build/Scoring

Gate results:

```text
py_compile=pass
focused pytest=17 passed in 0.77s
contained_runtime_contract_gate.status=pass
pre_real_run_manifest_precheck.status=pass
initial forbidden_action_audit.all_false=true
static rg scan=pass after executor classification
```

Static rg scan 命中项为 legacy 默认常量、guard/forbidden lists、negative tests、false audit fields 与 report text。未观察到 PBPR3_X contained executable path 写向 `latest/catalog/publish/published/accepted_latest/readonly/agent/monitor/broker/order/target` 或 formal `data_tw/canonical`, `data_tw/artifacts`, `data_tw/catalog`, `docs/tw_data_governance`。

Gate evidence:

```text
data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3w/contained_runtime_contract_gate.json
data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3w/pre_real_run_manifest_precheck.json
data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3w/forbidden_action_audit.json
```

## 5. Real Runtime Executed

Run id:

```text
pbpr3x_modela_20260708_contained
```

Fixed parameters:

```text
target_asof=2026-07-08
provider_root=data_tw/experiments/provider_bridge_productionization/pbpr2a_w_proxy_provider_only_rerun/pbpr2a_w_yahoo_proxy_provider_only_20260708/staged_qlib_bin
normalized_root=data_tw/experiments/provider_bridge_productionization/pbpr2a_w_proxy_provider_only_rerun/pbpr2a_w_yahoo_proxy_provider_only_20260708/candidate_normalized
output_root=data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3w
flags=--no-publish --no-catalog --no-latest --no-target-output
score flag=--allow-contained-real-execution
```

Executed:

```text
model_inference_input_real_build_executed=true
contained_qlib_scoring_executed=true
score_job_real_build_executed=true
model_signal_artifact_real_build_executed=true
validator_on_contained_artifacts_executed=true
```

Output artifacts:

```text
planned_future_outputs/model_inference_input/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/
planned_future_outputs/qlib_scoring_runs/pbpr3x_modela_20260708_contained/
planned_future_outputs/score_job/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/
planned_future_outputs/model_signal_artifact/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/
planned_future_outputs/score_pipeline_validation/pbpr3x_modela_20260708_contained/
planned_future_outputs/score_pipeline_report/pbpr3x_modela_20260708_contained/
```

Observed runtime status:

```text
ModelInferenceInput.status=READY
ModelInferenceInput.row_count=150
ScoreJob.pipeline_status=SCORED_ASOF_TARGET
ScoreJob.raw_score_rows=150
ModelSignalArtifact.status=READY
ModelSignalArtifact.signal_rows=150
ModelSignalArtifact.signal_asof=2026-07-08
validator.status=PASS
validator.errors=[]
forbidden_columns=[]
```

## 6. Evidence Produced

Evidence root:

```text
data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3w/
```

Required evidence:

```text
contained_runtime_contract_gate.json
pre_real_run_manifest_precheck.json
model_inference_input_manifest.json
score_job_manifest.json
model_signal_artifact_no_publish_manifest.json
validator_report.json
static_safety_audit.json
forbidden_action_audit.json
execution_report_supporting_summary.json
artifact_manifest.json
```

Evidence summary:

```text
execution_report_supporting_summary.verdict=REAL_CONTAINED_RERUN_PASS
model_inference_input_manifest.status=pass
score_job_manifest.status=pass
model_signal_artifact_no_publish_manifest.status=pass
validator_report.status=PASS
static_safety_audit.status=pass
forbidden_action_audit.all_false=true
```

No `blocker.json` is expected for this successful run.

## 7. Commands Run

```text
python -m py_compile scripts/run_tw_pbpr3_modela_no_publish_dry_run.py scripts/tw_modela_score_common.py scripts/build_tw_model_inference_input.py scripts/run_tw_model_score_job.py scripts/validate_tw_score_job.py scripts/build_tw_pbpr3w_contained_runtime_evidence.py scripts/build_tw_pbpr3x_contained_rerun_evidence.py tests/unit/test_pbpr3_modela_no_publish_entrypoint.py
python -m pytest tests/unit/test_pbpr3_modela_no_publish_entrypoint.py -q
rg -n "<PBPR3_X forbidden path/action tokens>" scripts/... tests/...
python scripts/run_tw_pbpr3_modela_no_publish_dry_run.py --target-asof 2026-07-08 --provider-root <PBPR2A-AC staged_qlib_bin> --normalized-root <PBPR2A-AC candidate_normalized> --output-root <PBPR3_X output root> --contained-runtime-contract-only --contained-runtime-contract-report <PBPR3_X gate json> --no-publish --no-catalog --no-latest --no-target-output --preflight-only --json
python scripts/build_tw_pbpr3x_contained_rerun_evidence.py --json precheck --static-rg-status pass
python scripts/build_tw_model_inference_input.py --asof 2026-07-08 --run-id pbpr3x_modela_20260708_contained --provider-root <PBPR2A-AC staged_qlib_bin> --normalized-root <PBPR2A-AC candidate_normalized> --output-root <PBPR3_X output root> --no-publish --no-catalog --no-latest --no-target-output --json
python scripts/run_tw_model_score_job.py --asof 2026-07-08 --run-id pbpr3x_modela_20260708_contained --input-dir <contained ModelInferenceInput dir> --provider-root <PBPR2A-AC staged_qlib_bin> --normalized-root <PBPR2A-AC candidate_normalized> --output-root <PBPR3_X output root> --no-publish --no-catalog --no-latest --no-target-output --allow-contained-real-execution --json
python scripts/validate_tw_score_job.py --score-dir <contained ScoreJob dir> --signal-dir <contained ModelSignalArtifact dir> --asof 2026-07-08 --contained-output-root <PBPR3_X planned_future_outputs> --json
python scripts/build_tw_pbpr3x_contained_rerun_evidence.py --json collect --static-rg-status pass --static-rg-notes <notes> --command-summary <summary>
```

Runtime notes:

```text
qlib.init provider_uri=<PBPR2A-AC staged_qlib_bin>
Matplotlib used a temporary /tmp cache because ~/.config/matplotlib is not writable.
Optional CatBoost/XGB modules were skipped by qlib import; Model A LGB scoring still completed.
```

## 8. Forbidden Actions Audit

Not executed:

```text
provider/network pull
Yahoo/Scrapling/FinMind/yfinance
provider publish
accepted/latest switch
qlib accepted latest refresh
latest/catalog publish
readonly latest publish
Agent prompt build or publish
production/default/frontend/monitor behavior change
monitor write
broker / quick-trade / real order
OrderIntentArtifact generation
target_position / target_weight / quantity / shares / lots / target output
model training/retraining/tuning
strategy replay
ReplayResult/NAV generation
```

## 9. Issues / Blockers / Deviations

No blocker.

Small in-scope repair performed during execution:

```text
scripts/run_tw_model_score_job.py
```

Reason: first successful contained 2026-07-08 run exposed a legacy hardcoded `true_20260625_score_generated` evidence field. The code now emits `target_asof_score_generated=true` for the actual target and keeps `true_20260625_score_generated=true` only for legacy 2026-06-25 runs. This avoids review ambiguity and does not change production defaults or publish behavior.

Residual risk for reviewer:

```text
qlib.init mutates only in-process qlib global state during scoring; observed provider_uri points to PBPR2A-AC contained provider root.
PBPR3_X result is no-publish signal-ready evidence only. It is not accepted/latest publish-ready, readonly latest published, Agent prompt latest published, or strategy/replay/order-ready.
```

## 10. Recommendation For Reviewer

Suggested reviewer verdict:

```text
PASS_RERUN_FOR_PBPR4_READONLY_AGENT_SOURCE_CONTEXT_WORKDOC_ONLY
```

Reviewer should independently verify JSON parse, artifact manifest checksums, score/signal validator output, forbidden action audit, and static scans. Any PASS must not authorize provider publish, accepted/latest switch, latest/catalog publish, readonly/Agent publish, monitor/broker/order, OrderIntentArtifact, target output, or production default changes.
