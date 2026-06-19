# Phase R15 Frontend Readonly Display 执行报告

生成日期：2026-06-16

## 1. 执行依据

用户请求引用：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER14_REVIEW_AND_R15_WORK_CN.md
```

本次执行前检查发现该文件当前不存在。R15 按以下已存在总路线文档执行：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER12_R16_READONLY_PRODUCTIZATION_FULL_CHAIN_WORK_CN.md
```

对应 R15 目标：在台股前端页面增加 readonly strategy snapshot 展示，只读显示 snapshot date、model/rule、top candidates、exit candidates、source manifest、quality/audit status 和 readonly safety labels；不得新增交易按钮、quick-trade、broker、monitor 写入、provider publish/accepted latest 切换或 snapshot 写入。

## 2. 本阶段改动

### 2.1 前端 API wrapper

新增：

```text
frontend/src/api/tw-stock.js
```

新增函数：

```text
getTwStockReadonlyStrategySnapshot()
```

行为：

```text
GET /api/tw-stock/readonly-strategy-snapshot
```

未新增 POST/PUT/PATCH/DELETE。

### 2.2 台股页面只读策略快照面板

修改：

```text
frontend/src/views/tw-stock-monitor/index.vue
```

新增面板：

```text
data-testid="readonly-strategy-snapshot-panel"
```

展示内容：

- `策略快照`
- `只读候选`
- `研究排名`
- `调入候选`
- `调出观察`
- `数据日期`
- `模型来源`
- `审计状态`
- snapshot `model_id` / `base_model_id`
- snapshot `strategy_rule` / `ranking_source`
- source manifest
- validation/checksum status
- readonly flags

新增加载方法：

```text
loadReadonlyStrategySnapshot()
```

该方法只调用 `getTwStockReadonlyStrategySnapshot()`，不调用 monitor scan/config save/alerts write/provider publish/accepted latest/quick-trade/broker/order 路径。

### 2.3 前端静态安全检查

新增：

```text
frontend/tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
```

检查内容：

- API wrapper 使用 GET；
- endpoint 为 `/readonly-strategy-snapshot`；
- 页面包含 R15 必需标签；
- 新增面板不含禁用文案：`下单`、`买入指令`、`卖出指令`、`目标仓位`、`自动交易`、`一键交易`、`券商同步`、`保证收益`、`胜率承诺`；
- loader 不调用非 snapshot 动作接口；
- 新增面板/loader 不含 provider publish / accepted latest / monitor write hints。

### 2.4 前端只读 E2E

新增：

```text
frontend/tests/e2e/tw-stock-readonly-strategy-snapshot-readonly.mjs
```

覆盖：

- 打开 `/tw-stock-monitor`；
- mock readonly strategy snapshot GET；
- 验证新增 panel 渲染候选、观察项、模型来源、审计状态；
- 验证新增 panel 不含 R15 禁用文案；
- 验证没有 quick-trade/broker/monitor write/provider publish/accepted latest/snapshot write 请求；
- 验证无 console error / page error。

## 3. 安全边界

本阶段未执行：

- 不训练；
- 不调参；
- 不重算 replay；
- 不修改默认策略；
- 不发布 provider；
- 不切换 provider accepted latest；
- 不修改 daily orchestrator；
- 不新增 broker/order/quick-trade；
- 不新增 target position / target weight；
- 不写 snapshot artifact。

新增前端面板仅消费 R14 API 输出的 readonly snapshot。

## 4. 验证结果

### 4.1 前端静态检查

命令：

```text
node tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
```

工作目录：

```text
frontend
```

结果：

```text
[readonly-strategy-snapshot-check] ok
```

### 4.2 前端构建

命令：

```text
corepack pnpm build
```

工作目录：

```text
frontend
```

结果：

```text
vite build passed
```

### 4.3 R15 只读 E2E

构建后使用静态服务运行：

```text
npx http-server dist -a 127.0.0.1 -p 8061
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8061 node tests/e2e/tw-stock-readonly-strategy-snapshot-readonly.mjs
```

结果：

```text
tw-stock readonly strategy snapshot e2e passed
```

说明：Vite preview 因系统 watcher 数量上限 `ENOSPC` 退出，改用 build 后的静态 `dist` 服务验证页面产物。静态服务验证后已停止。

### 4.4 后端/API 回归

命令：

```text
python -m py_compile backend/app/services/readonly_strategy_snapshot.py backend/app/routes/readonly_strategy_snapshot.py scripts/validate_tw_modular_readonly_snapshot.py
PYTHONPATH=backend python -m pytest backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

结果：

```text
py_compile passed
4 passed
readonly snapshot validator ok=true
```

### 4.5 总合同回归说明

命令：

```text
python scripts/run_tw_modular_contract_regression.py --json
```

结果：

```text
ok=false
```

定位：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/forbidden_scope_audit.csv
```

失败项：

```text
scope=frontend/src/views/tw-stock-monitor/index.vue
changed_path_count=1
status=fail
```

解释：该总回归的旧版 forbidden-scope audit 将 `frontend/src/views/tw-stock-monitor/index.vue` 的任何 tracked diff 视为失败；R15 的目标正是修改该页面增加只读展示。因此这是 R15 阶段边界与旧审计规则冲突，不代表新增 snapshot API、artifact contract 或前端只读 E2E 失败。

其他子项检查显示：

- signal artifact validation 全部 True 或适用性 skipped；
- full-rank artifact validation 全部 True；
- manifest coverage audit pass；
- readonly snapshot validator pass。

建议 R16 前由审查者决定：是否更新总合同回归的 forbidden-scope audit，使 R15/R16 已授权的前端只读展示改动不被误判为失败。

## 5. R15 Gate 对照

| Gate | 结果 | 证据 |
| --- | --- | --- |
| frontend_readonly_e2e_pass | pass | `tw-stock readonly strategy snapshot e2e passed` |
| network_no_forbidden_write | pass | E2E forbidden request count = 0；静态检查 loader/API 无写方法 |
| console_no_error | pass | E2E consoleErrors/pageErrors = 0 |
| forbidden_text_scan_pass | pass | `tw-stock-readonly-strategy-snapshot-check.mjs` |

## 6. 产物清单

新增/修改文件：

```text
frontend/src/api/tw-stock.js
frontend/src/views/tw-stock-monitor/index.vue
frontend/tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
frontend/tests/e2e/tw-stock-readonly-strategy-snapshot-readonly.mjs
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER15_FRONTEND_READONLY_DISPLAY_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER15_FRONTEND_READONLY_DISPLAY_REVIEW_HANDOFF_CN.md
```

## 7. 结论

R15 前端只读展示已完成。新增页面能力只读消费 R14 API，不写交易、monitor、provider、accepted latest 或 snapshot 状态。R15 自身 gate 通过。

总合同回归当前因旧 forbidden-scope audit 对 `frontend/src/views/tw-stock-monitor/index.vue` 的任何 diff 失败，需要在 R16 前审查是否修订审计范围。
