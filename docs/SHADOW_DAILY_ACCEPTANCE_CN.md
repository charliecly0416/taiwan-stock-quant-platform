# Shadow 日更部署与定时验收（2026-09-30）

## 结论与边界

clean 已部署独立 shadow 日更和重试。真实 systemd timer 完成采集、历史补齐、78F 构建检查，运行过程完成，但 **2026-09-29 的 B 排名没有发布**：当日50条候选中48条特征完整，TW7610 与 TW3624 未通过冻结模型输入门禁。不能将服务 Result=success / execution_status=COMPLETED 解释成模型 READY。

Model A 仍是唯一产品默认，150条信号、Agent、readonly前端可用；B 保持 production_allowed=false、mainline_blocking=false、no_apply=true。没有训练、替换模型、补零、递补候选或接入模拟账户。

## 修正内容

- 独立 clean-shadow.service / timer；A 发布与 B 采集互不等待，同日 A 已完成也不会跳过 B 重试。
- 从已发布 A 批次取 Top50，TW7769 不递补；FinMind 只抓需要的标的，TAIEX 指数使用正确代码；公开接口可匿名，可选用户 token。
- 缓存按标的续抓；补齐冻结末日之后的 A 排名历史，优先保留已发布排名；历史缓存不能写入信号文件。
- 独立 Yahoo ^TWII 日历排除个股日期并集里的非市场日期，价格与指数先按日历对齐再滚动。法人类别、融资券真实昨余额、OX、可用日和缺数保持显式处理。
- 各次运行保存不可变输入副本、特征和信号；delta 只用于冻结历史之后的日期。模型实际读取新 delta。发布 B 指针前再次检查 A 批次；切 A 批次时不继承旧 delta。
- 运维 API、健康检查、备份包含 shadow。按日检查漏跑；缺数给出具体股票和字段，主线不跟随变为 BLOCKED。

## 当前输入缺口

| 股票 | 已取得的证据 | 门禁 |
| --- | --- | --- |
| TW7610 | 本次 FinMind 融资券返回0行；A候选历史仅9/22、9/23、9/24、9/29四次 | 融资券特征及rank_change_5d缺失 |
| TW3624 | 截至9/29首次进入已补齐的A候选排名 | rank_change_1d / 3d / 5d缺失 |

补数不能制造不存在的融资券数据或历史候选排名。后续定时器会重新获取并检查；不能保证下一交易日就满足合同。要允许缺失值或额外排除股票，必须另行验证模型合同，本次未调整。

## 实机证据

部署目录：`/home/chuliyang/.local/share/tw-stock-clean/releases/clean-20260930-shadow`。

仓库外部署前备份：`/home/chuliyang/.local/state/tw-stock-clean/backups/snapshots/20260930T021826-b8eadc88/manifest.json`。prepare 完成隔离恢复、全新 venv、pip check、前端构建、当前日期本地发布、150排名和Agent检查；激活后 `/api/ready` 为 true、asof=2026-09-29。

定时验收 run_id：`0b4c682b4d9b4991b08cc9be1fe3a03a`，UTC 02:42:00—02:42:20，trigger_reason=scheduled、local_only=false、execution_status=COMPLETED、status=BLOCKED、gate=B19R2R_INCOMPLETE_78F，未写 B 指针。

这是给真实 clean-shadow.timer 加一次 OnActiveSec 后的**受控定时验收**，不是9/30收盘后的正常场次。临时触发已撤下。常规定时为台北工作日18:45、19:45、20:45；首个部署后常规场次尚未到达，不能提前声称成功。

完整定时证据：`~/.local/state/tw-stock-clean/shadow-acceptance-20260930.json`；运行产物在部署目录的 `data_tw/product/artifacts/shadow/{run_id}/run.json`、`feature_coverage.json`、`source_inputs/`。

前两次受控尝试暴露并修复了日历差异与历史缓存写错目标路径。后者影响9/24信号CSV，已从校验一致的不可变副本逐字节恢复；9/29信号未被改写。恢复证据在 `~/.local/state/tw-stock-clean/shadow-acceptance-recovery/recovery.json`；新增回归证明补历史不修改 A 文件。

## 验证与限制

- 当前源码 pytest：210通过；前端 Node 测试通过；部署中 pnpm build、pip check通过。
- M3、ARCH-1、模块合同回归通过；部署目录 stack通过。stack修正了Agent检查硬编码9/24的问题，改查当前市场日期。
- 在线8000端口的只读前端验收 ui_passed=true、failures=[]；使用DOM/网络/控制台证据，没有调用 view_image 或人工读图。
- 实机冻结历史日期2026-05-07的真实 A/B 比较为 READY、Top50交集49，证明冻结B评分依赖可用。当前日期没有完整 B 输入，因此新日期 READY 发布仍未在实机证明；不能用fixture或历史评分代替。
- 尝试额外重建9/10输入时，FinMind匿名接口返回HTTP402额度上限，未完成该额外历史日期的评分验证。正常定时每次约101次请求，前端GET不发起采集；重试分散在三个小时。额度或网络错误保留为执行失败，不能改成模型READY。
- 旧冻结构建时的价格源文件均已更新，不能直接以当前价格文件重现旧矩阵数值并声称逐值一致；冻结模型和历史特征未改动。新数据的 available_at 为下一交易日策略推导，captured_at 保存真实抓取时间，不把事后补数称作当时采集的前瞻证据。

日常操作与诊断入口见 [运维手册](OPERATIONS_CN.md)。
