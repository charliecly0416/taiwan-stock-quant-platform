# 当前主线验收

更新时间：2026-09-28 15:13 UTC。**Model A clean 已成为GitHub默认主线并接管正式5000/8000服务；本轮完成独立环境恢复、部署和持续运维接入，可用于当前研究产品及面试展示。** 验收不等于所有历史实验入口等价，也不承诺投资收益或未来零故障。

## 运行版本与入口

- GitHub默认分支：`product-clean`；旧main保留，`legacy-main-20260928`固定切换前版本。
- 已部署代码：`a454b29431b6322092ba2fffb0dc81d32c5f0d8d`；稳定版本 `clean-v1.0.0` 对应该代码，后续文档提交不改变运行代码。
- 正式目录：`~/.local/share/tw-stock-clean/releases/clean-20260928-ops`，独立venv；源码checkout仍用于开发。实际目录以systemd WorkingDirectory为准。
- 两个端口均HTTP200 / ready=true；基线为Model A `e4_frozen_qlib_2018_2022`，策略Top50 / exit one worst / next_open。
- 当前asof为2026-09-24，release为 `2026-09-24-2026-09-28T15:08:47.300926+00:00-68d2cad4`。9月24日与9月23日各150条信号，恢复前后排名、分数和各rank字段完全相同。
- 当前维护状态OK、alerts为空。Web、daily.timer、health.timer、backup.timer均active且enabled。服务切换后NRestarts=0。

## 本轮检查与证据

证据目录：`tmp/clean_operations_20260928/`，保留本机，不提交市场数据、模型、账本或token。

| 检查 | 结果 | 证据文件 |
| --- | --- | --- |
| Python全套 | 195 passed | pytest.log |
| 前端Node | 12 passed | node.log |
| Vite生产构建 | PASS；JS约30.18KB，CSS约13.86KB（未压缩） | build.log |
| ARCH-1 | PASS | arch1.json；deployed_arch1.json |
| M3日更合同 | PASS；24个focused tests | m3.json |
| 模块合同 | PASS；70个focused tests | modules.json |
| 真实资料stack | 源码与部署目录均PASS | stack.json；deployed_stack.json |
| 正式8000浏览器 | 七页 × 桌面/平板/手机PASS | frontend/summary.json |
| 新增运维面板 | 三视口均显示OK，无水平溢出 | live_runtime.json |
| 独立恢复和新venv启动 | 15,773文件恢复；依赖检查、构建、150排名、Agent通过 | prepare.json；部署目录deployment.log |
| 结果一致性 | 两个交易日排名和分数逐字段完全相同 | restored_signal_comparison.json |
| 模拟账本连续性 | 全部表结构和数据一致，SQLite integrity_check=ok | ledger_continuity.json |
| 正式切换 | READY；当前目录变更已核对 | activate.json；live_runtime.json |
| 真实备份和健康service | 备份READY；health OK，无告警 | live_operations.json |
| 部署失败恢复 | fixture通过：旧units/Web恢复；拒绝过时备份 | test_clean_deployment.py |
| GitHub CI | 运行36441229360成功，对应已部署提交 | clean-product workflow |

Python/模块测试使用fixtures与隔离输出。stack为真实数据smoke与数值不变量检查；浏览器脚本自身 `release_acceptance=NOT_EVALUATED`，上线判断综合实际恢复、部署、API与浏览器证据，未把单个脚本当成所有发布条件的证明。

## 前端、Agent和只读边界

七页内容完整，console error、page error、失败响应、失败请求和禁止请求均为0。覆盖排名、Top30/50、排名变化、行情指标、回放、比较、Agent、系统页。已验证DOM内容和几何布局；截图仅在本地保存，**未调用view_image，未将图片传入模型；人工像素视觉复核未执行**。

模拟账户的浏览器动作在本轮使用fixture，覆盖预览、确认、历史和token不持久化；本轮部署则实际复制并核对现有clean账本全部表与数据，没有写用户账户。此前同日真实API及浏览器模拟账户闭环证据保留在 `tmp/clean_mainline_20260928/`，不把它冒充本轮重新执行。

Agent通过后端simple-chat读取已验证每日产物，默认本地解释。未读取.env、未调用远端OpenAI、未调用券商或真实订单。比较页维持no_apply。导航竞态测试的三个 `isolated_navigation_case` 是刻意注入的fixture，非线上资料缺口；历史比较渲染亦有明确fixture标记。

## 运维、备份与恢复

- 真实切换于2026-09-28 15:11 UTC完成。原目录保留，未删除旧源码、资产或缓存。
- 首份恢复快照为 `~/.local/state/tw-stock-clean/backups/snapshots/20260928T145100-df0adcdf/manifest.json`，其旁 `restore-verification.json` 记录真实恢复PASS。
- 新运行目录的备份service已成功执行，最新快照 `20260928T151119-ab8e5594`，15,775文件、约869MB逻辑数据。静态内容去重存储。
- 健康检查每10分钟；备份每日台北04:00；日更工作日台北18:30、19:30、20:30。所有timer已启用，不能将“启用”当作已长期运行的证据。
- 2026-09-28 12:30 UTC的真实scheduled记录为 `NO_NEW_MARKET_SESSION`。下一次日更计划2026-09-29 10:30 UTC；下一新增交易日完整scheduled采集发布需等待真实触发，尚未宣称通过。
- 升级使用指定Git版本 + 当前资产快照；prepare先验证，activate同步最新账本并切换服务。自动失败恢复通过fixture测试，未人为破坏生产来制造故障演习。

## 范围与后续条件

- B19R2R仍是影子研究模型，production_allowed=false、mainline_blocking=false；新日期78F资料不足不阻塞A。
- 旧登录、旧账户尚未迁移；现有clean账本已保留。功能保留与替代关系见 [替代清单](CLEAN_REPLACEMENT_CN.md)，不会悄悄恢复自由订单等范围外入口。
- 私有GitHub仓库的分支保护被套餐限制拒绝（HTTP403）；CI正常执行，但服务器强制合并门禁尚不可用。没有将仓库公开。
- 告警目前为系统页和journal；备份位于同机仓库外，尚无外部消息渠道和异地存储。30天/至少7份是归档计划，不会自动删除共享对象。
- Docker、远端大模型调用、公网域名/HTTPS、长时间soak和下一新增交易日完整定时流程未验收。正式部署使用本机Python/systemd，不依赖这些可选路径。

面试操作见 [演示路线](INTERVIEW_DEMO_CN.md)，模块串联见 [架构](ARCHITECTURE_CN.md)，后续升级和故障恢复见 [运维](OPERATIONS_CN.md)。
