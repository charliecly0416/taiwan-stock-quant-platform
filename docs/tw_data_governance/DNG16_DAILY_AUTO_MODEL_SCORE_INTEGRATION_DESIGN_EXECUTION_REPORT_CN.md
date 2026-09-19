# DNG16 Daily Auto Model Score Integration Design 执行报告

生成时间：2026-06-29T14:10:00+00:00

## 1. Scope

- Assigned phase：`DNG16 daily auto model score integration design`
- Mainline/work document：`docs/tw_data_governance/DNG16_DAILY_AUTO_MODEL_SCORE_INTEGRATION_DESIGN_WORK_CN.md`
- Target asof：`2026-06-26`
- 重点修改：`scripts/run_daily_tw_stock_auto_update.py`

非目标确认：未 formal publish、未覆盖 formal provider/normalized、未切 accepted latest、未更新 latest_signal、未 publish readonly/Agent latest、未 production switch、未策略 replay/NAV、未 broker/order/quick-trade、未生成 target_position/target_weight、未 FinMind fallback、未 mixed-provider bridge、未训练或调参。

## 2. Documents / Contracts / Skills Read

- `docs/tw_data_governance/DNG16_DAILY_AUTO_MODEL_SCORE_INTEGRATION_DESIGN_WORK_CN.md`
- `docs/tw_data_governance/DNG15_R_B_ISOLATED_MODELA_SCORE_INTEGRATION_REVIEW_CN.md`
- `data_tw/catalog/dng15_r_b_isolated_modela_score_integration_validation.json`
- `scripts/run_daily_tw_stock_auto_update.py`
- `scripts/build_tw_dng15_r_b_isolated_modela_score_integration.py`
- `/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md`
- 补充核查：`data_tw/catalog/dng15_r_a_r_modela_20260626_candidate_readiness.json`
- 补充核查：`data_tw/catalog/dng15_r_a_r_yahoo_access_repair_decision.json`

## 3. Changes Made

- 在 daily auto orchestrator 中新增 isolated provider candidate 与 existing isolated Model A artifact 识别 helper。
- 修改 `run_model_signal_gate`：`--enable-model-signal-gate` 时优先复用 DNG15_R-B validator PASS 的 isolated Model A artifact；若缺 artifact 且 formal provider stale，则在 R-A-R candidate ready 时运行 `scripts/build_tw_dng15_r_b_isolated_modela_score_integration.py`。
- 扩展 `model_signal_gate_summary.json`：新增 provider selection、formal calendar、isolated candidate、existing artifact reuse、Model A input/score/signal path 等字段。
- 修改 `daily_chain_status`：formal provider stale 时仍保持 `qlib_provider_view_status=BLOCKED_PROVIDER_VIEW_STALE`，同时 Model A 三项表达 isolated readiness。
- 修改 `skipped_asof_ledger`：记录 `formal_provider_stale_but_isolated_model_a_ready`。
- 新增 DNG16 validation JSON 与本执行报告。

## 4. Evidence Produced

- DNG16 validation：`data_tw/catalog/dng16_daily_auto_model_score_integration_design_validation.json`
- safe dry-run job：`data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T140625Z/job.json`
- daily chain status：`data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T140625Z/daily_chain_status.json`
- skipped asof ledger：`data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T140625Z/skipped_asof_ledger.json`
- model signal gate summary：`data_tw/ops/daily_auto_update/dng9_model_signal_gate_dry_run/model_signal_gate_summary.json`
- model signal gate validation：`data_tw/catalog/dng9_model_signal_gate_validation.json`

关键 dry-run 结果：

```text
job_id=daily_tw_stock_auto_update_20260626_20260629T140625Z
model_signal_gate.mode=daily_auto_gate_reused_existing_isolated
provider_selection_mode=validated_isolated_provider_candidate
formal_provider_calendar_covers_asof=false
formal_provider_calendar_max=2026-06-25
isolated_candidate_used=true
reused_existing_model_a_artifact=true
model_a_score_job=false
model_a_status=SCORED_ASOF_TARGET
model_b_status=BLOCKED_INPUT_NOT_READY
```

`daily_chain_status` 关键状态：

```text
qlib_provider_view_status=BLOCKED_PROVIDER_VIEW_STALE
model_a_inference_input_status=READY_EXISTING_ISOLATED_ARTIFACT
model_a_score_status=READY_EXISTING_ISOLATED_ARTIFACT
model_a_signal_status=READY_EXISTING_ISOLATED_ARTIFACT
blocked_at=qlib_provider_view_or_formal_calendar
publish_latest_gate_status=DISABLED_BY_DEFAULT
```

## 5. Validators / Commands

```bash
python -m py_compile scripts/run_daily_tw_stock_auto_update.py scripts/build_tw_dng15_r_b_isolated_modela_score_integration.py
```

结果：exit code `0`。

```bash
python scripts/run_daily_tw_stock_auto_update.py \
  --asof 2026-06-26 \
  --force \
  --skip-finmind \
  --skip-qlib \
  --enable-model-signal-gate \
  --today-earliest-time 00:00
```

结果：exit code `0`。

## 6. Compliance With Mainline

- formal provider calendar 仍只到 `2026-06-25`，未被标记为 ready。
- `2026-06-26` Model A readiness 来自 DNG15_R-B isolated artifact 和 DNG15_R-A-R validated staged provider candidate。
- gate summary 明确 `publish_latest_gate=false`、`accepted_latest_switch=false`、`readonly_latest_publish=false`、`agent_prompt_publish=false`、`production_allowed=false`。
- daily auto 未使用旧 `latest_signal.json` 冒充 target asof；`latest_signal_asof` 仍记录为 `2026-06-17`。

## 7. Forbidden Actions Audit

- `formal_publish=false`
- `formal_provider_mutated=false`
- `formal_normalized_mutated=false`
- `accepted_latest_switch=false`
- `latest_signal_updated=false`
- `readonly_latest_published=false`
- `agent_prompt_latest_published=false`
- `production_default_model_or_strategy_switched=false`
- `strategy_replay_or_nav_triggered=false`
- `broker_order_quick_trade_triggered=false`
- `target_position_or_weight_generated=false`
- `finmind_fallback=false`
- `mixed_provider_bridge=false`
- `model_training_or_tuning=false`

## 8. Issues / Blockers / Deviations

- 无阻断性 blocker。
- 本实现保持最小范围：DNG16 只接入 DNG15_R-B fixed asof fixture 的 validated isolated Model A score；更通用的 provider candidate refresh/selection 应进入 DNG17。
- safe dry-run 使用 `--skip-finmind --skip-qlib`，因此 raw status 来自既有 prior job evidence；这符合本阶段禁止 FinMind fallback 与 formal provider publish 的要求。

## 9. Files Changed

- `scripts/run_daily_tw_stock_auto_update.py`
- `data_tw/catalog/dng16_daily_auto_model_score_integration_design_validation.json`
- `docs/tw_data_governance/DNG16_DAILY_AUTO_MODEL_SCORE_INTEGRATION_DESIGN_EXECUTION_REPORT_CN.md`
- dry-run 产物目录：`data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260626_20260629T140625Z/`
- 更新的 gate summary/validation：`data_tw/ops/daily_auto_update/dng9_model_signal_gate_dry_run/model_signal_gate_summary.json`、`data_tw/catalog/dng9_model_signal_gate_validation.json`

## 10. Recommendation For Reviewer

建议 verdict：`PASS_GO_DNG17_DAILY_AUTO_PROVIDER_CANDIDATE_REFRESH_INTEGRATION`。

理由：daily auto 已能在 formal provider stale 且已有 validated DNG15_R-B isolated Model A artifact 时，复用 target asof score/signal 并写入 model signal gate summary 与 daily_chain_status；所有 forbidden actions 保持 false。DNG17 应将 staged provider candidate refresh 从手动 R-A-R 纳入 daily auto，但仍不 publish formal provider。
