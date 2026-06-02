---
created_at: 2026-06-02
status: design_only_disabled_by_default
scope: tw_stock_qlib_option_c_dry_run_scheduler_design
---

# qlib Option C dry-run scheduler 设计草案（默认关闭）

本文件仅定义后续 dry-run-only scheduler 的安全设计，不启用定时任务，不触发任何运行。

## 默认开关

```text
ENABLE_TW_QLIB_OPTION_C_SCHEDULER=false
```

默认值必须为 `false`。未经过单独审核前，服务启动不得自动运行 dry-run。

## 允许命令

scheduler 骨架只能调用固定命令：

```bash
python examples/tw/run_option_c_daily_signal_option_c_provider.py --asof YYYY-MM-DD --dry-run
```

禁止追加或透传以下能力：

- normal signal run
- latest_signal.json 写入
- accepted artifact 生成
- Scrapling refresh
- formal publish
- provider rebuild/overwrite
- broker / order / paper / live / target position

## 安全依赖

启用前必须依赖 Step6 后端能力：

- `data_tw/ops/option_c_jobs/option_c_ops.lock` 多进程文件锁。
- stale lock 检测与失败路径释放。
- dry-run API admin 或 `tw_stock_qlib_ops` / `tw_stock_ops` 权限。
- ops job retention 仅清理 `data_tw/ops/option_c_jobs/option_c_dry_run_*`。

## 运行窗口建议

后续若审核允许实现 scheduler，应先只支持人工配置 asof 解析策略，例如台湾交易日收盘后读取最近可用交易日。实现前不得假设当日数据已经存在。

## 审核门槛

进入启用审核前至少需要：

- 真实 dry-run 闭环已人工执行并通过。
- 浏览器 admin/non-admin smoke 覆盖触发按钮可见性或后端拒绝。
- dangerous requests 计数为 0。
- latest_signal 指纹在 dry-run 前后不变。

## Research-only

scheduler 设计只服务台股 qlib Option C 研究信号运维可观测性，不连接 broker，不写订单，不写持仓，不提供交易执行入口。
