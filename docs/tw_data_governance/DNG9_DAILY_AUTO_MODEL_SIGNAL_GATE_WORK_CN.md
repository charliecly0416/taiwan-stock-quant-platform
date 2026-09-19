# DNG9 Daily Auto Model Signal Gate 集成工作文档

生成日期：2026-06-29

## 1. 背景

DNG8 审查结论：

```text
PASS_WITH_CONDITIONS_GO_DNG9
```

条件：

- DNG9 只能接入 gate/blocker 语义；
- 不能在 DNG3 外部源修复前生成真实 Model B LTR signal；
- 不得 publish/latest switch。

## 2. 目标

把 DNG7 Model A score pipeline 和 DNG8 Model B blocker pipeline 接入 `scripts/run_daily_tw_stock_auto_update.py` 的显式 `model_signal_gate`。

默认关闭。只有显式参数或环境变量开启时，才允许调用只读模型信号 pipeline。

## 3. 必须生成/更新

```text
scripts/run_daily_tw_stock_auto_update.py
scripts/validate_tw_daily_orchestrator_m3.py 或相关 validator（如需）
data_tw/ops/daily_auto_update/dng9_model_signal_gate_dry_run/model_signal_gate_summary.json
data_tw/catalog/dng9_model_signal_gate_validation.json
docs/tw_data_governance/DNG9_DAILY_AUTO_MODEL_SIGNAL_GATE_EXECUTION_REPORT_CN.md
```

## 4. Gate 设计

新增显式 gate：

```text
--enable-model-signal-gate
TW_DAILY_AUTO_ENABLE_MODEL_SIGNAL_GATE=true
```

默认：

```text
model_signal_gate=false
model_a_score_job=false
model_b_ltr_score_job=false
publish_latest_gate=false
accepted_latest_switch=false
```

开启 gate 后允许：

- 调用 DNG7 Model A builder / score job；
- 调用 DNG8 Model B blocker/score job；
- 写 `model_signal_gate_summary.json`；
- 写 job.json 中的只读状态字段。

开启 gate 后仍禁止：

- 模型训练/调参；
- provider refresh/publish；
- accepted latest switch；
- readonly/Agent latest publish；
- replay/NAV；
- broker/order/target_position/target_weight。

## 5. Dry-run / 静态验证

如果直接运行 daily auto 会触发 FinMind update，则不得运行真实 daily auto。可以做以下验证：

1. py_compile；
2. M3 daily orchestrator validator；
3. 新增 model signal gate dry-run helper 或静态 summary builder；
4. 检查默认不开 gate；
5. 检查开启 gate 时只会调用 DNG7/DNG8 只读脚本。

## 6. model_signal_gate_summary.json

必须包含：

```text
schema_version
created_at
asof
gate_enabled
model_a_status
model_a_signal_path
model_b_status
model_b_blockers
fallback_policy
publish_latest_gate
accepted_latest_switch
forbidden_actions_audit
```

## 7. 禁止动作

不得执行：

```text
真实抓数
provider refresh / publish
qlib accepted latest switch
readonly latest publish
Agent prompt latest publish
模型训练
模型调参
策略收益回放
ReplayResult/NAV 生成
broker/order/quick-trade
target_position / target_weight
```

## 8. 执行报告

报告必须说明：

1. daily auto 集成点。
2. 默认 gate 状态。
3. dry-run / static validation 结果。
4. Model A / Model B gate summary。
5. M3 daily orchestrator validator 结果。
6. forbidden action audit。
7. 是否建议进入 DNG10。
