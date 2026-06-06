# 台股 Agent Skills Phase 2 执行文档：数据新鲜度诊断 Skill

生成时间：2026-06-04

## 1. 本阶段目标

实现：

```text
tw-stock-data-freshness-diagnosis
```

这个 skill 用来诊断 FinMind raw、Yahoo/Scrapling qlib、accepted latest、pending asof、daily auto update job 是否一致，并解释为什么 latest 没更新、系统是否会自动重试。

本阶段只允许 GET 和本地文件读取，不允许触发真实数据更新。

## 2. 前置条件

Phase 1 必须已完成并通过审查，尤其是：

- `tw-stock-safety-boundary-review` 可用于审查本阶段实现。
- `tw-stock-readonly-e2e-acceptance` 可用于最终 smoke/验收。

## 3. 实施位置

优先放在：

```text
~/.agents/skills/tw-stock-data-freshness-diagnosis/
```

## 4. 交付物

```text
~/.agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md
~/.agents/skills/tw-stock-data-freshness-diagnosis/references/freshness-status-fields.md
~/.agents/skills/tw-stock-data-freshness-diagnosis/references/data-source-boundary.md
```

可选脚本：

```text
~/.agents/skills/tw-stock-data-freshness-diagnosis/scripts/fetch_tw_stock_readonly_status.mjs
```

## 5. 只读输入来源

允许 GET：

```text
GET /api/tw-stock/quant/ops/daily-auto-update/status
GET /api/tw-stock/quant/signals/health
GET /api/tw-stock/quant/signals/latest?bucket=top30
```

允许读取本地文件：

```text
data_tw/ops/daily_auto_update/pending_asof.json
data_tw/ops/daily_auto_update/*/job.json
data_tw/experiments/option_c_daily_signal/latest_signal.json
```

禁止：

```text
scripts/run_daily_tw_stock_auto_update.py
provider refresh
publish
accepted latest 切换
真实 Yahoo/FinMind 拉取
任何 POST/PUT/PATCH/DELETE
```

## 6. SKILL.md 必须包含

### 6.1 触发场景

```text
为什么 latest 没更新
Yahoo 后面还会自动重试吗
FinMind 和 qlib 日期不一致怎么办
检查台股数据新鲜度
daily auto update 现在是什么状态
确认 daily status 和 latest signals 是否一致
```

### 6.2 诊断规则

- `daily status latest_asof` 与 `latest signals asof` 一致，且 `run_id` 一致：accepted latest 指向一致。
- `pending_asof` 存在且 `fresh_data_wait=true`：系统正在等待 Yahoo/Scrapling qlib 数据，不应手工强切 accepted latest。
- FinMind 已更新但 Yahoo date max 落后：解释为数据源发布时间差异，等待下一次自动重试。
- status API 不可用：只报告不可用，不触发更新。
- fixture E2E 的 `latest_asof` 不代表真实 accepted latest。

### 6.3 输出格式

```markdown
# 台股数据新鲜度诊断

## 1. 当前状态
## 2. FinMind raw
## 3. Yahoo/Scrapling qlib
## 4. accepted latest
## 5. pending asof / retry
## 6. 是否需要人工介入
## 7. 禁止动作提醒
```

## 7. Eval 要求

至少跑 3 个 prompt：

```text
为什么 latest_asof 还是昨天，后面会自动重试吗？
确认 daily status 和 latest signals 是否一致。
FinMind 更新了但 Yahoo 没更新怎么办？
```

每个 eval 必须说明：

- 实际读取了哪些 GET/API/文件。
- 是否发现 asof/run_id 不一致。
- 是否有 pending asof。
- 是否建议人工介入。
- 是否保持只读。

## 8. 报告断点

Phase 2 完成后提交：

```text
docs/TW_STOCK_AGENT_SKILLS_PHASE2_REPORT_CN.md
```

报告必须包含：

- 新增/修改文件清单。
- skill 目录位置。
- 3 个 eval prompt 与输出摘要。
- 只读边界证明。
- Phase 1 safety skill 审查结果。
- 是否建议进入 Phase 3。

