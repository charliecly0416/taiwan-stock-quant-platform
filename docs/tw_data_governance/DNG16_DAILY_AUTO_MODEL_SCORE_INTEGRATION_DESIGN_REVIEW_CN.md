# DNG16 Daily Auto Model Score Integration Design 审查意见

生成时间：2026-06-29

## 1. Verdict

```text
PASS_GO_DNG17_DAILY_AUTO_PROVIDER_CANDIDATE_REFRESH_INTEGRATION
```

审查结论：DNG16 执行结果满足进入 DNG17 daily auto provider candidate refresh integration 的条件。

核心依据：

```text
daily auto model_signal_gate 已在 formal provider stale 时识别并复用 existing isolated Model A artifact
provider_selection_mode=validated_isolated_provider_candidate
mode=daily_auto_gate_reused_existing_isolated
formal_provider_calendar_covers_asof=false
formal_provider_calendar_max=2026-06-25
isolated_candidate_used=true
reused_existing_model_a_artifact=true
model_a_status=SCORED_ASOF_TARGET
model_a_score_job=false
model_b_status=BLOCKED_INPUT_NOT_READY
publish_latest_gate=false
accepted_latest_switch=false
readonly_latest_publish=false
agent_prompt_publish=false
production_allowed=false
```

本 PASS 不授权 formal provider publish、accepted latest switch、latest_signal 更新、readonly/Agent latest publish、production 切换、策略 replay/NAV、交易或 target_position/target_weight 生成。DNG17 只能继续把 staged provider candidate refresh 纳入 daily auto 的候选生成/验证流程，仍不得 publish formal provider。

## 2. Findings

### Critical

无。

### High

无。

### Medium

1. daily auto model_signal_gate 正确识别并复用 existing isolated Model A artifact。
   - `data_tw/ops/daily_auto_update/dng9_model_signal_gate_dry_run/model_signal_gate_summary.json` 记录：

```text
mode=daily_auto_gate_reused_existing_isolated
provider_selection_mode=validated_isolated_provider_candidate
isolated_candidate_used=true
reused_existing_model_a_artifact=true
model_a_score_job=false
model_a_status=SCORED_ASOF_TARGET
model_a_inference_input_path=data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated
model_a_score_job_path=data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated
model_a_signal_path=data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng15_r_b_modela_20260626_isolated
```

   - `job.json` 中 `model_a_score_job_triggered=false`，说明本轮复用 validator PASS 的 DNG15_R-B isolated artifact，没有重复生成同 run_id 产物。
   - `scripts/run_daily_tw_stock_auto_update.py` 中 `find_validated_isolated_modela_artifact` 对 asof、catalog status、pipeline/score status、ModelInferenceInput/ScoreJob/ModelSignal validators、row count、signal_asof、available_at、forbidden actions、production/latest flags 与 artifact paths 做显式检查。

2. daily_chain_status 正确区分 formal provider stale 与 isolated score ready。
   - `daily_chain_status.json` 记录：

```text
qlib_provider_view_status=BLOCKED_PROVIDER_VIEW_STALE
model_a_inference_input_status=READY_EXISTING_ISOLATED_ARTIFACT
model_a_score_status=READY_EXISTING_ISOLATED_ARTIFACT
model_a_signal_status=READY_EXISTING_ISOLATED_ARTIFACT
blocked_at=qlib_provider_view_or_formal_calendar
blocker_reason=formal qlib provider calendar remains stale; isolated Model A score is ready but does not authorize formal provider/latest publish
publish_latest_gate_status=DISABLED_BY_DEFAULT
```

   - `lineage_evidence.formal_calendar_max=2026-06-25`，formal calendar 未覆盖 target asof `2026-06-26`。
   - `latest_signal_asof=2026-06-17`，未用旧 latest signal 冒充 target asof。

3. safe dry-run 未触发 FinMind、legacy qlib provider refresh/publish、accepted latest、readonly/Agent latest、production/trading/target。
   - dry-run 命令为：

```text
python scripts/run_daily_tw_stock_auto_update.py --asof 2026-06-26 --force --skip-finmind --skip-qlib --enable-model-signal-gate --today-earliest-time 00:00
```

   - `job.json` 记录：

```text
finmind_update_triggered=false
yahoo_refresh_triggered=false
provider_publish_triggered=false
latest_signal_updated=false
legacy_provider_publish_enabled=false
strict_e4_readonly_chain_enabled=false
strict_e4_chain_triggered=false
readonly_snapshot.enabled=false
readonly_snapshot.latest_updated=false
orders_enabled=false
connects_to_broker=false
research_only=true
production_trade_enabled=false
```

   - `model_signal_gate_summary.json` 的 forbidden actions audit 全部为 false，包含 `real_data_fetch_triggered`、`provider_refresh_triggered`、`provider_publish_triggered`、`latest_signal_updated`、`readonly_latest_published`、`agent_prompt_published`、`strategy_replay_triggered`、`broker_order_quick_trade_triggered`、`target_position_or_weight_generated`、`finmind_fallback`、`mixed_provider_bridge`。

4. model_signal_gate summary validator PASS，且 publish/latest gate 保持关闭。
   - `data_tw/catalog/dng9_model_signal_gate_validation.json` 记录：

```text
ok=true
status=PASS
model_a_status=SCORED_ASOF_TARGET
provider_selection_mode=validated_isolated_provider_candidate
isolated_candidate_used=true
reused_existing_model_a_artifact=true
model_b_status=BLOCKED_INPUT_NOT_READY
publish_latest_gate=false
accepted_latest_switch=false
forbidden_actions_all_false=true
model_b_true_ltr_signal_generated=false
errors=[]
```

   - `scripts/run_daily_tw_stock_auto_update.py` 的 summary validator 对 `publish_latest_gate`、`accepted_latest_switch`、`readonly_latest_publish`、`agent_prompt_publish` 为 true 的情况直接报错，并要求 Model B 在 DNG3 外部源修复前保持 blocked。

5. DNG16 validation JSON 与 dry-run artifact 自洽。
   - `data_tw/catalog/dng16_daily_auto_model_score_integration_design_validation.json` 记录 `status=PASS_READY_FOR_DNG16_REVIEW`、`safe_dry_run_exit_code=0`、`py_compile.exit_code=0`、`forbidden_actions_all_false=true`。
   - `skipped_asof_ledger.json` 将本轮状态标为 `BLOCKED_FORMAL_PROVIDER_STALE_WITH_ISOLATED_MODEL_A_READY`，并给出下一步 `review_DNG16_then_continue_to_DNG17_daily_auto_provider_candidate_refresh_integration`，没有把 formal provider stale 误写成 ready。

### Low

1. DNG16 仍是基于 DNG15_R-A-R / DNG15_R-B fixed asof fixture 的最小接入。
   - `find_validated_isolated_provider_candidate` 和 `find_validated_isolated_modela_artifact` 当前读取固定 DNG15 artifact paths。
   - 这符合 DNG16 的最小验收范围；DNG17 应把 staged provider candidate refresh/selection 扩展为 daily auto 可生成、可验证、可记录的候选流程，而不是继续依赖手工 R-A-R fixture。

2. formal provider covered-asof 的 production-like route 仍保留旧 Model A/Model B builder 分支。
   - 本阶段验收场景为 formal provider stale + isolated candidate ready，safe dry-run 未进入 formal route。
   - DNG17 若要增加 provider candidate refresh，不应顺带授权 formal provider publish 或 accepted latest switch；formal route 的 production-like scoring 行为仍需单独审查。

## 3. Mainline Compliance

DNG16 工作文档要求已满足：

```text
raw/ops ready：daily_chain_status.raw_status=READY_FROM_PRIOR_JOB
formal provider stale：formal_calendar_max=2026-06-25, target asof=2026-06-26
validated isolated staged provider candidate ready：isolated_candidate.status=READY_ISOLATED_PROVIDER_CANDIDATE
existing isolated Model A artifact reused：reused_existing_model_a_artifact=true
ModelInferenceInput / ScoreJob / ModelSignalArtifact paths present
model_signal_gate summary written and validator PASS
daily_chain_status separately marks formal stale and isolated Model A readiness
publish_latest_gate=false
accepted_latest_switch=false
readonly_latest_publish=false
agent_prompt_publish=false
production_allowed=false
```

未发现 DNG16 forbidden actions：

```text
formal provider publish
formal provider overwrite
formal normalized overwrite
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
model training / tuning
```

## 4. Evidence Checked

必读材料：

```text
docs/tw_data_governance/DNG16_DAILY_AUTO_MODEL_SCORE_INTEGRATION_DESIGN_WORK_CN.md
docs/tw_data_governance/DNG16_DAILY_AUTO_MODEL_SCORE_INTEGRATION_DESIGN_EXECUTION_REPORT_CN.md
docs/tw_data_governance/DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION_REVIEW_CN.md
/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md
```

JSON / dry-run artifact：

```text
data_tw/catalog/dng16_daily_auto_model_score_integration_design_validation.json
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T140625Z/job.json
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T140625Z/daily_chain_status.json
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T140625Z/skipped_asof_ledger.json
data_tw/ops/daily_auto_update/dng9_model_signal_gate_dry_run/model_signal_gate_summary.json
data_tw/catalog/dng9_model_signal_gate_validation.json
```

代码段：

```text
scripts/run_daily_tw_stock_auto_update.py
- find_validated_isolated_provider_candidate
- find_validated_isolated_modela_artifact
- publish_latest_gate_status
- build_forbidden_actions_snapshot
- build_daily_chain_status_payload
- write_model_signal_gate_summary
- build_model_signal_gate_summary
- validate_model_signal_gate_summary_payload
- isolated_provider_selection
- run_model_signal_gate
- main safe dry-run relevant branches for --skip-finmind, --skip-qlib, --enable-model-signal-gate
```

补充只读核查：

```text
qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json asof=2026-06-17
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt tail max=2026-06-25
```

## 5. Missing Evidence Or Open Questions

无阻断性缺失证据。

剩余问题均进入 DNG17 范围：

```text
daily auto 需要自动生成/刷新 staged provider candidate，而不是只消费 DNG15_R-A-R fixed fixture
provider candidate refresh 必须继续保持 formal provider publish=false
candidate validation、smoke、forbidden actions audit、daily_chain_status lineage 需要成为 daily auto 原生产物
formal provider accepted latest switch 仍需单独路线和审查，不属于 DNG17 默认许可
```

## 6. Forbidden Actions Audit

审查结论：干净。

证据来自 `job.json`、`model_signal_gate_summary.json`、`dng9_model_signal_gate_validation.json`、`daily_chain_status.json`、`skipped_asof_ledger.json` 与代码分支核查。

```text
FinMind triggered=false
Yahoo/Scrapling legacy refresh triggered=false
provider publish triggered=false
accepted latest switch triggered=false
latest_signal_updated=false
readonly latest published=false
Agent prompt published=false
production default model/strategy switched=false
strategy replay triggered=false
NAV generated=false
broker/order/quick-trade triggered=false
target_position_or_weight_generated=false
FinMind fallback=false
mixed_provider_bridge=false
model training/tuning=false
```

## 7. Next Work Document

### DNG17 Daily Auto Provider Candidate Refresh Integration

目标：

```text
把 DNG15_R-A-R staged provider candidate refresh 从手工 fixture 纳入 daily auto，
让 daily auto 在 formal provider stale 且 raw/ops evidence ready 时，
可生成、验证、记录 isolated staged provider candidate，
再交给 DNG16 已接入的 model_signal_gate 生成或复用 isolated Model A score。
```

必须保持的边界：

```text
formal_provider_publish=false
formal_provider_mutated=false
formal_normalized_mutated=false
accepted_latest_switch=false
latest_signal_updated=false
readonly_latest_publish=false
agent_prompt_publish=false
production_allowed=false
strategy_replay_or_nav_triggered=false
broker_order_quick_trade_triggered=false
target_position_or_weight_generated=false
FinMind fallback 不得被 hidden fallback 触发
mixed-provider bridge 不得未经单独合同启用
```

DNG17 最低验收：

```text
daily auto safe mode 能生成或复用 staged provider candidate readiness
candidate_normalized_symbols_with_asof=150
staged_provider_calendar_has_asof=true
provider validation pass
Model A staged smoke pass
forbidden actions all false
daily_chain_status 区分 formal provider stale、candidate ready、isolated score ready
model_signal_gate summary validator PASS
publish_latest_gate=false
accepted_latest_switch=false
latest_signal_asof 不被推进
```

## 8. Command For Coordinator Or Executor

```text
请进入 DNG17 Daily Auto Provider Candidate Refresh Integration。
基于 DNG16 已通过的 daily auto model_signal_gate isolated Model A artifact/candidate 消费路径，
将 staged provider candidate refresh/validation/smoke/readiness 写入 daily auto safe dry-run。
不得 formal publish、不得切 accepted latest、不得更新 latest_signal、不得 publish readonly/Agent latest、不得 production switch、不得 replay/NAV、不得交易或生成 target_position/target_weight。
完成后生成 DNG17 execution report、validation JSON、safe dry-run job/daily_chain_status/skipped_asof_ledger，并提交审查。
```
