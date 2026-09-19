# 台股研究产品稳定运维手册

日常巡检先使用 `docs/ops/DAILY_OPERATIONS_CHECKLIST_CN.md`；本文处理备份、恢复、日志轮转和部署切换等低频操作。

## 服务探针

- `GET /api/health` 只判断 Flask 进程是否存活。
- `GET /api/ready` 对 PostgreSQL 执行只读探针，验证 registry、Model A、只读策略快照与 Agent prompt 的同日指针和 checksum 合同，并确认当前进程未启用交易、订单、监控扫描、策略恢复、支付或后台写入 worker；任一条件失败返回 HTTP 503。
- readiness 不访问行情 provider、不运行模型、不发布产物，也不提供跳过 artifact 合同的环境开关。

`scripts/ensure_tw_stock_services.sh` 使用 HTTP 探针，不再只凭端口判断服务正常。端口已被占用但 HTTP 探针失败时，脚本记录错误并退出，不会启动第二个冲突进程。脚本通过 `flock` 防止 cron 和人工调用并发。

可移植配置：

```bash
export TW_STOCK_PLATFORM_ROOT=/srv/taiwan-stock-quant-platform
export TW_STOCK_PYTHON=/srv/venv/bin/python
export TW_STOCK_BACKEND_PORT=5000
export TW_STOCK_FRONTEND_PORT=8000
```

未设置 `TW_STOCK_PYTHON` 时，watchdog 依次查找 `python3` 和 `python`。
backend 默认由单 worker、四线程的 Gunicorn gthread 启动。可用 `TW_STOCK_BACKEND_THREADS` 调整线程数；watchdog 固定单 worker，避免应用内部后台线程被多 worker 重复初始化。

ngrok 默认关闭。确实需要公网演示时才设置：

```bash
export TW_STOCK_ENABLE_NGROK=true
export NGROK_BIN=/usr/local/bin/ngrok
export TW_STOCK_NGROK_PORT=4040
```

服务启动后的 HTTP 探针若失败，watchdog 会终止本次刚创建的进程组。它不会终止启动前已存在的未知监听者。

## 备份与归档完整性检查

先执行只读计划。`required_inputs_complete` 必须为 `true`；缺少任何受管资产时，创建命令会拒绝继续：

```bash
python scripts/tw_stock_ops_backup.py plan
```

创建数据库和产品产物备份需要明确确认。`DATABASE_URL` 只通过环境传给 `pg_dump`，不会放进命令参数或 manifest：

```bash
TW_STOCK_BACKUP_ROOT=/mnt/backup/tw-stock \
DATABASE_URL='postgresql://...' \
python scripts/tw_stock_ops_backup.py create --confirm-create
```

每次备份后执行无写入归档完整性检查：

```bash
python scripts/tw_stock_ops_backup.py drill \
  --backup-dir /mnt/backup/tw-stock/tw_stock_ops_YYYYMMDDTHHMMSSZ
```

检查会逐文件核对 artifact tar 的大小和 SHA256，并用 `pg_restore --list` 验证数据库归档可读；不会连接数据库，也不会写 live artifacts。这不等于已经完成真实恢复。正式恢复演练必须在新建隔离数据库和空目录中解包、恢复并启动应用验收，再进行受控切换。禁止直接覆盖线上数据库或 latest 指针。

`--skip-database` 只适合开发测试或单独的 artifact 备份，不能作为完整灾备。

该备份覆盖当前产品指针与产物、Model A 模型和 accepted qlib provider、B19R2R frozen 模型与 prospective ledger，以及 PostgreSQL。它不复制约 6.2GB 的历史 `option_c_ops` 或约 2.3GB 的历史 daily-auto 运行目录，因此用于恢复当前产品和继续日更，不是完整的历史 PIT 证据归档。需要长期保存审计证据时，应另外对这两个目录制定对象存储与保留策略。

源码、依赖锁文件和前端构建输入由版本控制系统恢复，`frontend/dist` 应从锁定版本重新构建。`.env`、`SECRET_KEY`、数据库密码和第三方凭据不进入 artifact 备份；它们必须由部署环境的 secret manager 或等价的加密密钥备份独立恢复。不要把秘密复制进 artifact tar 或仓库。

备份计划会扫描受管输入中的带认证 PostgreSQL URL；`plaintext_credential_findings` 非空时，plan 的 `required_inputs_complete=false`，create 会拒绝执行。manifest 用 `contains_plaintext_credentials` 表示 artifact 明文凭据检查，用 `contains_sensitive_database_dump` 表示数据库 dump；即使前者为 false，包含 dump 的整个备份仍是 0600 的敏感资产。

日更 cron 不应声明 `DATABASE_URL`。本机通过 `scripts/run_daily_env.sh` 从 0600、非 symlink 的 `backend/.env` 加载环境；wrapper 在权限过宽或缺少连接串时拒绝启动。修改 cron 后同时检查 live crontab 与 `data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron`，后者也必须保持 0600。

## 日志轮转

仓库提供 `docs/ops/quantdinger-logrotate.example`。部署时将 `/path/to/taiwan-stock-quant-platform` 和 `su` 行的部署用户/用户组替换为实际值，再由管理员安装到 `/etc/logrotate.d/`。仓库改动不会自动修改系统配置。

安装前检查：

```bash
sudo logrotate --debug /path/to/rendered-quantdinger-logrotate
```

当前 `copytruncate` 适用于这些持续打开的重定向日志。部署后应检查轮转文件的属主、压缩结果和磁盘占用。

本机 2026-09-18 已将渲染配置安装到 `/etc/logrotate.d/quantdinger-tw-stock`（root:root 0644），并把 63MB 日更 `cron.log` 实际轮转为 `.1`；其他未达到 20MB 的日志保持不变。`copytruncate` 仍有极短的复制/截断竞争窗口，不可替代不可变运行证据。

## 部署后验收

先在备用端口启动候选 backend，并执行只读验收：

```bash
python scripts/verify_tw_stock_readonly_deployment.py \
  --base-url http://127.0.0.1:5001 \
  --expected-asof YYYY-MM-DD
```

脚本只对七个查询端点执行 GET，并确认 readiness、实际进程的只读运行边界、日期一致、Model A baseline、accepted/无 pending、只读运维门禁和比较页不可应用。它还用 POST/PUT/PATCH/DELETE 验证三个只读端点均返回 405；这些请求不会进入业务 handler。

候选通过后才停止旧 backend，并运行 `scripts/ensure_tw_stock_services.sh`。随后把同一命令的 `--base-url` 改为 `http://127.0.0.1:5000`，失败时立即停止新进程、恢复部署前版本与密钥备份，再启动旧版本。未保留可启动的部署前源码和密钥时，禁止执行替换。

部署验收还必须完成：

1. 人工运行一次 `scripts/ensure_tw_stock_services.sh`，确认没有重复拉起进程，backend 由单 worker gthread Gunicorn 承载。
2. 安装并 dry-run 日志轮转配置。
3. 选择外部持久卷执行一次完整备份和 archive integrity drill；另在隔离环境完成一次真实恢复演练。
4. 保留合法 full-scope B19 shadow 的真实运行证据；BLOCKED 不影响 A 主链，但必须保留受控错误码并修复运行原因。

本机 2026-09-18 已完成 5001 候选和 5000 正式实例验收；数据库凭据轮换后，正式实例再次通过验收并保持单 worker、四线程 Gunicorn，最终证据见 `tmp/deployment_acceptance_live_5000_final.json`。替代备份包含 4816 个 artifact 文件和 PostgreSQL dump，已通过归档完整性检查；临时 PostgreSQL 16 集群的 57 表隔离恢复同时绑定了源 dump SHA256，证据见 `tmp/isolated_database_restore_drill_after_credential_rotation.json`。含旧明文凭据的备份已删除。live crontab 已与 0600 的 installed cron 逐字节同步，两条任务均使用 `scripts/run_daily_env.sh`，且不含明文连接串。
