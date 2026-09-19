# DNG9 Daily Auto Model Signal Gate 审查工作文档

生成日期：2026-06-29

## 1. 审查输入

```text
docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md
docs/tw_data_governance/DNG9_DAILY_AUTO_MODEL_SIGNAL_GATE_WORK_CN.md
docs/tw_data_governance/DNG9_DAILY_AUTO_MODEL_SIGNAL_GATE_EXECUTION_REPORT_CN.md
scripts/run_daily_tw_stock_auto_update.py
scripts/validate_tw_daily_orchestrator_m3.py
data_tw/ops/daily_auto_update/dng9_model_signal_gate_dry_run/model_signal_gate_summary.json
data_tw/catalog/dng9_model_signal_gate_validation.json
```

## 2. 审查目标

判断 DNG9 是否安全接入显式 `model_signal_gate`，是否可以进入 DNG10 StrategyInputBundle / Readonly Snapshot / Agent Prompt source context 衔接。

## 3. 必查项

1. `model_signal_gate` 是否默认关闭。
2. 只有显式 `--enable-model-signal-gate` / `TW_DAILY_AUTO_ENABLE_MODEL_SIGNAL_GATE=true` 才可能调用 Model A / Model B pipeline。
3. Model B blocker 是否仍被保留，未生成真实 LTR signal。
4. `publish_latest_gate=false`、`accepted_latest_switch=false`。
5. daily orchestrator M3 validator 是否通过。
6. 是否未运行真实 daily auto、未触发抓数、训练、调参、回放、publish、latest switch、交易动作。

## 4. 必须运行

```text
python -m py_compile scripts/run_daily_tw_stock_auto_update.py scripts/validate_tw_daily_orchestrator_m3.py
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
```

如 DNG9 有专用 validation JSON，可只读检查其内容。

## 5. Verdict

审查结论只能是：

```text
PASS_GO_DNG10
PASS_WITH_CONDITIONS_GO_DNG10
FAIL_NEEDS_DNG9_REPAIR
STOP_COORDINATOR_DECISION_REQUIRED
```

## 6. 输出

审查者必须写：

```text
docs/tw_data_governance/DNG9_DAILY_AUTO_MODEL_SIGNAL_GATE_REVIEW_CN.md
```

若通过，必须说明 DNG10 只能做下游只读 source context / bundle 接线，不得 publish latest。
