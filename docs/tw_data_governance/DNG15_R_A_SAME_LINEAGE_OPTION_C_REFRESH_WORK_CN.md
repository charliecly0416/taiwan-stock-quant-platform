# DNG15_R-A Same-Lineage Option C Normalized Refresh / Isolated Provider Candidate 工作文档

生成日期：2026-06-29

## 1. 背景

DNG15 已完成执行和审查，结论为：

```text
STOP_NEEDS_COORDINATOR_DECISION
```

核心 blocker 已具体化为：

```text
normalized_source_missing_asof_and_formal_refresh_requires_network
```

当前事实：

- `FinMind raw daily price` 已有 `2026-06-26`；
- frozen Model A 所需的同口径 `Option C Yahoo/Scrapling normalized` 只到 `2026-06-25`；
- formal `option_c_150_qlib_bin` calendar 只到 `2026-06-25`；
- 因此不能合法生成 `2026-06-26` Model A score；
- 不允许用 FinMind raw 直接冒充 Option C qlib provider input。

统筹已授权进入：

```text
DNG15_R-A same-lineage Yahoo/Scrapling Option C normalized refresh / isolated provider candidate build
```

## 2. 目标

在不切 production latest、不覆盖 formal provider、不发布 readonly/Agent latest 的前提下，为 `2026-06-26` 建立同口径 Yahoo/Scrapling Option C staged 数据链：

```text
Yahoo/Scrapling same-lineage fetch
-> candidate_normalized
-> staged_qlib_bin
-> normalized/provider validator
-> Model A staged model smoke
-> optional daily signal dry-run against staged/publish-dry-run gate
-> DNG15_R-A execution report
```

若成功，最低目标是证明：

```text
candidate_normalized symbols_success=150/150
candidate_normalized symbols_with_asof=150/150
staged_qlib_bin calendar_has_asof=true
staged_qlib_bin expected feature fields complete
staged Model A smoke prediction_rows=150
finite_prediction_share=1.0
formal_provider_mutated=false
latest_signal_updated=false
production_allowed=false
```

若失败，必须输出机器可读 blocker，明确卡在：

```text
network_unavailable
yahoo_scrapling_fetch_failed
symbols_missing_asof
normalized_validation_failed
staged_provider_dump_failed
staged_provider_validation_failed
model_smoke_failed
unexpected_latest_or_formal_mutation
```

## 3. 授权边界

本阶段允许：

- 对 Yahoo Finance chart API 通过 Scrapling 发起 staged same-lineage fetch；
- 使用本地 proxy（如 `http://127.0.0.1:7890`）或无 proxy 进行 fetch；
- 只写入 isolated/staged 目录；
- 用 `DumpDataAll` 从 candidate normalized 重建 isolated `staged_qlib_bin`；
- 运行 staged Model A smoke；
- 运行 dry-run publish audit 或 daily signal dry-run，只要不写 latest；
- 生成 execution/review 文档和 catalog/readiness artifact。

本阶段仍禁止：

- 覆盖 formal `option_c_150_normalized`；
- 覆盖 formal `option_c_150_qlib_bin`；
- 执行 formal provider publish；
- 切 qlib accepted latest；
- 修改 `latest_signal.json`；
- publish readonly latest；
- publish Agent prompt latest；
- 切 production default model/strategy；
- 触发模型训练、调参、LTR rerank 训练；
- 触发策略回放以外的生产动作；
- broker/order/quick-trade；
- 生成 target_position 或 target_weight；
- 用 FinMind raw fallback 或混合 provider bridge。

如果执行者发现现有脚本需要进入 `publish` mode 才能完成，必须停下；本阶段最多允许 `dry-run-publish`。

## 4. 目标 asof

主目标：

```text
2026-06-26
```

理由：

- DNG15 的首个缺口就是 `2026-06-26`；
- `2026-06-27`、`2026-06-28` 是周末，不作为交易日推进；
- `2026-06-29` 可在后续 DNG16 或独立 continuation 中处理，不要求本轮一口气推进。

## 5. 推荐执行命令

执行者可按实际环境调整 proxy、timeout、sleep，但必须保持 staged-only：

```bash
python qlib_pipeline/examples/tw/run_option_c_yahoo_scrapling_refresh.py \
  --asof 2026-06-26 \
  --start 2015-01-01 \
  --universe option_c_accepted_150 \
  --output-root data_tw/experiments/dng15_r_a_option_c_ops \
  --job-id dng15_r_a_option_c_yahoo_scrapling_refresh_20260626 \
  --proxy http://127.0.0.1:7890 \
  --timeout 30 \
  --retries 1 \
  --sleep-seconds 0.2 \
  --continue-on-error \
  --max-workers 4 \
  --report-path docs/tw_data_governance/DNG15_R_A_OPTION_C_STAGED_REFRESH_REPORT_CN.md
```

若 proxy 不可用，可以重试一次无 proxy：

```bash
python qlib_pipeline/examples/tw/run_option_c_yahoo_scrapling_refresh.py \
  --asof 2026-06-26 \
  --start 2015-01-01 \
  --universe option_c_accepted_150 \
  --output-root data_tw/experiments/dng15_r_a_option_c_ops \
  --job-id dng15_r_a_option_c_yahoo_scrapling_refresh_20260626_noproxy \
  --proxy "" \
  --timeout 30 \
  --retries 1 \
  --sleep-seconds 0.5 \
  --continue-on-error \
  --max-workers 4 \
  --report-path docs/tw_data_governance/DNG15_R_A_OPTION_C_STAGED_REFRESH_REPORT_CN.md
```

如果 staged refresh 成功，可运行 dry-run publish audit：

```bash
python qlib_pipeline/examples/tw/publish_option_c_yahoo_scrapling_refresh.py \
  --job-dir data_tw/experiments/dng15_r_a_option_c_ops/dng15_r_a_option_c_yahoo_scrapling_refresh_20260626 \
  --asof 2026-06-26 \
  --mode dry-run-publish \
  --provider-scope option_c_150 \
  --publish-job-id dng15_r_a_option_c_dry_run_publish_20260626 \
  --report-path docs/tw_data_governance/DNG15_R_A_OPTION_C_DRY_RUN_PUBLISH_REPORT_CN.md
```

注意：不得使用 `--mode publish`。

## 6. 必须生成的产物

执行者必须生成：

```text
docs/tw_data_governance/DNG15_R_A_SAME_LINEAGE_OPTION_C_REFRESH_EXECUTION_REPORT_CN.md
data_tw/catalog/dng15_r_a_same_lineage_option_c_refresh_decision.json
data_tw/catalog/dng15_r_a_modela_20260626_candidate_readiness.json
```

若 staged refresh 成功，还应存在：

```text
data_tw/experiments/dng15_r_a_option_c_ops/<job_id>/candidate_normalized/
data_tw/experiments/dng15_r_a_option_c_ops/<job_id>/staged_qlib_bin/
data_tw/experiments/dng15_r_a_option_c_ops/<job_id>/reports/execution_summary.json
data_tw/experiments/dng15_r_a_option_c_ops/<job_id>/reports/fetch_report.json
data_tw/experiments/dng15_r_a_option_c_ops/<job_id>/reports/normalized_validation.json
data_tw/experiments/dng15_r_a_option_c_ops/<job_id>/reports/provider_validation.json
data_tw/experiments/dng15_r_a_option_c_ops/<job_id>/reports/model_smoke.json
```

如果 dry-run publish audit 成功，还应存在：

```text
qlib_pipeline/data_tw/experiments/option_c_ops/dng15_r_a_option_c_dry_run_publish_20260626/reports/publish_execution_summary.json
```

## 7. 决策 artifact 字段要求

`dng15_r_a_same_lineage_option_c_refresh_decision.json` 至少包含：

```text
schema_version
generated_at
asof
route
decision
status
job_dir
candidate_normalized_path
staged_provider_path
fetch_status
normalized_validation_status
provider_validation_status
model_smoke_status
symbols_expected
symbols_success
symbols_with_asof
calendar_has_asof
prediction_rows
finite_prediction_share
production_allowed=false
publish_latest_authorized=false
formal_provider_mutated=false
formal_normalized_mutated=false
latest_signal_updated=false
forbidden_actions
next_recommended_route
```

`dng15_r_a_modela_20260626_candidate_readiness.json` 至少包含：

```text
schema_version
asof
model_id=e4_frozen_qlib_2018_2022
candidate_input_status
staged_provider_calendar_max
staged_provider_calendar_has_asof
candidate_normalized_symbols_with_asof
candidate_model_smoke_status
score_generated=false unless an explicit isolated score job is added and validated
formal_provider_unchanged=true
latest_signal_unchanged=true
blockers
```

## 8. 验证要求

至少运行：

```bash
python -m py_compile qlib_pipeline/examples/tw/run_option_c_yahoo_scrapling_refresh.py qlib_pipeline/examples/tw/publish_option_c_yahoo_scrapling_refresh.py qlib_pipeline/scripts/dump_bin.py
```

若新增脚本，也必须 `py_compile`。

必须验证：

- staged refresh summary `status=staged_refresh_complete_waiting_for_review` 或明确失败 blocker；
- `formal_provider_mutated=false`；
- `formal_normalized_mutated=false`；
- `latest_signal_updated=false`；
- no FinMind fallback；
- no mixed provider bridge；
- no production publish；
- no accepted latest switch。

可以运行 DNG14 overlay，但不能要求它推进，因为本阶段尚未切 formal provider/latest：

```bash
python scripts/build_tw_dng14_multi_day_chain_observation.py --json
```

若 overlay 仍显示 `latest_ready_chain_asof=2026-06-25`，这不是失败；只要 staged candidate ready，即可进入下一步 DNG15_R-B 或 DNG16-like isolated score integration 设计。

## 9. 审查要求

审查者必须生成：

```text
docs/tw_data_governance/DNG15_R_A_SAME_LINEAGE_OPTION_C_REFRESH_REVIEW_CN.md
```

审查 verdict 只能是：

```text
PASS_GO_DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION
PASS_WITH_CONDITIONS_GO_DNG15_R_B
FAIL_NEEDS_DNG15_R_A_REPAIR
STOP_NEEDS_COORDINATOR_DECISION
```

通过条件：

- 同口径 Yahoo/Scrapling staged candidate 已覆盖 `2026-06-26`；
- staged qlib provider candidate 通过 validator；
- Model A staged smoke 通过；
- formal provider、formal normalized、latest_signal 均未改变；
- 没有 FinMind fallback / mixed-provider；
- 没有生产发布或 accepted latest switch。

若网络不可用或 Yahoo/Scrapling 当日口径不可得，审查者应给 `STOP_NEEDS_COORDINATOR_DECISION` 或 `FAIL_NEEDS_DNG15_R_A_REPAIR`，并明确下一步是否需要：

- 更换 proxy / 增加 retries；
- 等待 Yahoo 数据可用；
- 授权 research-only mixed-provider drift validator；
- 或放弃 6/26 staged candidate。

## 10. 执行者命令

```text
请执行 DNG15_R-A Same-Lineage Option C Normalized Refresh / Isolated Provider Candidate。
先读取本工作文档、DNG15 执行报告、DNG15 审查意见、主线文档。
只允许 staged same-lineage Yahoo/Scrapling refresh、isolated provider candidate、validator、dry-run publish audit。
禁止 formal publish、accepted latest switch、latest_signal 更新、readonly/Agent latest publish、生产切换、交易、target_position/target_weight、FinMind fallback。
完成后写执行报告和两个 catalog JSON。
```

## 11. 审查者命令

```text
请独立审查 DNG15_R-A 执行结果。
重点检查 staged candidate 是否真覆盖 2026-06-26、是否同口径 Yahoo/Scrapling、是否没有 formal/latest/publish mutation、是否没有 FinMind fallback。
给出明确 verdict，并写下一步 DNG15_R-B 或 repair 工作建议。
```
