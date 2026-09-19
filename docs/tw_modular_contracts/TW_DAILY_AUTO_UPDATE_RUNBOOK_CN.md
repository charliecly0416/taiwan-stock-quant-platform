# 台股日更自动化 Runbook

生成日期：2026-06-18

## 2026-09-18 运维审查补充

当前唯一 active baseline 为 Model A；B19R2R 是独立研究影子，不自动切换模型或策略。下文的默认执行说明不代表本机已授权 cron 的全部部署参数，不应照抄示例覆盖现有 crontab。

同日 Model A 已 accepted 后，非 strict 的 full 正交采集若覆盖不完整，在开启 B19 且保护路径未变化时进入独立影子分支。完整市场覆盖仍记录 FAIL；B19 自行检查 Exact-50、TW7769 排除、78F 和 PIT。此分支不得重复发布 A/provider，也不得设置或清除主链 pending。

影子只能绑定同日、同 logical acquisition run 的 A 原始不可变 publish snapshot；缺失或绑定不一致时独立 BLOCKED，不回退到可变 provider。strict 或保护路径漂移仍按阻断规则处理。

日更与 readonly 运维 API 的 `b19r2r_shadow` 状态为 READY、BLOCKED、NOT_ATTEMPTED 或 NOT_OBSERVED；`readiness_scope=status_observation_only` 表示运行状态观察，不表示收益评估或模型准入通过。最近 daily no-op 不应遮蔽最近 full 的影子结果。事件的 `settlement_pending` 不等于已完成自动收益结算。

本轮实际只读观察：A、策略快照和 Agent prompt 日期均为 2026-09-18，无 pending。最近一次真实 full cron 的 B19 为 BLOCKED；同日受控两阶段重试已生成 `READY_RESEARCH_SHADOW`，但状态 API 不把手动重试冒充定时成功。自动 wrapper 已修为先预抓 TWII、再封存 cutoff、最后评分；当前 v2 精确实现仍需下一个合法 full cron 留下自动证据。

日志轮转模板见 `../ops/quantdinger-logrotate.example`；本机已安装到 `/etc/logrotate.d/quantdinger-tw-stock` 并实际轮转 63MB cron 日志。模板使用 copytruncate，有短暂复制/截断竞争，不可用这些日志代替不可变审计记录。HTTP readiness、数据库备份和隔离恢复演练均已完成；总体审查与证据见 `../PRODUCT_OPERATIONS_REVIEW_CN.md`。

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

产品定时任务默认采用双频 scope：

```text
高频：TW_DAILY_AUTO_FINMIND_SCOPE=daily
低频：TW_DAILY_AUTO_FINMIND_SCOPE=full
```

高频 `daily` 负责价格基础日更，避免每两小时重复抓取 quota-heavy 正交数据。

低频 `full` 负责归档：

- daily price；
- corporate actions；
- institutional trades；
- margin trading；
- monthly revenue；
- valuation。

不得只保留 daily scope 而完全取消 full scope：

```text
TW_DAILY_AUTO_FINMIND_SCOPE=daily
```

因为 `daily` scope 会追加：

```text
--no-corporate-actions --no-institutional --no-margin --no-monthly-revenue --no-valuation
```

这会主动跳过法人、融资融券等后续研究需要的正交数据。若为了 quota 或 402 blocker 做降级，必须保留一条低频 full scope cron，或在 job report 中说明 full scope 暂停原因。

当前推荐 cron 形态：

```cron
# Daily price / base freshness, every 2 hours.
30 */2 * * * ... TW_DAILY_AUTO_FINMIND_SCOPE=daily ... scripts/run_daily_tw_stock_auto_update.py

# Orthogonal full scope, once per weekday at Asia/Taipei 22:45.
# It is staggered away from the every-2h daily job to avoid non-blocking flock collision.
45 14 * * 1-5 ... TW_DAILY_AUTO_FINMIND_SCOPE=full TW_DAILY_AUTO_FINMIND_PROVIDER_ERROR_COOLDOWN_HOURS=12 ... scripts/run_daily_tw_stock_auto_update.py
```

R11 后 full scope 具备 segment cache/cooldown：已成功覆盖 asof 的 segment 可复用，402/rate-limit segment 会冷却，避免高频重复打 provider。

R13_R 后 cache 复用还必须通过 origin gate：cache 中的 stdout/stderr 必须存在、位于 repo 的 `data_tw/ops/daily_auto_update/` 下，且不得来自 `/tmp/pytest` 或测试临时目录。若 origin 不合法，自动任务必须忽略该 cache 并重新执行该 segment，不能把空 stdout 当作成功。

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


### 5.6 strict E4 readonly price/TWII bridge

strict E4 readonly chain 仍然是显式非默认 gate：

```text
--enable-strict-e4-readonly-chain
TW_DAILY_AUTO_ENABLE_STRICT_E4_READONLY_CHAIN=true
```

R3_W 后新增的 price/TWII bridge 也是显式参数，默认必须为空：

```text
--strict-e4-readonly-price-bridge-dir <path>
--strict-e4-readonly-twii-bridge <path>
TW_DAILY_AUTO_STRICT_E4_READONLY_PRICE_BRIDGE_DIR=<path>
TW_DAILY_AUTO_STRICT_E4_READONLY_TWII_BRIDGE=<path>
```

合同边界：

- 只有 `--enable-strict-e4-readonly-chain` 开启时，bridge 参数才会传给 YZ2/YZ2R。
- 两个 bridge 参数必须同时提供或同时为空；只提供其中一个时 strict E4 chain `STOP/FAIL`。
- bridge 缺失或覆盖不足时 YZ2/YZ2R 必须失败，不得 fallback 到 stale formal `normalized_nonempty` 伪装成功。
- YZ2 会把 `readonly_price_bridge_used`、`readonly_twii_bridge_used`、source trace、freshness audit 写入产物。
- YZ2R 会把 `readonly_price_bridge_used` 和 source trace 写入产物。
- 该 bridge 不触发 provider publish、accepted latest switch、formal latest write，也不写 `daily_ltr_rerank_latest` 或 `latest_orthogonal_features_latest`。
- 该 bridge 产物仍是 readonly / diagnostic / research signal，不是 production publish。

合同验证器：

```bash
python scripts/validate_tw_daily_strict_e4_readonly_bridge_contract.py \
  --job-json data_tw/ops/daily_auto_update/{job_id}/job.json \
  --json
```

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
| `full_orthogonal_refresh_passed` | 产品 latest 已是目标 asof；完整 segmented acquisition 成功，normalized payload 在目标日观察到 150/150 研究范围且 protected latest 不变。该 observed coverage 不是 authoritative scope/PIT 证明，strict HSA8/Model B gate 可继续保持 blocked。不会追加 quota-aware batch，也不会进入 provider、模型评分或产品 latest 发布。 | 无需处理研究刷新；strict HSA8 状态按 evidence 独立判断。 |
| `full_orthogonal_refresh_incomplete` | 独立 full cron 已运行，但命令、target-asof observed coverage、150 支研究范围或 protected latest unchanged 任一未通过。产品 latest 不回退。 | 检查该 job 的 `full_orthogonal_refresh_evidence.json`，修复明确失败项后重试。 |
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
