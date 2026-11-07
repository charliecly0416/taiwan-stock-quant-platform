# 当前主线验收

更新时间：2026-11-07（UTC）。**clean Model A 已完成停更区间补齐、真实交易日历修复及正式部署，当前研究功能可用；历史自动采集曾连续失败，不能称为全自动链路已长期稳定。** 下一个新增交易日的正式定时验收尚待真实触发。

## 当前运行状态

- GitHub 仓库已公开，默认分支为 `product-clean`；旧主线保留在 `legacy-main-20260928`。
- 已部署11/7两轨历史版本，代码身份见本机 `~/.local/state/tw-stock-clean/current-deployment.json`；其前一代码版本为 `70fc35c70ca33c68c126d958a6921a8d8f221b83`。原 `clean-v1.0.0` 标签只代表9/28版本。
- 正式目录：`~/.local/share/tw-stock-clean/releases/clean-20261107-audited`，独立 venv；于11/7 06:33 UTC切换。Web、daily、shadow、health、backup 的 WorkingDirectory 均已核对。
- 正式5000/8000均 HTTP 200、ready=true，最新数据为2026-11-06。Web active，切换后 NRestarts=0。
- 当前 A 批次：`2026-11-06-2026-11-07T06:31:17.718053+00:00-abd51c82`。
- 唯一 baseline：Model A `e4_frozen_qlib_2018_2022`；策略 `top50_exit_one_worst_sell`；执行 `next_open`。
- B19R2R 已手动完成同一 A 批次的11/6特征与50支重排，状态 READY；仍为 `production_allowed=false`、`mainline_blocking=false`、`no_apply=true`。

## 两轨历史接入（11/7）

A 与 A+B 的查询、排名变化、比较和回放已平行提供，首页各轨道有独立入口；切换模型会更新历史日期和回放范围。默认仍A，B不进入模拟账户。接口 `GET /api/tw-stock/history?model=model_a_plus_b` 返回已校验日期及来源，其他研究接口沿用同一 `model` 参数。

10/12–11/6的18个交易日已全部可查：A共2,700条，B共900条；B的900×78个特征值均有限。补算包已复制进产品store的 `history/reconstruction-6a132adfb0764023843fd289c902e795`，查询不依赖外部实验目录。它明确标记为 `historical_reconstruction`，不是当时实时或定时结果。比较按B的来源批次选择A，当前日期不复用另一A批次的B。

既有 A / Shadow 定时器分别保留；新信号保存公开配置上下文，成功发布后自动被历史发现，指针推进不丢历史，不新增第三条归档调度。尚未发生下一交易日的真实定时触发，不能据此宣称日更已长期稳定。

| 10/12–11/6同策略、next_open、同费用回放 | A | A+B |
| --- | --- | --- |
| 累计收益 | -30.90% | -31.42% |
| 最大回撤 | -31.51% | -31.94% |
| 模拟交易数 | 82 | 80 |

B在此短区间没有优于A，功能平行不代表模型效果提升。两侧API结果均与独立回放核验一致。

本次证据位于 `~/.local/state/tw-stock-clean/audits/parallel-history-20261107/`：239项Python测试、13项Node测试、前端构建、M3/模块合同/ARCH-1通过；真实运行配置的stack通过。源码checkout保留旧忽略资产，最初直接运行stack命中了旧批次并失败，未据此改写或重建它；正式配置复验为PASS。隔离及正式36次排名查询、成对回放通过；桌面、笔记本、平板和手机的新历史流程及七页浏览器检查通过，错误/禁止请求/横向溢出均为0。截图已通过 `view_image` 进行人工视觉复核，确认首页意图列表已折叠、日期不换行、各主要面板无空白或重叠。

部署未改六个active/Shadow/日更状态指针、冻结模型或模拟账户。最终采用原正式目录的代码补丁，旧代码在仓库外备份并验证恢复；临时代码目录已退出服务，所有units仍指向原正式目录，以保持既有备份资产边界。

含两轨历史的新备份 `~/.local/state/tw-stock-clean/backups/snapshots/20261107T103404-e2a442dd/manifest.json` 已验证16,500个文件；`backup-final.json` 与 `backup-verification.json` 保存证据。

## 停更区间、连续性与底层修复

对10/8–11/6的22个工作日共66条 scheduled 记录审查发现：没有漏触发，但只有1次完整发布、5次无新交易日跳过，另有48次 SSL 失败和12次刷新异常。10/12起没有持续成功更新。本次恢复明确记录为 manual，未清空或改写历史 scheduled 记录。

另发现Shadow历史缓存按日期与股票合并多个A批次，导致个别日期出现151–152条。已改为按日期整批替换、当前active批次优先，只保留有效150条与实际开市日期；新增竞争批次和不完整缓存回归验证。

独立对照证交所实际成交记录与 Yahoo `^TWII` 发现，10/23实际没有交易，却被旧 provider 的个股日期并集混入。仅检查年度休市表不足以发现这个问题。已修复为独立指数日历：保存原始交易日期、剔除非开市个股记录、拒绝非日历输入；指数未到目标日则阻塞发布。

已按修正后的日历重建10/12–11/6的 **18个交易日**（不是19天），每个交易日150条信号，共2,700条。正式接口已验证10/23返回 BLOCKED，10/27的排名变化正确对比10/22。恢复配置仅单次扩大历史窗口，正式 `daily.history_sessions` 仍为2。

这些历史信号由本次保存的修正行情和原冻结模型补算，属于事后重建，不能冒充当日实时发布、当时已观察到的预测或定时成功证据。

| 检查 | 本轮结果 |
| --- | --- |
| 行情覆盖 | 1,986支来源，11/6有效1,963支，覆盖率98.84%；本次抓取异常为0 |
| CSV结构 | 5,111,734行；键重复、乱序、日历外记录检查通过；近期OHLCV检查通过 |
| 区间连续性 | 没有发现区间内部缺口；逐日150候选均有当天价格；23支长期无新行情标的不在当日150候选中 |
| Qlib行情对照 | 261,079个近期二进制数值与标准CSV一致 |
| 候选选择 | 18日保存集合与按当日数据重新筛选的150候选一致 |
| 独立重算 | 2,700条分数排名全部一致，最大分数误差约9.95e-17 |
| 正式API | 18日各150条排名与文件一致；分数差在JSON序列化精度内 |
| 独立市场对照 | 18个实际交易日期与证交所一致；2308同期72个OHLC值核对通过 |
| 回放账本 | 18日回放READY；82笔模拟交易；独立Decimal核算next_open、费用、Top50规则和NAV通过 |

## 中间产物保存边界

当前批次目录为 `data_tw/product/artifacts/releases/{run_id}`，不是源码checkout中的旧数据目录。最终部署沿用本次已验证的行情provider，具体路径以active.json的provider/selection_prices字段为准，可引用同运行目录内之前的不可变采集批次；信号、意图和Agent位于当前A批次。

| 层 | 实际保存或计算方式 |
| --- | --- |
| 原始标准行情 | `provider_runs/{run_id}/normalized/TW*.csv`；保留完整可用历史 |
| 交易日历 | 同次 `market_calendar.csv` 与 provider 的 `calendars/day.txt`；refresh报告引用来源与摘要 |
| Qlib行情provider | 同次 `provider/features/` 二进制OHLCV等行情字段；这不是Alpha158特征矩阵 |
| Model A分数 | `signals/model_a/{asof}/signals.csv` 与manifest；本次恢复18日全部落盘，含分数和rank字段 |
| 策略意图 | `intents/model_a/{asof}`；本次仅物化最终11/6，其他历史策略可由信号按需计算 |
| Agent每日上下文 | `agent_daily_prompt/2026-11-06`；本批次没有逐日补建历史问答，历史simple-chat会明确返回不可用 |
| Alpha158矩阵 | 不逐日保存大矩阵；保留行情、日历、冻结模型和配置，可重新计算；本轮已重算比对 |
| B19R2R | 独立 `shadow/{run_id}` 保存来源输入、78F delta、50支分数与manifest；shadow_active绑定同一A批次 |
| 运维证据 | daily运行、manual/scheduled状态、备份与health分别保留 |

## 软件、接口与前端验收

证据位于仓库外 `~/.local/state/tw-stock-clean/audits/continuity-20261107/`，独立行情、分数与回放核算在 `after-calendar-fix/`，最终部署验收在 `final/`。`final/lineage_validation.json`逐文件证明最终版13,904个provider文件、1,986份行情及18日分数排名与独立验算批次一致，因此沿用同一组A回放证据；Shadow历史另行重建，124个实际交易日每天均为150条，并独立复算最终50条B分数。修复前文件只用于问题溯源，不替代修复后结果；不提交行情、模型、账本或凭据。

| 检查 | 本轮结果 / 证据 |
| --- | --- |
| 前端Node | 12 passed；`node-final.log` |
| Python全套 | 226 passed，1条pandas FutureWarning；`pytest-shadow-history-fix.log` |
| M3 / 模块合同 / ARCH-1 | PASS；M3 50 tests，模块73 tests；三项JSON为审查根目录的m3-shadow-history-fix、modules-shadow-history-fix、arch1-shadow-history-fix |
| 新环境依赖与前端构建 | pip check、pnpm install --frozen-lockfile、pnpm build通过；正式目录 `deployment.log` |
| 真实数据stack | PASS；`final/stack.json` |
| 分数、回放及市场独立核对 | `after-calendar-fix/`内audit、score_recomputation、replay_ledger_validation、independent_market_validation JSON |
| 正式API及Shadow绑定 | PASS；`final/live_continuity.json` |
| 正式8000浏览器 | 七页×桌面/平板/手机PASS；`final/frontend/summary.json` |
| GitHub代码CI | success；[run 42347140317](https://github.com/charliecly0416/taiwan-stock-quant-platform/actions/runs/42347140317) |

浏览器检查覆盖排名、变化、行情、回放、比较、Agent和系统页，失败响应、失败请求、禁止请求、console/page错误均为0，DOM几何无水平溢出。人工视觉复核使用正式服务截图完成；另增加1100像素笔记本宽度，确认统计栏不溢出。浏览器模拟账户写操作由fixture拦截，没有写用户账户；部署使用SQLite backup复制账本并通过integrity_check。导航竞态与历史比较fixture有独立标记，不冒充真实数据证明。按只读E2E技能核对网络、控制台和交互证据。

当前Agent默认读取已验证每日产物作本地解释；没有调用远端模型。单个stack/浏览器脚本自身仍标记 `release_acceptance=NOT_EVALUATED`，上表综合真实数据、部署和独立核算记录本轮结果。

## 运维与仍需观察的范围

- 11/7新备份 `~/.local/state/tw-stock-clean/backups/snapshots/20261107T063402-89968427/manifest.json` 已验证16,386个文件，含修复后的当前数据、Shadow和一致性模拟账本。证据为 `final/backup-verification.json`；旧运行目录与旧资产保留。
- Clash按其官方clashctl入口检查，Yahoo使用free节点；订阅每60分钟更新。未直接切断服务或留下悬空代理变量。
- timers均启用。A下次计划11/9台北18:30、19:30、20:30；Shadow为18:45、19:45、20:45。health每10分钟、备份台北04:00。
- 最新health仍为CRITICAL，唯一告警 `SCHEDULED_DAILY_FAILED` 指向历史正式调度失败；Web ready与手动恢复成功不会抹除它。下一交易日真实触发后需分别检查A完整发布及Shadow结果，不能用周末NO_NEW或手动重试替代。
- 10/12–11/6回放累计收益 **-30.90%**、最大回撤 **-31.51%**、手续费约NT$3,304。同期官方指数收盘变动约-19.47%，与策略next_open含费用口径不同，不能直接当作严格超额收益；当前结果不能支持“近期效果好”的结论。
- 当前Agent问答可用，但本批次历史每日prompt/intent未全部物化；如需历史问答档案，应作为明确补建任务，不能动态伪装为已存产物。
- 旧登录与旧账户迁移、远端大模型、公网HTTPS、Docker、异地备份及长期soak未在本轮新增验收。系统为只读研究与simulation-only账户，比较页保持no_apply。

面试展示见 [演示路线](INTERVIEW_DEMO_CN.md)，后端串联见 [架构](ARCHITECTURE_CN.md)，运维入口见 [运维](OPERATIONS_CN.md)，功能范围见 [替代清单](CLEAN_REPLACEMENT_CN.md)。9/28首发与10月阶段记录保留于Git历史和既有文档，不覆盖本页当前状态。
