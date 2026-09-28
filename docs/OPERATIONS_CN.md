# Clean 运行与运维

当前正式入口为 `http://localhost:8000`，API 同时监听 `127.0.0.1:5000`。两者来自同一个 clean Flask 应用；工作目录为仓库根，运行分支为 `product-clean`。Web 使用 Gunicorn 双 worker，由用户级 systemd 管理。

## 查看状态

在仓库根运行：

```bash
curl -fsS http://127.0.0.1:5000/api/health
curl -fsS http://127.0.0.1:5000/api/ready
curl -fsS http://127.0.0.1:5000/api/tw-stock/operations/latest
systemctl --user status clean-web.service clean-daily.timer
systemctl --user list-timers clean-daily.timer
journalctl --user -u clean-web.service -n 60 --no-pager
journalctl --user -u clean-daily.service -n 60 --no-pager
```

health 是进程检查；ready 检查 Model A、provider 日历、已物化信号和每日问答来源。operations 区分 manual、scheduled 与 active_release；手动发布成功不能替代定时运行证据。查询不会触发采集。

## 日更与发布

`clean-daily.timer` 在台北工作日 18:30、19:30、20:30 调用唯一日更入口。先查询指数实际交易日；如果仍是已发布交易日且 ready，记录 `NO_NEW_MARKET_SESSION`，避免重复抓全历史。周末和休市不能仅按自然日判定陈旧。

日更接入 Yahoo 行情增量与必要的复权修订回补；完成全市场流动性筛选后，Model A 只评分 150 支。B19R2R 影子资料不作为 Model A 发布前提。当前日更包含前一交易日信号，支持榜单变化和已知 next_open 的模拟预览。

```bash
# 常规维护：立即按实际交易日抓取并发布，使用 manual 标记
python scripts/run_product.py daily --publish
# 仅在本地数据已齐备时发布指定日期；不抓取
python scripts/run_product.py daily --asof 2026-09-24 --local-only --publish
# 隔离 fixture 验证，不发布
python scripts/run_product.py daily --asof 2026-09-24 --dry-run
```

真实发布是运维动作，不作为普通代码测试。新批次保存在 `data_tw/product/artifacts/releases/<run_id>/`；Model A、策略和问答通过后原子替换 `data_tw/product/artifacts/active.json`。运行记录位于 `data_tw/product/artifacts/daily/<asof>/<run_id>/run.json`，定时状态位于 `scheduler_status.json`。失败保持当前完整批次；锁冲突返回 `DAILY_ALREADY_RUNNING`。不要手改 signals.csv、manifest 或 prompt。

## 更新服务

```bash
corepack pnpm --dir frontend build
python scripts/install_clean_services.py --start
systemctl --user is-active clean-web.service clean-daily.timer
curl -fsS http://127.0.0.1:8000/api/ready
```

安装器将 `ops/` 中模板渲染到 `~/.config/systemd/user/`，生成私有模拟账户签名文件（0600），启用 Web 和 timer。当前账户已启用 linger，登出不停止服务。不要同时恢复旧保活 cron，避免它抢回 5000/8000。旧 cron 备份位于 `~/.local/state/tw-stock-clean/deployment-20260928T115143/crontab.before`；本次仅停用旧 Web 保活与旧日更入口，其余 cron 保留。

## 故障处理与恢复

- Web 不健康：先查看 systemd 和日志；确认本机市场数据与冻结模型仍在，再重启 `clean-web.service`。
- 新日更失败但 ready 仍为 true：继续服务旧批次，按该次 run.json 的失败阶段处理后手动重试。
- 需要回退批次：暂时停止 timer，选择 `releases/<run_id>/release.json` 中已验证批次；备份 active.json 后，用同目录临时文件和原子 replace 恢复该 release JSON。检查 ready 与排名日期，再启动 timer。不要用复制单个信号文件的方式混合批次。
- 重复性失败：检查 Yahoo 可达性、磁盘空间和 provider coverage。FinMind 附加数据只影响对应研究功能，不能默认为 Model A 的阻塞条件。

当前不自动删除旧批次与 provider。磁盘不足时按仓库备份规则安排保留策略，不在排错时删历史资产。Docker 是可选部署方式，本轮没有完成容器构建。

## 模拟账户与访问

当前 `paper.enabled=true`，账户存储为 `data_tw/product/paper/accounts.sqlite3`。以专用演示身份生成一小时令牌，在前端“模拟账户”页输入：

```bash
python scripts/run_product.py paper-token --owner interview
```

令牌只放在请求 Authorization header，不进 URL 或研究请求；不提交、不写入报告。先创建账户、再预览、再明确确认。使用前一已物化交易日，可获得下一开盘模拟结果；最新日期尚无下一交易日行情时，不能生成虚假的成交。账户与旧登录系统独立；未自动迁移旧账户。

8000 当前监听外部网卡，面试可通过已有主机网络入口或 SSH 转发访问。异地公网部署时再配置域名、HTTPS 和访问策略；本轮只验收了本机正式服务与端口。
