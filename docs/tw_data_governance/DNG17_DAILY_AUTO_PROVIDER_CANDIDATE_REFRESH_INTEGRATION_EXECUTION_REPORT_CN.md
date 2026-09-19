# DNG17 Daily Auto Provider Candidate Refresh Integration 执行报告

生成时间：2026-06-29T14:26:37Z

## 1. Scope

- Assigned phase：`DNG17 Daily Auto Provider Candidate Refresh Integration`
- Work document：`docs/tw_data_governance/DNG17_DAILY_AUTO_PROVIDER_CANDIDATE_REFRESH_INTEGRATION_WORK_CN.md`
- Prior review：`docs/tw_data_governance/DNG16_DAILY_AUTO_MODEL_SCORE_INTEGRATION_DESIGN_REVIEW_CN.md`
- Target asof：`2026-06-26`

非目标确认：未 formal publish、未覆盖 formal provider/normalized、未切 accepted latest、未更新 latest_signal、未 publish readonly/Agent latest、未 production switch、未 strategy replay/NAV、未 broker/order、未生成 target_position/target_weight、未 FinMind fallback、未 mixed-provider bridge、未训练或调参。

## 2. Documents / Contracts / Skills Read

- `docs/tw_data_governance/DNG17_DAILY_AUTO_PROVIDER_CANDIDATE_REFRESH_INTEGRATION_WORK_CN.md`
- `docs/tw_data_governance/DNG16_DAILY_AUTO_MODEL_SCORE_INTEGRATION_DESIGN_REVIEW_CN.md`
- `scripts/run_daily_tw_stock_auto_update.py`
- `scripts/build_tw_dng15_r_a_r_yahoo_access_repair_artifacts.py`
- `scripts/build_tw_dng15_r_b_isolated_modela_score_integration.py`
- `/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`

## 3. Changes Made

- 在 `scripts/run_daily_tw_stock_auto_update.py` 新增 explicit gate：`--enable-provider-candidate-refresh`，环境变量为 `TW_DAILY_AUTO_ENABLE_PROVIDER_CANDIDATE_REFRESH`，默认 false。
- 新增 daily auto provider candidate selection 顺序：current job DNG17 readiness -> prior same-asof daily-auto DNG17 readiness -> DNG15_R-A-R fixture fallback。
- 在 formal provider stale 且 `--enable-model-signal-gate` 开启时，daily auto 会写 `provider_candidate_refresh_decision.json` / `provider_candidate_readiness.json` 到当前 job 目录。
- `--skip-qlib` 继续阻止 legacy formal provider refresh/publish，但不阻止 safe provider candidate refresh/reuse gate。
- `model_signal_gate` 优先消费当前 job 的 DNG17 candidate readiness；若 existing isolated Model A artifact 已 PASS，则复用 existing isolated score。
- `scripts/build_tw_dng15_r_b_isolated_modela_score_integration.py` 新增可选 `--decision-path` / `--readiness-path`，默认仍读 DNG15_R-A-R fixture。
- 生成 `data_tw/catalog/dng17_daily_auto_provider_candidate_refresh_integration_validation.json`。

## 4. Evidence Produced

### 4.1 Safe dry-run

命令：

```bash
python scripts/run_daily_tw_stock_auto_update.py --asof 2026-06-26 --force --skip-finmind --skip-qlib --enable-model-signal-gate --enable-provider-candidate-refresh --today-earliest-time 00:00
```

结果：

- exit code：`0`
- job_id：`daily_tw_stock_auto_update_20260626_20260629T142612Z`
- job.json：`data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T142612Z/job.json`
- daily_chain_status：`data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T142612Z/daily_chain_status.json`
- skipped_asof_ledger：`data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T142612Z/skipped_asof_ledger.json`
- provider_candidate_refresh_decision：`data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T142612Z/provider_candidate_refresh_decision.json`
- provider_candidate_readiness：`data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T142612Z/provider_candidate_readiness.json`

### 4.2 Provider candidate decision/readiness

- provider_candidate_refresh_status：`READY_REUSED_VALIDATED_PROVIDER_CANDIDATE`
- provider_candidate_refresh_triggered：`false`
- provider_candidate_reused_existing：`true`
- reused source：`data_tw/catalog/dng15_r_a_r_yahoo_access_repair_decision.json` / `data_tw/catalog/dng15_r_a_r_modela_20260626_candidate_readiness.json`
- current job candidate_source：`current_job_dng17`
- source_provider：`Yahoo`
- source_client：`Scrapling Fetcher direct chart API with proxy`
- fetch_status：`pass`
- symbols_success：`150/150`
- symbols_with_asof：`150/150`
- provider_validation_status：`pass`
- calendar_has_asof：`true`
- calendar_max：`2026-06-26`
- model_smoke_status：`pass`
- prediction_rows：`150`
- finite_prediction_share：`1.0`

### 4.3 Model signal gate

- summary：`data_tw/ops/daily_auto_update/dng9_model_signal_gate_dry_run/model_signal_gate_summary.json`
- validation：`data_tw/catalog/dng9_model_signal_gate_validation.json`
- validation_status：`PASS`
- mode：`daily_auto_gate_reused_existing_isolated`
- provider_selection_mode：`validated_isolated_provider_candidate`
- isolated_candidate_readiness_path：`data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T142612Z/provider_candidate_readiness.json`
- reused_existing_model_a_artifact：`true`
- model_a_status：`SCORED_ASOF_TARGET`
- model_b_status：`BLOCKED_INPUT_NOT_READY`
- publish_latest_gate：`false`
- accepted_latest_switch：`false`
- forbidden_actions_all_false：`true`

### 4.4 Chain status

- raw_status：`READY_FROM_PRIOR_JOB`
- formal_calendar_max：`2026-06-25`
- qlib_provider_view_status：`BLOCKED_PROVIDER_VIEW_STALE`
- latest_signal_asof：`2026-06-17`
- model_a_inference_input_status：`READY_EXISTING_ISOLATED_ARTIFACT`
- model_a_score_status：`READY_EXISTING_ISOLATED_ARTIFACT`
- model_a_signal_status：`READY_EXISTING_ISOLATED_ARTIFACT`
- provider_candidate_refresh_status：`READY_REUSED_VALIDATED_PROVIDER_CANDIDATE`
- blocked_at：`qlib_provider_view_or_formal_calendar`

### 4.5 Refresh failure safety probe

先前同命令 run：

- job_id：`daily_tw_stock_auto_update_20260626_20260629T142415Z`
- exit code：`0`
- provider_candidate_refresh_status：`BLOCKED_YAHOO_STAGED_REFRESH_FAILED`
- 原因：本机 `127.0.0.1:7890` proxy 未开启，Yahoo/Scrapling staged refresh 无法连接。
- 安全结果：formal provider、formal normalized、latest_signal 均未变更；model_signal_gate 仍复用 existing isolated score。

该 probe 证明 gate enabled 且 live refresh 失败时会安全 blocked，不会落到 formal publish 或 FinMind/mixed-provider fallback。

## 5. Compliance With Work Document

- `--enable-provider-candidate-refresh` 默认 false，只有 explicit gate 下生效。
- `--enable-model-signal-gate` + `--enable-provider-candidate-refresh` 下，formal stale 场景可生成或复用 provider candidate decision/readiness。
- `--skip-qlib` 未触发 legacy formal refresh/publish，也未阻断 safe candidate reuse gate。
- daily_chain_status 区分 formal provider stale、DNG17 candidate ready、existing isolated Model A score ready。
- model_signal_gate 成功消费 current-job DNG17 readiness，并复用 existing isolated Model A artifact。

## 6. Forbidden Actions Audit

- formal_provider_publish：`false`
- formal_provider_overwrite：`false`
- formal_normalized_overwrite：`false`
- accepted_latest_switch：`false`
- latest_signal_updated：`false`
- readonly_latest_publish：`false`
- agent_prompt_latest_publish：`false`
- production_default_model_or_strategy_switch：`false`
- strategy_replay_or_nav：`false`
- broker/order/quick-trade：`false`
- target_position/target_weight：`false`
- FinMind fallback：`false`
- mixed-provider bridge：`false`
- model training/tuning：`false`

## 7. Validator / Test Output

- `python -m py_compile scripts/run_daily_tw_stock_auto_update.py scripts/build_tw_dng15_r_a_r_yahoo_access_repair_artifacts.py scripts/build_tw_dng15_r_b_isolated_modela_score_integration.py`：exit code `0`
- safe dry-run：exit code `0`
- `data_tw/catalog/dng9_model_signal_gate_validation.json`：`status=PASS`
- `data_tw/catalog/dng17_daily_auto_provider_candidate_refresh_integration_validation.json`：`status=PASS_READY_FOR_DNG17_REVIEW`

## 8. Issues / Blockers / Deviations

- 当前环境没有可用的 `127.0.0.1:7890` proxy，因此 live Yahoo/Scrapling staged refresh probe 未能生成新的 daily-auto candidate；该失败被安全记录为 `BLOCKED_YAHOO_STAGED_REFRESH_FAILED`。
- 最终验收 dry-run 复用已 validated 的 DNG15_R-A-R candidate，并在当前 daily auto job 下写入 DNG17 decision/readiness；这符合 DNG17 的 same-asof validated candidate reuse 规则。
- `latest_signal_asof` 保持 `2026-06-17`，formal provider calendar 仍为 `2026-06-25`，没有被推进。

## 9. Files Changed

- `scripts/run_daily_tw_stock_auto_update.py`
- `scripts/build_tw_dng15_r_b_isolated_modela_score_integration.py`
- `docs/tw_data_governance/DNG17_DAILY_AUTO_PROVIDER_CANDIDATE_REFRESH_INTEGRATION_EXECUTION_REPORT_CN.md`
- `data_tw/catalog/dng17_daily_auto_provider_candidate_refresh_integration_validation.json`
- `data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T142612Z/provider_candidate_refresh_decision.json`
- `data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T142612Z/provider_candidate_readiness.json`
- `data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T142612Z/daily_chain_status.json`
- `data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T142612Z/skipped_asof_ledger.json`

## 10. Recommendation For Reviewer

建议 verdict：`PASS_GO_DNG18_END_TO_END_DAILY_AUTO_SHADOW_CLOSURE`。

理由：DNG17 explicit provider candidate refresh gate 已接入 daily auto，默认关闭；safe dry-run 在 `--skip-qlib` 下没有触发 legacy formal refresh/publish，能写 current-job DNG17 candidate decision/readiness，并让 model_signal_gate 消费 candidate/复用 isolated score。所有 forbidden actions 保持 false。
