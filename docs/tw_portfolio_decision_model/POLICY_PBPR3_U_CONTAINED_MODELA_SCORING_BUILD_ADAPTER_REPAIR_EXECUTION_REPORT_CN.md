---
created_at: 2026-07-10
status: execution_report
phase: PBPR3_U_CONTAINED_MODELA_SCORING_BUILD_ADAPTER_REPAIR
target_asof: 2026-07-08
verdict: IMPLEMENTED_CONTAINED_ADAPTER_CONTRACT_STATIC_ONLY
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
readonly_latest_publish_allowed: false
agent_prompt_publish_allowed: false
monitor_write_allowed: false
order_or_target_output_allowed: false
---

# PBPR3_U Contained Model A Scoring/Build Adapter Repair 执行报告

## 1. Scope

Assigned phase:

```text
PBPR3_U_CONTAINED_MODELA_SCORING_BUILD_ADAPTER_REPAIR
```

Mainline document:

```text
docs/tw_portfolio_decision_model/POLICY_PBPR_PROVIDER_BRIDGE_PRODUCTIONIZATION_MAINLINE_CN.md
```

Work document:

```text
docs/tw_portfolio_decision_model/POLICY_PBPR3_U_CONTAINED_MODELA_SCORING_BUILD_ADAPTER_REPAIR_WORK_CN.md
```

本次只修复 PBPR3_T blocker 的合约层：新增 PBPR3-contained Model A scoring/build adapter contract/static/fixture/mock evidence。未运行真实 qlib scoring，未运行真实 ModelInferenceInput build、ScoreJob build、ModelSignalArtifact build，也未运行 legacy `build_tw_model_inference_input.py`、`run_tw_model_score_job.py`、`validate_tw_score_job.py` 的真实 artifact 路径。

## 2. Documents / Contracts / Skills Read

已读取：

```text
docs/tw_portfolio_decision_model/POLICY_PBPR_PROVIDER_BRIDGE_PRODUCTIONIZATION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PBPR3_T_RERUN_WITH_SAFE_SCORING_ADAPTER_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_PBPR3_T_RERUN_WITH_SAFE_SCORING_ADAPTER_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PBPR3_T_RERUN_WITH_SAFE_SCORING_ADAPTER_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBPR3S_SAFE_ISOLATED_MODELA_SCORING_ADAPTER_REVIEW_CN.md
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

## 3. Changes Made

代码变更：

```text
scripts/run_tw_pbpr3_modela_no_publish_dry_run.py
tests/unit/test_pbpr3_modela_no_publish_entrypoint.py
scripts/build_tw_pbpr3u_contained_modela_adapter_evidence.py
```

核心实现：

- 新增 `validate_contained_adapter_contract(...)`，显式接收 `target_asof`、`provider_root`、`normalized_root`、`output_root`、`no_publish`、`no_catalog`、`no_latest`、`no_target_output`。
- 新增 `--contained-adapter-contract-only` / `--contained-adapter-contract-report` CLI 模式，只生成合约报告，不触发真实 scoring/build。
- 新增 planned future output path derivation，所有路径派生自显式 `output_root`，并位于 `planned_future_outputs/` 下。
- 新增 path containment validator：拒绝 legacy provider root、legacy output root、`data_tw/canonical`、`data_tw/artifacts`、`data_tw/catalog`、latest/catalog/publish/published/accepted_latest/readonly/agent/monitor/broker/order/target_position/target_weight/target_output path。
- 新增 PBPR3_U evidence builder，写入 work doc 指定的 8 个 JSON evidence。

未修改 production/default registry、frontend、daily orchestrator、monitor、Agent prompt/tool/action、accepted latest pointer、formal provider/catalog 路径。

## 4. Evidence Produced

PBPR3_U evidence root:

```text
data_tw/experiments/provider_bridge_productionization/pbpr3u_contained_modela_scoring_build_adapter_repair/
```

写入：

```text
adapter_contract_summary.json
path_containment_matrix.json
fixture_adapter_plan.json
mocked_unit_test_summary.json
static_safety_audit.json
forbidden_action_audit.json
artifact_manifest.json
execution_report_supporting_summary.json
```

当前 evidence 状态：

```text
adapter_contract_summary.status=pass
path_containment_matrix.status=pass
fixture_adapter_plan.status=pass
mocked_unit_test_summary.status=pass
static_safety_audit.status=pass
forbidden_action_audit.status=pass_no_forbidden_action_observed
execution_report_supporting_summary.verdict=IMPLEMENTED_CONTAINED_ADAPTER_CONTRACT
artifact_manifest.status=pass
```

## 5. Commands Run

```text
sed -n ... required docs/contracts/scripts
git status --short
rg -n "PBPR3_U|contained_modela|pbpr3u|adapter_contract" docs scripts tests data_tw/experiments/provider_bridge_productionization
python -m py_compile scripts/run_tw_pbpr3_modela_no_publish_dry_run.py tests/unit/test_pbpr3_modela_no_publish_entrypoint.py
python -m pytest tests/unit/test_pbpr3_modela_no_publish_entrypoint.py -q
python -m py_compile scripts/run_tw_pbpr3_modela_no_publish_dry_run.py scripts/build_tw_pbpr3u_contained_modela_adapter_evidence.py tests/unit/test_pbpr3_modela_no_publish_entrypoint.py
python -m pytest tests/unit/test_pbpr3_modela_no_publish_entrypoint.py -q
python scripts/build_tw_pbpr3u_contained_modela_adapter_evidence.py --mocked-unit-status pass --mocked-unit-summary '13 passed in 0.26s' --json
```

结果：

```text
py_compile=pass
focused pytest=13 passed
PBPR3_U evidence builder=status pass
```

Commands intentionally not run:

```text
python scripts/build_tw_model_inference_input.py ...
python scripts/run_tw_model_score_job.py ...
python scripts/validate_tw_score_job.py ...
```

Skip reason:

```text
PBPR3_U is static/fixture/mock repair only and does not authorize real scoring/build or validator on real artifacts.
```

## 6. Compliance With Mainline

PBPR readiness separation is preserved:

```text
raw-ready != provider-ready
provider/bridge-ready != signal-ready
signal-ready != accepted/latest publish-ready
readonly context-ready != readonly latest published
Agent context-ready != Agent prompt latest published
```

PBPR3_U does not promote provider readiness to signal readiness. It only provides a fail-closed contained adapter contract for a later reviewed PBPR3_V rerun work document.

## 7. Forbidden Actions Audit

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
real qlib scoring
model training/tuning
real ModelInferenceInput build
real ScoreJob build
real ModelSignalArtifact build
readonly latest publish
Agent prompt build or publish
production/default/frontend/monitor behavior change
monitor write
broker / quick-trade / real order
OrderIntentArtifact generation
target_position / target_weight / quantity / shares / lots / target output
```

## 8. Issues / Blockers / Deviations

No blocker remains for the PBPR3_U assigned scope.

Remaining limitation by design:

```text
PBPR3_U does not prove real qlib scoring works. It only proves a contained adapter contract and path boundary for a later reviewed no-publish rerun.
```

## 9. Files Changed

```text
scripts/run_tw_pbpr3_modela_no_publish_dry_run.py
scripts/build_tw_pbpr3u_contained_modela_adapter_evidence.py
tests/unit/test_pbpr3_modela_no_publish_entrypoint.py
docs/tw_portfolio_decision_model/POLICY_PBPR3_U_CONTAINED_MODELA_SCORING_BUILD_ADAPTER_REPAIR_EXECUTION_REPORT_CN.md
data_tw/experiments/provider_bridge_productionization/pbpr3u_contained_modela_scoring_build_adapter_repair/adapter_contract_summary.json
data_tw/experiments/provider_bridge_productionization/pbpr3u_contained_modela_scoring_build_adapter_repair/path_containment_matrix.json
data_tw/experiments/provider_bridge_productionization/pbpr3u_contained_modela_scoring_build_adapter_repair/fixture_adapter_plan.json
data_tw/experiments/provider_bridge_productionization/pbpr3u_contained_modela_scoring_build_adapter_repair/mocked_unit_test_summary.json
data_tw/experiments/provider_bridge_productionization/pbpr3u_contained_modela_scoring_build_adapter_repair/static_safety_audit.json
data_tw/experiments/provider_bridge_productionization/pbpr3u_contained_modela_scoring_build_adapter_repair/forbidden_action_audit.json
data_tw/experiments/provider_bridge_productionization/pbpr3u_contained_modela_scoring_build_adapter_repair/artifact_manifest.json
data_tw/experiments/provider_bridge_productionization/pbpr3u_contained_modela_scoring_build_adapter_repair/execution_report_supporting_summary.json
```

## 10. Recommendation For Reviewer

Recommended reviewer gate:

```text
PASS_REPAIR_FOR_PBPR3_V_RERUN_WORKDOC_ONLY
```

该 PASS 只能授权 reviewer 写 PBPR3_V rerun work doc；不能直接授权 publish/latest、accepted/latest switch、qlib refresh、readonly/Agent latest publish、monitor、broker/order、OrderIntentArtifact 或 target output。
