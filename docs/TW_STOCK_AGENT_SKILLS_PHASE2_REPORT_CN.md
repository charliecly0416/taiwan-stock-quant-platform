# 台股 Agent Skills Phase 2 执行报告

生成时间：2026-06-04

## 1. 结论

已按 `docs/TW_STOCK_AGENT_SKILLS_PHASE2_EXECUTION_CN.md` 完成 Phase 2，新增用户级 skill：

```text
/home/chuliyang/.agents/skills/tw-stock-data-freshness-diagnosis
```

该 skill 用于只读诊断 FinMind raw、Yahoo/Scrapling qlib、accepted latest、pending asof、daily auto update job 是否一致，并解释 latest 未更新和自动重试状态。

本阶段只执行 GET 与本地文件读取，未触发真实数据更新、provider refresh/publish、accepted latest 切换或任何 POST/PUT/PATCH/DELETE。

建议进入 Phase 3。

## 2. 新增/修改文件清单

用户级 skill：

```text
/home/chuliyang/.agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md
/home/chuliyang/.agents/skills/tw-stock-data-freshness-diagnosis/references/freshness-status-fields.md
/home/chuliyang/.agents/skills/tw-stock-data-freshness-diagnosis/references/data-source-boundary.md
/home/chuliyang/.agents/skills/tw-stock-data-freshness-diagnosis/scripts/fetch_tw_stock_readonly_status.mjs
```

项目内文档：

```text
docs/TW_STOCK_AGENT_SKILLS_PHASE2_REPORT_CN.md
```

## 3. Skill 目录位置

```text
/home/chuliyang/.agents/skills/tw-stock-data-freshness-diagnosis
```

## 4. Skill 触发描述

触发场景覆盖：

- 为什么 latest 没更新。
- Yahoo/Scrapling 后续是否会自动重试。
- FinMind 和 qlib 日期不一致如何解释。
- 检查台股数据新鲜度。
- daily auto update 当前状态。
- daily status 与 latest signals 是否一致。
- latest_asof、accepted latest、pending_asof、fresh_data_wait、run_id、retry status 解释。

输出固定为：

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

## 5. 实际读取证据

helper 脚本执行：

```bash
node /home/chuliyang/.agents/skills/tw-stock-data-freshness-diagnosis/scripts/fetch_tw_stock_readonly_status.mjs http://127.0.0.1:5000 /home/chuliyang/taiwan-stock-quant-platform
```

实际只读 API：

```text
GET http://127.0.0.1:5000/api/tw-stock/quant/ops/daily-auto-update/status
GET http://127.0.0.1:5000/api/tw-stock/quant/signals/health
GET http://127.0.0.1:5000/api/tw-stock/quant/signals/latest?bucket=top30
```

实际本地读取：

```text
data_tw/ops/daily_auto_update/pending_asof.json
data_tw/ops/daily_auto_update/*/job.json
data_tw/experiments/option_c_daily_signal/latest_signal.json
```

读取摘要：

```json
{
  "readonly": true,
  "allowed_methods_used": ["GET", "local_file_read"],
  "forbidden_methods_used": [],
  "latest_asof_match": true,
  "run_id_match": true,
  "pending_asof": "2026-06-03",
  "pending_reason": "fresh_data_wait",
  "fresh_data_wait": true,
  "accepted_latest_asof": "2026-06-02",
  "accepted_latest_run_id": "option_c_daily_signal_20260602_20260603T031450Z",
  "api_unavailable": []
}
```

## 6. Eval Prompt 与输出摘要

### 6.1 Eval 1

Prompt：

```text
为什么 latest_asof 还是昨天，后面会自动重试吗？
```

实际输出摘要：

- 读取了 daily auto-update status、signals health、latest signals、`pending_asof.json` 和最近 job.json。
- 当前 accepted latest 为 `2026-06-02`，run_id 为 `option_c_daily_signal_20260602_20260603T031450Z`。
- 当前存在 `pending_asof=2026-06-03`，`pending_reason=fresh_data_wait`。
- daily status 返回 `next_retry_hint="pending asof 2026-06-03 will be retried by the installed schedule; reason=fresh_data_wait"`。
- 结论：latest 没更新是因为 Yahoo/Scrapling qlib 目标日期数据尚未完整；后续自动化排程会继续重试 pending 日期。
- 不建议人工强切 accepted latest。
- 全程只读。

### 6.2 Eval 2

Prompt：

```text
确认 daily status 和 latest signals 是否一致。
```

实际输出摘要：

- 读取了：

```text
GET /api/tw-stock/quant/ops/daily-auto-update/status
GET /api/tw-stock/quant/signals/latest?bucket=top30
GET /api/tw-stock/quant/signals/health
```

- daily status：

```json
{
  "latest_asof": "2026-06-02",
  "latest_status": "accepted",
  "latest_run_id": "option_c_daily_signal_20260602_20260603T031450Z"
}
```

- latest signals：

```json
{
  "status": "accepted",
  "asof": "2026-06-02",
  "run_id": "option_c_daily_signal_20260602_20260603T031450Z",
  "bucket": "top30",
  "top30_count": 30,
  "top50_count": 50
}
```

- 对比结果：`latest_asof_match=true`，`run_id_match=true`。
- 结论：daily status 与 latest signals 当前一致指向同一个 accepted latest。
- 全程只读。

### 6.3 Eval 3

Prompt：

```text
FinMind 更新了但 Yahoo 没更新怎么办？
```

实际输出摘要：

- 读取了 daily status、pending 文件和最近 job.json。
- 最近已完成关键 job：`daily_tw_stock_auto_update_20260603_20260603T171533Z`。
- 该 job 的状态为 `fresh_data_wait`，`asof=2026-06-03`，`latest_before=2026-06-02`，`latest_after=2026-06-02`。
- 该 job 显示 `finmind_update_triggered=true`、`yahoo_refresh_triggered=true`、`provider_publish_triggered=false`、`latest_signal_updated=false`。
- job message 明确说明 Yahoo/Scrapling 没有产生完整 asof 数据，下一次排程应继续重试同一个 asof。
- 结论：这是数据源发布时间差异或 Yahoo/Scrapling 完整性不足导致的等待状态，不应把 FinMind raw 混入 qlib provider，也不应手工强切 accepted latest。
- 是否需要人工介入：当前不需要；应先等待自动重试。若多次排程持续失败，再单独检查 cron 环境或 Yahoo/Scrapling 可用性，但不属于本 skill 的自动动作。
- 全程只读。

## 7. 只读边界证明

本阶段实际执行过的行为：

- 读取 Phase 2 执行文档。
- 创建用户级 skill 文件。
- 执行 helper 脚本读取允许的 GET/API 与本地 JSON 文件。
- 使用 Phase 1 safety helper 审查 Phase 2 产物。
- 写入本报告。

确认未执行：

- `scripts/run_daily_tw_stock_auto_update.py`
- provider refresh
- provider publish
- accepted latest 切换
- 真实 Yahoo/FinMind 拉取
- POST/PUT/PATCH/DELETE
- broker / quick-trade / order
- target position / target weight

helper 脚本输出中 `forbidden_methods_used=[]`。

## 8. Phase 1 Safety Skill 审查结果

审查 helper 脚本实现：

```bash
node /home/chuliyang/.agents/skills/tw-stock-safety-boundary-review/scripts/audit_tw_stock_diff.mjs /home/chuliyang/.agents/skills/tw-stock-data-freshness-diagnosis/scripts/fetch_tw_stock_readonly_status.mjs
```

结果：

```json
{
  "dangerous_api_hits": [],
  "dangerous_text_hits": []
}
```

审查完整 skill 文档时，Phase 1 helper 命中了 `POST /api/tw-stock/monitor/config`、`/api/quick-trade/`、`/api/broker/`、`target position` 等关键词。人工复核上下文后判定为通过，原因是这些命中全部出现在 `Forbidden Actions` / `Data Source Boundary` 的禁止清单中，用于明确拒绝危险动作，不是可执行入口或行动建议。

## 9. 观察与注意事项

- 当前真实 API 一致指向 `accepted latest asof=2026-06-02`。
- 当前存在 `pending_asof=2026-06-03`，原因是 `fresh_data_wait`。
- daily status 暴露了 `cron_installed_hint=true` 与 next retry hint，说明系统预期后续自动重试 pending 日期。
- 本仓库 `data_tw/experiments/option_c_daily_signal/latest_signal.json` 仍是 self-contained demo 的 `asof=2026-06-01`，而真实 API 当前使用的 accepted latest 来自 `qlib_pipeline/data_tw/...`；诊断时应优先以 daily status 与 latest signals API 的一致性为准，同时把该本地文件作为可读证据而非唯一事实来源。

## 10. 是否建议进入 Phase 3

建议进入 Phase 3。

理由：

- Phase 2 skill 已落在用户级 skills 目录。
- `SKILL.md` 覆盖触发场景、诊断规则、输出格式和只读边界。
- reference 文件完整描述字段口径与数据源边界。
- helper 脚本已验证可读取 GET/API 与本地文件，并输出 asof/run_id/pending/retry 摘要。
- Phase 1 safety skill 审查通过；文档中的危险关键词均为禁止清单上下文。
