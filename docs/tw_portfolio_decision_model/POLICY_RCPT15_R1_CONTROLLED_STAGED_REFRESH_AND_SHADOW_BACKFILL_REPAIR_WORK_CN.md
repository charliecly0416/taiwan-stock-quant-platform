---
created_at: 2026-06-25
status: work
phase: RCPT15_R1_CONTROLLED_STAGED_REFRESH_AND_SHADOW_BACKFILL_REPAIR
parent_mainline: docs/tw_portfolio_decision_model/POLICY_RCPT15_ISOLATED_SHADOW_BACKFILL_MAINLINE_CN.md
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT15_R0_R_STRICTLY_ISOLATED_SIGNAL_AND_RERANK_BUILDER_CONTRACT_REVIEW_CN.md
user_authorized_external_staged_refresh: true
production_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
latest_pointer_write_allowed: false
order_or_target_output_allowed: false
---

# RCPT15_R1 Controlled Staged Refresh And Shadow Backfill Repair 工作文档

## 1. 背景

RCPT15_R0_R 已确认 `2026-06-18..2026-06-25` 不能从现有本地 artifacts 直接生成严格隔离 shadow backfill：

- 目标日缺少 `option_c signal/top50`。
- O2 orthogonal feature 覆盖不足。
- normalized price / TWII 覆盖不足。
- 现有 rerank 脚本会触碰 latest pointer，不能原样复用。

用户已授权本阶段进行受控数据补齐，但授权范围仅限研究/shadow/staged artifacts，不允许推进 production/latest/provider/order。

## 2. 目标

补齐 RCPT shadow 研究所需的目标日输入，优先覆盖交易日：

```text
2026-06-18
2026-06-19
2026-06-22
2026-06-23
2026-06-24
2026-06-25
```

周末：

```text
2026-06-20
2026-06-21
```

必须标记为 non-trading-day skip，不强行生成信号。

## 3. 授权范围

允许：

- 使用 `qlib_pipeline/examples/tw/run_option_c_yahoo_scrapling_refresh.py` 或等价新脚本进行 Yahoo/Scrapling staged refresh。
- 写入 RCPT15/R1 专用实验目录或 Option C ops staged job 目录。
- 从 staged provider 生成 research-only prediction/top30/top50 artifacts。
- 构建 shadow-only O2 feature/rerank artifacts。
- 生成执行报告、manifest、validator 和审查证据。

不允许：

- provider publish。
- accepted latest switch。
- 修改 `qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json`。
- 修改 `data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/daily_ltr_rerank_latest.json`。
- 修改 production/default/latest/provider/frontend/Agent/monitor/order。
- 生成 `OrderIntent`、`target_weight`、`target_position`、`quantity_instruction`、broker/quick-trade/real order。
- 模型训练、调参、universe 扩展。

## 4. 执行阶段

### R1A Staged Price Refresh

执行者应先尝试：

```text
python qlib_pipeline/examples/tw/run_option_c_yahoo_scrapling_refresh.py \
  --asof 2026-06-25 \
  --start 2015-01-01 \
  --output-root data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/option_c_ops \
  --job-id rcpt15_r1_option_c_yahoo_scrapling_refresh_20260625 \
  --continue-on-error
```

如网络或 proxy 不可用，执行者必须记录失败证据并停止，不得改走 provider publish 或 accepted latest。

### R1B Shadow Signal Builder

若 R1A staged provider validation 与 model smoke 通过，执行者应生成目标交易日的 shadow-only signal artifacts：

```text
prediction.csv
top30_signals.csv
top50_signals.csv
signal_summary.json
artifact_manifest.json
```

输出必须位于：

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/shadow_signals/
```

不得写 formal `option_c_daily_signal` 目录或 latest pointer。

### R1C Shadow O2 Feature Refresh

若本地 DB/raw archive 足够，执行者应构建目标日 PIT-safe O2 feature。若不足，必须记录缺口，不得拉取未授权来源或修改 formal O2 latest。

### R1D Shadow Rerank Builder

若 R1B/R1C 均通过，执行者可生成 shadow-only LTR rerank artifacts。必须输出到 RCPT15_R1 目录，不得写 `daily_ltr_rerank_latest.json`。

## 5. 必需输出

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r1_controlled_staged_refresh_and_shadow_backfill_repair/
```

必须输出：

```text
manifest.json
stage_refresh_status.json
target_date_backfill_matrix.csv
shadow_signal_artifact_index.csv
shadow_o2_feature_status.csv
shadow_rerank_status.csv
dependency_gap_audit.csv
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R1_CONTROLLED_STAGED_REFRESH_AND_SHADOW_BACKFILL_REPAIR_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R1_CONTROLLED_STAGED_REFRESH_AND_SHADOW_BACKFILL_REPAIR_REVIEW_CN.md
```

## 6. 允许结论

```text
PASS_READY_FOR_RCPT14A_RERUN_WITH_NEW_SHADOW_DAYS
PASS_PARTIAL_SHADOW_SIGNALS_ONLY_RERANK_BLOCKED
STOP_NETWORK_OR_STAGED_REFRESH_FAILED
STOP_FEATURE_OR_RERANK_INPUTS_INSUFFICIENT
FAIL_NEEDS_REPAIR_CONTRACT_OR_EVIDENCE_INCOMPLETE
STOP_SCOPE_OR_SAFETY_VIOLATION
```

## 7. 给执行者的命令

```text
请执行 RCPT15_R1_CONTROLLED_STAGED_REFRESH_AND_SHADOW_BACKFILL_REPAIR。用户已授权受控 Yahoo/Scrapling staged refresh，但仍禁止 provider publish、accepted latest switch、latest pointer write、production/default/latest/provider/frontend/Agent/monitor/order 和 order/target/broker。请按 R1A-R1D 顺序执行；任何一步失败都要停止在允许结论内并写完整证据。
```

## 8. 给审查者的命令

```text
请审查 RCPT15_R1 执行报告与 artifacts。重点确认用户授权范围是否被严格限制在 staged/shadow，是否没有 production/latest/provider/order 越界；若补齐成功，判断是否可进入 RCPT14A rerun；若失败，判断失败属于网络、staged refresh、O2 feature 还是 rerank 输入问题。
```
