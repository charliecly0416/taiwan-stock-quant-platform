---
created_at: 2026-07-10
status: review_opinion
phase: PBPR3_X_RERUN_WITH_CONTAINED_REAL_RUNTIME
target_asof: 2026-07-08
reviewer: PBPR3_X_REVIEWER
verdict: PASS_RERUN_FOR_PBPR4_READONLY_AGENT_SOURCE_CONTEXT_WORKDOC_ONLY
production_allowed: false
provider_pull_allowed: false
network_command_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
qlib_refresh_allowed: false
real_qlib_scoring_executed_by_reviewer: false
model_inference_input_build_executed_by_reviewer: false
score_job_build_executed_by_reviewer: false
model_signal_artifact_build_executed_by_reviewer: false
readonly_latest_publish_allowed: false
agent_prompt_publish_allowed: false
monitor_write_allowed: false
order_or_target_output_allowed: false
target_output_allowed: false
next_work_document: docs/tw_portfolio_decision_model/POLICY_PBPR4_READONLY_AGENT_SOURCE_CONTEXT_WORK_CN.md
---

# PBPR3_X Rerun With Contained Real Runtime Review

## 1. Verdict

Reviewer verdict:

```text
PASS_RERUN_FOR_PBPR4_READONLY_AGENT_SOURCE_CONTEXT_WORKDOC_ONLY
```

PBPR3_X 已产生可审查的 `target_asof=2026-07-08` contained no-publish Model A rerun artifacts。该 PASS 只允许进入 PBPR4 readonly/Agent source-context work document；不授权 provider publish、accepted/latest switch、qlib accepted latest refresh、latest/catalog publish、readonly latest publish、Agent prompt publish、monitor、broker/order、OrderIntentArtifact、target_position/target_weight/quantity/shares/lots/target output 或 production/default switch。

## 2. Findings

### Critical

None.

### High

None.

### Medium

None.

### Low

- `contained_runtime_contract_gate.json` 继承 PBPR3_W contract schema，顶层 `runtime_paths` 使用 `pbpr3w_fixture` 作为 contract-only 样例 run id；实际 PBPR3_X payload manifests 内的 `contained_runtime_config.runtime_paths` 使用 `pbpr3x_modela_20260708_contained`，且全部位于 PBPR3_X `planned_future_outputs/` 下。该点不阻断，但 PBPR4/PBPR5 后续报告应优先引用实际 payload manifests。
- `feature_lineage.json` 和 ModelInferenceInput manifest 中保留 `data_tw/canonical/...20260625` 作为历史 price-store lineage/reference。未观察到 PBPR3_X 输出写入 formal `data_tw/canonical`；真实 scoring provider root 为 PBPR2A-AC accepted contained provider root。PBPR4 不得把该 canonical reference 解释为 publish/latest readiness。

## 3. Mainline Compliance

PBPR readiness separation 保持成立：

```text
raw-ready != provider-ready
provider/bridge-ready != signal-ready
signal-ready != accepted/latest publish-ready
readonly context-ready != readonly latest published
Agent context-ready != Agent prompt latest published
```

PBPR3_X 只证明 contained no-publish signal artifact 可以在固定 `target_asof=2026-07-08` 下生成并通过 validator。它不是 publish-ready、readonly latest published、Agent prompt-ready、strategy replay-ready 或 order-ready。

## 4. Evidence Checked

读取并核对：

```text
docs/tw_portfolio_decision_model/POLICY_PBPR_PROVIDER_BRIDGE_PRODUCTIONIZATION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PBPR3_X_RERUN_WITH_CONTAINED_REAL_RUNTIME_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_PBPR3_X_RERUN_WITH_CONTAINED_REAL_RUNTIME_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PBPR3_W_CONTAINED_REAL_RUNTIME_REPAIR_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md
scripts/build_tw_pbpr3x_contained_rerun_evidence.py
scripts/run_tw_model_score_job.py
```

Evidence root:

```text
data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3w/
```

Key observed status:

```text
contained_runtime_contract_gate.status=pass
pre_real_run_manifest_precheck.status=pass
model_inference_input_manifest.status=pass
score_job_manifest.status=pass
model_signal_artifact_no_publish_manifest.status=pass
validator_report.status=PASS
static_safety_audit.status=pass
forbidden_action_audit.all_false=true
execution_report_supporting_summary.verdict=REAL_CONTAINED_RERUN_PASS
artifact_manifest.status=pass
artifact_manifest.missing=[]
artifact_manifest.checksum_mismatches=[]
blocker.json=absent
```

Actual artifact checks:

```text
ModelInferenceInput: asof=2026-07-08, status=READY, rows=150
Qlib prediction: datetime=2026-07-08, rows=150
ScoreJob: asof=2026-07-08, status=SCORED_ASOF_TARGET, raw_score_rows=150
ModelSignalArtifact: signal_asof=2026-07-08, status=READY, rows=150
signals.csv duplicate(date,instrument)=0
signals.csv instrument_count=150
signals.csv score_rank/candidate_rank/full_qlib_rank minmax=1..150
signals.csv available_at_lte_signal_asof=true
```

`signals.csv` columns:

```text
date
instrument
model_name
model_family
candidate_rank
buy_score
raw_score
score_rank
full_qlib_rank
signal_asof
available_at
source_artifact
source_model_artifact
source_feature_artifact
```

No forbidden signal columns observed:

```text
target_position
target_weight
quantity
shares
lots
target
order
future_return
future_excess_return
forward_return
label
realized_pnl
realized_return
action
holding
position
order_qty
execution_price
execution_date
broker_order_id
```

`run_tw_model_score_job.py` review:

```text
contained qlib scoring still requires runtime_config.allow_real_execution == true
runtime_config validation remains before contained scoring
contained provider_uri is PBPR2A-AC staged_qlib_bin
run_metadata flags provider_switch_performed/provider_mutation_triggered/latest_write_performed are false
validation.json now correctly records target_asof_score_generated=true and true_20260625_score_generated=false for 2026-07-08
legacy/default publish/latest behavior was not broadened by the reviewed change
```

## 5. Commands Run By Reviewer

Allowed checks run:

```text
python -m py_compile scripts/run_tw_pbpr3_modela_no_publish_dry_run.py scripts/tw_modela_score_common.py scripts/build_tw_model_inference_input.py scripts/run_tw_model_score_job.py scripts/validate_tw_score_job.py scripts/build_tw_pbpr3w_contained_runtime_evidence.py scripts/build_tw_pbpr3x_contained_rerun_evidence.py tests/unit/test_pbpr3_modela_no_publish_entrypoint.py
python -m pytest tests/unit/test_pbpr3_modela_no_publish_entrypoint.py -q
python -c "<PBPR3_X top-level JSON parse>"
python -c "<PBPR3_X artifact_manifest checksum recomputation>"
python -c "<PBPR3_X evidence status summary>"
python -c "<CSV row/schema/forbidden-column audit>"
python -c "<actual artifact manifest and validator summary>"
python -c "<path containment and blocker absence checks>"
rg -n "<forbidden path/action tokens>" data_tw/.../rerun_after_pbpr3w scripts/run_tw_model_score_job.py scripts/build_tw_pbpr3x_contained_rerun_evidence.py
sed -n ... reviewed docs/scripts
find data_tw/.../rerun_after_pbpr3w -maxdepth ... -type f
```

Results:

```text
py_compile=pass
focused pytest=17 passed in 0.75s
PBPR3_X top-level JSON parse=pass for 10 files
artifact_manifest.status=pass
artifact_manifest.entries=20
artifact_manifest.missing=[]
artifact_manifest checksum_mismatches=[]
manifest checksum recomputation mismatches=[]
blocker.json=absent
```

Commands intentionally not run:

```text
provider/network pull
Yahoo/Scrapling/FinMind/yfinance
provider publish
accepted/latest switch
qlib accepted latest refresh
latest/catalog publish
readonly latest publish
Agent prompt build or publish
monitor/broker/order
OrderIntentArtifact generation
target_position/target_weight/quantity/shares/lots/target output
strategy replay
real build/scoring rerun
```

## 6. Missing Evidence Or Open Questions

No blocking missing evidence.

PBPR4 must treat PBPR3_X output as isolated no-publish source evidence only. It may design/validate source-context wiring against this artifact, but must not publish latest pointers or connect Agent prompt latest/default consumers.

## 7. Forbidden Actions Audit

Reviewer did not run and did not observe:

```text
provider/network pull
provider publish
accepted/latest switch
qlib refresh
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

Keyword scan classification:

```text
no_publish/no_catalog/no_latest/no_target_output fields: allowed safety flags
target_position/target_output hits: false audit fields or no_target_output declarations
publish/latest/readonly/agent/monitor/broker/order hits: forbidden-action audit/report text or false flags
data_tw/canonical hits: lineage/source reference only, not PBPR3_X output path
```

## 8. Next Work Document

Next work document written:

```text
docs/tw_portfolio_decision_model/POLICY_PBPR4_READONLY_AGENT_SOURCE_CONTEXT_WORK_CN.md
```

PBPR4 is restricted to readonly/Agent source-context readiness design and no-publish/no-latest wiring evidence. It must not publish readonly latest, build or publish Agent prompt latest, switch production defaults, trigger monitor/broker/order, generate OrderIntentArtifact, or output target fields.
