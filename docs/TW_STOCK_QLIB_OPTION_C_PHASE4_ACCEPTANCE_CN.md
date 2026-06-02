---
created_at: 2026-06-02
status: acceptance_report
scope: quantdinger_tw_stock_qlib_option_c_phase4_final_acceptance
role: executor
execution_doc: docs/TW_STOCK_QLIB_OPTION_C_PHASE4_ACCEPTANCE_EXECUTION_CN.md
audit_breakpoint: docs/TW_STOCK_QLIB_OPTION_C_PHASE4_ACCEPTANCE_CN.md
---

# qlib Option C 台股研究信号 Phase 4 最终验收报告

## 1. Phase 4 验收摘要

Phase 4 可以进入收尾。当前证据表明以下闭环已经成立：

```text
盘后 automation 判断
-> EOD pipeline 触发
-> Yahoo-only 数据补齐
-> staged validation
-> Option C 专用 provider publish
-> accepted latest 生成
-> QuantDinger latest reader 输出下一交易日 research ranking
-> 同 asof 幂等跳过
```

最终验收没有扩大能力，没有修改前端，没有启动常驻任务，也没有开启生产默认配置。

## 2. Step 1/2/3 证据索引

Step 1 report：

```text
docs/TW_STOCK_QLIB_OPTION_C_PHASE4_STEP1_REPORT_CN.md
```

结论摘要：

- 已实现 disabled-by-default 的 EOD pipeline。
- 受控真实 smoke 完成 Yahoo-only refresh、staged validation、Option C provider publish、accepted latest update。
- `pipeline_status=eod_pipeline_passed`
- `latest_run_id=option_c_daily_signal_20260601_20260602T082705Z`
- `signals_count=30`

Step 2 report：

```text
docs/TW_STOCK_QLIB_OPTION_C_PHASE4_STEP2_REPORT_CN.md
```

结论摘要：

- 已实现 disabled-by-default 的 EOD automation scheduler 控制层。
- 覆盖 Asia/Taipei 盘后窗口、provider calendar asof 推导、accepted latest 幂等跳过。
- 最新 reader/API 增加 `target_horizon`、`target_date`、research-only 语义字段。
- 本步骤没有真实 refresh/publish/provider mutation。

Step 3 report：

```text
docs/TW_STOCK_QLIB_OPTION_C_PHASE4_STEP3_REPORT_CN.md
```

结论摘要：

- 临时启用 automation/pipeline/accepted scheduler/normal publish 后，automation tick 真实触发完整 EOD pipeline。
- 第一轮 tick：`eod_automation_pipeline_passed`
- pipeline job：`option_c_eod_pipeline_20260601_20260602T090056Z`
- refresh job：`option_c_yahoo_scrapling_refresh_20260601_20260602T090056Z_eod`
- publish job：`option_c_yahoo_scrapling_publish_20260601_20260602T090634Z_eod`
- accepted latest scheduler job：`option_c_accepted_latest_scheduler_20260601_20260602T090704Z`
- latest run：`option_c_daily_signal_20260601_20260602T090715Z`
- 第二轮 tick：`already_accepted_latest`

## 3. 当前 accepted latest 状态

latest pointer：

```text
/home/chuliyang/qlib/data_tw/experiments/option_c_daily_signal/latest_signal.json
```

当前内容摘要：

```text
status=accepted
created_at=2026-06-02T09:07:27+00:00
asof=2026-06-01
run_dir=data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260601_20260602T090715Z
top30_signals=data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260601_20260602T090715Z/top30_signals.csv
top50_signals=data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260601_20260602T090715Z/top50_signals.csv
diagnostic_only=true
research_signal_not_order=true
```

top30 文件行数：

```text
31 /home/chuliyang/qlib/data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260601_20260602T090715Z/top30_signals.csv
```

该 CSV 包含 1 行表头，因此实际 top30 信号数量为 30。

## 4. 自动补数到 latest 闭环结论

Step 3 的自动闭环已通过：

```text
first_tick.status=eod_automation_pipeline_passed
pipeline.status=eod_pipeline_passed
pipeline.asof=2026-06-01
pipeline.data_source_policy=Yahoo-only Scrapling chart API
pipeline.universe=option_c_accepted_150
pipeline.provider_scope=option_c_150
pipeline.refresh_triggered=true
pipeline.provider_mutation_triggered=true
pipeline.latest_signal_updated=true
latest_run_id=option_c_daily_signal_20260601_20260602T090715Z
signals_count=30
```

Yahoo refresh 结果：

```text
source=Yahoo Finance chart API via Scrapling
source_policy=Yahoo-only; no yfinance; no FinMind fallback; no mixed provider
symbols_expected=150
symbols_success=150
symbols_empty=[]
symbols_failed={}
rows_written=396941
```

staged gate：

```text
symbols_success=150
symbols_expected=150
normalized_status=pass
provider_status=pass
model_smoke_status=pass
prediction_rows=150
finite_prediction_share=1.0
```

accepted latest scheduler：

```text
status=accepted_latest_scheduler_passed
asof=2026-06-01
normal_signal_run=true
latest_signal_updated=true
accepted_artifact_generated=true
```

结论：Phase 4 的“盘后自动判断到 latest 可读”闭环已经在受控环境中跑通。

## 5. 下一交易日 research ranking 语义结论

latest reader 证据来自 Step 3 smoke：

```text
status=accepted
asof=2026-06-01
run_id=option_c_daily_signal_20260601_20260602T090715Z
signals_count=30
target_horizon=next_trading_day_research_ranking
target_date=null
signal_semantics=research_only_cross_sectional_ranking
recommendation_semantics=watchlist_not_trade_advice
```

结论：

- 输出是研究排序，不是交易建议。
- `target_horizon=next_trading_day_research_ranking` 已存在。
- `target_date=null` 表示当前 provider calendar 没有更晚交易日可用于明确落点；语义仍为下一交易日研究 ranking。
- `recommendation_semantics=watchlist_not_trade_advice` 明确限制为观察清单，不是下单建议。

## 6. 幂等和防重复结论

同一 `asof=2026-06-01` 已 accepted 后，第二轮 automation tick 返回：

```text
status_code=400
status=already_accepted_latest
message=accepted latest already exists for asof
automation_job_id=option_c_eod_automation_20260601_20260602T090728Z
pipeline_job_id=null
latest_run_id=option_c_daily_signal_20260601_20260602T090715Z
signals_count=30
refresh_triggered=false
provider_mutation_triggered=false
latest_signal_updated=false
```

第二轮 automation job：

```text
type=option_c_eod_automation
status=already_accepted_latest
refresh_triggered=false
provider_mutation_triggered=false
latest_signal_updated=false
```

结论：同 asof 防重复成立，不会重复触发 pipeline、refresh、publish 或 latest 更新。

## 7. 默认关闭和无 loop 结论

当前默认 env：

```text
ENABLE_TW_QLIB_OPTION_C_EOD_AUTOMATION=None
ENABLE_TW_QLIB_OPTION_C_EOD_PIPELINE=None
ENABLE_TW_QLIB_OPTION_C_ACCEPTED_LATEST_SCHEDULER=None
ENABLE_TW_QLIB_OPTION_C_NORMAL_PUBLISH=None
```

Step 3 status 证据：

```text
auto_loop_started=false
loop_enabled=false
```

pipeline env config 证据：

```text
enabled=true
mode=controlled_smoke
auto_loop_started=false
loop_enabled=false
```

accepted latest scheduler 证据：

```text
auto_loop_started=false
refresh_triggered=false
publish_triggered=false
provider_mutation_triggered=false
```

结论：

- 默认未启用。
- 没有启动常驻 loop。
- 没有配置 cron/systemd。
- Phase 4 仍停留在受控 manual/test-client smoke 和 disabled-by-default 状态。

## 8. Yahoo-only 和 provider mutation 边界

Yahoo-only policy：

```text
data_source_policy=Yahoo-only Scrapling chart API
source=Yahoo Finance chart API via Scrapling
source_policy=Yahoo-only; no yfinance; no FinMind fallback; no mixed provider
```

publish summary：

```text
status=publish_complete_waiting_for_review
publish_job_id=option_c_yahoo_scrapling_publish_20260601_20260602T090634Z_eod
provider_scope=option_c_150
publish_result_status=published
```

provider strategy：

```text
Strategy A: Option C dedicated 150-symbol formal normalized/provider; legacy wider provider remains observed-only and is not overwritten
```

formal paths：

```text
formal_normalized=data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized
formal_provider=data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin
legacy_formal_normalized=data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty
legacy_formal_provider=data_tw/experiments/yahoo_adjusted_primary/qlib_bin
```

结论：

- refresh 只使用 Yahoo Scrapling。
- 无 FinMind fallback。
- 无 yfinance。
- 无 mixed provider。
- publish 只影响 Option C dedicated provider。
- legacy provider/normalized 保持 observed-only，没有被覆盖。
- API/UI 未开放 provider path 参数。

## 9. no-trading/research-only 边界

Step 3 automation、pipeline、publish、accepted latest、latest reader 均保持：

```text
orders_enabled=false
connects_to_broker=false
paper_orders_enabled=false
live_trading_enabled=false
quick_trade_enabled=false
writes_orders=false
writes_positions=false
research_signal_not_order=true
```

结论：

- 无 broker 连接。
- 无 quick trade。
- 无 paper/live order。
- 无 target position。
- 无下单。
- 无仓位建议。
- 当前能力严格限定为台股 Option C 研究信号和观察清单。

## 10. 测试结果

已执行：

```text
python -m py_compile backend/app/services/tw_stock_qlib_option_c_eod_automation.py backend/app/services/tw_stock_qlib_option_c_eod_pipeline.py backend/app/services/tw_stock_qlib_option_c.py backend/app/routes/tw_stock.py
```

结果：通过。

已执行：

```text
python -m pytest backend/tests/test_tw_stock_qlib_option_c_ops.py -q
```

结果：

```text
54 passed in 1.27s
```

已执行：

```text
python -m pytest backend/tests/test_tw_stock_qlib_option_c_signals.py backend/tests/test_tw_stock_quant_signal_api.py -q
```

结果：

```text
67 passed in 1.39s
```

本次最终验收报告未涉及前端展示变化，因此未执行前端测试。

## 11. 残余风险和生产启用前提

残余风险：

- Step 3 第一轮 automation 因本地 latest 事前已覆盖 `2026-06-01`，使用了临时 stale reader fixture 绕过 automation 前置 idempotency 判断。影响范围仅限第一轮 tick 的“是否已 accepted”判断；真实 EOD pipeline、Yahoo refresh、provider publish、accepted latest 和 latest reader 都走真实路径。第二轮 tick 已使用真实 latest reader 验证幂等。
- 本次 asof 为 `2026-06-01`，因为执行时 `2026-06-02` 尚未进入 provider calendar。闭环目标已达成，但生产启用仍需要在连续交易日观察。
- Yahoo Scrapling refresh 本次使用本地代理 `http://127.0.0.1:7890`。生产环境需要明确代理可用性、失败重试和网络 SLA。
- 当前没有启用生产 loop/cron/systemd，因此还没有长期调度稳定性证据。

生产启用前提：

- 明确 Yahoo chart API/Scrapling 网络路径和代理策略。
- 建立交易日历更新 SLA，避免盘后 automation 因 calendar 未更新而误判无新 asof。
- 配置失败告警：refresh 失败、symbols 缺失、validation fail、publish fail、accepted latest fail。
- 建立人工值守策略：盘后何时检查、失败如何重跑、何时允许 publish、何时保持旧 latest。
- 保持默认 disabled，只有在验收批准后再显式配置启用项。
- 继续禁止 provider path 从 API/UI 注入，继续禁止 FinMind fallback 和 legacy provider overwrite。
- 继续保持 research-only/no-trading 边界。

## 12. 是否建议 Phase 4 收尾

建议 Phase 4 收尾。

依据：

- Step 1 完成 EOD pipeline skeleton 和真实受控 refresh/publish/latest smoke。
- Step 2 完成 automation 控制层、盘后窗口、calendar asof、幂等逻辑和 latest 语义字段。
- Step 3 完成受控启用 automation tick 到真实 EOD pipeline 的完整闭环，并验证二次 tick 幂等跳过。
- 当前 accepted latest 可读，top30 数量正确。
- Yahoo-only、Option C dedicated provider、legacy 不覆盖边界成立。
- no-trading/research-only 边界成立。
- 默认关闭和无 loop/cron/systemd 成立。
- 后端验收测试全部通过。
