# DNG7 ModelInferenceInput / qlib Model A ScoreJob 工作文档

生成日期：2026-06-29

## 1. 背景

DNG6_R 审查结论：

```text
PASS_GO_DNG7
```

DNG7 是模型层入口，但只允许 qlib Model A 的只读 pipeline。不得训练、不得调参、不得切 latest、不得 publish、不得 LTR Model B。

## 2. 目标

建立 qlib Model A 的标准推理输入、ScoreJob、ModelSignalArtifact builder/validator。

如果本地模型 artifact、qlib provider view、feature dump 或推理依赖不足，必须显式 BLOCK，不得伪造 score。

## 3. 必须生成

脚本：

```text
scripts/build_tw_model_inference_input.py
scripts/run_tw_model_score_job.py
scripts/validate_tw_model_inference_input.py
scripts/validate_tw_score_job.py
```

产物：

```text
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/{run_id}/manifest.json
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/{run_id}/inference_frame.csv
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/{run_id}/schema.json
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/{run_id}/source_readiness.json
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/{run_id}/feature_lineage.json
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/{run_id}/pit_audit.csv
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/{run_id}/coverage_audit.csv
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/{run_id}/validator_report.json
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022/{run_id}/manifest.json
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022/{run_id}/raw_scores.csv
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022/{run_id}/rank_audit.csv
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022/{run_id}/model_load_audit.json
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022/{run_id}/input_readiness.json
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022/{run_id}/output_model_signal_manifest.json
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022/{run_id}/validator_report.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/{run_id}/manifest.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/{run_id}/signals.csv
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/{run_id}/schema.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/{run_id}/coverage_audit.csv
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/{run_id}/forbidden_field_audit.csv
data_tw/catalog/dng7_modela_score_pipeline_validation.json
docs/tw_data_governance/DNG7_MODELA_SCORE_PIPELINE_EXECUTION_REPORT_CN.md
```

## 4. 输入来源

允许读取：

```text
data_tw/catalog/data_catalog.json
data_tw/catalog/latest_status.json
data_tw/catalog/daily_readiness_dashboard.json
data_tw/catalog/readiness_matrix/2026-06-25/price_market_calendar.json
data_tw/canonical/price_store/tw_equity_daily/dng2_r_price_market_calendar_20260625/
qlib_pipeline/data_tw/**
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/**
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/**
```

## 5. 允许的两种实现路径

### 5.1 真正本地推理

如果本地 qlib provider、模型 artifact、推理代码、feature dump 齐备，可只读生成目标 asof 的 qlib Model A score。

必须记录：

```text
model_artifact_path
qlib_provider_view
feature_dump_status
inference_command
```

### 5.2 受控 legacy signal adapter

如果无法安全本地推理，但已有同 asof 或较旧 asof 的合法 ModelSignalArtifact，可生成 `BLOCKED_INPUT_NOT_READY` 或 `SKIPPED_ALREADY_EXISTS` / `LEGACY_ADAPTER_PARTIAL`。

不得把旧 asof signal 冒充 2026-06-25 新 score。

## 6. ModelSignalArtifact 字段

`signals.csv` 必须符合 `MODEL_SIGNAL_CONTRACT_CN.md`：

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

## 7. Validator 要求

必须检查：

- required files；
- required fields；
- forbidden fields；
- no future labels；
- date/instrument unique；
- score/rank numeric；
- available_at policy；
- no training/no tuning；
- no publish/no latest switch；
- score_status 合法；
- 如果 asof 不等于目标 asof，必须 partial/block。

## 8. 禁止动作

不得执行：

```text
模型训练
模型调参
LTR Model B rerank
真实抓数
provider refresh / publish
qlib accepted latest switch
readonly latest publish
Agent prompt latest publish
策略收益回放
ReplayResult/NAV 生成
broker/order/quick-trade
target_position / target_weight
```

## 9. 执行报告

报告必须说明：

1. 是真推理、SKIPPED_ALREADY_EXISTS、LEGACY_ADAPTER_PARTIAL 还是 BLOCKED。
2. ModelInferenceInput 状态。
3. ScoreJob 状态。
4. ModelSignalArtifact 状态。
5. 是否生成了 2026-06-25 qlib Model A score。
6. validator 输出。
7. forbidden action audit。
8. 是否建议进入 DNG8。
