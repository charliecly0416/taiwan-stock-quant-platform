# DNG9 Daily Auto Model Signal Gate 审查报告

生成时间：2026-06-29T09:30:07+00:00

审查者：DNG9 Reviewer

## 1. Verdict

```text
PASS_WITH_CONDITIONS_GO_DNG10
```

DNG9 执行结果通过审查，可以进入 DNG10，但只允许进入下游只读 source context / StrategyInputBundle / Readonly Snapshot / Agent Prompt source context 的接线与验证。DNG10 不得 publish latest，不得切 qlib accepted latest，不得把 Model B blocker 解释为真实 LTR signal，也不得触发抓数、训练、调参、回放或交易动作。

给出带条件通过的原因：DNG9 的 `model_signal_gate` 已默认关闭，显式 gate 才可能调用 Model A / Model B pipeline；本次 dry-run/catalog 证据显示 Model B 仍是 blocker 语义，`publish_latest_gate=false`、`accepted_latest_switch=false`。同时，M3 validator 仍提示 legacy provider refresh/publish 与 accepted latest 代码存在，虽然均在显式非默认 gate 后且默认不可达，因此进入 DNG10 时必须继续保留 publish/latest 边界。

## 2. Findings

### Critical

无。

### High

无。

### Medium

无。

### Low / 条件项

1. DNG10 只能做只读下游接线。
   - 证据：DNG9 工作单要求 `publish_latest_gate=false`、`accepted_latest_switch=false`；summary 和 validation 均满足。
   - 条件：DNG10 不得 publish readonly latest、Agent prompt latest、formal qlib accepted latest，也不得把 model signal gate 通过解释为生产默认展示授权。

2. Model B LTR 仍受 DNG3 外部源修复 blocker 约束。
   - 证据：dry-run enabled 静态路径要求 Model B 为 `BLOCKED_INPUT_NOT_READY`；当前 summary 为 default-disabled，未生成 `model_b_signal_path`。
   - 条件：在 `corporate_actions`、`monthly_revenue`、`valuation` 修复并通过 PIT-safe readiness 前，Model B 只能输出 blocker / fallback policy，不得生成真实 LTR ModelSignalArtifact。

3. legacy provider/latest 代码仍存在，但默认不可达。
   - 证据：M3 validator 返回两个 warning：`legacy_provider_publish_path_present`、`legacy_accepted_latest_path_present`。
   - 条件：这些路径必须继续保持在显式非默认 `--enable-legacy-provider-publish` gate 后；DNG10 不得复用或放宽该 gate。

## 3. 已审查输入

已阅读：

```text
docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md
docs/tw_data_governance/DNG9_DAILY_AUTO_MODEL_SIGNAL_GATE_WORK_CN.md
docs/tw_data_governance/DNG9_DAILY_AUTO_MODEL_SIGNAL_GATE_REVIEW_WORK_CN.md
docs/tw_data_governance/DNG9_DAILY_AUTO_MODEL_SIGNAL_GATE_EXECUTION_REPORT_CN.md
scripts/run_daily_tw_stock_auto_update.py
scripts/validate_tw_daily_orchestrator_m3.py
data_tw/ops/daily_auto_update/dng9_model_signal_gate_dry_run/model_signal_gate_summary.json
data_tw/catalog/dng9_model_signal_gate_validation.json
```

本审查未修复代码，未运行真实 daily auto，未抓数，未训练，未调参，未回放，未 publish，未切 latest，未执行交易动作。

## 4. Gate 默认关闭审查

结论：通过。

`scripts/run_daily_tw_stock_auto_update.py` 中 `--enable-model-signal-gate` 的默认值来自：

```text
TW_DAILY_AUTO_ENABLE_MODEL_SIGNAL_GATE=false
```

默认 job 字段记录：

```text
model_signal_gate_enabled=false
model_signal_gate_default_reachable=false
model_a_score_job_triggered=false
model_b_ltr_score_job_triggered=false
```

`run_model_signal_gate()` 在 `enabled=false` 时只写 default-disabled summary/validation，不调用 Model A 或 Model B pipeline。

## 5. 显式 Gate 调用边界

结论：通过。

只有以下显式入口会开启 model signal gate：

```text
--enable-model-signal-gate
TW_DAILY_AUTO_ENABLE_MODEL_SIGNAL_GATE=true
```

开启后代码路径才会调用：

```text
scripts/build_tw_model_inference_input.py
scripts/run_tw_model_score_job.py
scripts/build_tw_modelb_ltr_inference_input.py
scripts/run_tw_modelb_ltr_score_job.py
```

`--dng9-model-signal-gate-dry-run-summary` 会在任何 daily provider update 前直接写 summary/validation 并退出，符合 DNG9 静态验证边界。

## 6. Model B Blocker 审查

结论：通过。

当前落盘 summary：

```text
gate_enabled=false
model_b_status=DISABLED_BY_DEFAULT
model_b_blockers=["model_signal_gate_disabled"]
model_b_signal_path=""
dng3_external_source_repair_required_before_true_model_b_ltr_signal=true
```

validator 还强制检查：当静态 enabled 或真实 gate 触发 Model B score job 时，Model B 必须保持 `BLOCKED_INPUT_NOT_READY`，否则写入 `model_b_must_remain_blocked_until_dng3_external_source_repair` 错误。未发现绕过 DNG3 blocker 或生成真实 Model B LTR signal 的证据。

## 7. Publish / Latest / 禁止动作审查

结论：通过。

summary 与 catalog validation 均显示：

```text
publish_latest_gate=false
accepted_latest_switch=false
readonly_latest_publish=false
agent_prompt_publish=false
production_allowed=false
research_only=true
forbidden_actions_audit.all_false=true
```

forbidden actions 全部为 false，包括：

```text
real_data_fetch_triggered=false
provider_refresh_triggered=false
provider_publish_triggered=false
qlib_accepted_latest_switched=false
model_training_triggered=false
model_tuning_triggered=false
strategy_replay_triggered=false
replay_result_nav_generated=false
broker_order_quick_trade_triggered=false
target_position_or_weight_generated=false
```

M3 validator 也确认：

```text
default_provider_refresh_reachable=false
default_provider_publish_reachable=false
default_accepted_latest_reachable=false
broker_order_patterns_present=[]
monitor_write_patterns_present=[]
model_signal_gate_forbidden_actions_audit_present=true
```

## 8. 本地验证结果

已运行：

```bash
python -m py_compile scripts/run_daily_tw_stock_auto_update.py scripts/validate_tw_daily_orchestrator_m3.py
```

结果：通过，退出码 0，无输出。

已运行：

```bash
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
```

结果摘要：

```text
ok=true
status=passed
errors=[]
warnings=[
  legacy_provider_publish_path_present,
  legacy_accepted_latest_path_present
]
model_signal_gate_present=true
model_signal_gate_default_disabled=true
model_signal_gate_default_unreachable_recorded=true
model_signal_gate_calls_modela_pipeline=true
model_signal_gate_calls_modelb_blocker_pipeline=true
model_signal_gate_modelb_blocked_until_dng3_repair=true
model_signal_gate_forbidden_actions_audit_present=true
```

## 9. DNG10 放行边界

DNG9 不需要 repair。DNG10 可以继续：

- 只读 StrategyInputBundle / source context 接线。
- 只读 Readonly Snapshot / Agent Prompt source context 接线。
- 引用 DNG9 summary/validation 作为 gate 状态证据。
- 在 Model B 未修复前继续传播 blocker / qlib-only fallback requires explicit strategy contract 语义。

DNG10 禁止：

- 运行真实 daily auto 抓数。
- provider refresh / publish。
- qlib accepted latest switch。
- readonly latest 或 Agent prompt latest publish。
- 模型训练或调参。
- 策略收益回放、ReplayResult 或 NAV 生成。
- broker/order/quick-trade。
- `target_position` / `target_weight`。
- 将 Model B blocker 或 qlib-only fallback 冒充为真实 LTR signal。

最终结论：

```text
PASS_WITH_CONDITIONS_GO_DNG10
```
