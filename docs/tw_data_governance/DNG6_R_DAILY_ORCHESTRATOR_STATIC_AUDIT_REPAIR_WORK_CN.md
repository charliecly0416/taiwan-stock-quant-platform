# DNG6_R Daily Orchestrator 静态审计误报修复工作文档

生成日期：2026-06-29

## 1. 背景

DNG6 审查结论：

```text
PASS_WITH_CONDITIONS_GO_DNG7
```

但建议审计命令失败：

```text
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
```

命中：

```text
script_broker_order_pattern
```

审查判断是字段名 `broker_order_quick_trade_triggered=false` 的静态误报，不是实际 broker/order 调用。DNG6_R 必须修复该误报或调整字段命名，让 M3 daily orchestrator 审计恢复通过。

## 2. 目标

修复静态审计失败，同时保持所有安全边界不变：

```text
provider_publish=false
accepted_latest_switch=false
model_signal_gate=false
publish_latest_gate=false
broker_order=false
quick_trade=false
target_position=false
target_weight=false
```

## 3. 允许修改

允许修改：

```text
scripts/run_daily_tw_stock_auto_update.py
scripts/validate_tw_daily_orchestrator_m3.py
docs/tw_data_governance/DNG6_R_DAILY_ORCHESTRATOR_STATIC_AUDIT_REPAIR_EXECUTION_REPORT_CN.md
```

也允许更新 DNG6 dashboard validation 产物，如果 validator 重跑需要。

## 4. 禁止动作

不得执行：

```text
真实抓数
provider refresh / publish
qlib accepted latest switch
readonly latest publish
Agent prompt latest publish
模型训练
模型推理
模型 score 生成
策略收益回放
ReplayResult/NAV 生成
broker/order/quick-trade
target_position / target_weight
```

不得通过删除安全审计来“通过”。如果修改 validator，必须让它更精确地区分字段名/安全声明与真实调用。

## 5. 必须验证

```text
python -m py_compile scripts/run_daily_tw_stock_auto_update.py scripts/validate_tw_daily_orchestrator_m3.py scripts/build_tw_daily_readiness_dashboard.py scripts/validate_tw_daily_readiness_dashboard.py
python scripts/validate_tw_daily_readiness_dashboard.py --dashboard data_tw/catalog/daily_readiness_dashboard.json --json
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
```

## 6. 输出

必须写：

```text
docs/tw_data_governance/DNG6_R_DAILY_ORCHESTRATOR_STATIC_AUDIT_REPAIR_EXECUTION_REPORT_CN.md
```

报告必须说明：

1. 误报原因。
2. 修改了什么。
3. 三条验证命令结果。
4. forbidden action audit。
5. 是否建议进入 DNG7。
