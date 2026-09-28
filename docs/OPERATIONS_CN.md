# Clean 运行与运维

前端 `http://localhost:8000`，API `http://127.0.0.1:5000`。同一Gunicorn/Flask应用提供API与构建后的前端。正式运行目录由systemd确定；升级采用独立目录，源码checkout不是运行数据的默认操作目录。

## 状态与操作目录

```bash
systemctl --user show clean-web.service -p WorkingDirectory --value
# 后续维护先进入上面输出的目录，使用该目录的 .venv/bin/python
curl -fsS http://127.0.0.1:5000/api/ready
curl -fsS http://127.0.0.1:5000/api/tw-stock/operations/latest
systemctl --user list-timers clean-daily.timer clean-health.timer clean-backup.timer
journalctl --user -u clean-web -u clean-daily -u clean-health -u clean-backup -n 80 --no-pager
```

系统页显示模块链路、当前批次、日更与维护状态。ready是当前批次可服务；日更失败仍可继续提供旧完整批次；备份与日更失败单独告警，不能用ready掩盖。告警显示在UI与本机journal，尚未接入外部邮件或消息通知。

## 日更

台北工作日18:30、19:30、20:30运行 `clean-daily.timer`。指数实际交易日决定是否采集；休市记录 `NO_NEW_MARKET_SESSION`，不按自然日制造“新交易日”。全市场行情只用于流动性筛选，Model A评分150支，策略Top50；B影子资料不阻塞A。

每次尝试先持久记录RUNNING；早期请求失败也记录BLOCKED及失败类型。定时与手动记录分开。发布生成完整独立release，通过后原子切换active.json，失败保留旧批次。

```bash
# 以下为运维动作，不用来做普通代码验证
.venv/bin/python scripts/run_product.py daily --publish
# 已有本地数据的指定日期发布，不抓取
.venv/bin/python scripts/run_product.py daily --asof YYYY-MM-DD --local-only --publish
```

2026-09-28 12:30 UTC的实际定时尝试记录休市跳过。下一次新增交易日的完整定时采集、评分与发布仍需由未来实际运行证明，不能将这次跳过或手动发布替代它。

## 健康、备份与容量

`clean-health.timer` 每10分钟检查Web、计划漏跑、失败/超时、备份与磁盘。工作日台北21:30后应有当日定时尝试（包括休市跳过）；备份超过36小时告警；空间少于10GB告警。结果写当前artifact store的 `ops/health.json`。

`clean-backup.timer` 每日台北04:00运行。仓库外默认目录 `~/.local/state/tw-stock-clean/backups` 权限0700，对象0600。只备份登记资产、配置、当前批次、日更证据、定制Qlib wheel和一致性SQLite账本；不扫描home、不备份.env或签名秘密。不可变对象按内容去重，静态模型无需每天重复复制。

```bash
.venv/bin/python scripts/maintain_clean_product.py health
.venv/bin/python scripts/maintain_clean_product.py backup
.venv/bin/python scripts/maintain_clean_product.py verify-backup --manifest /absolute/snapshot/manifest.json
.venv/bin/python scripts/maintain_clean_product.py restore --manifest /absolute/snapshot/manifest.json --out /new/empty/path
.venv/bin/python scripts/maintain_clean_product.py retention
```

restore拒绝覆盖已有目录，验证对象与SQLite后生成重新定位的 `runtime-config.yaml`；旧产物字节不改写，需在新目录本地重新发布才可激活。prepare命令将完成此步骤。新主机不恢复签名秘密，安装器创建新秘密，旧token需重签。

保留策略为30天、至少7个快照，retention仅列出可归档计划，**不自动删除共享对象或旧资产**。删除须依仓库规则先验证仓库外副本可恢复。当前备份在同一台机器，能处理误改与代码升级；整盘损坏保护需要另一个存储位置，尚未配置异地备份。

## 可复现部署和升级

需要系统Python 3.13、Node.js 24/corepack、systemd用户服务、已登记的台湾定制Qlib wheel及资产备份。后端使用requirements-runtime.lock约束，前端使用frozen lockfile。脚本从指定Git提交导出源码，恢复资产，建新venv，安装依赖与构建前端，本地重新发布并验证150条排名与Agent后才标记READY。

在源码checkout执行（目标必须不存在，选择持久目录）：

```bash
python scripts/deploy_clean_product.py prepare --ref clean-v1.0.0 --snapshot /absolute/snapshot/manifest.json --destination /absolute/new-release
python scripts/deploy_clean_product.py activate --destination /absolute/new-release
```

prepare不影响现有服务。activate拒绝日期过时的备份，获得日更锁，暂停Web写入并复制最新模拟账本，安装units后探测ready；启动失败恢复此前units和Web。旧目录保留。服务配置备份在 `~/.local/state/tw-stock-clean/service-installs/`；当前部署记录在 `current-deployment.json`。切换后从systemd查询新运行目录再执行维护。

代码回退：用**最新资产备份**与此前稳定Git标签重新prepare/activate，避免恢复旧账本。数据批次回退则使用下述命令，先暂停日更timer，选择已验证release；命令验证目标后原子切换，不混合单个信号文件。

```bash
systemctl --user stop clean-daily.timer
.venv/bin/python scripts/maintain_clean_product.py rollback-release --release VALIDATED_RELEASE_ID
curl -fsS http://127.0.0.1:5000/api/ready
systemctl --user start clean-daily.timer
```

独立安装器为 `scripts/install_clean_services.py --start`。7个units包括Web、daily service/timer、health service/timer、backup service/timer。用户已开启linger，登出不停止服务。旧保活cron备份保留于 `~/.local/state/tw-stock-clean/deployment-20260928T115143/crontab.before`，不恢复旧入口抢占端口。

## 账户、访问和发布边界

```bash
.venv/bin/python scripts/run_product.py paper-token --owner interview
```

演示token只用于模拟账户Authorization header，不提交、不放URL。账户创建、预览、确认后才改变模拟账本。最新日期没有下一交易日行情时不伪造成交。旧功能与账户范围见 [替代清单](CLEAN_REPLACEMENT_CN.md)。

GitHub默认分支为product-clean；旧main保留于legacy-main-20260928。当前私有仓库套餐拒绝强制分支保护，CI仍执行但不宣称合并门禁已强制。公网域名/HTTPS、Docker、外部告警和异地备份均不在当前实测范围；当前本机服务可经已有网络或SSH转发展示。
