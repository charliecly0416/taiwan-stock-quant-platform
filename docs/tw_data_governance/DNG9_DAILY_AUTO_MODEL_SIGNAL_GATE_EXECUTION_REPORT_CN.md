# DNG9 Daily Auto Model Signal Gate 执行报告

生成时间：2026-06-29T08:17:27+00:00

## 1. 结论

执行状态：`PASS_GO_DNG10_GATE_ONLY`

DNG9 已把 DNG7 Model A score pipeline 与 DNG8 Model B blocker pipeline 接入 `scripts/run_daily_tw_stock_auto_update.py` 的显式 `model_signal_gate`。默认关闭；只有 `--enable-model-signal-gate` 或 `TW_DAILY_AUTO_ENABLE_MODEL_SIGNAL_GATE=true` 开启后，daily auto 才会调用只读模型信号 pipeline。

本次只做静态 / dry-run summary，没有运行真实 daily auto，没有触发真实抓数、provider refresh/publish、accepted latest switch、readonly/Agent publish、模型训练/调参、策略收益回放、ReplayResult/NAV、broker/order/quick-trade、`target_position` 或 `target_weight`。

## 2. Daily Auto 集成点

- CLI gate：`--enable-model-signal-gate`
- 环境变量 gate：`TW_DAILY_AUTO_ENABLE_MODEL_SIGNAL_GATE=true`
- dry-run summary 模式：`--dng9-model-signal-gate-dry-run-summary`
- summary 输出：`data_tw/ops/daily_auto_update/dng9_model_signal_gate_dry_run/model_signal_gate_summary.json`
- catalog validation：`data_tw/catalog/dng9_model_signal_gate_validation.json`

显式 gate 开启后的调用顺序：

1. `scripts/build_tw_model_inference_input.py`
2. `scripts/run_tw_model_score_job.py`
3. `scripts/build_tw_modelb_ltr_inference_input.py`
4. `scripts/run_tw_modelb_ltr_score_job.py`

默认路径记录：

- `model_signal_gate_enabled=false`
- `model_signal_gate_default_reachable=false`
- `model_a_score_job_triggered=false`
- `model_b_ltr_score_job_triggered=false`
- `publish_latest_gate=false`
- `accepted_latest_switch=false`

## 3. Gate Summary

生成的 dry-run summary：

- `gate_enabled=false`
- `model_a_status=DISABLED_BY_DEFAULT`
- `model_a_signal_path=""`
- `model_b_status=DISABLED_BY_DEFAULT`
- `model_b_blockers=["model_signal_gate_disabled"]`
- `model_b_signal_path=""`
- `fallback_policy=model_b_qlib_only_fallback_requires_explicit_strategy_contract`
- `publish_latest_gate=false`
- `accepted_latest_switch=false`
- `forbidden_actions_audit.all_false=true`

catalog validation：

- `status=PASS`
- `default_disabled=true`
- `forbidden_actions_all_false=true`
- `model_b_true_ltr_signal_generated=false`
- `recommendation=GO_DNG10_GATE_ONLY`

## 4. DNG3 / Model B 边界

DNG9 没有生成真实 Model B LTR signal。当前 DNG3 外部源修复仍是 Model B LTR 的前置条件；在 `corporate_actions`、`monthly_revenue`、`valuation` 修复并重新通过 PIT-safe canonical feature readiness 之前，Model B 只能保持 blocker / `BLOCKED_INPUT_NOT_READY` 语义。

本次 dry-run summary 明确记录：

- `dng3_external_source_repair_required_before_true_model_b_ltr_signal=true`
- `model_b_signal_path=""`
- `model_b_true_ltr_signal_generated=false`

## 5. 验证结果

已运行：

```bash
python -m py_compile scripts/run_daily_tw_stock_auto_update.py scripts/validate_tw_daily_orchestrator_m3.py scripts/build_tw_model_inference_input.py scripts/run_tw_model_score_job.py scripts/build_tw_modelb_ltr_inference_input.py scripts/run_tw_modelb_ltr_score_job.py
```

结果：通过，无输出。

已运行：

```bash
python scripts/run_daily_tw_stock_auto_update.py --asof 2026-06-25 --dng9-model-signal-gate-dry-run-summary
```

结果：`ok=true`，写出 default-disabled `model_signal_gate_summary.json` 与 `dng9_model_signal_gate_validation.json`。

已运行：

```bash
python scripts/run_daily_tw_stock_auto_update.py --asof 2026-06-25 --enable-model-signal-gate --dng9-model-signal-gate-dry-run-summary
```

结果：`ok=true`，仅验证静态开启状态下 Model B 仍为 `BLOCKED_INPUT_NOT_READY`；未调用模型 job 或 daily auto。

已运行：

```bash
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
```

结果：`ok=true`，`status=passed`。仅有两个既有边界警告：legacy provider refresh/publish 与 accepted latest 代码仍存在，但都在显式非默认 gate 后，默认不可达。

## 6. Forbidden Action Audit

通过。未触发：

- 真实抓数。
- provider refresh / publish。
- qlib accepted latest switch。
- readonly latest publish。
- Agent prompt publish。
- 模型训练 / 调参。
- 策略收益回放。
- ReplayResult / NAV。
- broker / order / quick-trade。
- `target_position` / `target_weight`。

## 7. DNG10 建议

建议进入 DNG10，但范围必须限定为 `GO_DNG10_GATE_ONLY`：继续做下游只读消费合同 / strategy input gate 的显式接线与验证，不得把 Model B blocker 解释成真实 LTR signal，也不得 publish/latest switch。
