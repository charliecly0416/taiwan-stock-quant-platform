# DNG6_R Daily Orchestrator 静态审计误报修复审查报告

生成日期：2026-06-29

审查者：DNG6_R reviewer

## 1. 结论

```text
PASS_GO_DNG7
```

DNG6_R 修复可以进入 DNG7。`validate_tw_daily_orchestrator_m3.py` 仍会检测真实 broker/order runtime pattern；本轮通过原因是只忽略形如 `"*broker_order*": False` 的安全声明字段，不是关闭或删除 broker/order 审计。`run_daily_tw_stock_auto_update.py` 的 daily auto 默认 gate 仍关闭，未发现默认路径触发 provider publish、accepted latest switch、broker/order、quick-trade、target_position、target_weight、模型训练/推理/score、回放或 latest publish。

## 2. 已审查输入

```text
docs/tw_data_governance/DNG6_R_DAILY_ORCHESTRATOR_STATIC_AUDIT_REPAIR_WORK_CN.md
docs/tw_data_governance/DNG6_R_DAILY_ORCHESTRATOR_STATIC_AUDIT_REPAIR_REVIEW_WORK_CN.md
docs/tw_data_governance/DNG6_R_DAILY_ORCHESTRATOR_STATIC_AUDIT_REPAIR_EXECUTION_REPORT_CN.md
scripts/validate_tw_daily_orchestrator_m3.py
scripts/run_daily_tw_stock_auto_update.py
scripts/build_tw_daily_readiness_dashboard.py
scripts/validate_tw_daily_readiness_dashboard.py
```

## 3. 核心审查判断

### 3.1 broker/order 检测仍有效

`scripts/validate_tw_daily_orchestrator_m3.py` 中仍保留：

```text
SCRIPT_FORBIDDEN_RUNTIME_PATTERNS["broker_order"] =
["broker_order", "submitOrder", "placeOrder", "quick-trade", "quickTrade"]
```

新的 `forbidden_runtime_pattern_matches()` 只在 `is_false_safety_declaration_line()` 判定为安全声明时忽略命中。该判定要求整行匹配：

```text
"<包含 pattern 的字段名>": False
```

因此 `"broker_order_quick_trade_triggered": False` 被归入 `broker_order_ignored_safety_declarations`，而非 False 字段、字符串、函数调用或真实 runtime pattern 仍进入 `broker_order_runtime_matches` 并触发 `script_broker_order_pattern`。

审查者另做 `/tmp` 静态探针：复制 `scripts/run_daily_tw_stock_auto_update.py` 到 `/tmp/dng6_r_orchestrator_probe.py`，插入：

```text
"probe_runtime": "broker_order",
```

再运行同一 validator，结果为失败：

```text
ok=false
status=failed
errors=[script_broker_order_pattern]
broker_order_runtime_matches=[{"pattern":"broker_order","line":834,"line_text":"\"probe_runtime\": \"broker_order\","}]
```

这证明修复没有把 broker/order 检测整体放空。

### 3.2 只忽略 false safety declaration

原始脚本审计结果显示：

```text
broker_order_patterns_present=[]
broker_order_runtime_matches=[]
broker_order_ignored_safety_declarations=[
  {"pattern":"broker_order","line":833,"reason":"false_safety_declaration"}
]
monitor_write_patterns_present=[]
monitor_write_runtime_matches=[]
```

第 833 行对应 dashboard finalize 观测字段：

```text
"broker_order_quick_trade_triggered": False
```

该字段是 forbidden action audit 声明，不是 broker/order/quick-trade 调用。

### 3.3 daily auto 默认 gate 仍关闭

`scripts/run_daily_tw_stock_auto_update.py` 仍使用显式非默认 gate：

```text
--enable-legacy-provider-publish
default=env_flag("TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH", False)

--enable-strict-e4-readonly-chain
default=env_flag("TW_DAILY_AUTO_ENABLE_STRICT_E4_READONLY_CHAIN", False)

--enable-data-catalog-dashboard
default=env_flag("TW_DAILY_AUTO_ENABLE_DATA_CATALOG_DASHBOARD", False)
```

M3 静态审计确认：

```text
legacy_provider_gate_default_disabled=true
strict_e4_readonly_gate_default_disabled=true
default_provider_refresh_reachable=false
default_provider_publish_reachable=false
default_accepted_latest_reachable=false
provider_refresh_guarded=true
provider_publish_guarded=true
accepted_latest_call_guarded=true
```

### 3.4 forbidden action 未触发

本次审查只运行静态编译和 validator。未运行 daily auto、未抓数、未训练、未推理、未 score、未回放、未 publish、未切 latest、未触发 broker/order/quick-trade。

dashboard validator 确认：

```text
forbidden_actions_all_false=true
production_ready=false
route_dependency_all_gate_pass=false
```

## 4. 必须验证结果

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

两条 warning 表示 legacy provider/latest 代码路径仍存在，但静态审计确认其仍在显式非默认 gate 后，不构成本轮阻断。

## 5. DNG7 边界

同意进入 DNG7，但 DNG7 仍必须保持研究只读边界：

```text
不得训练
不得模型推理或生成真实 score，除非 DNG7 明确建立只读 ModelInferenceInput / ScoreJob 合同并先通过 validator
不得 provider refresh / publish
不得 qlib accepted latest switch
不得 readonly latest publish
不得 Agent prompt latest publish
不得 replay/NAV
不得 broker/order/quick-trade
不得生成 target_position / target_weight
```
