---
created_at: 2026-06-01
status: handoff_document
scope: quantdinger_tw_option_c_research_signal_integration
source_project: qlib
target_project: ../QuantDinger
final_evidence_commit: a4179eed3d32fd21c296345fb3fba14f3e01cdaa
---

# QuantDinger 台股量化接入说明：qlib Option C 研究信号方案

本文档面向负责 `../QuantDinger` 项目的 Codex。目标是让 QuantDinger 能够理解并接入本仓库已经完成验证的台股量化研究方案，把 qlib 产出的台股横截面排序信号作为 QuantDinger 的研究观察名单、监控页或分析输入。

重要边界：

```text
本方案当前只产生 research-only signals。
它不是订单系统，不输出目标仓位，不生成可执行交易指令，也未授权自动交易、实盘交易、调参或重训。
```

---

## 1. 项目当前在做什么

本 qlib 项目完成了一条针对台股的 Option C 研究主线：

1. 使用 Yahoo-only 台股数据构建 qlib provider。
2. 使用固定的 Alpha158 + LightGBM 模型 recorder 做横截面预测。
3. 对 150 支已验收的台股 universe 生成每日分数。
4. 输出 top30 / top50 研究信号，供人工观察、QuantDinger 展示或后续研究分析。
5. 保留严格安全边界：不交易、不下单、不调参、不重训、不混用 FinMind fallback。

当前可用的最终入口是：

```text
examples/tw/run_option_c_daily_signal.py
```

最终证据包提交：

```text
a4179eed3d32fd21c296345fb3fba14f3e01cdaa
```

最新已验收 daily signal wrapper v2 审查：

```text
docs/tw_audit/166_codex_audit_round_88_daily_signal_wrapper_v2_report.md
```

---

## 2. QuantDinger 应该把它理解成什么

建议 QuantDinger 把本方案接成一个“台股研究信号输入源”，而不是交易策略执行器。

推荐产品含义：

```text
台股 AI/量化观察名单
台股研究排序
台股候选池
台股 cross-sectional score board
```

不建议使用的含义：

```text
买入建议
卖出建议
自动交易策略
目标持仓
下单列表
```

QuantDinger 可以做的事情：

1. 展示每日 top30 / top50 台股排序。
2. 把 score、rank、asof、recorder id 展示给用户。
3. 与 QuantDinger 已有台股趋势、K 线、监控提醒、回测页面做并列展示。
4. 允许用户把某些 symbol 加入自选、观察、人工复盘列表。
5. 记录历史 daily signal runs，供后续研究和人工比较。

QuantDinger 不应该直接做的事情：

1. 根据 top30/top50 自动下单。
2. 把信号转换为 target position。
3. 触发 broker API、IBKR、quick_trade、live_trading。
4. 在未审查的情况下自动 refresh provider、替换数据源、切换 FinMind。
5. 在 QuantDinger 里重训 qlib 模型或改参数。

---

## 3. qlib 侧关键路径

以下路径均以 qlib 仓库根目录 `/home/chuliyang/qlib` 为基准。

### 3.1 每日信号入口

```text
examples/tw/run_option_c_daily_signal.py
```

常用命令：

```bash
python examples/tw/run_option_c_daily_signal.py --dry-run
python examples/tw/run_option_c_daily_signal.py --max-workers 8
```

显式指定日期，通常只用于测试或复核：

```bash
python examples/tw/run_option_c_daily_signal.py --asof 2026-06-01 --dry-run
python examples/tw/run_option_c_daily_signal.py --asof 2026-06-01 --max-workers 8
```

推荐运行顺序：

1. 先执行 `--dry-run`。
2. 确认 dry-run 返回 `dry_run_preflight_pass`。
3. 再执行正常模式生成信号。
4. QuantDinger 只导入 accepted normal run 的输出。

### 3.2 输出根目录

```text
data_tw/experiments/option_c_daily_signal/
```

指针文件：

```text
data_tw/experiments/option_c_daily_signal/latest_signal.json
```

一次 accepted run 的例子：

```text
data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260601_20260601T121228Z/
```

该目录下主要文件：

```text
prediction.csv
top30_signals.csv
top50_signals.csv
signal_summary.json
formal_validation.json
preflight_status.json
run_metadata.json
artifact_manifest.json
implementation_report.md
```

---

## 4. 当前冻结模型和数据契约

当前 daily signal wrapper 固定使用已经验收的 Option C recorder、config、provider 和 universe。

```text
recorder_id: 950741cfd5f14ee5a05464fec3e12e0a
experiment_id: 607910013167647574
config: configs/tw_yahoo_primary_alpha158.yaml
provider: data_tw/experiments/yahoo_adjusted_primary/qlib_bin
market: tw_liquid_dyn
benchmark: TWII
model: Yahoo-only Alpha158 + LightGBM
universe_count: 150
```

当前 150 支预测 universe 来源：

```text
data_tw/experiments/option_c_forward_validation/timed_data_availability_retry_20260601T101323Z/symbols_accepted_prediction_universe.txt
```

不要在 QuantDinger 接入阶段扩大 universe、替换模型、切换 provider 或重训。若未来要扩展到更多股票，应另开研究主线，重新做数据覆盖、IC、稳定性和运行成本审查。

---

## 5. daily signal 输出契约

### 5.1 latest_signal.json

QuantDinger 最简单的接入方式是读取：

```text
data_tw/experiments/option_c_daily_signal/latest_signal.json
```

示例结构：

```json
{
  "created_at": "2026-06-01T12:12:40+00:00",
  "run_dir": "data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260601_20260601T121228Z",
  "asof": "2026-06-01",
  "top30_signals": "data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260601_20260601T121228Z/top30_signals.csv",
  "top50_signals": "data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260601_20260601T121228Z/top50_signals.csv",
  "diagnostic_only": true,
  "research_signal_not_order": true
}
```

字段含义：

| field | meaning |
| --- | --- |
| `created_at` | 指针更新时间，UTC |
| `run_dir` | 本次 accepted run 目录 |
| `asof` | 信号对应的市场日期 |
| `top30_signals` | top30 CSV 相对路径 |
| `top50_signals` | top50 CSV 相对路径 |
| `diagnostic_only` | 必须为 true，表示诊断/研究用途 |
| `research_signal_not_order` | 必须为 true，表示不是订单 |

### 5.2 top30_signals.csv / top50_signals.csv

CSV 列：

```text
asof,instrument,score,rank,source_model_recorder,diagnostic_only,research_signal_not_order
```

示例：

```csv
asof,instrument,score,rank,source_model_recorder,diagnostic_only,research_signal_not_order
2026-06-01,TW3231,0.133519245576231,1,950741cfd5f14ee5a05464fec3e12e0a,True,True
2026-06-01,TW3189,0.1239334931140571,2,950741cfd5f14ee5a05464fec3e12e0a,True,True
```

字段含义：

| field | meaning |
| --- | --- |
| `asof` | 信号日期 |
| `instrument` | qlib 台股代码，格式如 `TW2330` |
| `score` | 模型预测分数，只能用于排序和研究解释 |
| `rank` | 分数降序排名，1 为最高 |
| `source_model_recorder` | 固定模型 recorder id |
| `diagnostic_only` | 研究/诊断用途标记 |
| `research_signal_not_order` | 非订单标记 |

QuantDinger 如需展示股票代码，可将 `TW2330` 规范化为 `2330`，但数据库中建议同时保留原始 `instrument`，避免来源不清。

### 5.3 signal_summary.json

accepted normal run 关键字段：

```json
{
  "status": "accepted",
  "asof": "2026-06-01",
  "prediction_rows": 150,
  "top30_rows": 30,
  "top50_rows": 50,
  "finite_prediction_share": 1.0,
  "diagnostic_only": true,
  "research_signal_not_order": true,
  "paper_trading_started": false,
  "live_trading_started": false,
  "target_trades_generated": false,
  "executable_orders_generated": false
}
```

QuantDinger 导入前至少检查：

```text
status == accepted
prediction_rows == 150
top30_rows == 30
top50_rows == 50
finite_prediction_share == 1.0
diagnostic_only == true
research_signal_not_order == true
paper_trading_started == false
live_trading_started == false
target_trades_generated == false
executable_orders_generated == false
```

### 5.4 run_metadata.json

用于审计和导入留痕。关键字段：

```text
status
asof
dry_run
frozen_recorder
config
provider_uri
market
benchmark
model_retraining_performed
model_tuning_performed
provider_switch_performed
FinMind_fallback_used
mixed_provider_fill_used
stale_data_policy
artifact_retention_policy
```

QuantDinger 应在导入记录里保存 `run_id`、`run_metadata` 路径和 `source_model_recorder`。

---

## 6. 状态语义

daily signal wrapper 可能出现以下状态。

| status | meaning | QuantDinger action |
| --- | --- | --- |
| `dry_run_preflight_pass` | 预检通过，未生成预测 | 可显示“预检通过”，不要导入 signals |
| `accepted` | 正常生成 top30/top50 | 可导入并展示 |
| `wait_state_data_refresh_needed` | 数据不够新，脚本按 wait-state 停止 | 不导入新信号，提示需要另行审查数据刷新 |
| `blocked_formal_validation_failed` | formal validation 未通过 | 不导入，显示阻塞原因 |
| `failed` | 脚本失败 | 不导入，保留错误日志 |

最重要规则：

```text
只有 status=accepted 的 normal run 可以被 QuantDinger 导入为当日研究信号。
dry-run、wait-state、blocked、failed 都不能生成或替代当日信号。
```

---

## 7. QuantDinger 推荐接入方式

### 7.1 最小可行接入

建议先做只读导入，不改交易模块。

流程：

1. QuantDinger 后端读取 qlib 的 `latest_signal.json`。
2. 根据 `top30_signals` / `top50_signals` 路径读取 CSV。
3. 读取同一 run 目录下的 `signal_summary.json` 和 `run_metadata.json`。
4. 校验状态和 safety flags。
5. 写入 QuantDinger 自己的研究信号表，或先不落库、只提供只读 API。
6. 前端台股监控页展示“qlib Option C 研究排序”。

推荐只读环境变量：

```text
QLIB_TW_OPTION_C_ROOT=/home/chuliyang/qlib
QLIB_TW_OPTION_C_LATEST=data_tw/experiments/option_c_daily_signal/latest_signal.json
```

QuantDinger 不应在第一阶段直接调用数据刷新或 provider rebuild 脚本。

### 7.2 推荐数据库表

如果 QuantDinger 要落库，建议新增独立研究表，不复用订单表、交易表或策略持仓表。

表名建议：

```text
qd_tw_quant_research_signal_runs
qd_tw_quant_research_signals
```

`qd_tw_quant_research_signal_runs` 推荐字段：

| field | type idea | meaning |
| --- | --- | --- |
| `id` | serial / bigint | QuantDinger 内部 id |
| `run_id` | text unique | qlib run 目录名 |
| `asof` | date | 信号日期 |
| `status` | text | 必须为 accepted 才导入 signals |
| `created_at_utc` | timestamptz | qlib 指针或 run 生成时间 |
| `source_root` | text | qlib 根目录 |
| `run_dir` | text | qlib run 相对路径 |
| `top30_path` | text | top30 CSV 路径 |
| `top50_path` | text | top50 CSV 路径 |
| `recorder_id` | text | qlib recorder id |
| `provider_uri` | text | qlib provider |
| `config_path` | text | qlib config |
| `prediction_rows` | int | 应为 150 |
| `finite_prediction_share` | numeric | 应为 1.0 |
| `diagnostic_only` | bool | 应为 true |
| `research_signal_not_order` | bool | 应为 true |
| `raw_summary_json` | jsonb | 原始 summary |
| `raw_metadata_json` | jsonb | 原始 metadata |
| `imported_at` | timestamptz | QuantDinger 导入时间 |

`qd_tw_quant_research_signals` 推荐字段：

| field | type idea | meaning |
| --- | --- | --- |
| `id` | serial / bigint | QuantDinger 内部 id |
| `run_id` | text | 关联 run |
| `asof` | date | 信号日期 |
| `instrument` | text | qlib 原始代码，如 `TW2330` |
| `symbol` | text | QuantDinger 展示代码，如 `2330` |
| `score` | numeric | qlib score |
| `rank` | int | 排名 |
| `bucket` | text | `top30` 或 `top50` |
| `source_model_recorder` | text | recorder id |
| `diagnostic_only` | bool | true |
| `research_signal_not_order` | bool | true |
| `created_at` | timestamptz | 导入时间 |

唯一约束建议：

```text
unique(run_id, bucket, instrument)
unique(asof, bucket, instrument)
```

### 7.3 推荐 API

可以放在 QuantDinger 现有台股 API 命名空间下，例如：

```text
GET  /api/tw-stock/quant/signals/latest
GET  /api/tw-stock/quant/signals/runs
GET  /api/tw-stock/quant/signals/run/<run_id>
POST /api/tw-stock/quant/signals/import-latest
```

第一阶段也可以只实现：

```text
GET /api/tw-stock/quant/signals/latest
```

返回建议：

```json
{
  "status": "ok",
  "asof": "2026-06-01",
  "run_id": "option_c_daily_signal_20260601_20260601T121228Z",
  "diagnostic_only": true,
  "research_signal_not_order": true,
  "top30": [
    {
      "instrument": "TW3231",
      "symbol": "3231",
      "score": 0.133519245576231,
      "rank": 1,
      "source_model_recorder": "950741cfd5f14ee5a05464fec3e12e0a"
    }
  ],
  "top50_count": 50
}
```

错误和阻塞返回建议：

```json
{
  "status": "wait_state_data_refresh_needed",
  "message": "qlib formal data/provider is stale; no new research signal imported",
  "research_signal_not_order": true
}
```

### 7.4 前端展示建议

QuantDinger 前端已有台股监控页时，建议新增一个独立区块：

```text
qlib Option C 研究排序
```

展示字段：

```text
rank
symbol
score
asof
recorder
bucket
```

页面必须明确显示：

```text
研究信号，不是买卖建议或订单
```

建议功能：

1. top30 / top50 tabs。
2. 按 rank 展示。
3. 点击 symbol 跳转 QuantDinger 既有台股趋势/K 线页面。
4. 可添加到观察名单，但默认不创建提醒、不下单。
5. 如果 latest signal stale 或状态不是 accepted，显示阻塞状态。

---

## 8. QuantDinger 调用 qlib 的两种模式

### 模式 A：QuantDinger 只读 qlib 输出

这是推荐第一阶段。

优点：

```text
实现简单
风险低
不需要 QuantDinger 管理 qlib 模型生命周期
不会误触数据刷新、重训或交易路径
```

缺点：

```text
需要 qlib 侧先由人工或 cron 跑 daily signal wrapper
QuantDinger 只消费结果，不负责生成结果
```

### 模式 B：QuantDinger 触发 qlib daily signal wrapper

可以作为第二阶段，但必须加严格限制。

允许触发：

```bash
python /home/chuliyang/qlib/examples/tw/run_option_c_daily_signal.py --dry-run
python /home/chuliyang/qlib/examples/tw/run_option_c_daily_signal.py --max-workers 8
```

禁止触发：

```text
任何 provider rebuild
任何 Yahoo refresh
任何 FinMind fallback
任何 training / tuning
任何 trading / order script
```

如果 QuantDinger 要触发 qlib 命令，建议后端用 allowlist：

```text
allowed_command = ["python", "examples/tw/run_option_c_daily_signal.py"]
allowed_flags = ["--dry-run", "--max-workers", "--asof"]
```

并且必须在 `/home/chuliyang/qlib` 作为 cwd 执行。

---

## 9. 数据新鲜度和 wait-state

daily signal wrapper 不会自动刷新数据。

如果请求的 `asof` 超过 formal source/provider 覆盖范围，状态会变成：

```text
wait_state_data_refresh_needed
```

这不是 bug，是设计边界。原因是数据刷新会改变 formal provider，需要单独审查，不能混入每日信号生成。

QuantDinger 遇到 wait-state 时应：

1. 不生成新的研究信号。
2. 不沿用旧信号冒充今日信号。
3. 显示“qlib 数据未覆盖最新交易日，需要先执行另行审查的数据刷新流程”。
4. 保留上一次 accepted signal，但标记为历史信号。

QuantDinger 不应自动切 FinMind 补洞。当前 Option C 证据路径是 Yahoo-only，FinMind fallback 会改变数据语义，需要另开研究和审查。

---

## 10. 当前验证结论和限制

### 10.1 已完成

已完成并接受：

```text
Option C final evidence package
formal forward validation through first true post-snapshot label date
daily signal wrapper v2
dry-run evidence
stale-data wait-state evidence
accepted normal daily signal run
top30/top50 local output contract
```

最新 accepted normal run：

```text
run_dir: data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260601_20260601T121228Z
asof: 2026-06-01
prediction_rows: 150
top30_rows: 30
top50_rows: 50
finite_prediction_share: 1.0
```

formal validation / labels IC 关键结果：

```text
joined_rows: 150
IC: 0.053062410428110135
RankIC: 0.0396003694441474
```

### 10.2 限制

当前限制：

1. 只有一个 true post-snapshot label slice，不足以授权交易。
2. universe 固定为 150 支，不代表全市场。
3. 数据路径是 Yahoo-only，不应混用 FinMind。
4. daily signal artifacts 是 local operational outputs，默认不提交。
5. 自动刷新、自动重建 provider、自动调参、自动重训都不在当前范围内。
6. `153` formal refresh 中 `pre_refresh_*` backup 曾被 same-root rerun 覆盖，不能作为原始 rollback evidence 描述。

QuantDinger 接入时要保留这些限制，不要在页面或 API 中暗示该信号已经可交易。

---

## 11. 建议给 QuantDinger Codex 的实现顺序

### 阶段 1：只读导入和展示

目标：

```text
把 qlib latest accepted top30/top50 作为 QuantDinger 台股研究信号展示出来。
```

建议任务：

1. 新增 qlib signal reader service。
2. 读取 `latest_signal.json`。
3. 校验 `signal_summary.json` 和 `run_metadata.json`。
4. 解析 top30/top50 CSV。
5. 暴露只读 API。
6. 前端台股监控页增加 research-only ranking 区块。
7. 增加测试，确保状态不是 accepted 时不返回新信号。
8. 增加安全审计测试，禁止导入 live trading / quick trade / broker order 路径。

阶段 1 验收：

```text
latest accepted signal 可显示
wait-state / blocked / failed 不被当成新信号
diagnostic_only 和 research_signal_not_order 被保留
没有订单、仓位、交易 API 调用
```

### 阶段 2：可选落库

目标：

```text
保存历史 signal runs 和 signals，方便 UI 查看历史和人工复盘。
```

建议任务：

1. 新增 migration。
2. 新增 import-latest 脚本或 API。
3. 以 `run_id` 做幂等导入。
4. 增加历史 run API。
5. 增加 UI 历史选择。

阶段 2 仍然禁止交易。

### 阶段 3：可选调度

目标：

```text
QuantDinger 可定时触发 qlib daily signal wrapper，但只触发 dry-run 和 normal signal。
```

建议任务：

1. 后端增加 allowlisted command runner。
2. 先执行 dry-run，pass 后才执行 normal。
3. 遇到 wait-state 只记录状态。
4. 不触发数据刷新。
5. 加超时、日志和错误展示。

阶段 3 仍然不允许 provider mutation。

### 阶段 4：未来研究扩展

以下都需要另开研究主线：

```text
扩展 universe 到更多台股
引入 FinMind 或多源融合
自动刷新 formal provider
多 label slice forward validation
paper trading
交易规则、仓位 sizing、风控
模型重训或调参
```

---

## 12. QuantDinger 侧实现注意事项

### 12.1 路径处理

qlib 输出里大多是相对 qlib repo root 的路径。QuantDinger 读取时要拼接：

```text
/home/chuliyang/qlib + relative_path
```

不要假设 QuantDinger cwd 就是 qlib。

### 12.2 symbol 规范化

qlib 使用：

```text
TW2330
```

QuantDinger 台股模块可能使用：

```text
2330
```

建议：

```text
instrument = TW2330
symbol = 2330
```

两者都保存。不要丢掉 `instrument`。

### 12.3 score 解释

`score` 是模型横截面预测分数，主要用于排序。

不要把 score 解释成：

```text
预期涨幅
胜率
收益率
买入强度
仓位比例
```

推荐展示为：

```text
模型排序分数
研究排序分
cross-sectional score
```

### 12.4 历史信号处理

如果今日没有 accepted run，QuantDinger 可以显示上一条 accepted run，但必须标记：

```text
历史信号
asof=<旧日期>
当前没有新的 accepted qlib signal
```

不要复制旧 run 生成新 asof。

### 12.5 测试建议

QuantDinger 至少应添加以下测试：

1. `latest_signal.json` 指向 accepted run 时，API 返回 top30/top50。
2. `signal_summary.status != accepted` 时，API 不返回新信号。
3. `diagnostic_only != true` 或 `research_signal_not_order != true` 时拒绝导入。
4. `prediction_rows != 150` 时拒绝导入。
5. 缺少 CSV 或 JSON 时返回清晰错误。
6. 安全测试：研究信号接入模块不得 import/call live trading、IBKR、broker、quick_trade、order submission。

---

## 13. 面向执行者的一句话

在 QuantDinger 中先做 qlib Option C daily signal 的只读接入：读取 `/home/chuliyang/qlib/data_tw/experiments/option_c_daily_signal/latest_signal.json`，只接受 `status=accepted` 且 `research_signal_not_order=true` 的 top30/top50，展示为台股研究排序，禁止连接任何交易、订单、重训、调参或数据刷新路径。

---

## 14. 参考文件

qlib 侧核心文件：

```text
examples/tw/run_option_c_daily_signal.py
configs/tw_yahoo_primary_alpha158.yaml
docs/tw_audit/156_option_c_final_forward_validation_summary_report.md
docs/tw_audit/158_option_c_final_evidence_packaging_commit_plan.md
docs/tw_audit/166_codex_audit_round_88_daily_signal_wrapper_v2_report.md
```

qlib 侧核心数据/输出：

```text
data_tw/experiments/option_c_daily_signal/latest_signal.json
data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260601_20260601T121228Z/
data_tw/experiments/option_c_forward_validation/timed_data_availability_retry_20260601T101323Z/symbols_accepted_prediction_universe.txt
data_tw/experiments/yahoo_adjusted_primary/qlib_bin
```

最终证据提交：

```text
a4179eed3d32fd21c296345fb3fba14f3e01cdaa
```

