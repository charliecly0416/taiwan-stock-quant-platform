# Phase R15 审查与 R16 前置建议

生成日期：2026-06-16

## 1. 审查结论

R15 前端只读展示自身审查通过，但不建议直接进入 R16。

原因不是 R15 前端新增能力越界，而是总合同回归 `run_tw_modular_contract_regression.py` 仍把 `frontend/src/views/tw-stock-monitor/index.vue` 的任何 tracked diff 判为 forbidden scope。R15 本身授权修改该页面增加 readonly snapshot 展示，因此当前回归规则与 R15 授权范围冲突。

建议先执行一个 R15R / R16-prep 小修复：修订总合同回归 forbidden-scope audit，让已授权的 readonly frontend display diff 进入更细粒度检查，而不是按路径一刀切失败。修复后再进入 R16 daily orchestrator integration。

## 2. 审查对象

R15 handoff：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER15_FRONTEND_READONLY_DISPLAY_REVIEW_HANDOFF_CN.md
```

R15 执行报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER15_FRONTEND_READONLY_DISPLAY_EXECUTION_REPORT_CN.md
```

前端改动：

```text
frontend/src/api/tw-stock.js
frontend/src/views/tw-stock-monitor/index.vue
frontend/tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
frontend/tests/e2e/tw-stock-readonly-strategy-snapshot-readonly.mjs
```

## 3. 复核结果

### 3.1 Frontend API wrapper 只读

新增函数：

```text
getTwStockReadonlyStrategySnapshot()
```

调用：

```text
GET /api/tw-stock/readonly-strategy-snapshot
```

未新增 `POST` / `PUT` / `PATCH` / `DELETE`。

### 3.2 新增面板只读展示

新增面板：

```text
data-testid="readonly-strategy-snapshot-panel"
```

展示内容包含：

```text
策略快照
只读候选
研究排名
调入候选
调出观察
数据日期
模型来源
审计状态
source manifest
validation
checksum
readonly flags
```

新增刷新按钮只调用：

```text
loadReadonlyStrategySnapshot()
  -> getTwStockReadonlyStrategySnapshot()
```

未发现新增交易按钮、quick-trade、broker、monitor scan/config/alerts 写入、provider publish、accepted latest 切换或 snapshot 写入。

### 3.3 文案边界通过

新增 readonly panel 未包含 R15 禁止文案：

```text
下单
买入指令
卖出指令
目标仓位
自动交易
一键交易
券商同步
保证收益
胜率承诺
```

页面其他历史模块中存在 `broker`、`orders_enabled=false`、`connects_to_broker=false` 等只读/模拟说明，不属于 R15 新增面板的 actionable 交易语义，不作为 R15 阻塞。

### 3.4 前端静态检查通过

复核命令：

```bash
cd frontend
node tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
```

结果：

```text
[readonly-strategy-snapshot-check] ok
```

### 3.5 前端构建通过

复核命令：

```bash
cd frontend
corepack pnpm build
```

结果：

```text
vite build passed
```

说明：命令输出中存在 `/bin/sh: 2: source: not found`，但 build 最终退出码为 0，不影响 R15 判断。

### 3.6 后端/API 与 snapshot validator 仍通过

复核命令：

```bash
PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py
```

结果：

```text
4 passed
```

复核命令：

```bash
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

结果：

```text
ok: true
checksum_ok: pass
latest_pointer_points_to_readonly_snapshot_only: pass
no_unsafe_field_names: pass
```

复核命令：

```bash
python -m pytest tests/unit/test_validate_tw_modular_artifact_contract.py
```

结果：

```text
13 passed
```

## 4. 总合同回归冲突

复核命令：

```bash
python scripts/run_tw_modular_contract_regression.py --json
```

结果：

```text
ok: false
```

失败文件：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/forbidden_scope_audit.csv
```

失败项：

```text
scope=frontend/src/views/tw-stock-monitor/index.vue
changed_path_count=1
status=fail
changed_paths=frontend/src/views/tw-stock-monitor/index.vue
```

其他 forbidden scope：

```text
scripts/run_daily_tw_stock_auto_update.py: pass
scripts/run_extended_oos_formal_replay_matrix.py: pass
backend_api_python: pass
src/api: pass
```

判断：该失败是旧总回归审计规则与 R15 授权范围冲突。它仍然重要，因为 R16 前必须让总合同回归重新变绿，否则 daily integration 阶段无法区分真实越界和已授权前端只读 diff。

## 5. Findings

### P1：R16 前必须修订总合同回归 forbidden-scope audit

当前总合同回归对 `frontend/src/views/tw-stock-monitor/index.vue` 采用路径级禁止，无法容纳 R15 已授权的 readonly display。

建议新增 R15R / R16-prep：

```text
允许 frontend/src/views/tw-stock-monitor/index.vue 中 readonly-strategy-snapshot-panel / loadReadonlyStrategySnapshot / getTwStockReadonlyStrategySnapshot 相关 diff；
继续禁止该页面新增 quick-trade / broker / order / target_position / target_weight / provider publish / accepted latest / monitor write；
继续要求 frontend readonly static scan / E2E network audit 通过；
总合同回归最终 ok=true。
```

### P2：R15 E2E 依赖 mock，R16 前应保留真实 API smoke

R15 E2E 使用 mock readonly strategy snapshot GET，适合验证前端行为和 forbidden network writes。

R16 前建议增加或保留一个真实后端 API smoke：

```text
frontend 页面 -> R14 API -> R13 latest snapshot
只允许 GET
forbidden write count = 0
console error = 0
```

这不是 R15 阻塞，但进入 daily integration 前会降低集成风险。

## 6. R16 前置工作建议

建议下一步不是直接 R16，而是先让执行者完成 R15R / R16-prep：

1. 修订 `scripts/run_tw_modular_contract_regression.py` 的 forbidden-scope audit。
2. 对 R15 授权前端 diff 做内容级白名单，而不是路径级失败。
3. 保持以下写路径仍为硬禁止：

```text
POST /api/tw-stock/monitor/config
POST /api/tw-stock/monitor/scan
POST /api/tw-stock/monitor/scan-all
POST /api/tw-stock/monitor/alerts
PUT/PATCH/DELETE /api/tw-stock/monitor/alerts/*
POST /api/tw-stock/quant/ops/** publish/refresh/provider/accepted
POST /api/quick-trade/**
/api/broker/**
order
target_position
target_weight
```

4. 复跑并要求：

```text
node tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
corepack pnpm build
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py
```

5. 输出：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER15R_FRONTEND_SCOPE_AUDIT_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER15R_FRONTEND_SCOPE_AUDIT_REPAIR_REVIEW_HANDOFF_CN.md
```

## 7. R16 边界提醒

R16 只能做 daily orchestrator integration，让每日流程在数据更新完成后生成 readonly snapshot。

R16 仍不得：

- provider publish；
- provider accepted latest switch；
- broker / quick-trade / order；
- monitor scan / config save / alerts write；
- 输出 target position / target weight；
- 改默认模型或策略；
- 训练、调参、score recompute、replay recompute。

R16 必须保证失败隔离：

```text
readonly snapshot 生成失败不得影响 daily data update 主流程；
不得覆盖 R13 latest unless validator pass；
必须有开关禁用 readonly snapshot publish；
必须输出清晰 audit / manifest / checksum。
```

## 8. 最终结论

R15 前端只读展示通过。

但在总合同回归恢复 `ok=true` 前，不建议进入 R16。建议先做 R15R / R16-prep，修复 forbidden-scope audit 与 R15 授权前端只读展示的冲突。
