# DNG15_R-B Isolated Model A Score Integration 审查意见

生成时间：2026-06-29T13:58:00+00:00

## 1. Verdict

```text
PASS_GO_DNG16_DAILY_AUTO_MODEL_SCORE_INTEGRATION_DESIGN
```

审查结论：DNG15_R-B 执行结果满足进入 DNG16 daily auto model score integration design 的条件。

核心依据：

```text
isolated score source_feature_artifact 指向 DNG15_R-A-R staged_qlib_bin
source_normalized_artifact 指向 DNG15_R-A-R candidate_normalized
未发现 formal option_c_150_qlib_bin / formal 2026-06-25 provider 被作为输入引用
ModelInferenceInput validator PASS, row_count=150, asof=2026-06-26
ScoreJob validator PASS, raw_score_rows=150, score_status=SCORED_ASOF_TARGET
ModelSignalArtifact validator PASS, signal_rows=150, signal_asof=2026-06-26
signals.csv 仅包含合同允许字段，无 forbidden fields
formal publish / accepted latest / latest_signal / readonly or Agent latest / production switch / replay / NAV / trading / target / FinMind / mixed-provider / training-tuning 均为 false
```

本 PASS 只确认 isolated Model A score integration 成功，不授权 formal provider publish、qlib accepted latest switch、readonly latest、Agent prompt latest 或 production default 切换。

## 2. Findings

### Critical

无。

### High

无。

### Medium

1. isolated score 的输入血缘可验证为 R-A-R staged provider，而不是 formal 6/25 provider。
   - `data_tw/catalog/dng15_r_b_isolated_modela_score_integration_validation.json` 记录：
     - `source_feature_artifact=qlib_pipeline/data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy/staged_qlib_bin`
     - `source_normalized_artifact=qlib_pipeline/data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy/candidate_normalized`
   - `model_load_audit.json` 记录 `qlib_init.provider_uri` 同样指向上述 R-A-R staged provider，且 `expression_cache=null`、`dataset_cache=null`。
   - 对 R-B artifact 搜索 `option_c_150_qlib_bin`、`option_c_150_normalized`、`2026-06-25` 未发现实际输入引用；命中项仅为 forbidden flags 的 false 声明。

2. ModelInferenceInput / ScoreJob / ModelSignalArtifact 三层均通过 validator，且数量和日期正确。
   - ModelInferenceInput `validator_report.json`：`ok=true`、`status=PASS`、`target_asof=2026-06-26`、`row_count=150`、`instrument_count=150`、`manifest_status=READY`、`source_status=READY`。
   - ScoreJob `validator_report.json`：`ok=true`、`status=PASS`、`raw_score_rows=150`、`signal_rows=150`、`score_status=SCORED_ASOF_TARGET`。
   - ModelSignalArtifact `validator_report.json`：`ok=true`、`status=PASS`、`signal_rows=150`、`date_min=2026-06-26`、`date_max=2026-06-26`、`instrument_count=150`。
   - 审查者重跑 validators，结果仍为 PASS。

3. signal contract 符合 R-B 工作文档要求。
   - `signals.csv` 列为：

```text
date,instrument,model_name,model_family,candidate_rank,buy_score,raw_score,score_rank,full_qlib_rank,signal_asof,available_at,source_artifact,source_model_artifact,source_feature_artifact
```

   - 独立 CSV 检查确认 `signal_rows=150`、`unique_instruments=150`、`date=2026-06-26`、`signal_asof=2026-06-26`、`available_at=2026-06-26`。
   - `forbidden_field_audit.csv` 显示 `PASS`，无 forbidden fields。
   - manifest 中 `extensions.fields={}`，未夹带 target、order、label、future_return、realized_pnl 等扩展字段。

4. forbidden actions audit 干净。
   - catalog、ModelInferenceInput manifest、ScoreJob manifest、ModelSignalArtifact manifest 均记录以下治理项为 false：

```text
formal_publish
formal_provider_mutated
formal_normalized_mutated
accepted_latest_switch
latest_signal_updated
readonly_latest_published
agent_prompt_latest_published
production_default_model_or_strategy_switched
strategy_replay_or_nav_triggered
broker_order_quick_trade_triggered
target_position_or_weight_generated
finmind_fallback
mixed_provider_bridge
model_training_or_tuning
```

   - ScoreJob manifest 同时记录 `fallback_used=false`、`production_allowed=false`、`not_published_latest=true`。

### Low

1. R-B 成功仍是 isolated artifact 成功，不是 daily auto 自动消费 staged provider 的完成项。
   - 当前产物证明 `2026-06-26` isolated Model A score 可生成。
   - DNG16 仍需要设计 daily auto 如何在 gate 下选择 provider candidate、生成 ModelInferenceInput / ScoreJob / ModelSignalArtifact、处理已有 score、处理 blocker，并保持 publish_latest_gate 默认关闭。

## 3. Mainline Compliance

符合 DNG15_R-B 工作文档与数据治理主线：

```text
ModelInferenceInput READY
ScoreJob SCORED_ASOF_TARGET
ModelSignalArtifact READY
raw_scores rows=150
signals rows=150
score_status=SCORED_ASOF_TARGET
signal_asof=2026-06-26
available_at=2026-06-26
source_feature_artifact points to R-A-R staged_qlib_bin
source_normalized_artifact points to R-A-R candidate_normalized
source_model_artifact points to frozen qlib Model A params.pkl
production_allowed=false
not_published_latest=true
no latest pointer write evidence in R-B artifact manifests
```

DNG15_R-A-R 审查意见已给出 `PASS_GO_DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION`，R-B 使用的 staged provider 与 candidate normalized 正是该审查批准进入 R-B 的输入。

## 4. Evidence Checked

必读文档：

```text
docs/tw_data_governance/DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION_WORK_CN.md
docs/tw_data_governance/DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION_EXECUTION_REPORT_CN.md
docs/tw_data_governance/DNG15_R_A_R_YAHOO_ACCESS_REPAIR_REVIEW_CN.md
docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md
/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md
```

R-B catalog 与 artifact：

```text
data_tw/catalog/dng15_r_b_isolated_modela_score_integration_validation.json
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated/manifest.json
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated/validator_report.json
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated/source_readiness.json
data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated/feature_lineage.json
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated/manifest.json
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated/validator_report.json
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated/model_load_audit.json
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated/input_readiness.json
data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated/raw_scores.csv
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated/manifest.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated/validator_report.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated/schema.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated/forbidden_field_audit.csv
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated/signals.csv
```

审查者重跑验证：

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

结果：两项均 `ok=true`、`status=PASS`，且行数和 asof 与 catalog 一致。

补充只读核查：

```text
signals.csv signal_rows=150
raw_scores.csv raw_rows=150
signals.csv columns_equal_allowed=true
signals.csv forbidden_hits=[]
signals.csv unique_instruments=150
raw_scores.csv raw_unique_instruments=150
```

## 5. Missing Evidence Or Open Questions

无阻断性缺失证据。

剩余注意事项：

1. R-B 未生成 StrategyInputBundle、readonly source context、Agent prompt 或 NAV，这是符合工作文档禁止策略回放/NAV和 latest publish 的边界。
2. R-B 通过不能被解释为 formal provider 已修复或 qlib accepted latest 已推进；formal `option_c_150_qlib_bin` 是否推进仍需单独授权路线。
3. DNG16 需要把当前 isolated 成功转化为 daily auto design，而不是在 R-B 内临时接自动流程。

## 6. Forbidden Actions Audit

审查结论：干净。

未发现以下行为：

```text
formal publish
formal option_c_150_normalized overwrite
formal option_c_150_qlib_bin overwrite
qlib accepted latest switch
latest_signal.json update
readonly latest publish
Agent prompt latest publish
production default model/strategy switch
strategy replay / NAV
broker/order/quick-trade
target_position / target_weight
FinMind fallback
mixed-provider bridge
model training / hyperparameter tuning
```

证据来自 R-B catalog、三层 manifest/source_readiness、ScoreJob manifest，以及 artifact 文本搜索。

## 7. Next Work Document

### DNG16 Daily Auto Model Score Integration Design

目标：

```text
把 DNG15_R-B 的 isolated Model A score 生成能力纳入 daily auto model_signal_gate 的设计，
让 daily auto 在 raw/normalized/provider candidate ready 时可自动生成标准 ModelInferenceInput / ScoreJob / ModelSignalArtifact，
同时保持 publish_latest_gate 默认关闭。
```

设计范围：

```text
Resolve target asof and pending_asof
Read DataCatalog / readiness / provider candidate
Select formal provider view or validated isolated candidate by explicit gate
Build ModelInferenceInput
Run ScoreJob with frozen Model A params.pkl
Build ModelSignalArtifact
Run validators
Write model_signal_gate_summary
Write daily_chain_status / skipped_asof_ledger status
Mark SKIPPED_ALREADY_EXISTS when existing artifact validator PASS
Mark BLOCKED_* when provider/model/input/validator missing
```

必须保留的安全边界：

```text
publish_latest_gate=false by default
formal provider publish requires separate route
qlib accepted latest switch requires separate route
readonly snapshot latest requires separate gate
Agent prompt latest requires separate gate
production default switch forbidden
broker/order/quick-trade forbidden
target_position/target_weight forbidden
training/tuning forbidden
FinMind fallback or mixed-provider bridge forbidden unless separately authorized and audited
```

最低设计验收：

```text
2026-06-26 R-B artifact 可作为 design fixture
daily auto 能区分 isolated candidate score ready 与 formal latest not published
validator pass 才能标记 ModelSignalArtifact READY
失败时写明 blocked layer，不用旧 signal 冒充新 asof
model_signal_gate 通过不等于 publish_latest_gate 通过
```

## 8. Command For Coordinator Or Executor

```text
请进入 DNG16 Daily Auto Model Score Integration Design。
以 DNG15_R-B isolated Model A score artifacts 作为 fixture/evidence，
设计 daily auto 的 model_signal_gate 如何生成或跳过 ModelInferenceInput / ScoreJob / ModelSignalArtifact。
必须保持 publish_latest_gate 默认关闭，不得 formal publish、不得切 accepted latest、不得更新 latest_signal、不得发布 readonly/Agent latest、不得生产切换、不得策略回放/NAV、不得交易或生成 target_position/target_weight。
```
