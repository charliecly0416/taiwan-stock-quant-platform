# DNG15_R-B Isolated Model A Score Integration 工作文档

生成日期：2026-06-29

## 1. 背景

DNG15_R-A-R 已通过审查：

```text
PASS_GO_DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION
```

已具备 `2026-06-26` Yahoo-only same-lineage staged provider candidate：

```text
candidate_normalized symbols_success=150/150
candidate_normalized symbols_with_asof=150/150
staged_qlib_bin calendar_has_asof=true
provider_validation.status=pass
Model A staged smoke.status=pass
prediction_rows=150
finite_prediction_share=1.0
```

关键输入：

```text
qlib_pipeline/data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy/staged_qlib_bin
qlib_pipeline/data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy/candidate_normalized
```

当前不能直接使用现有 DNG7 production-like 脚本，因为：

- `scripts/tw_modela_score_common.py` 仍固定 `TARGET_ASOF=2026-06-25`；
- `scripts/build_tw_model_inference_input.py` 依赖 fixed formal provider 和 fixed 6/25 readiness；
- `scripts/run_tw_model_score_job.py` 调用 fixed wrapper；
- `qlib_pipeline/examples/tw/run_option_c_daily_signal_option_c_provider.py` 明确只接受 formal `option_c_150_qlib_bin`，不接受 arbitrary provider path。

因此 R-B 必须新建隔离脚本，显式读取 R-A-R staged provider candidate，生成 isolated ModelInferenceInput / ScoreJob / ModelSignalArtifact。

## 2. 目标

为 `2026-06-26` 生成 isolated Model A score artifacts：

```text
ModelInferenceInput READY
ScoreJob SCORED_ASOF_TARGET
ModelSignalArtifact READY
```

输出目录必须是 isolated run_id，不得写 formal latest：

```text
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated/
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated/
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated/
```

最低通过条件：

```text
ModelInferenceInput validator PASS
ScoreJob validator PASS
ModelSignalArtifact validator PASS
raw_scores rows=150
signals rows=150
score_status=SCORED_ASOF_TARGET
signal_asof=2026-06-26
available_at=2026-06-26
source_feature_artifact points to staged_qlib_bin
source_normalized_artifact points to candidate_normalized
source_model_artifact points to frozen qlib Model A params.pkl
production_allowed=false
not_published_latest=true
no latest pointer write
```

## 3. 非目标 / 禁止动作

本阶段禁止：

- formal provider publish；
- 覆盖 formal `option_c_150_normalized`；
- 覆盖 formal `option_c_150_qlib_bin`；
- qlib accepted latest switch；
- 修改 `latest_signal.json`；
- publish readonly latest；
- publish Agent prompt latest；
- production default model/strategy switch；
- 触发模型训练、调参、LTR Model B；
- 触发策略回放/NAV；
- broker/order/quick-trade；
- target_position / target_weight；
- FinMind fallback；
- mixed-provider bridge。

允许：

- 读取 R-A-R staged provider / candidate normalized；
- 使用 qlib `DatasetH` + frozen `params.pkl` 对 staged provider 进行 asof snapshot prediction；
- 生成 isolated artifacts；
- 运行 validators；
- 生成 execution/review 文档和 catalog summary。

## 4. 实现要求

建议新增最小脚本：

```text
scripts/build_tw_dng15_r_b_isolated_modela_score_integration.py
```

脚本必须：

1. 读取 DNG15_R-A-R decision/readiness，确认 `PASS_GO_DNG15_R_B...` 或 candidate ready。
2. 验证 staged provider：
   - calendar includes `2026-06-26`；
   - 150 symbols；
   - `open/high/low/close/volume/vwap/factor` bins 完整；
   - no rejected fields。
3. 验证 candidate normalized：
   - 150 CSV；
   - 150/150 包含 `2026-06-26`；
   - date_max min/max 都为 `2026-06-26`。
4. 生成 `ModelInferenceInput`：
   - `inference_frame.csv` 150 rows；
   - `source_readiness.json`；
   - `feature_lineage.json`；
   - `coverage_audit.csv`；
   - `pit_audit.csv`；
   - `manifest.json`；
   - `validator_report.json`。
5. 使用 qlib isolated provider 执行 Model A prediction：
   - `qlib.init(provider_uri=<staged_qlib_bin>, region="tw", expression_cache=None, dataset_cache=None)`；
   - `Alpha158` handler；
   - `start_time=2015-05-04`；
   - `end_time=2026-06-26`；
   - snapshot segment `(2026-06-26, 2026-06-26)`；
   - load frozen model `qlib_pipeline/mlruns/.../params.pkl`；
   - 不训练、不 fit、不调参。
6. 生成 ScoreJob：
   - `raw_scores.csv`；
   - `rank_audit.csv`；
   - `model_load_audit.json`；
   - `input_readiness.json`；
   - `output_model_signal_manifest.json`；
   - `manifest.json`；
   - `validator_report.json`。
7. 生成 ModelSignalArtifact：
   - `signals.csv`；
   - `schema.json`；
   - `coverage_audit.csv`；
   - `forbidden_field_audit.csv`；
   - `manifest.json`；
   - `validator_report.json`。
8. 生成 catalog summary：
   - `data_tw/catalog/dng15_r_b_isolated_modela_score_integration_validation.json`。

## 5. 字段合同

`ModelSignalArtifact signals.csv` 必须包含并只按既有合同表达：

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

禁止字段：

```text
future_return_*
future_excess_return_*
forward_return_*
label_*
relevance_10d_top_heavy
ltr_relevance_label
realized_pnl
realized_return
action
holding
position
target_position
target_weight
order_qty
execution_price
execution_date
broker_order_id
```

## 6. 产物要求

执行者必须生成：

```text
docs/tw_data_governance/DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION_EXECUTION_REPORT_CN.md
data_tw/catalog/dng15_r_b_isolated_modela_score_integration_validation.json
```

以及：

```text
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated/
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated/
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated/
```

## 7. 验证要求

至少运行：

```bash
python -m py_compile \
  scripts/build_tw_dng15_r_b_isolated_modela_score_integration.py \
  scripts/validate_tw_model_inference_input.py \
  scripts/validate_tw_score_job.py
```

必须运行或等价复用：

```bash
python scripts/validate_tw_model_inference_input.py \
  --input-dir data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated \
  --asof 2026-06-26 \
  --json

python scripts/validate_tw_score_job.py \
  --score-dir data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated \
  --signal-dir data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated \
  --asof 2026-06-26 \
  --json
```

如果复用现有 validators 因 hardcoded common constants 误判 fixed provider，不得强行修改 production common constants；可在 R-B 脚本内生成等价 validator report，并在执行报告中说明原因。

## 8. 审查要求

审查者必须生成：

```text
docs/tw_data_governance/DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION_REVIEW_CN.md
```

verdict 只能是：

```text
PASS_GO_DNG16_DAILY_AUTO_MODEL_SCORE_INTEGRATION_DESIGN
PASS_WITH_CONDITIONS_GO_DNG16
FAIL_NEEDS_DNG15_R_B_REPAIR
STOP_NEEDS_COORDINATOR_DECISION
```

通过条件：

- ModelInferenceInput / ScoreJob / ModelSignalArtifact 均 ready；
- 150 rows；
- asof 正确；
- source_feature_artifact 指向 R-A-R staged provider；
- source_model_artifact 指向 frozen model；
- production/forbidden flags 干净；
- 没有 formal publish/latest switch/交易/target。

如果 isolated score 成功，但 daily auto 还不能自动消费 staged provider，审查者应给 PASS 并建议 DNG16 做 daily auto model score integration design，而不是在 R-B 擅自改自动流程。

## 9. 执行者命令

```text
请执行 DNG15_R-B Isolated Model A Score Integration。
先读取本工作文档、DNG15_R-A-R 执行和审查文档、DNG15_R-A-R decision/readiness、数据治理主线。
只允许消费 R-A-R staged provider candidate 生成 isolated ModelInferenceInput / ScoreJob / ModelSignalArtifact。
禁止 formal publish、accepted latest switch、latest_signal 更新、readonly/Agent latest publish、生产切换、策略回放、交易、target_position/target_weight、FinMind fallback、mixed-provider bridge。
完成后写执行报告和 validation JSON。
```

## 10. 审查者命令

```text
请独立审查 DNG15_R-B 执行结果。
重点检查 isolated score 是否真来自 R-A-R staged provider、是否 150 rows、是否 asof=2026-06-26、是否 validator pass、是否没有 forbidden actions。
给出明确 verdict，并写 DNG16 或 repair 建议。
```
