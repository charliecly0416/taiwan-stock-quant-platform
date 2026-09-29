# 2026-09-29 首个交易日日更链路检查

检查时间：2026-09-29 11:41 UTC。范围是正式 systemd 运行目录 `/home/chuliyang/.local/share/tw-stock-clean/releases/clean-20260928-ops`，只读读取服务状态、日志、产物和 GET API；未使用图片工具。

## 结论

第一次 scheduled attempt 在 10:30 UTC 因正式隔离 venv 缺少 `scrapling` 失败，状态被正确记录为 `BLOCKED`，旧的 2026-09-24 release 保持服务。补齐 `scrapling[fetchers]==0.4.8` 并通过 `pip check` 后，11:30 UTC 的系统 timer 自动重试成功，11:40 UTC 健康检查恢复 `OK`，无告警。

这证明 timer、失败隔离、依赖修复、Yahoo 增量行情、Model A、策略、Agent 产物、active 指针和 API 已串通。第一次失败暴露了部署依赖漏项，已在提交 `8238362` 固定；GitHub CI 已通过。

## 自动运行证据

- 10:30 UTC：`clean-daily.service` 由 `clean-daily.timer` 触发，失败原因是 `ModuleNotFoundError: scrapling`；`daily_status.json` 和 `scheduler_status.json` 均为 `BLOCKED`，`latest_pointer_written=false`。
- 11:30 UTC：仍由 `clean-daily.timer` 自动触发；provider refresh 完成，`clean-daily.service` 以 exit 0 结束，耗时约 5 分 9 秒。
- 11:40 UTC：`clean-health.service` 自动检查为 `OK`，`SCHEDULED` 状态、asof 和 run_id 均已更新到成功批次。
- 数据刷新：Yahoo provider `source_symbols=1986`，可用 `1934`，coverage `0.9738`，没有 fetch errors，calendar 最新日期为 `2026-09-29`。
- 备份、health、daily 三个 timer 仍为 enabled；Web 保持 active，两个 API 端口 ready。

## 产物链路

成功 run_id：`2026-09-29-2026-09-29T11:30:01.800898+00:00-17ce733e`

| 环节 | 结果 |
| --- | --- |
| provider / prices | READY，asof 2026-09-29 |
| Model A signal | READY，150 行、150 个唯一标的、rank 1–150 |
| Strategy intent | READY，50 行、50 个唯一标的；`top50_exit_one_worst_sell` / `next_open` |
| Agent DailyPrompt | READY，signal_asof 2026-09-29，manifest validation ok |
| active release | 已原子切换到 2026-09-29 run |
| `/api/ready` | HTTP 200，ready=true，asof 2026-09-29 |
| rankings API | HTTP 200，150 rows |
| strategy API | HTTP 200，50 intents |
| Agent context | HTTP 200，asof 2026-09-29，策略 50 条 |
| `/api/tw-stock/overview` | HTTP 200，prices latest_asof/calendar_latest 2026-09-29；Model A READY |

B19R2R 仍为 shadow-only，状态 SKIPPED/非阻塞；没有切换默认模型，也没有产生真实订单。

## 1964 与 150 的关系

本次 provider refresh 的 `source_symbols=1986`、可用 1934 是行情抓取和流动性筛选输入规模；Model A 发布前严格筛出并评分 150 支，策略再取 Top50。API 和物化信号均已核对为 150，不会把全市场数量直接展示成模型排名数量。

## 证据路径

- `data_tw/product/artifacts/daily_status.json`
- `data_tw/product/artifacts/scheduler_status.json`
- `data_tw/product/artifacts/active.json`
- `data_tw/product/artifacts/ops/health.json`
- 成功 release 的 `release.json`
- `signals/model_a/2026-09-29/manifest.json`
- `intents/model_a/2026-09-29/manifest.json`
- `agent_daily_prompt/2026-09-29/manifest.json`
- `tmp/clean_operations_20260928/freshness_fix_tests.log`
- `tmp/clean_operations_20260928/runtime_pip_check.log`

下一次 19:30、20:30 台北时间 timer 仍会按计划运行；本次检查没有手动启动日更，也没有把手动运行当作自动证据。
