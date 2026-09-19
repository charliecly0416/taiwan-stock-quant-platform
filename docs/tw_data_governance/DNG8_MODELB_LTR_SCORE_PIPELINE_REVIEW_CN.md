# DNG8 Model B LTR Score Pipeline 审查报告

生成时间：2026-06-29T08:09:03+00:00

## 1. Verdict

```text
PASS_WITH_CONDITIONS_GO_DNG9
```

DNG8 执行结果通过审查，但只能带条件进入 DNG9：允许进入 daily auto model-signal gate/blocker integration；不允许在 DNG3 仍为 blocked 时生成真实 Model B LTR signal、切 latest、publish、replay 或暴露为生产可用信号。

原因：DNG8 正确尊重了 DNG3 `can_continue_to_model_b_ltr=false`，产物状态为 `BLOCKED_INPUT_NOT_READY`，没有生成 fake LTR signal；fallback 只引用 DNG7 Model A，且明确要求下游 strategy contract 显式允许 qlib-only fallback 后才能消费。

## 2. Findings

### Critical

无。

### High

无。

### Medium

无。

### Low / 条件项

1. DNG9 只能集成 blocker/gate 语义。
   - 证据：`data_tw/catalog/readiness_matrix/2026-06-25/orthogonal_feature_store.json` 仍为 `can_continue_to_model_b_ltr=false`，`external_source_repair_required=true`。
   - 条件：DNG9 不得把 DNG8 的 `PASS_WITH_CONDITIONS_GO_DNG9` 解释为 Model B LTR signal 可生成；只允许在 DNG3 blocked 时继续输出 `BLOCKED_INPUT_NOT_READY`。

2. 真实 LTR signal 放行前仍需外部数据修复。
   - blocking datasets：`corporate_actions`、`monthly_revenue`、`valuation`。
   - 条件：只有 DNG3 重新通过并证明 PIT-safe canonical orthogonal feature families 齐备后，才可生成 `inference_frame.csv`、`raw_scores.csv`、Model B `signals.csv` 或 ModelSignalArtifact。

## 3. 审查证据

已阅读：

- `docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md`
- `docs/tw_data_governance/DNG8_MODELB_LTR_SCORE_PIPELINE_WORK_CN.md`
- `docs/tw_data_governance/DNG8_MODELB_LTR_SCORE_PIPELINE_REVIEW_WORK_CN.md`
- `docs/tw_data_governance/DNG8_MODELB_LTR_SCORE_PIPELINE_EXECUTION_REPORT_CN.md`
- `scripts/tw_modelb_ltr_score_common.py`
- `scripts/build_tw_modelb_ltr_inference_input.py`
- `scripts/run_tw_modelb_ltr_score_job.py`
- `scripts/validate_tw_modelb_ltr_score_job.py`
- `data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/dng8_modelb_ltr_20260625/`
- `data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/dng8_modelb_ltr_20260625/`
- `data_tw/catalog/dng8_modelb_ltr_score_pipeline_validation.json`
- `data_tw/catalog/readiness_matrix/2026-06-25/orthogonal_feature_store.json`

核心证据：

- DNG3 readiness：`can_continue_to_model_b_ltr=false`，`blocking_datasets=["corporate_actions","monthly_revenue","valuation"]`，`external_source_repair_required=true`。
- inference input manifest：`score_status=BLOCKED_INPUT_NOT_READY`，`model_b_ltr_ready=false`，`row_count=0`，`symbol_count=0`。
- score job manifest：`score_status=BLOCKED_INPUT_NOT_READY`，`ltr_signal_generated=false`，`signal_artifact=null`，`qlib_score_used_as_ltr_score=false`。
- catalog validation：`model_b_signal_generated=false`，`mode=BLOCKER_ARTIFACT_NO_INFERENCE`，validator `status=PASS`。

## 4. DNG3 Blocker 尊重情况

结论：通过。

DNG8 没有绕过 DNG3 blocker。`blocker_input_readiness.json`、`source_readiness.json`、ScoreJob `manifest.json` 和 catalog validation 均保留以下阻断信息：

```text
score_status=BLOCKED_INPUT_NOT_READY
model_b_ltr_ready=false
blocking_datasets=corporate_actions, monthly_revenue, valuation
blocker_reasons=dng3_can_continue_to_model_b_ltr_false,
orthogonal_feature_store_not_ready:PARTIAL_READY,
orthogonal_blocking_datasets:corporate_actions,monthly_revenue,valuation
```

这符合 DNG8 工作文档要求：正交数据不足时必须输出 blocker artifact，而不是硬生成 LTR score。

## 5. Fake LTR Signal 检查

结论：通过。

实际目录检查确认未生成以下文件：

```text
data_tw/canonical/.../dng8_modelb_ltr_20260625/inference_frame.csv
data_tw/artifacts/score_jobs/.../dng8_modelb_ltr_20260625/raw_scores.csv
data_tw/artifacts/score_jobs/.../dng8_modelb_ltr_20260625/rank_audit.csv
data_tw/artifacts/score_jobs/.../dng8_modelb_ltr_20260625/signals.csv
data_tw/artifacts/score_jobs/.../dng8_modelb_ltr_20260625/output_model_signal_manifest.json
```

ScoreJob manifest 也明确声明：

```text
signal_artifact=null
ltr_signal_generated=false
qlib_score_used_as_ltr_score=false
do_not_substitute_qlib_score_as_ltr_score=true
```

未发现用 qlib Model A score 冒充 LTR `buy_score`、`raw_score` 或 `score_rank` 的证据。

## 6. Fallback 审查

结论：通过。

fallback 语义被限定为：

```text
fallback_allowed=qlib_only_if_strategy_contract_allows
fallback_signal_artifact=data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng7_modela_20260625
```

DNG8 未生成 Model B signal，也未把 fallback 标记为 LTR signal。下游只有在 strategy dependency/contract 显式允许 qlib-only fallback 时，才能消费 DNG7 Model A。

## 7. Forbidden Action Audit

结论：通过。

脚本与产物审查未发现以下动作被触发：

- 模型训练或调参。
- 真实抓数。
- provider refresh / publish。
- qlib accepted latest switch。
- readonly latest publish。
- Agent prompt latest publish。
- 策略收益回放、ReplayResult 或 NAV 生成。
- broker/order/quick-trade。
- `target_position` / `target_weight` 生成。

命中的 forbidden 关键词主要出现在 deny-list、validator 检查、`forbidden_actions=false` 审计字段，以及 “not generated / not published latest” 说明中；未构成真实动作。

## 8. 验证命令

已运行：

```bash
python -m py_compile scripts/tw_modelb_ltr_score_common.py scripts/build_tw_modelb_ltr_inference_input.py scripts/run_tw_modelb_ltr_score_job.py scripts/validate_tw_modelb_ltr_score_job.py
```

结果：通过，无输出。

已运行：

```bash
python scripts/validate_tw_modelb_ltr_score_job.py --score-dir data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/dng8_modelb_ltr_20260625 --input-dir data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/dng8_modelb_ltr_20260625 --asof 2026-06-25 --json
```

结果摘要：

```text
status=PASS
ok=true
errors=[]
warnings=[]
score_status=BLOCKED_INPUT_NOT_READY
model_b_ltr_ready=false
fallback_allowed=qlib_only_if_strategy_contract_allows
fake_ltr_signal_detected=false
```

## 9. DNG9 放行边界

DNG8 不需要 repair；但 DNG9 的放行范围必须写清：

允许：

- 接入 Model B LTR readiness gate。
- 在 daily auto model-signal gate 中产出 blocker artifact。
- 当 DNG3 仍 blocked 时继续输出 `BLOCKED_INPUT_NOT_READY`。
- 在 strategy contract 显式允许时引用 DNG7 Model A qlib-only fallback。

禁止：

- 在当前 DNG3 blocker 未解除时生成 Model B LTR signal。
- 用 DNG7 Model A score 冒充 LTR score。
- 生成 `inference_frame.csv`、`raw_scores.csv`、Model B `signals.csv` 或 ModelSignalArtifact。
- publish/latest switch/replay/Agent prompt publish。

最终结论：

```text
PASS_WITH_CONDITIONS_GO_DNG9
```
