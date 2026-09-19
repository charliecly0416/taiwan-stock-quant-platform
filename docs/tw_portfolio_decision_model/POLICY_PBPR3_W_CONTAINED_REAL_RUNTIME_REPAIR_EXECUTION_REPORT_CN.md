---
created_at: 2026-07-10
status: execution_report
phase: PBPR3_W_CONTAINED_REAL_RUNTIME_REPAIR
target_asof: 2026-07-08
verdict: IMPLEMENTED_CONTAINED_REAL_RUNTIME_REPAIR_STATIC_ONLY
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
validator_on_real_artifacts_executed: false
readonly_latest_publish_allowed: false
agent_prompt_publish_allowed: false
monitor_write_allowed: false
order_or_target_output_allowed: false
target_output_allowed: false
---

# PBPR3_W Contained Real Runtime Repair 执行报告

## 1. Scope

Assigned phase:

```text
PBPR3_W_CONTAINED_REAL_RUNTIME_REPAIR
```

Mainline:

```text
docs/tw_portfolio_decision_model/POLICY_PBPR_PROVIDER_BRIDGE_PRODUCTIONIZATION_MAINLINE_CN.md
```

Work document:

```text
docs/tw_portfolio_decision_model/POLICY_PBPR3_W_CONTAINED_REAL_RUNTIME_REPAIR_WORK_CN.md
```

本次只执行 PBPR3_W repair：修复真实 Model A runtime 的 injected path 能力，并用 static/unit/fixture evidence 证明后续 PBPR3_X 可在 reviewed gate 下使用 `target_asof/provider_root/normalized_root/output_root/no_* flags` 派生 contained outputs。未执行真实 qlib scoring、真实 ModelInferenceInput build、真实 ScoreJob build、真实 ModelSignalArtifact build，未对真实新 artifact 跑 validator。

## 2. Documents / Contracts / Skills Read

已读取：

```text
docs/tw_portfolio_decision_model/POLICY_PBPR_PROVIDER_BRIDGE_PRODUCTIONIZATION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PBPR3_V_RERUN_WITH_CONTAINED_ADAPTER_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_PBPR3_V_RERUN_WITH_CONTAINED_ADAPTER_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PBPR3_V_RERUN_WITH_CONTAINED_ADAPTER_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBPR3_U_CONTAINED_MODELA_SCORING_BUILD_ADAPTER_REPAIR_REVIEW_CN.md
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

修改：

```text
scripts/tw_modela_score_common.py
scripts/build_tw_model_inference_input.py
scripts/run_tw_model_score_job.py
scripts/validate_tw_score_job.py
scripts/run_tw_pbpr3_modela_no_publish_dry_run.py
tests/unit/test_pbpr3_modela_no_publish_entrypoint.py
```

新增：

```text
scripts/build_tw_pbpr3w_contained_runtime_evidence.py
docs/tw_portfolio_decision_model/POLICY_PBPR3_W_CONTAINED_REAL_RUNTIME_REPAIR_EXECUTION_REPORT_CN.md
```

核心实现：

- `tw_modela_score_common.py` 新增 `ModelARuntimeConfig`、`make_modela_runtime_config(...)`、`validate_modela_runtime_config(...)`，统一派生 contained runtime paths。
- `build_tw_model_inference_input.py` 的 `build(...)` 支持可选 runtime config；传入后从 injected provider/normalized/output roots 派生输入与输出，legacy CLI 默认不变。
- `run_tw_model_score_job.py` 的 `run(...)` 支持可选 runtime config；传入后 score job、signal、qlib run、pipeline validation、execution report 均写入 injected output root 下的 `planned_future_outputs/`。默认 `allow_real_execution=false`，PBPR3_W 不可达真实 qlib scoring。
- `validate_tw_score_job.py` 支持 `--contained-output-root`，后续 validator 可先检查 score/signal dirs 是否在 contained root 内。
- `run_tw_pbpr3_modela_no_publish_dry_run.py` 新增 `--contained-runtime-contract-only` / `--contained-runtime-contract-report`，只产出 PBPR3_W runtime contract gate。
- 单测新增 PBPR3_W runtime contract pass/fail cases。

## 4. Runtime Contract Implemented

Runtime contract 显式参数：

```text
target_asof
provider_root
normalized_root
output_root
no_publish
no_catalog
no_latest
no_target_output
```

PBPR3_W target:

```text
target_asof=2026-07-08
provider_root=data_tw/experiments/provider_bridge_productionization/pbpr2a_w_proxy_provider_only_rerun/pbpr2a_w_yahoo_proxy_provider_only_20260708/staged_qlib_bin
normalized_root=data_tw/experiments/provider_bridge_productionization/pbpr2a_w_proxy_provider_only_rerun/pbpr2a_w_yahoo_proxy_provider_only_20260708/candidate_normalized
output_root=data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3w
```

Planned real payload root:

```text
data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3w/planned_future_outputs/
```

Planned runtime output dirs:

```text
planned_future_outputs/model_inference_input/e4_frozen_qlib_2018_2022/{run_id}/
planned_future_outputs/score_job/e4_frozen_qlib_2018_2022/{run_id}/
planned_future_outputs/model_signal_artifact/e4_frozen_qlib_2018_2022/{run_id}/
planned_future_outputs/qlib_scoring_runs/{run_id}/
planned_future_outputs/score_pipeline_validation/{run_id}/validation.json
planned_future_outputs/score_pipeline_report/{run_id}/execution_report.md
```

Legacy default constants remain for existing legacy CLI behavior, but contained runtime no longer depends on `INPUT_BASE/SCORE_BASE/SIGNAL_BASE/CATALOG_VALIDATION_PATH` for injected execution.

## 5. Evidence Produced

Evidence root:

```text
data_tw/experiments/provider_bridge_productionization/pbpr3w_contained_real_runtime_repair/
```

Required evidence:

```text
runtime_config_contract.json
path_containment_matrix.json
contained_runtime_static_audit.json
fixture_model_inference_input_plan.json
fixture_score_job_plan.json
fixture_model_signal_plan.json
mocked_unit_test_summary.json
forbidden_action_audit.json
execution_report_supporting_summary.json
artifact_manifest.json
```

Expected status after evidence builder:

```text
runtime_config_contract.status=pass
path_containment_matrix.status=pass
contained_runtime_static_audit.status=pass
fixture_model_inference_input_plan.status=pass
fixture_score_job_plan.status=pass
fixture_model_signal_plan.status=pass
mocked_unit_test_summary.status=pass
forbidden_action_audit.all_false=true
artifact_manifest.status=pass
```

## 6. Commands Run

```text
sed -n ... required docs/contracts/scripts
rg -n "RuntimeConfig|contained_runtime|runtime_config|build\\(|run_qlib\\(|validate\\(" scripts tests/unit | head -120
head -5 data_tw/experiments/provider_bridge_productionization/pbpr2a_w_proxy_provider_only_rerun/pbpr2a_w_yahoo_proxy_provider_only_20260708/staged_qlib_bin/instruments/all.txt
ls -la data_tw/experiments/provider_bridge_productionization/pbpr2a_w_proxy_provider_only_rerun/pbpr2a_w_yahoo_proxy_provider_only_20260708/staged_qlib_bin
find data_tw/experiments/provider_bridge_productionization/pbpr2a_w_proxy_provider_only_rerun/pbpr2a_w_yahoo_proxy_provider_only_20260708/staged_qlib_bin -maxdepth 2 -type f | head -20
python -m py_compile scripts/run_tw_pbpr3_modela_no_publish_dry_run.py scripts/tw_modela_score_common.py scripts/build_tw_model_inference_input.py scripts/run_tw_model_score_job.py scripts/validate_tw_score_job.py scripts/build_tw_pbpr3w_contained_runtime_evidence.py tests/unit/test_pbpr3_modela_no_publish_entrypoint.py
python -m pytest tests/unit/test_pbpr3_modela_no_publish_entrypoint.py -q
python scripts/build_tw_pbpr3w_contained_runtime_evidence.py --mocked-unit-status pass --mocked-unit-summary '17 passed in 0.77s' --json
python -c "<PBPR3_W JSON parse/status/manifest checksum summary>"
rg -n "<forbidden executable/path/action tokens>" scripts/tw_modela_score_common.py scripts/build_tw_model_inference_input.py scripts/run_tw_model_score_job.py scripts/validate_tw_score_job.py scripts/run_tw_pbpr3_modela_no_publish_dry_run.py scripts/build_tw_pbpr3w_contained_runtime_evidence.py tests/unit/test_pbpr3_modela_no_publish_entrypoint.py
```

Observed:

```text
py_compile=pass
pytest=17 passed in 0.77s
PBPR3_W evidence_builder=IMPLEMENTED_CONTAINED_REAL_RUNTIME_REPAIR
PBPR3_W JSON parse=pass for 10 files
artifact_manifest.status=pass
artifact_manifest.entries=17
artifact_manifest.missing=[]
artifact_manifest.checksum_mismatches=[]
static rg scan=legacy constants / guard lists / false audit fields / negative tests only; no forbidden action executed
```

Commands intentionally not run:

```text
python scripts/build_tw_model_inference_input.py ...
python scripts/run_tw_model_score_job.py ...
python scripts/validate_tw_score_job.py ... on real newly built artifacts
```

Skip reason: PBPR3_W forbids real build/scoring/validator on real newly built artifacts.

## 7. Forbidden Actions Audit

Not executed:

```text
provider/network pull
Yahoo/Scrapling/FinMind/yfinance
provider publish
accepted/latest switch
qlib refresh
real qlib scoring
real ModelInferenceInput build
real ScoreJob build
real ModelSignalArtifact build
validator on real newly built artifacts
latest/catalog/publish/published writes
readonly/Agent publish
monitor write
broker/order/OrderIntentArtifact
target_position/target_weight/quantity/shares/lots/target output
```

## 8. Issues / Blockers

No blocker found for PBPR3_W static repair.

Remaining by design:

```text
PBPR3_W does not prove real qlib scoring succeeds.
PBPR3_W does not produce real ModelInferenceInput/ScoreJob/ModelSignalArtifact.
PBPR3_W does not run validator on real newly built artifacts.
```

These are reserved for the next reviewed rerun phase.

## 9. Recommendation For Reviewer

Suggested reviewer gate:

```text
PASS_REPAIR_FOR_PBPR3_X_RERUN_WORKDOC_ONLY
```

The pass, if granted, should only authorize a next work document for PBPR3_X contained real rerun. It must not authorize provider/network, provider publish, accepted/latest switch, qlib refresh, readonly/Agent publish, monitor, broker/order, OrderIntentArtifact, or target output.
