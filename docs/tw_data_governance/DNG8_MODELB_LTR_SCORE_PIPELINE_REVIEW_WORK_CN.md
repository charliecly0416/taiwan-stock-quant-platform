# DNG8 LTR Model B Score Pipeline 审查工作文档

生成日期：2026-06-29

## 1. 审查输入

```text
docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md
docs/tw_data_governance/DNG8_MODELB_LTR_SCORE_PIPELINE_WORK_CN.md
docs/tw_data_governance/DNG8_MODELB_LTR_SCORE_PIPELINE_EXECUTION_REPORT_CN.md
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/{run_id}/
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/{run_id}/
data_tw/catalog/dng8_modelb_ltr_score_pipeline_validation.json
```

## 2. 审查目标

判断 DNG8 是否正确建立 Model B LTR pipeline/gate，并在正交数据不足时正确 BLOCK，而不是伪造 LTR score。

## 3. 必查项

1. 是否尊重 DNG3 `can_continue_to_model_b_ltr=false`。
2. 是否没有用 qlib score 冒充 LTR score。
3. 若 blocked，是否有 blocker artifact 和 validator report。
4. 若生成 LTR signal，是否满足 LTR top50 rerank 语义。
5. 是否未训练/调参/publish/latest switch/replay。

## 4. Verdict

审查结论只能是：

```text
PASS_GO_DNG9
PASS_WITH_CONDITIONS_GO_DNG9
FAIL_NEEDS_DNG8_REPAIR
STOP_EXTERNAL_SOURCE_REPAIR_REQUIRED
```

## 5. 输出

审查者必须写：

```text
docs/tw_data_governance/DNG8_MODELB_LTR_SCORE_PIPELINE_REVIEW_CN.md
```
