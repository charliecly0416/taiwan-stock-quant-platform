# 产品、工程与稳定运维审查

审查日期：2026-09-18。状态：限定修复、回归、独立交叉审查、备份恢复演练和部署验收完成，条件通过。

## 总体结论

模型开发可以告一段落，冻结当前模型与准入门槛，转入研究产品运维和工程收尾。项目具有实际研究价值，可以作为面试项目展示：候选、来源日期、模型/策略比较、历史模拟、模拟账户和解释助手形成了可用流程。

本轮结论是“Model A 研究产品及当前运行实例可转稳定维护”，不是“已证明长期无人值守生产稳定”。合同层具有扩展基础，但代码职责迁移尚未完成，不能称整个后端已充分解耦。HTTP readiness、只读部署验收、备份与隔离恢复、日志轮转均已有真实证据；B19 当前精确 v2 实现仍缺下一次合法 full cron 的自动证据，收益结算也尚未闭环。

仓库物理瘦身已分阶段完成：删除 1376 个无当前引用的历史文档、157 个退出运行/测试闭包的历史实验脚本，以及第一轮 90 个、最终轮 18 个可再生缓存目录。所有删除均先建立仓库外备份并通过隔离恢复哈希验证；3 个触发凭据模式门禁的缓存目录保守留在本机，未进入备份。前后端仍在 import/router 闭包内的继承模块继续保留。详见 `docs/ops/REPOSITORY_SLIMMING_REPORT_CN.md`。

## 目标与边界

目标用户是需要每日复盘、检查候选与比较研究结果的台股研究者。核心问题依次是：数据是哪天的、是否可信、哪些标的值得研究、为何排序、模型/策略如何比较、模拟账户状态是否可追溯。

当前产品是只读研究工作台与模拟账户，不是自动交易系统。Model A 是唯一 active baseline；B19R2R 是冻结的研究 challenger。模型开发可以暂停，但影子采集、后续结算和运行可靠性仍需验证。

本轮不训练或调参，不改变 baseline/默认策略，不执行 provider/latest 发布、交易或模拟账户变更。运行检查以只读 API、离线测试与 fixture Playwright 为主；B19 收尾仅抓取一次受控 TWII 输入并保持 `no_apply`、`no_latest_write`、`no_provider_write`。

## 统筹任务记录

| 范围 | 执行/检查责任 | 验收要求 | 状态 |
| --- | --- | --- | --- |
| 产品体验 | product_ux_audit | 核心结果不依赖维护配置；状态失败隔离；桌面/平板/手机和网络审计 | 通过，fixture 验收 |
| 运维 | operations_audit | 同日 A 已接受后的 full/B19 失败不污染 A pending，不重复发布 | 通过；scheduled BLOCKED，人工两阶段 READY |
| 后端可靠性 | backend_architecture_audit | Agent 路径不依赖启动 cwd；生产禁止历史 artifact override；输入错误返回可理解状态 | 通过，本机回归 |
| 启动安全、文档与 CI | 统筹 | CLI/WSGI 同等密钥校验；交易 worker 默认关闭；入口与实际 baseline 一致 | 本机通过，云端 CI 未运行 |
| 独立复核 | 执行者交叉审查 | 复核真实改动、故障场景和保护指针，记录证据限度 | 通过，无当前范围阻断项 |

## 已发现的问题

1. 研究模式继承的后台订单/持仓/策略恢复默认开启，与产品身份不符。CLI 才校验 SECRET_KEY，WSGI 可使用公开示例签名密钥。已改为启动前统一校验，默认关闭相关后台任务。
2. 从 `backend/` 启动时 Agent 默认 artifact 路径和 validator source path 依赖 cwd，可能误报缺失。
3. 前端配置读取失败会阻断核心只读刷新；一个产品状态接口失败可清空已经成功加载的策略上下文。
4. Model A 同日已接受后，full 正交 capture 不完整仍可设置主链 pending；其 universe gate 还可能在 B19 排除 TW7769 之前阻断。
5. 用户入口文档把旧 LTR 写成默认候选，且把源码默认和本机授权的发布配置混淆。已修正文档。
6. 后端 CI 仅手动触发。已补 push/PR 触发和研究启动安全检查；云端 CI 尚未运行，不能凭本机测试宣称云端通过。
7. live/installed cron 与历史快照曾含明文 `DATABASE_URL`，旧 artifact 备份因此带入连接凭据。已轮换数据库密码，移除 live/installed 及 28 份历史 cron 快照中的连接串，改由 `scripts/run_daily_env.sh` 从 0600 的 `backend/.env` 加载；备份工具现在扫描并拒绝带认证信息的 PostgreSQL URL。含旧凭据的备份已删除。

初读提出“already_up_to_date 会跳过标准 full 任务”，进一步核对已有 `should_run_full_orthogonal_refresh` 后确认不成立，未按这个错误诊断修改代码。

修复后的 full 影子分支只复用同日、同 logical acquisition run 的 A 原始不可变 publish snapshot，不回退到可变 provider。日更/full job ID 不同不意味着 logical run 不同；本轮没有放宽 B runner 的来源绑定要求。strict 或保护路径漂移仍阻断，full 覆盖失败仍保留真实 FAIL。

另补齐比较接口边界登记、错误默认模型配置的生产准入过滤、`maxItems` 参数校验、必要的 PyYAML/jsonschema 运行依赖及旧蓝图测试注册。Agent artifactDir override 仅限 TESTING。

产品默认收起技术来源明细及高级研究/维护区域，保留概览、比较、候选、历史模拟、模拟账户和 Agent。初始核心 context 请求由重复加载改为一次；状态读取部分失败保留已成功的数据，并支持重新刷新恢复。运维状态保留最近 full B19 结果，后续 daily no-op 不会遮蔽它。

运维历史扫描限制为最近 168 个候选，优先 scheduler run 时间；cron.log 仅尾读最多 64KB。真实本机只读聚合一次约 0.547 秒，该数值不是并发性能或线上 SLA。

## 架构判断

标准 artifact 合同把数据、特征、模型、策略、执行回放和展示隔开，是可扩展的基础。新增模型应输出 ModelSignal，新增策略声明 dependency，API 消费验证后的 artifact，故障不得反向改模型或 baseline。

这不等于整个代码库已经充分解耦。日更入口仍约 8,000 行，主 Vue 视图约 7,500 行；部分 route 拆分仍委托旧聚合模块。它们是渐进迁移的边界，尚未完成职责迁移。后续应按行为和合同拆分、保留回归与回滚，不以文件数量证明架构质量。

## 证据限度与发布要求

2026-09-18 的真实 full cron 已观察到 B19 `BLOCKED`：旧 TWII 抓取实现错误地要求同日 Yahoo 日线必须是不完整 stub。修复后，首次受控重试又揭示 cutoff 在内部抓取前封存的编排错误；第二阶段复用同一不可变 TWII 证据并在抓取后封存 cutoff，成功产生 `READY_RESEARCH_SHADOW`、50 行信号和 prospective 事件，五个保护指针保持不变。

正式自动 wrapper 已改为“预抓 TWII -> 封存微秒精度 cutoff -> 显式传入 scorer”，v2 capture manifest 同时绑定 schema、source ID、实现路径与 SHA256。该实现通过独立审查，但发生在本次真实受控 READY 之后，因此仍需下一次合法 full cron 留下当前精确 v2 的自动 READY/BLOCKED 证据。状态 API 继续显示最近一次定时 full job 为 BLOCKED，不把手动重试冒充自动成功。prospective 事件仍为 `settlement_required=true`，不代表每日收益结算和准入评估已闭环。

运行数据、冻结模型和部分 golden/实验材料在 ignored 目录中。面试展示必须明确哪些能力可由 fresh checkout 复现、哪些需要预先安装资产；不要把本机文件存在等同于发布包完整。

## 验证与独立审查

- 后端、ARCH 边界、B19、启动安全及运维相关综合回归：222 passed；两条既有 `datetime.utcnow` 弃用警告。
- `PYTHONPATH=.:backend python backend/scripts/verify_tw_stock_research_stack.py`：89 passed。与综合回归有交集，不能相加作为独立测试总数。
- `python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json`：PASS，仍提示显式 gate 下存在 legacy 发布路径。
- 前端 9 项静态/行为检查通过，包括 `frontend/tests/unit/tw-stock-readonly-load-isolation.mjs` 的并发合并、失败隔离与恢复检查。
- 最后一次 `corepack pnpm build` 通过，2338 模块、24.60 秒；构建仍存在较大的图表/UI vendor chunks，未据此证明首屏性能。最终合并定向回归为 129 passed；限定改动范围及全仓 `git diff --check` 通过。
- Playwright 正常与故障场景均通过：1440×980、1024×768、390×900，无水平/按钮/卡片溢出；技术明细默认收起；核心 context 初始请求严格一次。
- 正常场景失败响应 0；故障场景仅有主动注入的 config 与 productization-status 两个 503，核心日期、名单和比较仍显示。两场景禁止请求 0、页面异常 0。原始 console/network 审计保留注入错误。
- 最终稳定运维、readiness、启动安全、部署验收与 B19 定向回归分别通过；自动 TWII 时序修复相关测试 90 passed，独立架构复核扩展集 125 passed，M3 validator PASS。测试集有交集，不相加宣称总数。
- 最终收尾定向回归 123 passed；其中 ARCH-1 validator 已按 ModelSignal 每行 `available_at` 与 manifest `available_at_policy` 的实际合同修复，34 项检查全部通过。稳定运维与 ARCH-1 单独复核为 38 passed。
- 仓库物理瘦身后的扩大定向回归为 328 passed，研究栈为 89 passed；ARCH-1 34 项、M3、模块合同回归、2338 模块前端生产构建和 5000 live 只读部署验收全部通过。最终 runtime manifest 为 3917 条记录，validator PASS。
- 5000 正式实例在凭据轮换后再次验收：七个只读端点均为 HTTP 200，日期均为 2026-09-18，运行边界为 `readonly_research`，12 个写方法门禁均为 405。最终证据：`tmp/deployment_acceptance_live_5000_final.json`。
- 替代备份 `/home/chuliyang/backups/tw-stock/tw_stock_ops_20260918T170538Z` 共 4816 个 artifact 文件，`contains_plaintext_credentials=false`；归档 SHA/大小、`pg_restore --list` 通过，并在临时 PostgreSQL 16 集群完成 57 表隔离恢复。新恢复证据绑定了 manifest 与实际 dump SHA256：`tmp/isolated_database_restore_drill_after_credential_rotation.json`。

截图与 JSON：`tmp/product_audit_workbench_fixed/`、`tmp/product_audit_workbench_fault/`。这些是 fixture 验收，页面日期 2026-06-18，不是实时市场数据证明。超长 comparison 元素截图中固定导航出现在中部属于合成截图伪影；真实锚点留有导航偏移。

backend_architecture_audit 独立复核 B19 来源绑定、失败隔离和自动链编排；operations_audit 独立复核凭据、cron、部署、备份恢复和模型准入边界；product_ux_audit 独立复核产品体验、Agent loader、TESTING 限制与输入校验。三者均确认当前范围无稳定运维阻断项。

## 实际状态与后续收尾

本轮真实只读观察：A、readonly snapshot、Agent prompt 日期均对齐 2026-09-18，无 pending，信号 `accepted_validated=true`、`stale=false`。5000 已由旧 Flask 开发进程切换为单 worker、四线程 Gunicorn，凭据轮换后 `/api/ready` 与部署验收再次通过；交易、订单、监控、策略恢复、支付、反思和离线校准 worker 均关闭。遗留 ngrok 已停止，产品本地入口为 `http://127.0.0.1:8000/#/tw-stock-monitor`。

系统状态仍把最近一次定时 full B19 标为 BLOCKED；独立受控重试已经 READY，但不改变 Model A baseline，也不更新正式 latest。live crontab 已与 0600 的 installed cron 逐字节同步，两条任务均使用受控环境 wrapper，且不含明文连接串。`/etc/logrotate.d/quantdinger-tw-stock` 已按 root:root 0644 安装，63MB `cron.log` 已实际轮转为 `.1`，模板采用 `copytruncate`，持续写入时仍有短暂复制/截断竞争。

后续按以下顺序收尾，不需要继续调模型：

1. 在下一个合法 full cron 观察当前 v2 B19 自动 READY/BLOCKED 与绑定证据；有错误修运行链路，不放宽门禁。
2. 完成 prospective outcome 的自动结算与准入评估；完成前保持 `settlement_required`，不得切换 baseline。
3. 整理可复现的资产供应和隔离演示入口；干净依赖安装与云端 CI 尚未验证。
4. 修复少量依赖墙钟或固定 live ledger 条数的历史实验测试隔离债务。
5. 按合同逐步迁移大编排、legacy handler 与主 Vue 的职责；先保持产品行为和回归，不做无证据的大重构。

仓库 watchdog 已使用 HTTP liveness、严格 readiness、端口派生 URL、可配置部署根目录和 Gunicorn，当前运行实例已加载这些改动。自动结算闭环在完成前应继续标明 settlement pending。侧栏仍保留继承的 IDE、Strategy & Live 和会员等入口；面试定位应说明是基于 QuantDinger 扩展的台股量化研究平台，不把所有继承功能算作本轮完成的产品。

审查范围为台股研究主链、相关启动安全及产品入口；不能将其通过推广到继承的所有市场或交易模块。面试叙述见 `INTERVIEW_DEMO_CN.md`，不要把条件通过表述为全部功能已达到成熟生产部署。
