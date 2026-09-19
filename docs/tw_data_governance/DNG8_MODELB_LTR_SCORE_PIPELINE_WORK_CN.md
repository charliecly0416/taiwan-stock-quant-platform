# DNG8 LTR Model B Score Pipeline 工作文档

生成日期：2026-06-29

## 1. 背景

DNG7 审查结论：

```text
PASS_GO_DNG8
```

DNG3 已明确：

```text
can_continue_to_model_b_ltr=false
blocking_datasets=["corporate_actions","monthly_revenue","valuation"]
```

所以 DNG8 的首要目标不是硬生成 LTR score，而是建立 LTR Model B pipeline/gate，并在数据不齐时正确 BLOCK 或 fallback。

## 2. 目标

建立 Model B LTR 的 ModelInferenceInput / ScoreJob / ModelSignalArtifact builder/validator 或 blocker artifact。

若 LTR 必需正交数据不足，必须输出：

```text
score_status=BLOCKED_INPUT_NOT_READY
model_b_ltr_ready=false
fallback_allowed=qlib_only_if_strategy_contract_allows
```

不得用 qlib Model A score 冒充 LTR score。

## 3. 必须生成

脚本可复用 DNG7 通用脚本，也可新增：

```text
scripts/build_tw_modelb_ltr_inference_input.py
scripts/run_tw_modelb_ltr_score_job.py
scripts/validate_tw_modelb_ltr_score_job.py
```

产物：

```text
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/{run_id}/manifest.json
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/{run_id}/inference_frame.csv 或 blocker_input_readiness.json
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/{run_id}/source_readiness.json
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/{run_id}/feature_lineage.json
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/{run_id}/pit_audit.csv
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/{run_id}/manifest.json
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/{run_id}/input_readiness.json
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/{run_id}/validator_report.json
data_tw/catalog/dng8_modelb_ltr_score_pipeline_validation.json
docs/tw_data_governance/DNG8_MODELB_LTR_SCORE_PIPELINE_EXECUTION_REPORT_CN.md
```

如果真能生成 LTR score，还必须生成标准 ModelSignalArtifact。但只有在：

- Model A 2026-06-25 signal ready；
- DNG3 orthogonal features complete enough for trained LTR feature schema；
- LTR model artifact / schema ready；
- PIT audit pass；

全部满足时才允许。

## 4. 输入来源

必须读取：

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng7_modela_20260625/
data_tw/canonical/orthogonal_feature_store/daily_orthogonal/dng3_orthogonal_feature_store_20260625/
data_tw/catalog/readiness_matrix/2026-06-25/orthogonal_feature_store.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/**
```

## 5. 审计重点

必须明确：

- LTR 只在 Model A qlib top50 内 rerank；
- `candidate_rank` / `full_qlib_rank` 必须来自 Model A；
- `buy_score` / `score_rank` 才来自 LTR；
- 若 blocked，不得生成 fake signals.csv；
- 若 fallback qlib-only，只能引用 DNG7 Model A signal。

## 6. 禁止动作

不得执行：

```text
模型训练
模型调参
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

## 7. 执行报告

报告必须说明：

1. LTR 是否 ready。
2. 若 blocked，blocking_datasets 和 blocker 证据。
3. 若 fallback，fallback 语义。
4. 是否生成 Model B signal。
5. validator 输出。
6. forbidden action audit。
7. 是否建议进入 DNG9 daily auto model-signal gate integration。
