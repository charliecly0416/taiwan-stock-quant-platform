# DNG15_R-A Same-Lineage Option C Refresh 审查意见

生成时间：2026-06-29

## 1. Verdict

```text
STOP_NEEDS_COORDINATOR_DECISION
```

DNG15_R-A 不能进入 DNG15_R-B。执行者没有生成可消费的 `2026-06-26` same-lineage Yahoo/Scrapling `candidate_normalized`，也没有生成 `staged_qlib_bin`，因此缺少 DNG15_R-B isolated Model A score integration 的最小输入。

本次 STOP 的原因不是发现执行者越权或用错数据源，而是同口径 Yahoo/Scrapling 数据获取被外部网络/访问条件阻断：

```text
proxy: http://127.0.0.1:7890 connection refused
no-proxy: Yahoo chart API HTTP 403 for 300 ticker attempts
```

下一步需要统筹明确选择 repair 路线：更换可用 proxy / 调整 Yahoo same-lineage fetch 方案 / 等待 Yahoo 可用 / 授权 research-only mixed-provider drift validator / 放弃 2026-06-26 staged candidate。

## 2. Findings

### Critical

1. 未生成 `2026-06-26` same-lineage staged candidate，不能进入 DNG15_R-B。
   - `data_tw/catalog/dng15_r_a_same_lineage_option_c_refresh_decision.json` 显示 `decision=NO_STAGED_CANDIDATE_FETCH_BLOCKED`、`status=blocked`、`symbols_success=0`、`symbols_with_asof=0`、`calendar_has_asof=false`。
   - `data_tw/catalog/dng15_r_a_modela_20260626_candidate_readiness.json` 显示 `candidate_input_status=BLOCKED_CANDIDATE_NORMALIZED_NOT_READY`、`staged_provider_calendar_has_asof=false`、`candidate_model_smoke_status=not_run`、`score_generated=false`。
   - 两个 `candidate_normalized` 目录均为空：
     - `data_tw/experiments/dng15_r_a_option_c_ops/dng15_r_a_option_c_yahoo_scrapling_refresh_20260626/candidate_normalized`
     - `data_tw/experiments/dng15_r_a_option_c_ops/dng15_r_a_option_c_yahoo_scrapling_refresh_20260626_noproxy/candidate_normalized`
   - 在 `data_tw/experiments/dng15_r_a_option_c_ops` 下未发现 `staged_qlib_bin` 目录。

### High

1. blocker 证据充分。
   - proxy 作业 `execution_summary.json` / `fetch_report.json` 显示 `proxy_used=true`、`proxy=http://127.0.0.1:7890`、`http_status_counts={"none": 300}`、每个 `.TW`/`.TWO` attempt 均为 `curl: (7) Failed to connect to 127.0.0.1 port 7890`。
   - no-proxy 作业 `execution_summary.json` / `fetch_report.json` 显示 `proxy_used=false`、`http_status_counts={"403": 300}`、150 支标的的 `.TW`/`.TWO` 请求均为 `http_status:403`。
   - 两个作业均 `rows_written=0`、`fetch.status=fail`、`normalized_validation.status=fail`、`normalized_validation.errors=["missing_files"]`。

2. R-A 未满足工作文档通过条件。
   - 未达到 `candidate_normalized symbols_success=150/150`。
   - 未达到 `candidate_normalized symbols_with_asof=150/150`。
   - 未达到 `staged_qlib_bin calendar_has_asof=true`。
   - 未运行 Model A staged smoke，`prediction_rows=0`、`finite_prediction_share=0.0`。

### Medium

1. 执行报告对失败状态描述一致，没有把 blocked artifact 伪装成 ready artifact。
   - 执行报告、decision JSON、readiness JSON 均明确 `not_run` provider/model smoke 和 `production_allowed=false`。

2. 当前 review 不能证明未来换 proxy 后一定成功，只能证明本次 R-A 尝试在现有网络条件下失败。
   - Yahoo 403 可能与出口 IP、请求头、cookie/crumb、Scrapling impersonation 或 Yahoo 当时风控有关，需要 repair 节点重新验证。

### Low

1. 工作区存在大量历史 option_c_ops refresh/publish 产物，广域搜索容易误判为本轮行为。
   - 精确检查 `*dng15_r_a*` 后，未发现 `qlib_pipeline/data_tw/experiments/option_c_ops` 下新增 DNG15_R-A publish/dry-run-publish 目录。

## 3. Mainline Compliance

通过项：

- 已读取 DNG15_R-A 工作文档、执行报告、两个 catalog JSON、DNG15 上轮审查、数据治理主线、coordinator-executor-reviewer workflow skill。
- 执行者只生成了 blocked decision/readiness 和 staged fetch 失败报告，没有生成可消费 staged provider。
- 执行报告明确未进入 dry-run publish，因为 staged refresh 未 ready。
- `source_policy` 明确为 `Yahoo-only; no yfinance; no FinMind fallback; no mixed provider`。

未通过项：

- 未生成 `2026-06-26` same-lineage normalized candidate。
- 未生成 isolated `staged_qlib_bin`。
- 未通过 normalized/provider validator。
- 未运行 Model A staged smoke。
- 因此不得进入 DNG15_R-B。

## 4. Evidence Checked

必读文档：

```text
docs/tw_data_governance/DNG15_R_A_SAME_LINEAGE_OPTION_C_REFRESH_WORK_CN.md
docs/tw_data_governance/DNG15_R_A_SAME_LINEAGE_OPTION_C_REFRESH_EXECUTION_REPORT_CN.md
data_tw/catalog/dng15_r_a_same_lineage_option_c_refresh_decision.json
data_tw/catalog/dng15_r_a_modela_20260626_candidate_readiness.json
docs/tw_data_governance/DNG15_FORMAL_QLIB_PROVIDER_OR_CANONICAL_BRIDGE_REPAIR_REVIEW_CN.md
docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md
/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md
```

补充技能和引用：

```text
.agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md
.agents/skills/tw-stock-data-freshness-diagnosis/references/data-source-boundary.md
.agents/skills/tw-stock-data-freshness-diagnosis/references/freshness-status-fields.md
```

核心作业证据：

```text
data_tw/experiments/dng15_r_a_option_c_ops/dng15_r_a_option_c_yahoo_scrapling_refresh_20260626/reports/execution_summary.json
data_tw/experiments/dng15_r_a_option_c_ops/dng15_r_a_option_c_yahoo_scrapling_refresh_20260626/reports/fetch_report.json
data_tw/experiments/dng15_r_a_option_c_ops/dng15_r_a_option_c_yahoo_scrapling_refresh_20260626/reports/normalized_validation.json
data_tw/experiments/dng15_r_a_option_c_ops/dng15_r_a_option_c_yahoo_scrapling_refresh_20260626_noproxy/reports/execution_summary.json
data_tw/experiments/dng15_r_a_option_c_ops/dng15_r_a_option_c_yahoo_scrapling_refresh_20260626_noproxy/reports/fetch_report.json
data_tw/experiments/dng15_r_a_option_c_ops/dng15_r_a_option_c_yahoo_scrapling_refresh_20260626_noproxy/reports/normalized_validation.json
```

只读核查命令要点：

```text
find data_tw/experiments/dng15_r_a_option_c_ops -maxdepth 3 -type d -name staged_qlib_bin
```

结果为空。

```text
find <job>/candidate_normalized -maxdepth 2 -type f
ls -la <job>/candidate_normalized
```

两个 candidate 目录均没有 normalized CSV 文件。

```text
find qlib_pipeline/data_tw/experiments/option_c_ops -maxdepth 2 -type d -name '*dng15_r_a*'
find data_tw/experiments/dng15_r_a_option_c_ops -maxdepth 4 -type f -name '*publish*'
```

结果为空，未发现 DNG15_R-A publish/dry-run-publish 产物。

## 5. Missing Evidence Or Open Questions

当前缺少进入 R-B 的全部正向证据：

```text
same-lineage candidate_normalized 150/150
same-lineage candidate_normalized symbols_with_asof 150/150
staged_qlib_bin calendar_has_asof=true
provider_validation.status=pass
model_smoke.status=pass
prediction_rows=150
finite_prediction_share=1.0
```

需要统筹决定的问题：

1. 是否提供或授权可用 proxy，并重跑 R-A same-lineage Yahoo/Scrapling fetch。
2. 是否允许修改 Yahoo same-lineage fetch 方案，例如 cookie/crumb/session/header/impersonation repair，但仍保持 Yahoo/Scrapling same-lineage。
3. 是否等待 Yahoo 访问恢复后再重跑。
4. 是否授权 research-only mixed-provider FinMind bridge，并强制新增 drift validator。
5. 是否放弃 `2026-06-26` staged candidate，转向后续交易日路线。

## 6. Forbidden Actions Audit

审查结论：干净。

未发现本轮执行触发：

```text
formal publish
accepted latest switch
latest_signal update
readonly latest publish
Agent latest publish
production switch
broker/order/quick-trade
target_position
target_weight
FinMind fallback
mixed-provider bridge
model training or tuning
```

证据：

- decision JSON 中 `production_allowed=false`、`publish_latest_authorized=false`、`formal_provider_mutated=false`、`formal_normalized_mutated=false`、`latest_signal_updated=false`。
- readiness JSON 中 `score_generated=false`、`formal_provider_unchanged=true`、`latest_signal_unchanged=true`。
- execution summary 中 trading flags 均为 false，且 `research_signal_not_order=true`。
- `qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json` 文件时间仍为 2026-06-17 10:38。
- `data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json` 文件时间仍为 2026-06-18 14:34。
- `data_tw/artifacts/agent_daily_prompt/latest.json` 不存在，未见本轮 Agent latest publish。

## 7. Next Work Document

### DNG15_R-A-R Same-Lineage Fetch Access Repair

推荐下一步不是 DNG15_R-B，而是 DNG15_R-A repair 或统筹决策。

目标：

```text
在不切 formal provider、不 publish latest、不更新 latest_signal、不使用 FinMind fallback 的前提下，
恢复同口径 Yahoo/Scrapling fetch，
重新尝试 2026-06-26 candidate_normalized -> staged_qlib_bin -> validators -> Model A staged smoke。
```

允许：

- 使用统筹确认可用的 proxy。
- 调整 Yahoo/Scrapling 请求访问层，例如 session/cookie/header/impersonation/retry/backoff。
- 只写 isolated DNG15_R-A-R job 目录和新的 execution report/catalog decision。
- 若 staged refresh 成功，可运行 `dry-run-publish` audit，但仍不得 `--mode publish`。

禁止：

- formal provider publish。
- accepted latest switch。
- `latest_signal.json` 更新。
- readonly/Agent latest publish。
- 生产默认模型/策略切换。
- 交易、订单、quick-trade。
- target_position 或 target_weight。
- FinMind fallback 或 mixed-provider bridge，除非统筹单独授权 research-only drift validator route。

最低验收：

```text
candidate_normalized symbols_success=150/150
candidate_normalized symbols_with_asof=150/150
staged_qlib_bin calendar_has_asof=true
provider_validation.status=pass
model_smoke.status=pass
prediction_rows=150
finite_prediction_share=1.0
formal_provider_mutated=false
formal_normalized_mutated=false
latest_signal_updated=false
production_allowed=false
publish_latest_authorized=false
no FinMind fallback
no mixed provider bridge
```

如果统筹不愿继续 Yahoo/Scrapling access repair，则可选择新路线：

- `DNG15_R-X research-only mixed-provider drift validator`：只做研究比较，不生产 publish，不进入 R-B，必须量化 6/25 Yahoo/Scrapling vs FinMind OHLCV/Alpha158/score/rank overlap drift。
- `DNG15_R-W wait-and-retry`：等待 Yahoo 数据/访问恢复，保留当前 STOP。
- `DNG15_R-D abandon_20260626_candidate`：明确放弃 6/26 staged candidate，转向后续交易日，但不得把 6/26 标记为 ready。

## 8. Command For Coordinator

```text
请统筹决定 DNG15_R-A 后续路线：
1. 授权 DNG15_R-A-R 使用可用 proxy / Yahoo access repair 后重跑 same-lineage staged refresh；
2. 或授权 research-only mixed-provider drift validator；
3. 或等待 Yahoo 可用；
4. 或放弃 2026-06-26 staged candidate。

在以上决策前，不得进入 DNG15_R-B isolated Model A score integration。
```
