# DNG18 End-to-End Daily Auto Shadow Closure 执行报告

生成时间：2026-06-29T14:45:00Z

## 1. Scope

- 执行阶段：`DNG18 End-to-End Daily Auto Shadow Closure`
- 工作文档：`docs/tw_data_governance/DNG18_END_TO_END_DAILY_AUTO_SHADOW_CLOSURE_WORK_CN.md`
- 参考审查：`docs/tw_data_governance/DNG17_DAILY_AUTO_PROVIDER_CANDIDATE_REFRESH_INTEGRATION_REVIEW_CN.md`
- 参考执行报告：`docs/tw_data_governance/DNG17_DAILY_AUTO_PROVIDER_CANDIDATE_REFRESH_INTEGRATION_EXECUTION_REPORT_CN.md`
- target asof：`2026-06-26`

本轮只做 daily auto readonly/shadow 条件修复和证据生成。未触发 formal provider publish、accepted latest switch、latest_signal update、readonly/Agent latest publish、production switch、broker/order、target_position/target_weight、FinMind fallback、mixed-provider bridge、模型训练/调参。

## 2. Changes Made

修改文件：

- `scripts/run_daily_tw_stock_auto_update.py`
- `docs/tw_data_governance/DNG18_END_TO_END_DAILY_AUTO_SHADOW_CLOSURE_EXECUTION_REPORT_CN.md`
- `data_tw/catalog/dng18_end_to_end_daily_auto_shadow_closure_validation.json`
- safe job artifacts under `data_tw/ops/daily_auto_update/`

代码修复：

- 修复 provider candidate refresh/reuse gate 默认关闭语义：`--enable-model-signal-gate` 开启但未传 `--enable-provider-candidate-refresh` 时，gate 在查找 prior/fixture candidate 前直接返回 `DISABLED_BY_DEFAULT`，不写 current-job `provider_candidate_refresh_decision.json` / `provider_candidate_readiness.json`。
- 新增 DNG18 probe-only 开关，默认 false：
  - `--dng18-disable-provider-candidate-fallbacks`
  - `TW_DAILY_AUTO_DNG18_DISABLE_PROVIDER_CANDIDATE_FALLBACKS`
  - `--dng18-disable-existing-isolated-modela-reuse`
  - `TW_DAILY_AUTO_DNG18_DISABLE_EXISTING_ISOLATED_MODELA_REUSE`
- `--dng18-disable-provider-candidate-fallbacks` 会让 probe 路径不看 current-job/prior daily-auto/DNG15_R-A-R fixture candidate。
- `--dng18-disable-existing-isolated-modela-reuse` 会让 probe 路径不复用既有 isolated Model A score。
- 当 provider candidate refresh blocked 且 model signal gate 没有 validated provider candidate 时，`daily_chain_status.json` 明确写：
  - `model_a_inference_input_status=BLOCKED_PROVIDER_CANDIDATE_REFRESH`
  - `model_a_score_status=BLOCKED_PROVIDER_CANDIDATE_REFRESH`
  - `model_a_signal_status=BLOCKED_PROVIDER_CANDIDATE_REFRESH`

## 3. Validator / Compile

```bash
python -m py_compile scripts/run_daily_tw_stock_auto_update.py
```

- exit code：`0`

## 4. Safe Dry-Run Evidence

三条 dry-run 均使用：

```text
--skip-finmind --skip-qlib --today-earliest-time 00:00
```

未使用 formal publish/latest/production/trading/target 相关 gate。

### 4.1 Default-disabled regression

命令：

```bash
python scripts/run_daily_tw_stock_auto_update.py --asof 2026-06-26 --force --skip-finmind --skip-qlib --enable-model-signal-gate --today-earliest-time 00:00
```

结果：

- exit code：`0`
- job_id：`daily_tw_stock_auto_update_20260626_20260629T144008Z`
- job：`data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T144008Z/job.json`
- chain：`data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T144008Z/daily_chain_status.json`

关键证据：

- `provider_candidate_refresh_gate.enabled=false`
- `provider_candidate_refresh_status=DISABLED_BY_DEFAULT`
- `provider_candidate_refresh_triggered=false`
- `provider_candidate_reused_existing=false`
- current job 目录没有 `provider_candidate_refresh_decision.json`
- current job 目录没有 `provider_candidate_readiness.json`
- `daily_chain_status.lineage_evidence.provider_candidate_refresh_decision=""`
- `daily_chain_status.lineage_evidence.provider_candidate_readiness=""`
- `forbidden_actions.all_false=true`

说明：model signal gate 仍可按既有逻辑复用 isolated Model A artifact，但 provider candidate refresh/reuse gate 本身保持 disabled 且不包装/复用 candidate。

### 4.2 No-candidate failure blocked probe

命令：

```bash
python scripts/run_daily_tw_stock_auto_update.py --asof 2026-06-26 --force --skip-finmind --skip-qlib --enable-model-signal-gate --enable-provider-candidate-refresh --dng18-disable-provider-candidate-fallbacks --dng18-disable-existing-isolated-modela-reuse --proxy http://127.0.0.1:9 --refresh-timeout 1 --refresh-retries 1 --today-earliest-time 00:00
```

结果：

- exit code：`0`
- job_id：`daily_tw_stock_auto_update_20260626_20260629T144233Z`
- job：`data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T144233Z/job.json`
- chain：`data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T144233Z/daily_chain_status.json`
- refresh stdout：`data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T144233Z/provider_candidate_refresh_stdout.json`
- refresh stderr：`data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T144233Z/provider_candidate_refresh_stderr.txt`

关键证据：

- `dng18_disable_provider_candidate_fallbacks=true`
- `dng18_disable_existing_isolated_modela_reuse=true`
- `provider_candidate_refresh_status=BLOCKED_YAHOO_STAGED_REFRESH_FAILED`
- `provider_candidate_refresh_triggered=true`
- `provider_candidate_reused_existing=false`
- `model_signal_gate.ok=false`
- `model_signal_gate.provider_selection_mode=blocked_no_validated_provider`
- `isolated_candidate_used=false`
- `reused_existing_model_a_artifact=false`
- `model_a_score_job_triggered=false`
- `daily_chain_status.model_a_score_status=BLOCKED_PROVIDER_CANDIDATE_REFRESH`
- current job 目录没有 `provider_candidate_refresh_decision.json`
- current job 目录没有 `provider_candidate_readiness.json`
- `forbidden_actions.all_false=true`

失败注入方式：使用无效本地 proxy `http://127.0.0.1:9` 加短 timeout，safe 触发 Yahoo/Scrapling staged refresh failure，不修改 formal provider/normalized。

### 4.3 Closure dry-run

命令：

```bash
python scripts/run_daily_tw_stock_auto_update.py --asof 2026-06-26 --force --skip-finmind --skip-qlib --enable-model-signal-gate --enable-provider-candidate-refresh --today-earliest-time 00:00
```

结果：

- exit code：`0`
- job_id：`daily_tw_stock_auto_update_20260626_20260629T144401Z`
- job：`data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T144401Z/job.json`
- chain：`data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T144401Z/daily_chain_status.json`
- provider decision：`data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T144401Z/provider_candidate_refresh_decision.json`
- provider readiness：`data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T144401Z/provider_candidate_readiness.json`

关键证据：

- `provider_candidate_refresh_status=READY_REUSED_VALIDATED_PROVIDER_CANDIDATE`
- `provider_candidate_refresh_triggered=false`
- `provider_candidate_reused_existing=true`
- `provider_candidate_source=current_job_dng17`
- reused source：`data_tw/catalog/dng15_r_a_r_yahoo_access_repair_decision.json` / `data_tw/catalog/dng15_r_a_r_modela_20260626_candidate_readiness.json`
- `model_signal_gate.provider_selection_mode=validated_isolated_provider_candidate`
- `isolated_candidate_used=true`
- `reused_existing_model_a_artifact=true`
- `model_a_score_status=READY_EXISTING_ISOLATED_ARTIFACT`
- `publish_latest_gate_status=DISABLED_BY_DEFAULT`
- `formal_calendar_max=2026-06-25`
- `latest_signal_asof=2026-06-17`
- `forbidden_actions.all_false=true`

## 5. Forbidden Actions Audit

三条 DNG18 safe dry-run 均为 false：

- formal provider publish：`false`
- formal provider mutate：`false`
- formal normalized mutate：`false`
- accepted latest switch：`false`
- latest_signal update：`false`
- readonly latest publish：`false`
- Agent prompt latest publish：`false`
- production default model/strategy switch：`false`
- strategy replay / NAV：`false`
- broker/order/quick-trade：`false`
- target_position / target_weight：`false`
- FinMind fallback：`false`
- mixed-provider bridge：`false`
- model training/tuning：`false`

辅助证据：

- formal provider calendar 仍为 `2026-06-25`
- latest_signal 仍为 `2026-06-17`
- all jobs：`latest_after=2026-06-17`

## 6. Aggregated Validation

已写：

```text
data_tw/catalog/dng18_end_to_end_daily_auto_shadow_closure_validation.json
```

聚合结论：

- `status=PASS_READY_FOR_DNG18_REVIEW`
- `recommendation=PASS_DNG18_CLOSURE_REVIEW`
- `default_disabled_regression_no_current_job_candidate_artifacts=true`
- `no_candidate_probe_hides_prior_fixture_and_existing_modela=true`
- `no_candidate_probe_model_a_blocked=true`
- `closure_dry_run_passed=true`
- `formal_latest_production_trading_target_actions_not_triggered=true`

## 7. Notes / Deviations

- No-candidate failure probe 使用无效本地 proxy 作为 safe failure harness。原因是如果本地网络/proxy 可用，live refresh 可能成功，无法证明 failure blocked 路径。
- failure probe 创建了 failed staged refresh job 目录和 stdout/stderr/report 证据，但没有写 current daily-auto provider candidate decision/readiness。
- default-disabled regression 中 model signal gate 仍可复用既有 isolated Model A score；这不改变 provider candidate refresh/reuse gate 默认关闭语义。

## 8. Recommendation

建议交给 DNG18 reviewer 审查，候选 verdict：

```text
PASS_DNG18_CLOSURE
```

理由：DNG17 两个条件均已补齐；主 closure dry-run 保持通过；formal/latest/production/trading/target/FinMind fallback/mixed bridge/model training 全部未触发。
