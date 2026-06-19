# Phase M4 Frontend Readonly Display 执行报告

生成日期：2026-06-17

## 1. 执行结论

Phase M4 已完成前端只读展示边界整理，并通过静态 validator、组件级检查、生产构建、只读 E2E 和 M3R 日更脚本审计复跑。

本阶段只整理 readonly strategy snapshot / readonly replay window 的展示层级：主视图优先展示人工复盘需要的模型、策略、窗口、收益/回撤、交易次数、费用、覆盖状态和审计状态；工程追溯字段进入默认折叠的审计详情。未训练新模型，未新增正式策略，未运行新收益结论，未切默认策略，未触发 provider refresh / publish，未切 accepted latest，未修改 monitor config / scan / alerts，未连接 broker、quick-trade 或 order。

## 2. 改动范围

前端组件边界：

```text
frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue
frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue
frontend/src/views/tw-stock-monitor/components/ReplayAuditDetail.vue
frontend/src/views/tw-stock-monitor/index.vue
```

验证与回归：

```text
scripts/validate_tw_frontend_readonly_m4.py
scripts/run_tw_modular_contract_regression.py
frontend/tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
frontend/tests/unit/tw-stock-readonly-replay-window-check.mjs
frontend/tests/e2e/tw-stock-readonly-strategy-snapshot-readonly.mjs
frontend/tests/e2e/tw-stock-readonly-replay-window-readonly.mjs
```

M4 未继续修改 `scripts/run_daily_tw_stock_auto_update.py`，也未修改 Agent prompt/tool/action 行为。

## 3. Frontend user-first acceptance and safety evidence

### 3.1 Component boundary summary

| Component | 职责 | 证据 |
| --- | --- | --- |
| `ReadonlyStrategySnapshotPanel.vue` | 展示只读策略快照主指标，并引用折叠审计详情 | validator 记录 `exists=true`、`has_testid=true`、`has_audit_detail=true` |
| `ReadonlyReplayWindowPanel.vue` | 展示只读 replay window 主指标、窗口选择和回放摘要，并引用折叠审计详情 | validator 记录 `exists=true`、`has_testid=true`、`has_audit_detail=true` |
| `ReplayAuditDetail.vue` | 统一承载 source manifest、checksum、schema version、window index、run_id 等工程追溯字段 | validator 记录 `exists=true`、`has_testid=true` |

### 3.2 Primary fields vs audit fields mapping

主视图字段：

```text
model
strategy
legal_window
net_return
max_drawdown
action_count
fee_tax
coverage_status
audit_status
```

审计详情字段：

```text
source_manifest
checksum
schema_version
window_index
run_id
```

验证结果：`scripts/validate_tw_frontend_readonly_m4.py --json` 输出 `ok=true`，并确认 `source manifest` 不早于 replay 主指标展示，页面第一层不被 manifest/checksum/schema/window index 主导。

### 3.3 Screenshot evidence

截图产物位于：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/m4_frontend_readonly/readonly_strategy_snapshot_desktop_collapsed.png
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/m4_frontend_readonly/readonly_strategy_snapshot_desktop_expanded.png
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/m4_frontend_readonly/readonly_strategy_snapshot_mobile.png
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/m4_frontend_readonly/readonly_replay_window_desktop_collapsed.png
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/m4_frontend_readonly/readonly_replay_window_desktop_expanded.png
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/m4_frontend_readonly/readonly_replay_window_mobile.png
```

说明：Vite dev/preview server 在当前环境触发 ENOSPC watcher 限制，因此截图由 `corepack pnpm build` 后的生产构建通过 `python -m http.server` 静态服务生成。E2E 中 API 请求由 Playwright route mock，只读页面渲染、折叠/展开和移动端布局均已覆盖。

### 3.4 GET-only network audit artifact

GET-only 审计产物：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/m4_frontend_readonly_validation.json
```

关键结果：

```text
readonly_workflow_only_get=true
forbidden_request_count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_provider_publish_refresh_accepted_latest_request_count=0
broker_quick_trade_orders_request_count=0
```

### 3.5 Forbidden text and semantics scan

M4 validator 对 readonly workflow 组件和三类 readonly API wrapper 扫描以下禁止语义：

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

结果：全部命中数为 0，`forbidden text/semantics scan` 通过。

### 3.6 Legacy provider gate not exposed proof

M4 validator 对前端 readonly workflow 和 Agent surface 扫描 legacy gate token：

```text
--enable-legacy-provider-publish: 0
TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH: 0
```

结果：`legacy_provider_gate_not_exposed=true`。M4 没有把 M3R 的 legacy provider publish / accepted latest gate 暴露到前端、文案、请求参数或 Agent context。

### 3.7 Agent untouched or placeholder-only proof

Agent 边界审计结果：

```text
agent_related_changed_paths=[]
agent_marker_presence.tw-stock-agent-panel=true
agent_marker_presence.agentSuggestedQuestions=true
agent_marker_presence.chatTwStockAgent=true
agent_marker_presence.agentSkills=true
agent_forbidden_surface_hits=0
agent_implementation_untouched=true
agent_contract_placeholder_only=true
```

结论：M4 未扩展 Agent prompt/tool/action，未新增 broker/order/quick-trade/provider publish/accepted latest/target position/target weight 能力。Agent 在 M0-M6 范围内仍保持 placeholder-only / readonly context 边界。

### 3.8 Build and E2E result

前端构建：

```text
corepack pnpm build: pass
```

只读 E2E：

```text
tw-stock readonly replay window e2e passed
tw-stock readonly strategy snapshot e2e passed
```

截图和 E2E 均来自生产构建静态服务。静态服务对真实 API 返回 404 的日志由 Playwright route mock 覆盖，不影响只读前端边界验证。

## 4. 回归结果

已复跑：

```bash
python -m py_compile scripts/validate_tw_frontend_readonly_m4.py scripts/run_tw_modular_contract_regression.py
python scripts/validate_tw_frontend_readonly_m4.py --json
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
python scripts/run_tw_modular_contract_regression.py --json
node tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
node tests/unit/tw-stock-readonly-replay-window-check.mjs
corepack pnpm build
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:5173 node tests/e2e/tw-stock-readonly-replay-window-readonly.mjs
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:5173 node tests/e2e/tw-stock-readonly-strategy-snapshot-readonly.mjs
```

关键结果：

```text
M4 validator: ok=true, schema_version=m4.0.0
contract regression: ok=true
m3_daily_script_audit_status=passed
m4_frontend_readonly_status=passed
m4_forbidden_request_count=0
m4_legacy_provider_gate_not_exposed=true
frontend unit checks: pass
frontend build: pass
readonly E2E: pass
```

说明：部分 Python / Node 命令在普通 sandbox 下会被 `bwrap: loopback: Failed RTM_NEWADDR` 拦截，本轮按离线验证用途提权复跑通过。

## 5. 安全边界

M4 明确未执行：

```text
provider refresh
provider publish
accepted latest switch
monitor config save
monitor scan
alerts write
broker
quick-trade
orders
training
new replay conclusion
default strategy switch
Agent prompt/tool/action expansion
```

M4 只证明前端 readonly display 层级和请求边界，不构成任何生产发布、默认策略切换、交易执行或收益承诺授权。

## 6. 残余风险

1. `scripts/run_daily_tw_stock_auto_update.py` 仍保留显式 legacy provider publish gate；M4 证明前端和 Agent 未暴露该 gate，但不改变 legacy gate 本身的治理状态。
2. M4 validator 是静态扫描加 E2E mock network 审计，不是浏览器运行时对所有历史页面路径的完整证明。
3. 当前截图使用生产构建静态服务生成；真实 API 集成环境仍需在部署验收中复跑只读 E2E。

## 7. 结论

Phase M4 完成。Readonly strategy snapshot 与 readonly replay window 已形成前端组件边界，主视图优先服务人工复盘，审计字段默认折叠但可追溯；readonly workflow 保持 GET-only，禁止请求和禁止语义命中数为 0；legacy provider gate 未暴露；Agent 未扩权；M3R script audit 仍通过。
