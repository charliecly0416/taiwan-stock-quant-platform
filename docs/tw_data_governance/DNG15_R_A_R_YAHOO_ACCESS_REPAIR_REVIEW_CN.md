# DNG15_R-A-R Yahoo Same-Lineage Access Repair 审查意见

生成时间：2026-06-29

## 1. Verdict

```text
PASS_GO_DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION
```

审查结论：DNG15_R-A-R 已满足进入 DNG15_R-B isolated Model A score integration 的最低条件。

核心依据：

```text
Yahoo-only same-lineage candidate_normalized symbols_success=150/150
candidate_normalized symbols_with_asof=150/150 for 2026-06-26
staged_qlib_bin calendar_has_asof=true
provider_validation.status=pass
Model A staged smoke status=pass
prediction_rows=150
finite_prediction_share=1.0
forbidden actions 全部为 false
```

本次 optional dry-run-publish 的 downstream formal daily-signal dry-run 失败不阻断 DNG15_R-B，因为 DNG15_R-B 的输入是 isolated staged provider / staged prediction，不要求 formal provider publish，也禁止通过 formal publish 修复 downstream formal daily-signal。若下一阶段目标改为 formal daily-signal 或正式 publish，该失败才是阻断项。

## 2. Findings

### Critical

无。

### High

无。

### Medium

1. `2026-06-26` Yahoo-only same-lineage candidate 已实际生成并通过 normalized validation。
   - `fetch_report.json` 显示 `source=Yahoo Finance chart API via Scrapling`、`source_policy=Yahoo-only; no yfinance; no FinMind fallback; no mixed provider`、`proxy_used=true`、`symbols_expected=150`、`symbols_success=150`、`rows_written=400355`。
   - `normalized_validation.json` 显示 `status=pass`、`files_found=150`、`missing_count=0`、`empty_count=0`、`symbols_with_asof=150`、`date_max_min=2026-06-26`、`date_max_max=2026-06-26`。
   - 只读核查 `candidate_normalized` 实际文件数为 `150`。

2. staged qlib provider 已实际生成并通过 provider validation。
   - `provider_validation.json` 显示 `status=pass`、`calendar_max=2026-06-26`、`calendar_has_asof=true`、`active_universe_count=150`。
   - `expected_field_counts` 中 `open/high/low/close/volume/vwap/factor` 全部为 `150`。
   - `missing_feature_symbols=[]`、`rejected_fields_present=[]`。

3. Model A staged smoke 已通过。
   - `model_smoke.json` 显示 `status=pass`、`asof=2026-06-26`、`symbols=150`、`prediction_rows=150`、`finite_prediction_share=1.0`。
   - `staged_prediction.csv` 为 `151` 行，扣除表头后正好 `150` 条 prediction。
   - `published_latest_signal=false`、`formal_provider_mutated=false`。

4. dry-run-publish downstream formal daily-signal failure 不应阻断 R-B。
   - `publish_execution_summary.json` 显示 staged gate 已 `pass`，summary 中 `symbols_success=150`、`normalized_status=pass`、`provider_status=pass`、`model_smoke_status=pass`。
   - `publish_result.status=dry_run_only_no_mutation`，`normalized_publish=planned_not_executed`，`provider_publish=planned_not_executed`。
   - 下游失败来自 formal daily-signal dry-run：`status=blocked_formal_validation_failed`，errors 为 `option_c_formal_source_missing_asof` 和 `option_c_provider_calendar_stale`。
   - 这说明 formal provider 仍未发布到 2026-06-26，符合本阶段禁止 formal publish 的边界；它会阻断 formal daily-signal / publish route，但不阻断 isolated Model A staged score integration。

### Low

1. job report 内部路径口径有轻微不一致。
   - catalog 顶层 artifact 指向 `qlib_pipeline/data_tw/experiments/...`，这是当前实际存在的位置。
   - 部分 report 内部字段写作 `data_tw/experiments/...`，在仓库根目录下该路径不存在。
   - 该问题不影响本次审查结论，因为所有必需 artifact 均可在 `qlib_pipeline/data_tw/experiments/...` 下验证；建议 DNG15_R-B 读取 catalog 顶层路径，避免使用 report 内部相对路径。

2. 本轮没有生成 drift validator artifact 是合理的。
   - selected client 为 `scrapling_direct_with_proxy`，仍是原始 Scrapling direct Yahoo chart API client，只是通过 proxy 修复 access。
   - 工作文档要求 drift validator 的触发条件是使用非原始 Scrapling direct client，例如 `curl_cffi` 或 `yfinance`；本轮未触发该条件。

## 3. Mainline Compliance

通过项：

```text
candidate_normalized symbols_success=150/150
candidate_normalized symbols_with_asof=150/150
staged_qlib_bin calendar_has_asof=true
provider_validation.status=pass
model_smoke.status=pass
prediction_rows=150
finite_prediction_share=1.0
production_allowed=false
publish_latest_authorized=false
formal_provider_mutated=false
formal_normalized_mutated=false
latest_signal_updated=false
finmind_fallback=false
mixed_provider_bridge=false
```

补充只读验证：

```text
python -m py_compile \
  qlib_pipeline/examples/tw/run_option_c_yahoo_scrapling_refresh.py \
  qlib_pipeline/examples/tw/publish_option_c_yahoo_scrapling_refresh.py \
  qlib_pipeline/scripts/dump_bin.py \
  scripts/build_tw_dng15_r_a_r_yahoo_access_repair_artifacts.py
```

结果：通过，无编译错误。

## 4. Evidence Checked

必读文档：

```text
docs/tw_data_governance/DNG15_R_A_R_YAHOO_ACCESS_REPAIR_WORK_CN.md
docs/tw_data_governance/DNG15_R_A_R_YAHOO_ACCESS_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_data_governance/DNG15_R_A_SAME_LINEAGE_OPTION_C_REFRESH_REVIEW_CN.md
docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md
/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md
```

Catalog artifacts：

```text
data_tw/catalog/dng15_r_a_r_yahoo_access_repair_decision.json
data_tw/catalog/dng15_r_a_r_modela_20260626_candidate_readiness.json
```

Staged job reports：

```text
qlib_pipeline/data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy/reports/execution_summary.json
qlib_pipeline/data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy/reports/fetch_report.json
qlib_pipeline/data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy/reports/normalized_validation.json
qlib_pipeline/data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy/reports/provider_validation.json
qlib_pipeline/data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy/reports/model_smoke.json
qlib_pipeline/data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy/reports/staged_prediction.csv
```

Dry-run-publish audit：

```text
qlib_pipeline/data_tw/experiments/option_c_ops/dng15_r_a_r_option_c_dry_run_publish_20260626/reports/publish_execution_summary.json
docs/tw_data_governance/DNG15_R_A_R_OPTION_C_DRY_RUN_PUBLISH_REPORT_CN.md
```

只读核查要点：

```text
candidate_normalized file count = 150
staged_prediction.csv line count = 151 including header
staged_qlib_bin/calendars/day.txt exists
staged_qlib_bin/features contains 150 symbol directories
```

## 5. Missing Evidence Or Open Questions

无阻断性缺失证据。

剩余注意事项：

1. DNG15_R-B 应明确使用 isolated staged provider，不得隐式读取 formal `option_c_150_qlib_bin`。
2. DNG15_R-B 应读取 catalog 顶层 `staged_provider_path` / `candidate_normalized_path`，不要依赖 report 内部的 `data_tw/experiments/...` 相对路径。
3. 若后续目标变成 formal daily-signal 或 formal publish，必须另开授权并先解决 formal source/calendar stale；本次 PASS 不授权 formal publish。

## 6. Forbidden Actions Audit

审查结论：干净。

`dng15_r_a_r_yahoo_access_repair_decision.json` 与 `dng15_r_a_r_modela_20260626_candidate_readiness.json` 均显示：

```text
formal_publish=false
formal_provider_mutated=false
formal_normalized_mutated=false
accepted_latest_switch=false
latest_signal_updated=false
readonly_latest_published=false
agent_prompt_latest_published=false
production_default_model_or_strategy_switched=false
broker_order_quick_trade_triggered=false
target_position_or_weight_generated=false
finmind_fallback=false
mixed_provider_bridge=false
model_training_or_tuning=false
```

`publish_execution_summary.json` 进一步显示：

```text
mode=dry-run-publish
publish_result.status=dry_run_only_no_mutation
latest_signal_updated=false
latest_signal_unchanged=true
normal_signal_run=false
orders_enabled=false
connects_to_broker=false
writes_orders=false
writes_positions=false
```

未发现 formal publish、accepted latest switch、latest_signal 更新、readonly/Agent latest publish、生产切换、交易、target_position/target_weight、FinMind fallback 或 mixed-provider bridge。

## 7. Next Work Document

### DNG15_R-B Isolated Model A Score Integration

目标：

```text
使用 DNG15_R-A-R 生成的 isolated staged qlib provider，
完成 2026-06-26 Model A isolated score integration，
生成 R-B 所需的 isolated score / rank / readiness artifacts，
但不 formal publish、不切 latest、不更新 latest_signal。
```

输入：

```text
staged_provider_path:
qlib_pipeline/data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy/staged_qlib_bin

candidate_readiness:
data_tw/catalog/dng15_r_a_r_modela_20260626_candidate_readiness.json

staged_prediction evidence:
qlib_pipeline/data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy/reports/staged_prediction.csv
```

最低要求：

```text
asof=2026-06-26
model_id=e4_frozen_qlib_2018_2022
input_provider_isolated=true
formal_provider_mutated=false
latest_signal_updated=false
publish_latest_authorized=false
production_allowed=false
prediction_rows=150
finite_prediction_share=1.0
rank_rows=150
no order / no target / no production switch
```

禁止：

```text
formal provider publish
formal normalized overwrite
qlib accepted latest switch
latest_signal update
readonly latest publish
Agent prompt latest publish
production default model/strategy switch
broker/order/quick-trade
target_position / target_weight
FinMind fallback
mixed-provider bridge
model training or tuning
```

## 8. Command For Executor

```text
请执行 DNG15_R-B isolated Model A score integration。
必须读取本审查意见、DNG15_R-A-R 工作文档、执行报告、两个 catalog JSON、staged job reports、数据治理主线和 coordinator-executor-reviewer workflow skill。
只能消费 DNG15_R-A-R isolated staged qlib provider：
qlib_pipeline/data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy/staged_qlib_bin
不得 formal publish、不得切 accepted latest、不得更新 latest_signal、不得 publish readonly/Agent latest、不得生产切换、不得交易、不得生成 target_position/target_weight、不得使用 FinMind fallback 或 mixed-provider bridge、不得训练或调参。
完成后写 DNG15_R-B execution report 和 catalog/readiness artifacts，供 reviewer 审查。
```
