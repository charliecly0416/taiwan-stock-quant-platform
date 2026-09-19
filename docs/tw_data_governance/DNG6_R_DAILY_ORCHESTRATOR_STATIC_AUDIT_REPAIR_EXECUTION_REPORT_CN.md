# DNG6_R Daily Orchestrator 静态审计误报修复执行报告

生成日期：2026-06-29

## 1. 结论

```text
PASS_GO_DNG7
```

本轮仅修复 `scripts/validate_tw_daily_orchestrator_m3.py` 的静态误报识别逻辑，未修改 `scripts/run_daily_tw_stock_auto_update.py` 的 gate、默认行为或安全声明字段。

## 2. 误报原因

`validate_tw_daily_orchestrator_m3.py` 原先对 `SCRIPT_FORBIDDEN_RUNTIME_PATTERNS["broker_order"]` 使用全文子串匹配：

```text
broker_order
```

因此 `run_daily_tw_stock_auto_update.py` 中 DNG6 dashboard finalize 观测字段：

```text
"broker_order_quick_trade_triggered": False
```

被误判为 broker/order runtime pattern。该字段是禁止动作审计声明，值为 `False`，不是 broker/order/quick-trade 调用。

## 3. 修改内容

修改文件：

```text
scripts/validate_tw_daily_orchestrator_m3.py
```

变更：

1. 新增 `is_false_safety_declaration_line()`，识别形如 `"xxx<pattern>xxx": False` 的安全审计声明行。
2. 新增 `forbidden_runtime_pattern_matches()`，将 forbidden runtime pattern 命中拆分为：
   - `*_runtime_matches`
   - `*_ignored_safety_declarations`
3. 保留原有安全审计和错误条件：只要出现非 False 安全声明的 runtime pattern，仍会报 `script_broker_order_pattern` 或 `script_monitor_write_pattern`。

未修改：

```text
scripts/run_daily_tw_stock_auto_update.py
```

未打开任何 gate，未删除 dashboard / forbidden action / M3 安全审计。

## 4. 验证结果

### 4.1 py_compile

命令：

```text
python -m py_compile scripts/run_daily_tw_stock_auto_update.py scripts/validate_tw_daily_orchestrator_m3.py scripts/build_tw_daily_readiness_dashboard.py scripts/validate_tw_daily_readiness_dashboard.py
```

结果：

```text
PASS
```

### 4.2 DNG6 dashboard validator

命令：

```text
python scripts/validate_tw_daily_readiness_dashboard.py --dashboard data_tw/catalog/daily_readiness_dashboard.json --json
```

结果摘要：

```text
ok=true
status=PASS
dashboard_status=BLOCKED_OR_PARTIAL_NOT_PRODUCTION_READY
production_ready=false
route_dependency_all_gate_pass=false
forbidden_actions_all_false=true
error_count=0
warning_count=0
readiness_layer_status_counts:
  BLOCK=1
  BLOCKED_FOR_MODEL_B_LTR=1
  PARTIAL_READY=3
```

### 4.3 M3 daily orchestrator static audit

命令：

```text
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
```

结果摘要：

```text
ok=true
status=passed
errors=[]
warnings:
  legacy_provider_publish_path_present
  legacy_accepted_latest_path_present
```

关键安全边界：

```text
legacy_provider_gate_default_disabled=true
strict_e4_readonly_gate_default_disabled=true
default_provider_refresh_reachable=false
default_provider_publish_reachable=false
default_accepted_latest_reachable=false
provider_refresh_guarded=true
provider_publish_guarded=true
accepted_latest_call_guarded=true
broker_order_patterns_present=[]
broker_order_runtime_matches=[]
broker_order_ignored_safety_declarations=[{"pattern":"broker_order","line":833,"reason":"false_safety_declaration"}]
monitor_write_patterns_present=[]
monitor_write_runtime_matches=[]
```

两条 warning 表示 legacy provider/latest 代码路径仍存在，但仍处于显式非默认 gate 后；不是默认路径可达错误。

## 5. Forbidden Action Audit

本轮未执行：

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

DNG6 dashboard validator 确认：

```text
forbidden_actions_all_false=true
production_ready=false
```

## 6. 是否建议进入 DNG7

建议进入 DNG7，但范围仍限于：

```text
ModelInferenceInput / qlib Model A ScoreJob 合同与 validator
只读 qlib Model A score pipeline 设计或静态验证
继续引用 DNG6 dashboard、DNG5 route dependency validation 和 readiness matrix
```

DNG7 不得训练、不切 qlib accepted latest、不 provider publish、不 readonly/Agent latest publish、不 replay/NAV、不 broker/order/quick-trade、不生成 target_position/target_weight。
