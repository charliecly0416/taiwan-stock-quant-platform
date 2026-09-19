# DNG7 ModelA Score Pipeline 审查报告

生成日期：2026-06-29

审查者：DNG7 Reviewer

## 1. 审查结论

Verdict：`PASS_GO_DNG8`

DNG7 执行结果可以进入 DNG8 的只读策略输入合同阶段。通过原因是：

1. DNG7 生成了目标 asof `2026-06-25` 的 qlib Model A score，ScoreJob 状态为 `SCORED_ASOF_TARGET`，不是旧 signal 冒充，也不是 partial/block。
2. ModelInferenceInput、ScoreJob、ModelSignalArtifact 三层产物均有 manifest、schema/audit、validator report 与 source lineage。
3. source run 明确为 `option_c_daily_signal_20260625_20260629T075235Z`，其 `prediction.csv` 日期为 `2026-06-25`，并由 frozen `params.pkl` 通过 qlib fixed Option C provider 只读 predict 生成。
4. `ModelSignalArtifact` 含合同要求的 core fields，150 行、150 个 instrument、`date/signal_asof/available_at=2026-06-25`，无 duplicate key，无 forbidden columns。
5. 执行与产物均声明并验证未训练、未调参、未触发 LTR Model B、未抓数、未 provider refresh/publish、未切 qlib accepted latest、未 publish readonly/Agent latest、未 replay/NAV、未 broker/order/quick-trade、未生成 target position/weight。

DNG8 仍只能继续做只读 StrategyInputBundle / route input 合同与 validator。此 PASS 不授权 replay、readonly latest publish、Agent prompt latest publish、frontend default、provider publish、accepted latest switch 或任何交易相关动作。

## 2. 已审查输入

已阅读指定材料：

```text
docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md
docs/tw_data_governance/DNG7_MODELA_SCORE_PIPELINE_WORK_CN.md
docs/tw_data_governance/DNG7_MODELA_SCORE_PIPELINE_REVIEW_WORK_CN.md
docs/tw_data_governance/DNG7_MODELA_SCORE_PIPELINE_EXECUTION_REPORT_CN.md
scripts/tw_modela_score_common.py
scripts/build_tw_model_inference_input.py
scripts/run_tw_model_score_job.py
scripts/validate_tw_model_inference_input.py
scripts/validate_tw_score_job.py
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/dng7_modela_20260625/
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022/dng7_modela_20260625/
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng7_modela_20260625/
data_tw/catalog/dng7_modela_score_pipeline_validation.json
```

按新模型审查合同额外核对：

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md
qlib_pipeline/examples/tw/run_option_c_daily_signal_option_c_provider.py
qlib_pipeline/data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260625_20260629T075235Z/run_metadata.json
```

本审查未抓数、未修复、未训练、未调参、未重新推理或 score、未回放、未 publish、未切 latest。

## 3. 本地验证结果

执行：

```bash
python -m py_compile scripts/tw_modela_score_common.py scripts/build_tw_model_inference_input.py scripts/run_tw_model_score_job.py scripts/validate_tw_model_inference_input.py scripts/validate_tw_score_job.py
```

结果：通过，退出码 0。

执行：

```bash
python scripts/validate_tw_model_inference_input.py --input-dir data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/dng7_modela_20260625 --json
```

结果摘要：

```text
ok=true
status=PASS
artifact_type=ModelInferenceInput
target_asof=2026-06-25
row_count=150
instrument_count=150
manifest_status=READY
source_status=READY
errors=[]
```

执行：

```bash
python scripts/validate_tw_score_job.py --score-dir data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022/dng7_modela_20260625 --json
```

结果摘要：

```text
ok=true
status=PASS
artifact_type=ScoreJob
target_asof=2026-06-25
raw_score_rows=150
signal_rows=150
score_status=SCORED_ASOF_TARGET
signal_summary.row_count=150
signal_summary.duplicate_key_count=0
signal_summary.date_min=2026-06-25
signal_summary.date_max=2026-06-25
signal_summary.instrument_count=150
signal_summary.forbidden_columns=[]
errors=[]
```

## 4. 真实 2026-06-25 Score 审查

审查结论：合格，是真实目标 asof score。

ScoreJob manifest：

```text
asof=2026-06-25
status=SCORED_ASOF_TARGET
score_status=SCORED_ASOF_TARGET
row_count=150
qlib_source_run.run_id=option_c_daily_signal_20260625_20260629T075235Z
qlib_source_run.status=accepted
```

source run metadata：

```text
asof=2026-06-25
status=accepted
model_path=mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a/artifacts/params.pkl
provider_uri=data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin
normalized_source=data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized
```

source prediction 抽查：

```text
datetime,instrument,score
2026-06-25,TW1301,0.103441232996687
2026-06-25,TW1303,0.06310599699213373
```

`signals.csv` 抽查显示：

```text
date=2026-06-25
signal_asof=2026-06-25
available_at=2026-06-25
source_artifact=qlib_pipeline/data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260625_20260629T075235Z/prediction.csv
source_model_artifact=qlib_pipeline/mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a/artifacts/params.pkl
source_feature_artifact=qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin
```

因此 DNG7 没有把旧 asof signal 冒充为 2026-06-25。

## 5. Source Lineage 与 PIT 审查

ModelInferenceInput manifest/source readiness 记录：

```text
model_artifact_path=qlib_pipeline/mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a/artifacts/params.pkl
model_artifact_sha256=06dc2b59e411044da9747eb58e3a70336b02c0818a9e180a39d8b3302409775e
legacy_e1_model_alias_path=data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/run/phasee1_frozen_qlib_model.pkl
qlib_provider_calendar_max=2026-06-25
normalized_source_summary.symbols_with_asof=150
provider_field_inventory.status=pass
feature_dump_status=READY
```

Feature lineage 记录：

```text
inference_mode=qlib DatasetH snapshot + frozen Option C LGBModel.predict
feature_handler=qlib.contrib.data.handler.Alpha158
provider_required_fields=close,factor,high,low,open,volume,vwap
source_config=qlib_pipeline/configs/tw_yahoo_primary_alpha158.yaml
source_universe=qlib_pipeline/data_tw/experiments/option_c_forward_validation/timed_data_availability_retry_20260601T101323Z/symbols_accepted_prediction_universe.txt
pit_policy=snapshot segment is restricted to asof; Alpha158 rolling features derive from current/past provider rows only
```

`qlib_pipeline/examples/tw/run_option_c_daily_signal_option_c_provider.py` 中本轮调用路径为 fixed Option C provider：加载 frozen `MODEL_PATH`，构造 `DatasetH(..., segments={"snapshot": (asof, asof)})`，然后执行 `model.predict(dataset, segment="snapshot")`。未发现训练、调参、provider mutation 或 latest 写入路径被 DNG7 调用。

## 6. ModelSignalArtifact 合同审查

`signals.csv` 字段：

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

审查判断：

- core fields 完整，符合 `MODEL_SIGNAL_CONTRACT_CN.md`。
- qlib Model A 映射为 `candidate_rank=score_rank`、`buy_score=raw_score`、`full_qlib_rank=score_rank`，与纯 qlib 模型语义一致。
- `available_at` 不晚于 `signal_asof`。
- `extensions.fields={}`，没有未声明 extension 字段。
- forbidden field audit 为 PASS，validator summary 也显示 forbidden columns 为空。
- manifest 标记 `production_allowed=false`、`not_published_latest=true`。

## 7. 禁止动作审查

DNG7 三层产物与 source run 均记录禁止动作未触发：

```text
model_training_triggered=false
model_tuning_triggered=false
ltr_model_b_triggered=false
real_data_fetch_triggered=false
provider_refresh_triggered=false
provider_publish_triggered=false
qlib_accepted_latest_switched=false
readonly_latest_published=false
agent_prompt_published=false
strategy_replay_triggered=false
replay_result_nav_generated=false
broker_order_quick_trade_triggered=false
target_position_or_weight_generated=false
```

source run metadata 额外记录：

```text
allow_refresh=false
paper_trading_started=false
live_trading_started=false
target_trades_generated=false
executable_orders_generated=false
model_retraining_performed=false
model_tuning_performed=false
provider_switch_performed=false
refresh_triggered=false
publish_triggered=false
provider_mutation_triggered=false
```

审查结论：未发现 latest switch、publish、LTR、训练/调参、replay 或交易链路被触发。

## 8. Catalog Validation 审查

`data_tw/catalog/dng7_modela_score_pipeline_validation.json` 记录：

```text
run_id=dng7_modela_20260625
asof=2026-06-25
model_id=e4_frozen_qlib_2018_2022
pipeline_status=SCORED_ASOF_TARGET
true_20260625_score_generated=true
mode=TRUE_LOCAL_INFERENCE
model_signal_status=READY
blockers=[]
```

catalog 汇总与本地 validator 复验一致。

## 9. DNG8 边界

允许进入 DNG8 的范围：

```text
StrategyInputBundle / route input bundle 合同
只读消费 DNG7 ModelSignalArtifact
validator / manifest / lineage / readiness gate
```

DNG8 仍禁止：

```text
provider refresh / publish
qlib accepted latest switch
readonly latest publish
Agent prompt latest publish
frontend default switch
策略收益回放或 ReplayResult/NAV 生成
broker/order/quick-trade
target_position / target_weight
```

## 10. Verdict

```text
PASS_GO_DNG8
```
