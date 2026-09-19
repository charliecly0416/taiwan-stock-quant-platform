# DNG15_R-A-R Yahoo Same-Lineage Access Repair 执行报告

生成时间：2026-06-29T13:40:17+00:00

## 1. Scope

- Assigned phase：`DNG15_R-A-R Yahoo same-lineage access repair`
- Mainline document：`docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md`
- Work document：`docs/tw_data_governance/DNG15_R_A_R_YAHOO_ACCESS_REPAIR_WORK_CN.md`
- Target asof：`2026-06-26`
- Model：`e4_frozen_qlib_2018_2022`

非目标确认：未 formal publish、未切 accepted latest、未更新 latest_signal、未 publish readonly/Agent latest、未生产切换、未交易、未生成 target_position/target_weight、未使用 FinMind fallback 或 mixed-provider bridge。

## 2. Documents / Contracts / Skills Read

- `docs/tw_data_governance/DNG15_R_A_R_YAHOO_ACCESS_REPAIR_WORK_CN.md`
- `docs/tw_data_governance/DNG15_R_A_SAME_LINEAGE_OPTION_C_REFRESH_EXECUTION_REPORT_CN.md`
- `docs/tw_data_governance/DNG15_R_A_SAME_LINEAGE_OPTION_C_REFRESH_REVIEW_CN.md`
- `docs/tw_data_governance/DNG15_FORMAL_QLIB_PROVIDER_OR_CANONICAL_BRIDGE_REPAIR_REVIEW_CN.md`
- `docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md`
- `/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`

## 3. Changes Made

- 新增 `scripts/build_tw_dng15_r_a_r_yahoo_access_repair_artifacts.py`。
- 生成 `data_tw/catalog/dng15_r_a_r_yahoo_access_repair_decision.json`。
- 生成 `data_tw/catalog/dng15_r_a_r_modela_20260626_candidate_readiness.json`。
- 生成本执行报告。

## 4. Evidence Produced

### 4.1 Access diagnostic

- proxy `127.0.0.1:7890`：open。
- Scrapling no-proxy：`2330.TW` / `1785.TWO` 均 HTTP 403。
- curl_cffi no-proxy：`2330.TW` / `1785.TWO` 均 HTTP 403。
- yfinance no-proxy：`2330.TW` / `1785.TWO` 均 rate limited empty。
- Scrapling proxy：`2330.TW` / `1785.TWO` 均 HTTP 200。
- curl_cffi proxy：`2330.TW` / `1785.TWO` 均 HTTP 200。

### 4.2 Staged refresh

- job_dir：`qlib_pipeline/data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy`
- selected_client：`scrapling_direct_with_proxy`
- fetch_status：`pass`
- symbols_success：`150/150`
- rows_written：`400355`
- http_status_counts：`{'200': 150, '404': 38}`
- normalized_validation.status：`pass`
- symbols_with_asof：`150/150`
- staged provider validation：`pass`
- calendar_has_asof：`True`
- calendar_max：`2026-06-26`
- model_smoke.status：`pass`
- prediction_rows：`150`
- finite_prediction_share：`1.0`

### 4.3 Drift validator

- `not_required_original_scrapling_direct_client`：本轮最终 candidate 使用原始 Scrapling direct Yahoo chart client + proxy，没有使用 curl_cffi 或 yfinance 作为 candidate builder。

### 4.4 Optional dry-run publish audit

- status：`daily_signal_dry_run_failed`
- staged_gate：`pass`
- publish_result：`dry_run_only_no_mutation`
- daily_signal_dry_run：`fail`
- latest_signal_unchanged：`True`
- 说明：dry-run publish 的 staged gate 已通过，且 publish_result 为 `dry_run_only_no_mutation`；失败点是下游 formal daily-signal dry-run 仍读取未发布的 formal provider，因此报 formal source/calendar stale。未执行 `--mode publish`。

## 5. Compliance With Mainline

- decision：`PASS_GO_DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION`
- candidate_normalized symbols_success：`150/150`
- candidate_normalized symbols_with_asof：`150/150`
- staged calendar_has_asof：`True`
- provider_validation.status：`pass`
- model_smoke.status：`pass`
- production_allowed：`False`
- publish_latest_authorized：`False`

## 6. Forbidden Actions Audit

- `formal_provider_mutated=false`
- `formal_normalized_mutated=false`
- `latest_signal_updated=false`
- `publish_latest_authorized=false`
- `production_allowed=false`
- `finmind_fallback=false`
- `mixed_provider_bridge=false`
- 未运行 `--mode publish`。
- 未触发交易、订单、target_position、target_weight、模型训练或调参。

## 7. Issues / Blockers / Deviations

- 原 no-proxy Yahoo access 仍不可用：Scrapling/curl_cffi 为 HTTP 403，yfinance rate limited empty。
- 可用修复路径是 `http://127.0.0.1:7890` proxy + 原 Scrapling direct client。
- Optional dry-run publish audit 的下游 formal daily-signal dry-run 失败，原因为 formal provider 未发布且仍缺 2026-06-26；这是预期边界内的 no-mutation preflight blocker，不影响 isolated staged candidate readiness。

## 8. Files Changed

- `scripts/build_tw_dng15_r_a_r_yahoo_access_repair_artifacts.py`
- `docs/tw_data_governance/DNG15_R_A_R_YAHOO_ACCESS_REPAIR_EXECUTION_REPORT_CN.md`
- `data_tw/catalog/dng15_r_a_r_yahoo_access_repair_decision.json`
- `data_tw/catalog/dng15_r_a_r_modela_20260626_candidate_readiness.json`
- `qlib_pipeline/data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy/candidate_normalized/*`
- `qlib_pipeline/data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy/staged_qlib_bin/*`
- `qlib_pipeline/data_tw/experiments/dng15_r_a_r_yahoo_access_repair/dng15_r_a_r_yahoo_scrapling_refresh_20260626_proxy/reports/*`

## 9. Recommendation For Reviewer

建议 verdict：`PASS_GO_DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION`。

理由：本轮已生成 Yahoo-only same-lineage 2026-06-26 candidate normalized 150/150、staged qlib provider、provider validator pass、Model A staged smoke pass，且 forbidden actions 全部保持 false。dry-run publish audit 的 formal preflight 失败不应阻断 R-B，因为本阶段禁止 formal publish。
