# 台股日更自动化 Runbook

生成日期：2026-06-18

## 1. 目的

本文档说明台股产品日更自动化应如何运行、失败时如何判断、哪些动作允许、哪些动作禁止，以及如何把数据更新、模型信号、策略快照、前端展示和模拟账户只读链路串起来。

当前日更主入口：

```text
scripts/run_daily_tw_stock_auto_update.py
```

当前产品统一前端上下文：

```text
GET /api/tw-stock/current-strategy-context
```

当前产品 registry：

```text
configs/tw_product_artifact_registry.yaml
```

## 2. 当前安全边界

默认日更是 research-only / readonly orchestrator，不是实盘交易脚本。

默认允许：

- 解析目标 asof；
- 维护 pending asof；
- 更新 FinMind / QuantDinger raw archive；
- 在显式配置下发布只读策略快照；
- 记录 job artifact；
- 保留失败原因供下次重试。

默认禁止：

- Yahoo/Scrapling legacy provider publish；
- provider accepted latest 切换；
- qlib accepted latest 切换；
- monitor scan/config save/alerts 写入；
- broker、quick-trade、order；
- 自动切换默认模型或默认策略；
- 在日更脚本中训练模型或调参。

legacy provider publish / accepted latest 代码仍存在，但必须显式传入非默认 gate：

```text
--enable-legacy-provider-publish
```

或者显式环境变量：

```text
TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH=true
```

产品默认路径不得依赖这个 legacy gate。

## 3. 推荐调度方式

台湾市场收盘后，建议每两小时尝试一次。当前脚本会在没有 pending asof 且目标为当天时，等到 Asia/Taipei `18:00` 后才尝试拉取同日数据。

示例 cron：

```cron
30 18,20,22 * * 1-5 cd /home/chuliyang/taiwan-stock-quant-platform && python scripts/run_daily_tw_stock_auto_update.py >> data_tw/ops/daily_auto_update/cron.log 2>&1
30 0,2,4,6 * * 2-6 cd /home/chuliyang/taiwan-stock-quant-platform && python scripts/run_daily_tw_stock_auto_update.py >> data_tw/ops/daily_auto_update/cron.log 2>&1
```

说明：

- 具体时间应以部署机器时区和数据源更新习惯调整。
- 若前一轮因为数据未齐设置了 pending asof，下一轮应优先继续处理 pending asof，而不是跳到新日期。
- 不建议在盘中自动生成下一交易日策略。

## 4. 日更状态目录

主目录：

```text
data_tw/ops/daily_auto_update/
```

每次运行生成：

```text
data_tw/ops/daily_auto_update/{job_id}/job.json
data_tw/ops/daily_auto_update/{job_id}/finmind_stdout.txt
data_tw/ops/daily_auto_update/{job_id}/finmind_stderr.txt
...
```

pending 文件：

```text
data_tw/ops/daily_auto_update/pending_asof.json
```

`pending_asof.json` 语义：

| field | 语义 |
| --- | --- |
| `asof` | 需要继续重试的数据日期。 |
| `reason` | 失败或等待原因。 |
| `job_id` | 设置 pending 的 job。 |
| `updated_at` | 更新时间。 |

## 5. 运行流程

标准流程：

```text
resolve asof
  -> wait gate / pending gate
  -> materialize universe symbols
  -> FinMind raw archive update
  -> optional legacy provider path, default skipped
  -> optional readonly strategy snapshot publish
  -> job.json final status
```

### 5.1 resolve asof

优先级：

1. `--asof YYYY-MM-DD`
2. `pending_asof.json`
3. Asia/Taipei today

如果没有 pending asof 且目标是当天，脚本默认在 Asia/Taipei `18:00` 前返回等待状态。

### 5.2 symbol universe

脚本会从 accepted prediction universe 读取股票池：

```text
qlib_pipeline/data_tw/experiments/option_c_forward_validation/timed_data_availability_retry_20260601T101323Z/symbols_accepted_prediction_universe.txt
```

并落地到本次 job 的：

```text
finmind_symbols.txt
```

如果该 universe 文件缺失，脚本会 fallback 到：

```text
2330
0050
```

这是降级路径，不应被视为产品完整日更成功。

### 5.3 FinMind raw archive update

默认会运行：

```text
backend/scripts/update_tw_stock_daily.py
```

关键参数：

```text
--symbols-file <job_dir>/finmind_symbols.txt
--start <asof - lookback_days>
--end <asof>
--apply
```

默认 lookback：

```text
TW_DAILY_AUTO_FINMIND_LOOKBACK_DAYS=260
```

目的：保留足够历史 bar，避免趋势、复盘和候选解释缺少 120 日样本。

### 5.4 legacy qlib/provider path

默认：

```text
qlib_legacy_provider_path_skipped = true
```

只有显式 legacy gate 打开时，才会进入 Yahoo/Scrapling refresh、provider publish、accepted latest 切换。

这一路径是历史兼容，不是当前产品默认日更路径。

### 5.5 readonly strategy snapshot publish

由环境变量控制：

```text
ENABLE_TW_READONLY_STRATEGY_SNAPSHOT_PUBLISH=false
TW_READONLY_STRATEGY_SNAPSHOT_DRY_RUN=true
```

默认不发布 latest；即使开启，也先写 snapshot，再跑 validator。

只有同时满足：

```text
ENABLE_TW_READONLY_STRATEGY_SNAPSHOT_PUBLISH=true
TW_READONLY_STRATEGY_SNAPSHOT_DRY_RUN=false
validator ok
```

才允许更新：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

latest pointer 只是只读前端快照入口，不是 provider accepted latest，也不是交易目标。

## 6. 推荐产品化日更链路

后续严格产品化应收敛为：

```text
DataSource refresh
  -> DataReadinessGate
  -> FeatureArtifact refresh
  -> Model A Qlib signal
  -> Model B LTR rerank signal
  -> StrategyRule -> OrderIntentArtifact
  -> ReadonlyStrategySnapshot
  -> CurrentStrategyContext API
  -> Frontend / PaperPortfolio
```

其中：

- 默认自动任务可以只跑默认模型和默认策略；
- 当前端切换模型或策略时，后台可以从已拉取数据和已生成信号重新跑策略/回放，但不应重新抓数据；
- 如果新增模型需要更多数据，DataReadinessGate 必须用“只多不少”的检查口径阻断不完整链路；
- 不同模型应共享同一标准数据层，不应各自读取临时数据目录。

## 7. 关键状态码

`job.json.status` 常见值：

| status | 语义 | 处理 |
| --- | --- | --- |
| `already_up_to_date` | latest 已是目标 asof。 | 无需动作。 |
| `today_data_window_wait` | 当天数据窗口未到。 | 等下一轮。 |
| `weekend_no_pending_wait` | 周末且无 pending。 | 无需动作。 |
| `fresh_data_wait` | legacy refresh 未齐。 | 保留 pending，下轮重试。 |
| `provider_publish_failed` | legacy provider publish 失败。 | 不切 latest，保留 pending。 |
| `accepted_latest_failed` | legacy accepted latest 失败。 | 不切 latest，保留 pending。 |
| `accepted_latest_exception` | legacy accepted latest 异常。 | 查 traceback，保留 pending。 |
| `daily_auto_update_passed` | 本轮完成默认日更流程。 | 检查是否有 readonly snapshot warning。 |

## 8. `--latest validator` 失败什么时候发生

readonly snapshot latest validator 失败通常发生在：

- `latest.json` 指向的 snapshot manifest 不存在；
- manifest 的 `artifact_type` / `schema_version` 不符合合同；
- checksum 或 source file audit 不一致；
- snapshot 内 `readonly_only`、`production_trade_enabled=false` 等安全字段缺失；
- manifest 使用的 source artifact 被移动、归档或删除；
- latest pointer 写入成功但随后校验失败。

这不是“拉新数据没拉到”的同义词。拉新数据失败通常体现在 FinMind stderr、provider refresh 状态或 pending asof；latest validator 是快照产物完整性问题。

## 9. 数据齐备判定

日更进入模型/策略前，至少要确认：

| 检查 | 要求 |
| --- | --- |
| price coverage | 目标 universe 有足够价格数据。 |
| FinMind archive | 必要字段更新到目标 asof。 |
| Yahoo/adjusted price | 如果模型或回放需要 next_open/next_close，必须有对应价格。 |
| orthogonal features | LTR 所需正交特征满足 `available_at <= signal_asof`。 |
| qlib top150 | 底座 Qlib 能输出接近 150 支股票。 |
| qlib top50 | top50 能完整作为 LTR 输入。 |
| LTR top50 | LTR 只在 qlib top50 内重排，不新增股票。 |
| execution price | 目标执行日 next_open/next_close 可得。 |

如果任一模型需要的数据缺失，默认应阻断该模型，不应静默 fallback 成另一个模型的结果。

## 10. 前端展示串联

前端应通过统一 API 获取当前上下文：

```text
GET /api/tw-stock/current-strategy-context
```

展示层建议分为：

| 面板 | 数据来源 |
| --- | --- |
| 策略快照 | `strategy_snapshot` + `context` |
| 今日候选 | `rankings.ltr_top10` / `rankings.qlib_top50` |
| 模型切换 | `rankings.model_a` / `rankings.model_b` |
| 策略意图 | OrderIntentArtifact 对应 API |
| 模拟账户 | `paper_portfolio_context` + paper portfolio API |
| 回放窗口 | ReplayResultArtifact 对应 API |

前端不得直接读取旧 `daily_readonly_latest` 或本地 artifact 文件。

## 11. 运维排查顺序

当用户说“今天没有更新”时，按顺序查：

1. 查看最新 job：

```bash
ls -lt data_tw/ops/daily_auto_update | head
```

2. 查看 job status：

```bash
cat data_tw/ops/daily_auto_update/<job_id>/job.json
```

3. 查看是否有 pending：

```bash
cat data_tw/ops/daily_auto_update/pending_asof.json
```

4. 检查统一上下文：

```bash
PYTHONPATH=backend python - <<'PY'
from app.services.tw_stock_current_strategy_context import load_current_strategy_context
p = load_current_strategy_context()
print(p["context"])
print(p["consistency_audit"]["asof_alignment"])
PY
```

5. 如果前端显示旧日期，先确认 API 返回是否旧；如果 API 新但前端旧，再查前端缓存或组件绑定。

## 12. 必跑 validator

日更脚本安全边界：

```bash
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
```

readonly snapshot：

```bash
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

产品上下文 smoke：

```bash
PYTHONPATH=backend python - <<'PY'
from app.services.tw_stock_current_strategy_context import load_current_strategy_context
p = load_current_strategy_context()
assert p["ok"] is True
assert p["readonly_only"] is True
assert p["production_trade_enabled"] is False
assert p["no_write_guarantees"]["does_not_touch_broker_or_orders"] is True
print(p["context"]["signal_asof"], p["context"]["default_model_id"], p["context"]["strategy_rule"])
PY
```

前端构建：

```bash
cd frontend
corepack pnpm build
```

## 13. 修改日更链路的规则

允许的小改：

- 补充日志；
- 补充 validator；
- 增加只读状态输出；
- 从 registry 读取路径替代硬编码；
- 增加 dry-run 参数。

必须另开工作文档和审查的改动：

- 新增真实数据源；
- 改变模型信号生成；
- 改变默认模型或默认策略；
- 改变 snapshot latest pointer 语义；
- 打开 provider publish / accepted latest；
- 接入 monitor 写入；
- 接入 broker/order；
- 改变交易执行价口径；
- 改变前端默认展示逻辑。

## 14. 推荐后续改进

当前日更脚本仍是一个兼容历史路径的总入口。后续可逐步拆为：

```text
data_refresh_runner
data_readiness_gate
feature_refresh_runner
model_signal_runner
strategy_snapshot_runner
readonly_publish_runner
daily_orchestrator
```

但拆分时必须保持：

- `configs/tw_product_artifact_registry.yaml` 是产品路径入口；
- 每个 runner 输出 manifest；
- daily orchestrator 只编排，不内联策略或模型逻辑；
- 失败时保留上一版 latest；
- 所有写入都必须先过 validator；
- 默认仍保持 readonly，不触发真实交易。
