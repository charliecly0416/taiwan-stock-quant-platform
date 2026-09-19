# DNG7 Model A Score Pipeline 审查工作文档

生成日期：2026-06-29

## 1. 审查输入

```text
docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md
docs/tw_data_governance/DNG7_MODELA_SCORE_PIPELINE_WORK_CN.md
docs/tw_data_governance/DNG7_MODELA_SCORE_PIPELINE_EXECUTION_REPORT_CN.md
scripts/build_tw_model_inference_input.py
scripts/run_tw_model_score_job.py
scripts/validate_tw_model_inference_input.py
scripts/validate_tw_score_job.py
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/{run_id}/
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022/{run_id}/
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/{run_id}/
data_tw/catalog/dng7_modela_score_pipeline_validation.json
```

## 2. 审查目标

判断 DNG7 是否建立 qlib Model A score pipeline，是否真的生成目标 asof score，或是否正确 BLOCK/PARTIAL；是否可以进入 DNG8。

## 3. 必查项

1. 是否未训练、未调参。
2. 是否未触发 LTR Model B。
3. 若生成 2026-06-25 score，是否有模型 artifact、provider view、feature lineage。
4. 若使用旧 signal，是否明确 partial/block，没有冒充新 score。
5. ModelSignalArtifact 字段是否符合合同。
6. validator 是否通过。
7. 是否未 publish/latest switch。

## 4. 建议命令

```text
python -m py_compile scripts/build_tw_model_inference_input.py scripts/run_tw_model_score_job.py scripts/validate_tw_model_inference_input.py scripts/validate_tw_score_job.py
python scripts/validate_tw_model_inference_input.py --input-root <path> --json
python scripts/validate_tw_score_job.py --score-job-root <path> --json
```

## 5. Verdict

审查结论只能是：

```text
PASS_GO_DNG8
PASS_WITH_CONDITIONS_GO_DNG8
FAIL_NEEDS_DNG7_REPAIR
STOP_MODEL_INFERENCE_SOURCE_REQUIRED
```

## 6. 输出

审查者必须写：

```text
docs/tw_data_governance/DNG7_MODELA_SCORE_PIPELINE_REVIEW_CN.md
```
