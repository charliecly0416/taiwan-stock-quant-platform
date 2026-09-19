# 台股研究产品日常运维清单

本文是日常一页式检查表。备份、恢复、日志和部署切换的完整操作见 `STABLE_OPERATIONS_RUNBOOK_CN.md`。

## 1. 每日只读检查

```bash
curl -fsS http://127.0.0.1:5000/api/health
curl -fsS http://127.0.0.1:5000/api/ready | jq '{ready,status,signal_asof,checks}'
curl -fsS http://127.0.0.1:5000/api/tw-stock/quant/ops/daily-auto-update/status \
  | jq '.data | {ok,status,latest_asof,pending_asof,pending_reason,last_job_id,last_job_status,next_retry_hint,b19r2r_shadow}'
curl -fsS http://127.0.0.1:5000/api/tw-stock/quant/ops/readonly-status \
  | jq '.data | {ok,status,qlib_accepted_latest,controlled_signal_latest,readonly_strategy_snapshot_latest,agent_prompt_latest,b19r2r_shadow,latest_natural_cron_job,all_readonly_guards}'
ps -eo pid,cmd | rg 'gunicorn|serve_frontend_static_proxy'
crontab -l
```

正常状态应满足：

- health 返回成功，ready 为 `true`。
- backend 是单个 Gunicorn worker、四线程；frontend static proxy 存活。
- Model A、readonly snapshot 与 Agent prompt 的 `signal_asof`/`target_date` 对齐。
- `pending_asof` 为空，或有明确、仍可重试的原因。
- `all_readonly_guards=true`，orders/broker/quick-trade 均关闭。
- 周末或台湾市场休市日，latest 保持上一有效交易日。
- B19 `BLOCKED` 可以与 Model A ready 同时存在，但必须是 `mainline_blocking=false`。

不要只看最后一条 cron job。周末 no-op 是最新自然任务时，还要查看最近一个工作日成功的 Model A evidence 和最近 full-lane B19 evidence。

## 2. 状态分级

| 状态 | 含义 | 动作 |
| --- | --- | --- |
| 正常 | ready、日期对齐、无 pending | 记录结果，继续观察 |
| 观察 | 主链 ready，B19 blocked 且不阻断 | 保留错误码与 evidence，等待或修复 shadow 原因 |
| 警告 | pending 有合理 provider/cooldown 原因 | 检查下一重试窗口，不改 latest |
| 主链故障 | ready 503、Model A/snapshot/prompt 不一致 | 停止任何发布，按失败 check 定位 |
| 安全故障 | readonly guard 失败、异常 worker 开启 | 停止候选实例，恢复只读环境后再验收 |

## 3. 常见异常

### `/api/ready` 返回 503

先读取响应中的有限错误码：

- `database`：检查 PostgreSQL 服务和部署环境注入，禁止打印连接串。
- `readonly_runtime_boundary`：检查是否误开交易、监控、恢复或支付 worker。
- `research_artifact_contract`：检查 Model A、snapshot、Agent prompt 的路径、日期与 checksum。

readiness 不访问行情 provider。不要把 503 当成理由触发抓取或重训。

### latest 看起来过期

先确认台湾日期、是否交易日、是否已经过合法数据可得窗口。周末和假日保留上一交易日是正确行为。交易日异常时再检查：

```bash
curl -fsS http://127.0.0.1:5000/api/tw-stock/quant/ops/daily-auto-update/status | jq '.data'
```

按 `last_job_id` 查看对应 `data_tw/ops/daily_auto_update/<job_id>/job.json`。区分 raw readiness、qlib accepted latest、controlled signal latest、snapshot 和 Agent prompt；它们不是同一个指针。

### 存在 pending

确认 `pending_asof`、`pending_reason`、`next_retry_hint` 和最近任务的 blocker。provider 数据尚不可得或处于 cooldown 时，让已安装调度在下个窗口重试。不要清空 pending 或用旧数据伪造成功。

如果相同原因跨合法窗口持续失败，再做受控诊断。手工补跑必须指定目标日期、保留独立 job/evidence，且不能冒充自然 cron。

### B19R2R blocked

记录：

- full-lane job ID、asof、finished_at。
- 精确错误码和失败阶段。
- `mainline_blocking`、`production_allowed`、`no_apply`。
- Model A、snapshot、Agent prompt 和 accepted latest 是否未受影响。

B19 失败不要求回滚健康的 Model A。只有当前 v2 自动 full lane 的证据才能证明自动影子运行；人工 `READY_RESEARCH_SHADOW` 只证明受控路径可运行。

### provider quota 或 cooldown

尊重状态中的 retry hint，避免连续请求扩大限流。先使用现有 immutable raw/source evidence 做离线诊断。只有用户明确要求补抓，并且目标日期与 provider 可得性合法时，才运行真实抓取。

### cron drift

比较 live crontab 与 `data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron`。两者应使用 `scripts/run_daily_env.sh`，不得包含明文数据库 URL。不要用 `crontab <template>` 覆盖机器上的其他任务。

## 4. 何时不能手工触发

以下情况先停止并保留证据：

- 当前是周末、假日或目标日数据尚未发布。
- provider 明确 cooldown/quota，且没有用户授权绕开等待策略。
- 目标只是检查服务健康。
- 需要切换 provider/accepted latest、controlled latest 或 baseline 才能继续。
- 无法证明抓取数据的 `available_at`、same-run handoff 或目标日期。
- 手工运行会覆盖自然任务 evidence 或污染 pending。

历史回放可用于研发验证，但必须使用与训练/调参窗口隔离的封存数据，并标记为 historical diagnostic。它不能替代 prospective 证据。

## 5. 周期性检查

每周：

- 检查 cron 日志大小、logrotate 结果和磁盘空间。
- 运行 `python scripts/tw_stock_ops_backup.py plan`，确认 `required_inputs_complete=true` 和无明文凭据 finding。
- 检查 B19 prospective ledger 是否有未结算事件。

部署或重要变更后：

```bash
python scripts/verify_tw_stock_readonly_deployment.py \
  --base-url http://127.0.0.1:5001 \
  --expected-asof YYYY-MM-DD
```

先在备用端口验收，再按稳定运维手册执行切换与回退。不要直接覆盖正在运行的版本或 latest 指针。
