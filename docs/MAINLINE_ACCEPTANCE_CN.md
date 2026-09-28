# 当前主线验收

记录时间：2026-09-28 12:09 UTC。范围：本机 `product-clean` 工作树及实际 5000 / 8000 服务。结论：**Model A clean 主线已接管运行；已验收的前端研究流程、模拟账户和后端合同通过，可用于本机面试展示。** 本结论不代表已改远端默认分支、已完成公网部署或旧系统所有遗留功能等价。

## 实际运行

- `GET :5000/api/health` 与 `GET :8000/api/health` 均返回 `product=tw-stock-clean`；两个端口 ready 均为 HTTP 200。
- 当前批次信号日期：**2026-09-24**；发布 ID：`2026-09-24-2026-09-28T11:57:05.546295+00:00-49b26c99`。
- 当日 Model A 排名 **150 条**，策略意图 **50 条**，前一日 2026-09-23 信号 **150 条**；Agent 回答与榜首 TW3605 对齐，有有效引用。
- Gunicorn 双 worker，systemd active/running，检查时自动重启计数 0；最新启动以来无 Traceback、worker timeout 或启动失败。
- Web 和 daily.timer 均 enabled，linger=yes；台北工作日 18:30、19:30、20:30 运行。验收时下一次触发为 2026-09-28 12:30 UTC（20:30 台北）。**尚无一次真实 scheduled full lane 成功证据**，没有把手动发布写成定时成功。
- 15000 临时候选服务已关闭。原有相关旧保活、旧日更 cron 已注释，外部备份与恢复说明见 [运维手册](OPERATIONS_CN.md)。

## 验证结果

| 检查 | 本轮结果 | 证据 |
| --- | --- | --- |
| Python 全套 | 185 passed | `pytest.log` |
| 前端 Node | 11 passed | `node.log` |
| Vite 生产构建 | PASS；JS 约 29.18 KB，CSS 约 13.86 KB（未压缩） | 当前 frontend/dist |
| ARCH-1 | PASS | `arch1.json` |
| M3 日更 | PASS，16 focused tests | `m3.json` |
| 模块合同 | PASS，62 focused tests | `modules.json` |
| 真实资料 stack | PASS | `stack.json` |
| 正式 8000 浏览器 | 七页 × 桌面/平板/手机 PASS | `frontend/summary.json` |
| 模拟账户真实 API | 创建→预览→确认→历史；重复确认幂等 PASS | `paper_live.json` |
| 模拟账户真实浏览器 | 创建→预览→确认门槛→应用→历史 PASS | `paper_browser_live.json` |
| 短时并发 | 12 次 GET，4 并发，全成功，最慢 0.109 秒 | `live_checks.json` |
| 运行状态 | active、enabled，最新启动以来错误计数为 0 | `runtime_state.json` |

以上证据目录为 `tmp/clean_mainline_20260928/`，保留在本机，不提交市场资料或 token。浏览器验收的 `ui_passed=true`、`passed=true`，业务缺口、console error、page error、失败请求与禁止请求均为 0。测试覆盖 Top30/50、排名变化、行情、比较、回放、Agent、系统页与模拟账户门槛。历史比较另有隔离渲染 fixture；正式接口也实际调用并验证。所有截图只保存在本地，**未调用 view_image，未把图片传入模型，人工像素视觉复核未执行**。

模拟账户真实测试使用专用 owner `acceptance_20260928` 与 `acceptance_browser_20260928`，不接触用户旧账户。后者产生 43 条模拟动作；无需将候选 50 条强行等同于可买入数量，资金与最小数量约束仍生效。令牌未写入报告、URL 或浏览器持久存储。

## 结果准确性与回放

- 净值 = 现金 + 持仓市值；收益与初始/最终 NAV 对齐，回撤从初始资本计算，费用纳入现金与净值；测试包含最低手续费手算 fixture。
- 2025-06-23 至 2025-06-30：真实历史回放 READY，最终 NAV 1,008,037.06，收益 +0.8037%，最大回撤 -1.0410%，费用 1,898.71，58 笔模拟成交。
- 2026-09-21 至 2026-09-24：修复后 READY，最终 NAV 985,596.37，收益 -1.4404%，最大回撤 -2.2498%，费用 1,656.18，53 笔模拟成交。
- 2026-05-07 历史 A/B 比较 READY，Top50 重叠 49。比较回放预填 2026-05-07 至 2026-05-08，两轨均 READY；这只是已验证的短窗口，不包装成长周期效果结论。
- 排名连续、代码唯一、分数有限；缺行情或缺被选中股票的特征会阻止伪完整结果。Agent 引用固定发布批次，拒答交易行动问题。

短期真实回放既有盈利也有亏损，不作为未来投资效果承诺。

## 本轮解决的实际问题

1. 原旧后端进程与静态代理占据正式端口：已由 clean 同源应用接管，加入 systemd 服务、自动重启、日志和日更 timer。
2. 日更改 provider 后 API 仍读旧路径、同日重跑破坏旧 Agent 来源：通过不可变 release + active.json 原子切换统一 provider、信号与 prompt。
3. 旧流动性桥接文件缺近期日期：selection_universe 改为实际 provider 生命周期，流动性 Top150 仍按当日行情筛选；近期回放与前一日信号已通过。
4. simple-chat 读未解析配置：路由与 ProductService 共用本次已激活批次，并加入发布后 API 回归。
5. 比较页预填回放区间包含缺失的影子特征：改用有真实证据的历史窗口；任意缺资料日期仍明确 BLOCKED，不伪造 B 特征。
6. 每次查询复制全市场历史导致耗时：单股和候选背景按需读取；provider 构建流式写入，线程结果只保存摘要。
7. 文档混合旧 BLOCKED 与新上线结论：当前接手、架构、运维、演示和验收文档统一；旧报告标为历史记录。

## 已知范围与未执行项

- B19R2R 新日期 78F/PIT 特征仍是影子研究缺口；不阻塞 Model A，不进入模拟账户或默认。
- 当前 Agent 为本地产物解释；远端大模型适配未实调。旧登录/旧账户未迁移。
- Docker 构建未完成；正式运行采用原生 Python + systemd。新机器还需部署本机冻结模型、定制 Qlib 和历史数据。
- 未执行长时间 soak、真实下一次收盘日更、公网 HTTPS/域名验收；短时并发与服务检查不能代表长期可用性证明。
- Git 保持 `product-clean` 及原有未提交工作，不擅自重置、删除或推送远端默认分支。

面试操作与讲解顺序见 [演示路线](INTERVIEW_DEMO_CN.md)，模块图见 [架构](ARCHITECTURE_CN.md)。
