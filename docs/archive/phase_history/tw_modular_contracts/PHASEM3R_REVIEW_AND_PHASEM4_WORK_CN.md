# Phase M3R 审查与 Phase M4 工作文档

生成日期：2026-06-17

## 1. 审查结论

Phase M3R 通过，允许进入 Phase M4。

M3R 已关闭 M3 审查指出的关键阻断项：既有两小时自动更新脚本中的 Yahoo/Scrapling refresh、provider publish、accepted latest 切换仍保留为 legacy 代码，但默认 M3 合同路径不可达；只有显式传入 `--enable-legacy-provider-publish` 或显式设置 `TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH=true` 时才会进入 legacy 分支。

本次审查未运行真实日更脚本，未触发 provider refresh / publish，未切 accepted latest，未执行 monitor / broker / quick-trade / order 行为。

## 2. 复核范围

审查输入：

```text
docs/tw_modular_contracts/PHASEM3R_DAILY_ORCHESTRATOR_GATE_REPAIR_EXECUTION_REPORT_CN.md
scripts/run_daily_tw_stock_auto_update.py
scripts/validate_tw_daily_orchestrator_m3.py
tests/unit/test_tw_modular_m3_daily_orchestrator.py
docs/tw_modular_contracts/PHASEM_MODULAR_FOUNDATION_BEFORE_NEW_MODEL_STRATEGY_WORK_CN.md
```

审查重点：

```text
M3 默认路径是否仍可达 provider refresh
M3 默认路径是否仍可达 provider publish
M3 默认路径是否仍可达 accepted latest
validator 是否把默认可达 forbidden path 作为错误
测试是否覆盖 unsafe 默认可达脚本
是否引入 broker/order/quick-trade/monitor write/Agent 扩权
```

## 3. 通过项

### 3.1 两小时脚本默认路径已加 gate

`scripts/run_daily_tw_stock_auto_update.py` 新增显式 legacy gate：

```text
scripts/run_daily_tw_stock_auto_update.py:391-396
--enable-legacy-provider-publish
default=env_flag("TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH", False)
```

脚本将默认模式记录为 readonly orchestrator：

```text
scripts/run_daily_tw_stock_auto_update.py:437-441
m3_contract_mode = readonly_orchestrator_default
legacy_provider_publish_enabled = false
legacy_provider_refresh_default_reachable = false
legacy_provider_publish_default_reachable = false
legacy_accepted_latest_default_reachable = false
```

默认未开启 legacy gate 时，只记录跳过 legacy provider 路径：

```text
scripts/run_daily_tw_stock_auto_update.py:503-506
if not args.skip_qlib and not args.enable_legacy_provider_publish:
    qlib_legacy_provider_path_skipped = True
```

真实 legacy refresh / publish / accepted latest 代码被包在显式 gate 中：

```text
scripts/run_daily_tw_stock_auto_update.py:508-611
if not args.skip_qlib and args.enable_legacy_provider_publish:
    run_option_c_yahoo_scrapling_refresh.py
    publish_option_c_yahoo_scrapling_refresh.py
    publish_accepted_latest(asof)
```

这关闭了 M3 阻断项中的“默认可达 provider publish / accepted latest”问题。

### 3.2 Validator 已从 warning-only 改为 gate 判定

`scripts/validate_tw_daily_orchestrator_m3.py` 已用 AST 检查 legacy gate：

```text
scripts/validate_tw_daily_orchestrator_m3.py:189-197
guarded_ranges()
```

并检查 refresh / publish / accepted latest call 是否都在 guard 范围内：

```text
scripts/validate_tw_daily_orchestrator_m3.py:241-258
provider_refresh_guarded
provider_publish_guarded
accepted_latest_call_guarded
```

默认可达路径现在会进入 errors：

```text
scripts/validate_tw_daily_orchestrator_m3.py:318-329
default_provider_refresh_reachable -> error
default_provider_publish_reachable -> error
default_accepted_latest_reachable -> error
legacy_provider_gate_missing/default_enabled/block_not_guarded -> error
```

warning 仍保留，但只表示 legacy 代码存在，不再代表默认路径放行。

### 3.3 测试已修正预期

`tests/unit/test_tw_modular_m3_daily_orchestrator.py` 已不再期待“legacy warning only 即通过”。

实际脚本审计现在要求：

```text
tests/unit/test_tw_modular_m3_daily_orchestrator.py:94-99
legacy_provider_gate_present is True
legacy_provider_gate_default_disabled is True
legacy_provider_block_guarded is True
default_provider_refresh_reachable is False
default_provider_publish_reachable is False
default_accepted_latest_reachable is False
```

同时新增 unsafe 默认可达脚本负例：

```text
tests/unit/test_tw_modular_m3_daily_orchestrator.py:104-128
default_provider_refresh_reachable
default_provider_publish_reachable
default_accepted_latest_reachable
legacy_provider_gate_missing
```

这修复了 M3 中“测试把阻断项固化为通过”的问题。

## 4. 复跑验证

已复跑：

```bash
python -m py_compile scripts/run_daily_tw_stock_auto_update.py scripts/validate_tw_daily_orchestrator_m3.py scripts/run_tw_modular_contract_regression.py tests/unit/test_tw_modular_m3_daily_orchestrator.py
python scripts/validate_tw_daily_orchestrator_m3.py --run-golden --json
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
python -m pytest tests/unit/test_tw_modular_m_contract_validators.py tests/unit/test_tw_modular_m2_registry_validator.py tests/unit/test_tw_modular_m3_daily_orchestrator.py -q
python scripts/run_tw_modular_contract_regression.py --json
```

结果：

```text
py_compile: pass
M3 golden validator: ok=true, sample_count=16
M3 script audit: ok=true
default_provider_refresh_reachable=false
default_provider_publish_reachable=false
default_accepted_latest_reachable=false
pytest: 13 passed
contract regression: ok=true
```

说明：两个 validator 命令和合同回归在普通 sandbox 下仍会被 `bwrap: loopback: Failed RTM_NEWADDR` 拦截，本次按只读/离线审查用途提权复跑通过。

## 5. 台股只读安全边界审查

### Findings

Critical：未发现默认 M3 路径可达 broker/order/quick-trade/target-position，也未发现默认 M3 路径可达 provider refresh / publish / accepted latest。

High：未发现 monitor config save、monitor scan、alert write 路径。

Medium：legacy provider refresh / publish / accepted latest 代码仍保留，并可由显式非默认 gate 开启。该项不阻塞 M3R，但 M4 不得使用或暴露该 gate；后续生产治理应另开独立 approval / contract registry 方案。

Low：当前 script audit 是静态 AST 近似检查，不是完整控制流证明。M4 前端阶段不得依赖它作为生产发布授权，只能把它作为 M3 默认 readonly path 的边界证明。

### Verdict

M3R 对 M3 blocker 的修复通过。默认 M3 合同路径满足 readonly orchestrator 边界。

## 6. 残余风险

1. Legacy gate 仍允许通过 CLI 或环境变量显式开启生产 refresh / publish / accepted latest。
2. `scripts/run_daily_tw_stock_auto_update.py` 仍包含 FinMind raw archive 更新路径；M3R 本轮重点是 qlib provider refresh / publish / accepted latest gate，后续如要把所有真实数据拉取也纳入 dry-run 合同，需要单独定义 DataSource refresh policy。
3. M3R 通过不等于 legacy provider publish / accepted latest 获得生产发布放行。
4. M4 不能把 legacy gate 暴露到前端、Agent 或任何自动 workflow。

## 7. Phase M4 工作范围

M4 目标：整理前端只读展示边界，让用户看到简单、准确、清晰、实用的 readonly 研究结果，同时保持 replay / strategy / Agent 全部只读。

M4 不只是把旧字段搬到新组件，也必须证明展示层级更适合用户阅读：主视图优先服务人工复盘，工程审计字段可追溯但默认不压过用户指标。

建议交付物：

```text
frontend readonly display component boundary
readonly replay / strategy snapshot 主视图字段整理
审计字段折叠或二级展示
primary fields vs audit fields mapping
frontend readonly display validator
Agent readonly context placeholder validator
legacy provider gate not exposed proof
E2E network audit: readonly workflow only GET
forbidden text/semantics scan
desktop/mobile screenshot paths, if frontend changed
执行报告：PHASEM4_FRONTEND_READONLY_DISPLAY_EXECUTION_REPORT_CN.md
```

建议组件边界：

```text
ReadonlyStrategySnapshotPanel.vue
ReadonlyReplayWindowPanel.vue
ReplayMetricSummary.vue
ReplayActionsTable.vue
ReplayAuditDetail.vue
ReadonlyModelStrategySelector.vue
```

主视图优先展示：

```text
模型
策略
合法窗口
净收益
最大回撤
交易次数
手续费/税费
覆盖状态
审计状态
```

审计详情可以折叠展示：

```text
source manifest
checksum
window index
schema version
validator result
run_id
```

如果 M4 修改真实前端组件，执行报告应提供以下证据路径：

```text
desktop screenshot
mobile or narrow viewport screenshot
readonly replay panel screenshot
audit detail collapsed screenshot
audit detail expanded screenshot
```

这些截图不是为了视觉包装，而是为了证明：

```text
页面没有被 source manifest / checksum / schema version / window index 等工程字段主导
用户第一眼能看到模型、策略、窗口、收益/回撤、交易次数、费用、覆盖状态、审计状态
审计字段默认弱化但仍可追溯
页面没有出现下单、目标仓位、自动交易、保证收益、胜率承诺等语义
```

## 8. M4 禁止事项

M4 不得做以下事项：

```text
不得训练新模型
不得新增正式策略
不得运行新收益结论
不得切默认策略
不得触发 provider refresh / publish
不得切 accepted latest
不得调用或暴露 --enable-legacy-provider-publish
不得在前端代码、文案、请求参数或 Agent context 中出现 TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH
不得修改 monitor config / scan / alerts
不得连接 broker、quick-trade 或 order
不得在前端本地 replay
不得在前端本地生成策略意图
不得绕过后端窗口校验
不得显示目标仓位、下单、一键交易、自动交易、保证收益、胜率承诺
不得调用 POST/PUT/PATCH/DELETE 的 replay/strategy 路由
不得修改前端嵌入 Agent prompt、tool、action 或行为
不得继续修改 scripts/run_daily_tw_stock_auto_update.py；如必须触碰日更脚本，应停止 M4 并另开 M3S/M3RR 修复
```

允许：

```text
整理普通 readonly 展示组件
调整只读字段层级和折叠审计详情
新增 GET-only readonly E2E/network audit
定义 Agent 只读上下文合同占位
检查 M4 前端改动没有误碰 Agent 区域
复跑 M3R script audit，但不扩大 legacy gate 语义
```

## 9. M4 验收门槛

M4 完成后必须证明：

```text
readonly 展示组件从大页面拆出或形成明确组件边界
页面主视图不被工程审计字段主导
审计字段可追溯但默认不压过用户指标
frontend build 通过
E2E/network audit 证明 replay/strategy readonly workflow 只有 GET
forbidden_request_count=0
forbidden text/semantics scan 通过
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops/provider publish/refresh/accepted latest request count=0
broker / quick-trade / orders request count=0
--enable-legacy-provider-publish 未出现在前端代码、文案、请求参数或 Agent context
TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH 未出现在前端代码、文案、请求参数或 Agent context
Agent prompt/tool/action 未改，或仅完成合同占位并有结构化证明
M3R script audit 仍通过
```

M4 执行报告必须新增一节：

```text
Frontend user-first acceptance and safety evidence
```

该节至少列出：

```text
component boundary summary
primary fields vs audit fields mapping
desktop/mobile screenshot paths, if frontend changed
readonly replay panel screenshot paths, if frontend changed
audit detail collapsed / expanded screenshot paths, if frontend changed
GET-only network audit artifact
forbidden request count
forbidden text/semantics scan result
legacy provider gate not exposed proof
Agent untouched or placeholder-only proof
frontend build result
E2E result
```

Agent 未改证明必须结构化，不能只写一句“未修改”。至少包含：

```text
Agent prompt 文件或前端 Agent 区域 git diff 摘要
Agent tool/action registry 未变更证明
Agent panel static scan
forbidden tool/action/prompt expansion fixture 通过，若已有对应 validator
```

如果 M4 完全不触碰 Agent，执行报告应明确：

```text
Agent implementation untouched
Agent contract placeholder only
```

建议 M4 审查命令至少包括：

```bash
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
python scripts/run_tw_modular_contract_regression.py --json
corepack pnpm build
npx playwright test <M4 readonly e2e>
```

如果 M4 不涉及前端工程实际构建，应在执行报告中说明原因，并至少提供静态 validator 与 network audit artifact。M4 不得以 M3R 的 legacy gate 存在为理由新增任何前端或 Agent 控制入口。
