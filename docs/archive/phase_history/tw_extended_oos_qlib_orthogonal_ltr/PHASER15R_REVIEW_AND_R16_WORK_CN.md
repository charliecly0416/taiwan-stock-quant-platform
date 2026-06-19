# Phase R15R 审查与 R16 工作文档

生成日期：2026-06-16

## 1. R15R 审查结论

R15R 审查通过，允许进入 R16。

R15R 已修复 R15 授权前端只读展示 diff 与总合同回归 forbidden-scope audit 的冲突：

- `frontend/src/views/tw-stock-monitor/index.vue` 不再路径级一刀切失败；
- 该页面只有在当前 R15 readonly snapshot display diff 通过内容级审计时才放行；
- `scripts/run_daily_tw_stock_auto_update.py`、`scripts/run_extended_oos_formal_replay_matrix.py`、`backend_api_python`、`src/api` 仍保持路径级 hard fail；
- 总合同回归已恢复 `ok=true`；
- 前端静态检查、readonly snapshot validator、API tests、artifact contract tests 均通过。

## 2. R15R 审查对象

R15R handoff：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER15R_FRONTEND_SCOPE_AUDIT_REPAIR_REVIEW_HANDOFF_CN.md
```

R15R 执行报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER15R_FRONTEND_SCOPE_AUDIT_REPAIR_EXECUTION_REPORT_CN.md
```

修改文件：

```text
scripts/run_tw_modular_contract_regression.py
tests/unit/test_validate_tw_modular_artifact_contract.py
```

## 3. R15R 复核结果

### 3.1 Forbidden-scope audit 已细化

`forbidden_scope_audit.csv` 当前关键结果：

```text
frontend/src/views/tw-stock-monitor/index.vue:
  audit_mode=r15_readonly_frontend_content_audit
  changed_path_count=1
  status=pass
  authorized_readonly_frontend_diff=True
  required_missing=
  forbidden_matches=
  static_check_exists=True
  e2e_check_exists=True

scripts/run_daily_tw_stock_auto_update.py: pass
scripts/run_extended_oos_formal_replay_matrix.py: pass
backend_api_python: pass
src/api: pass
```

说明：R15 frontend diff 的放行不是路径级白名单，而是要求 readonly markers 存在、禁止模式不存在，并要求 R15 static / E2E 检查文件存在。

### 3.2 总合同回归恢复通过

复核命令：

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

结果：

```text
ok: true
signal_manifest_count: 5
strategy_dependency_count: 6
full_rank_artifact_count: 2
signal_validation_rows: 35
full_rank_validation_rows: 5
```

### 3.3 相关验证通过

复核命令：

```bash
python -m py_compile scripts/run_tw_modular_contract_regression.py
cd frontend && node tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：

```text
py_compile: pass
frontend static check: ok
readonly snapshot validator: ok=true
artifact contract tests: 14 passed
```

## 4. R15R 非阻塞建议

### P2：R15 readonly frontend forbidden patterns 可继续补强

当前 `R15_READONLY_FORBIDDEN_PATTERNS` 已覆盖：

```text
quick-trade
quickTrade
broker API path
R15 禁止中文交易文案
target-position / targetWeight / target_weight
provider publish / provider refresh
accepted latest
monitor helper
POST / PUT / PATCH / DELETE method
```

建议后续继续补充：

```text
target_position
target position
order_action
targetQty
target_quantity
submitOrder
placeOrder
connectBroker
```

当前 R15 diff 未出现这些字段，因此不阻塞 R15R 通过。但 R16/R17 前端或 daily 集成阶段应继续收紧。

## 5. R16 工作目标

R16 目标是把 readonly snapshot 生成接入 daily orchestrator 的末端，使每日数据更新完成后可以自动生成 readonly strategy snapshot。

R16 只能做：

```text
daily orchestrator integration for readonly snapshot publish
```

R16 不是 provider 治理重构，不是交易接入，不是模型重训，不是策略规则变更。

## 6. R16 允许改动范围

允许修改：

```text
scripts/run_daily_tw_stock_auto_update.py
```

允许新增：

```text
tests/unit/test_tw_daily_readonly_snapshot_integration.py
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER16_DAILY_READONLY_INTEGRATION_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER16_DAILY_READONLY_INTEGRATION_REVIEW_HANDOFF_CN.md
```

可选新增只读审计输出：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/daily_integration_audit.json
```

不得修改：

```text
frontend/
backend/app/routes/
backend/app/services/
backend_api_python/
src/api/
configs/tw_modular_registry.yaml
configs/tw_modular_replay_matrix.yaml
configs/strategy_dependencies/
```

除非执行报告明确说明只是测试 fixture 或文档，不得改 R13/R14/R15 已审查产物合同。

## 7. R16 必须实现的行为

### 7.1 开关控制

必须新增显式开关，默认建议关闭或 dry-run 安全模式，执行者需在报告中说明默认值：

```text
ENABLE_TW_READONLY_STRATEGY_SNAPSHOT_PUBLISH
```

或等价配置项。

要求：

- 开关关闭时不调用 readonly snapshot writer；
- 开关开启时只在 daily 数据更新流程完成后调用；
- dry-run / test 模式不得写 latest pointer，除非测试明确使用临时目录；
- 开关不得影响 provider accepted latest。

### 7.2 调用范围

R16 只能调用：

```text
scripts/publish_tw_modular_readonly_snapshot.py
scripts/validate_tw_modular_readonly_snapshot.py
```

或等价 Python 函数封装。

R16 不得调用：

```text
training scripts
score recompute scripts
replay recompute scripts
provider publish / refresh
accepted latest switch
broker / quick-trade / order
monitor scan / config / alerts write
```

### 7.3 失败隔离

R16 必须保证：

```text
readonly snapshot publish 失败不得导致 daily data update 主流程失败；
readonly snapshot validator 失败不得更新 readonly latest pointer；
readonly snapshot 失败必须记录 audit / warning；
daily 主流程状态必须区分 data update success 与 readonly snapshot publish failed；
```

建议返回结构：

```json
{
  "daily_update_ok": true,
  "readonly_snapshot": {
    "enabled": true,
    "attempted": true,
    "ok": true,
    "manifest": "data_tw/artifacts/publish/readonly_strategy_snapshot/YYYY-MM-DD/manifest.json",
    "latest_updated": true,
    "validator_ok": true,
    "error": ""
  }
}
```

### 7.4 Latest pointer 规则

R16 只允许更新：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

R16 不得修改：

```text
provider accepted latest
qlib accepted latest
trade target latest
任何 broker/order/position 状态
```

更新 latest 前必须满足：

```text
publish writer ok=true
readonly snapshot validator ok=true
checksum_ok=pass
latest_pointer_points_to_readonly_snapshot_only=pass
forbidden scope audit pass
```

## 8. R16 必须补充的测试

至少新增/覆盖：

1. 开关关闭时不调用 writer。
2. 开关开启且 writer/validator 成功时，daily 结果包含 readonly snapshot 成功状态。
3. writer 失败时 daily 主流程不失败，并记录 readonly snapshot failed。
4. validator 失败时不更新 readonly latest pointer。
5. forbidden static scan：daily 集成代码不得包含 broker / quick-trade / order / target_position / target_weight / accepted latest switch / provider publish。
6. 总合同回归 `python scripts/run_tw_modular_contract_regression.py --json` 必须仍为 `ok=true`。

## 9. R16 验证命令

执行者至少复跑：

```bash
python -m py_compile scripts/run_daily_tw_stock_auto_update.py scripts/publish_tw_modular_readonly_snapshot.py scripts/validate_tw_modular_readonly_snapshot.py
python -m pytest tests/unit/test_tw_daily_readonly_snapshot_integration.py
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
python scripts/run_tw_modular_contract_regression.py --json
PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py
cd frontend && node tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
```

如果执行者修改了前端或 API，则 R16 直接失败，除非有新的审查授权文档。

## 10. R16 禁止事项

R16 禁止：

- 训练；
- 调参；
- score recompute；
- replay recompute；
- 修改默认模型；
- 修改默认策略；
- 修改 R13 snapshot schema；
- 修改 R14 API contract；
- 修改 R15 frontend display；
- provider publish；
- provider refresh；
- provider accepted latest switch；
- monitor scan / config save / alerts write；
- broker / quick-trade / order；
- 读取真实券商持仓；
- 输出 target position / target weight；
- 将 readonly candidates 表述为交易建议。

## 11. R16 执行报告必须说明

执行报告必须包含：

```text
修改文件清单
开关名称和默认值
daily 调用点
readonly publish 调用命令/函数
失败隔离行为
latest pointer 更新条件
forbidden scope audit
验证命令与结果
是否触碰 provider accepted latest
是否触碰 broker/order/monitor
```

## 12. R16 审查交接必须输出

执行者完成后必须输出：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER16_DAILY_READONLY_INTEGRATION_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER16_DAILY_READONLY_INTEGRATION_REVIEW_HANDOFF_CN.md
```

审查者重点审查：

```text
daily integration 是否只调用 readonly publish
开关关闭是否无副作用
失败隔离是否有效
validator 失败是否阻止 latest 更新
是否未触碰 provider accepted latest
是否未触碰 broker/order/monitor
总合同回归是否 ok=true
```

## 13. 最终结论

R15R 通过。

可以进入 R16，但 R16 仅限 daily orchestrator integration for readonly snapshot publish，且必须满足开关控制、失败隔离、validator gate、只读 latest pointer 和交易链路零接触。
