# Phase U0 合同冻结与当前日更链路审计执行报告

生成日期：2026-06-17

## 1. 执行范围

本阶段根据 `docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_PRODUCTIZATION_MAINLINE_CN.md` 执行 U0：只做合同冻结与现状审计。

本轮没有修改生产代码，没有触发真实日更，没有运行 provider refresh / publish，没有切换 provider accepted latest 或 qlib accepted latest，没有写 monitor config / scan / alerts，没有连接 broker / quick-trade / orders，也没有训练、调参或重算模型分数。

## 2. 已审计入口

### 2.1 既有自动更新入口

| 入口 | 当前状态 | U 主线判定 |
| --- | --- | --- |
| `scripts/run_daily_tw_stock_auto_update.py` | 存在；用于 cron/systemd 风格的 unattended daily update | legacy + 待模块化接入入口；U0 不运行 |
| `docs/tw-daily-auto-update.cron.example` | 存在；示例为台股收盘后每两小时尝试运行 | 文档示例，不代表 U0 授权执行 |
| `data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron` | 存在本机安装标记；UTC 每 2 小时运行，加载 env 并调用日更脚本 | 现状审计对象；U0 不修改、不触发 |
| `data_tw/ops/daily_auto_update/cron.log` | 存在日志路径 | 只读状态来源 |
| `backend/app/services/tw_stock_daily_auto_update_status.py` | 存在 GET 状态服务，读取 latest_signal、pending_asof、last job 和 cron tail | 只读状态展示入口 |
| `/api/tw-stock/quant/ops/daily-auto-update/status` | 后端 GET 路由存在 | 只读状态 API；不是日更触发 API |

未发现 U0 需要新增 systemd/docker worker 入口。本轮没有查询或安装系统 crontab，仅检查仓库内已存在文件。

### 2.2 前端/API 当前读取 latest 的入口

| 入口 | 方法 | 读取对象 | 安全边界 |
| --- | --- | --- | --- |
| `frontend/src/api/tw-stock.js::getTwStockReadonlyStrategySnapshot` | GET | `/api/tw-stock/readonly-strategy-snapshot` | GET-only |
| `backend/app/routes/readonly_strategy_snapshot.py` | GET | latest readonly snapshot 或指定 asof snapshot | 不含 POST/PUT/PATCH/DELETE |
| `backend/app/services/readonly_strategy_snapshot.py` | 本地文件只读 | `data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json` | 校验 readonly、非交易、checksum 和 pointer 安全标志 |
| `data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json` | 文件 pointer | `2026-06-16/manifest.json` | `not_provider_accepted_latest=true`，`not_trade_target_latest=true` |
| `frontend/src/api/tw-stock.js::getLatestQlibOptionCSignals` | GET | `/api/tw-stock/quant/signals/latest` | 读取旧 Option C accepted latest；不是 U 主线 readonly snapshot 默认入口 |

U 主线默认应接入 `readonly_strategy_snapshot/latest.json` 这条 readonly latest pointer，而不是把 `qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json` 当作交易或策略默认入口。

## 3. 当前默认路径审计

### 3.1 Freshness check / asof 解析

`run_daily_tw_stock_auto_update.py` 当前逻辑：

- `resolve_asof()` 优先使用显式 `--asof`，其次使用 `data_tw/ops/daily_auto_update/pending_asof.json`，否则使用 Asia/Taipei today；
- `should_wait_before_pull()` 对当天同日数据设置最早拉取时间，默认 `18:00` Asia/Taipei；
- 若 `latest_signal.json` 已是目标 asof 且未 `--force`，脚本直接返回 `already_up_to_date`；
- 若同日数据窗口未开或周末无 pending asof，则返回 wait/noop 状态。

### 3.2 新数据写入位置

既有脚本默认可能写入：

| 类型 | 路径 | 说明 |
| --- | --- | --- |
| 日更 job | `data_tw/ops/daily_auto_update/<job_id>/job.json` | 记录 job 状态、stdout/stderr 路径和触发标志 |
| pending asof | `data_tw/ops/daily_auto_update/pending_asof.json` | fresh data wait / failure 后重试目标 |
| FinMind raw archive | 通过 `backend/scripts/update_tw_stock_daily.py --apply` 写入 QuantDinger raw archive | 真实数据写入；U0 未触发 |
| legacy Yahoo/Scrapling staged refresh | `qlib_pipeline/data_tw/experiments/option_c_ops/<refresh_job_id>/...` | 仅在显式 legacy gate 后触发 |
| legacy provider publish | `qlib_pipeline/data_tw/experiments/option_c_ops/<publish_job_id>/...` | 仅在显式 legacy gate 后触发 |
| readonly snapshot | `data_tw/artifacts/publish/readonly_strategy_snapshot/<asof>/...` | 由 readonly snapshot publish 脚本生成；默认 env 未开启 |
| readonly latest pointer | `data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json` | 只读研究展示 pointer，不是 provider accepted latest |

### 3.3 Provider refresh / publish / accepted latest

当前脚本包含两类路径：

| 路径 | 默认是否可达 | U 主线判定 |
| --- | --- | --- |
| M3 readonly orchestrator default | 默认路径；`--enable-legacy-provider-publish=false` | 跳过 legacy Yahoo/Scrapling refresh、provider publish、accepted latest switching |
| legacy provider publish path | 需要显式 `--enable-legacy-provider-publish` 或 env gate | legacy；不得作为 U 主线默认路径 |

脚本中 `publish_accepted_latest()` 会配置并调用 Option C accepted latest scheduler，具备切换 `latest_signal.json` 的能力。但该路径在默认 U 主线中禁止纳入，除非后续用户单独确认 provider publish / accepted latest 切换方案。

### 3.4 Monitor / broker / order 写入

审计到的 U0 相关入口没有自动连接 broker / quick-trade / orders。`run_daily_tw_stock_auto_update.py` 的 job payload 明确记录：

```text
orders_enabled=false
connects_to_broker=false
research_signal_not_order=true
```

但前端 API 文件中仍存在 monitor config save、scan、alerts update 等历史产品入口。这些不是 U 主线默认链路，后续 U1-U3 不得调用：

- `saveTwStockMonitorConfig` -> POST `/monitor/config`
- `scanTwStockMonitor` -> POST `/monitor/scan`
- `scanAllTwStockMonitors` -> POST `/monitor/scan-all`
- `updateTwStockAlert` -> PUT `/monitor/alerts/:id`

### 3.5 Readonly latest pointer

当前存在 readonly latest pointer：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

当前内容指向：

```text
asof: 2026-06-16
snapshot_manifest: data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/manifest.json
readonly_only: true
production_trade_enabled: false
not_provider_accepted_latest: true
not_trade_target_latest: true
```

后端 `readonly_strategy_snapshot` loader 会校验 pointer 类型、安全标志、manifest root、readonly 标志、非 target-position 标志和 checksum。

## 4. U 主线候选冻结

本主线冻结一个默认 readonly candidate，不自动引入 fresh qlib 或其他候选为默认：

| 字段 | 冻结值 |
| --- | --- |
| `model_id` | `e4_frozen_qlib_2023_2025_ltr` |
| `model_family` | `ltr` |
| `strategy_rule` | `top50_exit_one_worst_sell` |
| `display_role` | `primary_readonly_candidate` / `readonly_candidate` |
| `is_production_trading_default` | `false` |
| `not_order` | `true` |
| `not_target_position` | `true` |
| `not_investment_advice` | `true` |
| `source_signal_manifest` | `data_tw/artifacts/signals/e4_frozen_qlib_2023_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json` |
| `source_full_rank_manifest` | `data_tw/artifacts/full_rank/frozen_qlib_2018_2022_raw_oos/r9_full_rank_adapter_20260616/manifest.json` |
| `source_strategy_dependency` | `configs/strategy_dependencies/top50_exit_one_worst_sell.yaml` |
| `readonly_snapshot_latest` | `data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json` |

### 4.1 输入 artifacts

当前冻结输入：

- ModelSignalArtifact: `data_tw/artifacts/signals/e4_frozen_qlib_2023_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json`
- FullRankArtifact: `data_tw/artifacts/full_rank/frozen_qlib_2018_2022_raw_oos/r9_full_rank_adapter_20260616/manifest.json`
- StrategyDependency: `configs/strategy_dependencies/top50_exit_one_worst_sell.yaml`
- Shadow daily manifest: `data_tw/artifacts/shadow_modular_daily/2026-06-16/manifest.json`
- Readonly snapshot manifest: `data_tw/artifacts/publish/readonly_strategy_snapshot/2026-06-16/manifest.json`

### 4.2 训练窗口与信号窗口

基于现有 manifest 可冻结：

| 项 | 当前值 |
| --- | --- |
| legacy signal adapter source replay-ready scores | `phasee4_replay_ready_scores_2026.csv` |
| raw OOS score/rank source | `phasee1_raw_oos_score_rank_2023_2026.csv` |
| current ModelSignal window | `2026-01-02..2026-05-07` |
| current row_count | `3950` |
| current candidate_k | `50` |
| current readonly snapshot asof | `2026-06-16` |
| current Option C accepted latest asof | `2026-06-17`，仅作为 legacy latest 现状，不作为 U 主线默认 pointer |

训练窗口从当前文件名和主线命名推断为冻结模型 `2023-2025`；U0 不重新打开训练、调参或分数重算。

### 4.3 Feature / score / rank 依赖

`top50_exit_one_worst_sell` 冻结依赖字段：

```text
date
instrument
candidate_rank
buy_score
full_qlib_rank
signal_asof
available_at
```

排序和退出语义：

```text
buy_score: buy_ordering
full_qlib_rank: exit_worst_rank
max_buy_count: 1
max_sell_count: 1
```

ModelSignal legacy mapping：

```text
candidate_rank <- qlib_rank
buy_score <- phasee3_extended_oos_ltr_score
raw_score <- phasee3_extended_oos_ltr_score
full_qlib_rank <- raw qlib rank source with replay-ready fallback
signal_asof <- legacy signal date
available_at <- date, for historical replay parity only
```

U1 如生成真实 daily ModelSignalArtifact，必须重新声明 `available_at` 的真实 PIT 策略，不能沿用历史 parity 语义来解释实时可得性。

## 5. Legacy 路径与 U 主线 readonly path 划分

### 5.1 Legacy 路径

以下路径存在但不属于 U 主线默认能力：

- `--enable-legacy-provider-publish`
- `examples/tw/run_option_c_yahoo_scrapling_refresh.py`
- `examples/tw/publish_option_c_yahoo_scrapling_refresh.py`
- `publish_accepted_latest(asof)`
- `qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json` 写入或切换
- provider publish / accepted latest scheduler
- frontend/API 中的 qlib ops dry-run / scheduler / latest 运维入口
- monitor config / scan / alerts 写入口

### 5.2 U 主线 readonly path

U1-U3 应接入的 readonly path：

```text
FreshnessCheck
  -> DataIngestionArtifact
  -> FeatureArtifact
  -> ModelSignalArtifact
  -> OrderIntentArtifact
  -> ReadonlyStrategySnapshot
  -> RunRegistry
  -> data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
  -> GET-only API / Frontend display
```

U 主线 daily success 才能更新 readonly latest pointer；失败、no_new_data、validator 未过时必须失败关闭或保持 previous latest。

## 6. U0 通过标准自检

| 标准 | 结果 |
| --- | --- |
| 没有修改生产代码 | pass |
| 没有触发真实日更 | pass |
| 没有切 accepted latest | pass |
| 没有 provider publish | pass |
| 没有 broker/order/monitor 写入 | pass |
| 本主线输入/输出/候选模型策略冻结 | pass |
| 明确 legacy 与 readonly path | pass |

## 7. 下一阶段 U1 入口建议

U1 可以新增 artifact builder / validator，但仍不得触发 provider publish 或 accepted latest switch。建议第一批脚本只支持 dry-run/staging 输出：

```text
scripts/build_tw_daily_data_ingestion_artifact.py
scripts/validate_tw_daily_data_ingestion_artifact.py
scripts/build_tw_daily_feature_artifact.py
scripts/validate_tw_daily_feature_artifact.py
scripts/build_tw_daily_model_signal_artifact.py
scripts/validate_tw_daily_model_signal_artifact.py
```

建议输出根目录：

```text
data_tw/artifacts/daily_data_ingestion/<run_id>/
data_tw/artifacts/daily_features/<run_id>/
data_tw/artifacts/daily_model_signals/e4_frozen_qlib_2023_2025_ltr/<run_id>/
```

U1 必须处理两种状态：

- `fresh_data_detected`：生成 DataIngestion / Feature / ModelSignal artifact，并运行 validator；
- `no_new_data`：生成可审计 noop artifact，不更新 readonly latest pointer。

U1 不得把 `qlib_pipeline/.../latest_signal.json` 的 accepted 状态等同于 U 主线可发布状态；它只能作为 legacy 现状或输入候选，必须通过标准 artifact 和 validator 后才能进入 readonly snapshot 链。
