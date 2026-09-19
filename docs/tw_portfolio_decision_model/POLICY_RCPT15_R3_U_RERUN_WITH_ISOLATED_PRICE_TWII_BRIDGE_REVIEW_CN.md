---
created_at: 2026-06-26
status: review
phase: RCPT15_R3_U_RERUN_WITH_ISOLATED_PRICE_TWII_BRIDGE
verdict: PASS
reviewer_role: independent_reviewer
production_allowed: false
provider_publish_default_allowed: false
accepted_latest_switch_allowed: false
network_allowed: false
order_or_target_output_allowed: false
---

# RCPT15_R3_U Rerun With Isolated Price / TWII Bridge 重新审查意见

## 1. Verdict

```text
PASS
```

R3_U 执行产物已出现，复审确认其满足合同 pass gate：

```text
feature_whitelist_count = 78
missing_required_feature_count = 0
feature_package_rows = 250
rerank_score_rows = 250
top30_rows = 150
top50_rows = 250
stock_price_bridge_used = true
twii_bridge_used = true
price_latest_used_date_max = 2026-06-25
market_latest_used_date_max = 2026-06-25
pit_pass = true
forbidden_pass = true
no_network = true
no_fallback_or_fake_rerank = true
```

## 2. Findings

### Critical

无。

### High

无。

### Medium

无。

### Low

- `no_network` 主要由脚本源码静态检查、执行报告、manifest/validator、`forbidden_scope_audit.csv` 共同证明；本复审未重新运行执行脚本，也未采集 OS 级网络 trace。鉴于 R3_U 合同禁止审查者代跑补产物，当前证据足以闭环。

## 3. Mainline Compliance

已阅读并使用以下文件作为复审依据：

```text
/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_U_RERUN_WITH_ISOLATED_PRICE_TWII_BRIDGE_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_T_COORDINATOR_CLOSURE_AND_NEXT_STEP_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_U_RERUN_WITH_ISOLATED_PRICE_TWII_BRIDGE_EXECUTION_REPORT_CN.md
scripts/build_tw_policy_rcpt15_r3_u_rerun_with_isolated_price_twii_bridge.py
```

复审结论：

```text
R3_T stock_price_bridge 显式使用：通过
R3_T twii_bridge.csv 显式使用：通过
不读取 stale formal normalized_nonempty 作为 price/TWII source：通过
完整 78-feature package：通过
PIT gate：通过
freshness gate：通过
frozen O4 rerank：通过
diff artifacts：通过
forbidden scope：通过
```

## 4. Evidence Checked

### 4.1 Artifact 存在性

输出目录存在：

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r3_u_rerun_with_isolated_price_twii_bridge/
```

合同必需 artifacts 均存在：

```text
manifest.json
validator_report.json
feature_package.csv
feature_schema_audit.csv
feature_source_trace.csv
pit_audit.csv
forbidden_scope_audit.csv
rerank_score_snapshot.csv
rerank_top30.csv
rerank_top50.csv
freshness_before_after_audit.csv
rerank_diff_vs_r3_r.csv
top30_overlap_by_day.csv
rank_change_summary.csv
```

执行报告存在：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R3_U_RERUN_WITH_ISOLATED_PRICE_TWII_BRIDGE_EXECUTION_REPORT_CN.md
```

### 4.2 Manifest / Validator

`manifest.json` 与 `validator_report.json` 核心值：

```text
verdict = PASS_READY_FOR_REVIEW
ok = true
model_load_ok = true
feature_whitelist_count = 78
missing_required_feature_count = 0
coverage_pass = true
pit_pass = true
forbidden_pass = true
feature_package_rows = 250
rerank_score_rows = 250
top30_rows = 150
top50_rows = 250
stock_price_bridge_used = true
twii_bridge_used = true
price_latest_used_date_max = 2026-06-25
market_latest_used_date_max = 2026-06-25
price_latest_fresh_enough = true
market_latest_fresh_enough = true
bridge_source_pass = true
no_network = true
no_fallback_or_fake_rerank = true
no_training_or_tuning = true
no_order_target_quantity_broker = true
formal_normalized_nonempty_used_for_price_or_twii = false
```

### 4.3 显式使用 R3_T Bridge

脚本显式绑定：

```text
PRICE_DIR = R3_T_BRIDGE / "stock_price_bridge"
TWII_BRIDGE = R3_T_BRIDGE / "twii_bridge.csv"
```

`feature_source_trace.csv` 复查：

```text
r3_t_isolated_stock_price_bridge rows = 250
r3_t_isolated_twii_bridge rows = 250
max latest_used_date = 2026-06-25
max latest_available_at = 2026-06-25
normalized_nonempty references in trace = 0
```

`input_artifact_inventory.csv` 复查：

```text
r3_t_stock_price_bridge_dir access = read, exists = true
r3_t_twii_bridge access = read, exists = true
stale_formal_normalized_nonempty access = not_used
```

### 4.4 78-feature / PIT / Coverage

`feature_schema_audit.csv`：

```text
rows = 78
status pass = 78
present_in_feature_package true = 78
training_status training_feature = 78
source families:
  R2 isolated O2 = 44
  R3_T isolated stock_price_bridge = 15
  R1 shadow top50 derived = 12
  R3_T isolated twii_bridge = 7
```

`feature_package.csv`：

```text
rows = 250
feature days = 5
rows per day = 50
forbidden feature columns found = 0
```

`pit_audit.csv`：

```text
rows = 20
status pass = 20
feature families checked:
  institutional_flow
  margin_short
  r3_t_isolated_twii_bridge
  r3_t_isolated_stock_price_bridge
used_date_gt_asof_rows = 0 for all rows
available_at_gt_asof_rows = 0 for all rows
```

`coverage_audit.csv`：

```text
rows = 20
status pass = 20
coverage_ratio = 1.0 for checked families/days
```

### 4.5 Frozen O4 Rerank

脚本显式读取：

```text
O4_MODEL = data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_treatment_model.pkl
O4_WHITELIST = data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_feature_whitelist.csv
```

`model_load_audit.json`：

```text
model_exists = true
load_ok = true
loaded_with_pickle = true
frozen_model_used_for_predict = true
model_class = lightgbm.sklearn.LGBMRanker
model_feature_name_count = 78
model_sha256 = 5f98a74c3c8f7d2c0b95858d57ac766fd98eed89dd1cba5c2ca71c0a5d79426d
```

`rerank_score_snapshot.csv`：

```text
rows = 250
ltr_score finite = true
each eligible day rank range = 1..50
diagnostic_only = true for 250 rows
research_signal_not_order = true for 250 rows
```

### 4.6 Freshness / Diff Artifacts

`freshness_before_after_audit.csv`：

```text
rows = 5
status pass = 5
baseline price latest max = 2026-06-01
current price latest max = 2026-06-25
baseline market latest max = 2026-05-21
current market latest max = 2026-06-25
stock_price_bridge_used = true
twii_bridge_used = true
formal_normalized_nonempty_used_for_price_or_twii = false
```

`rerank_diff_vs_r3_r.csv`：

```text
rows = 250
merge_status both = all compared rows
score/rank deltas present
membership change flags present for top1/top5/top10/top30
```

`top30_overlap_by_day.csv`：

```text
rows = 5
overlap_count range = 21..25
r3_r_top30_count = 30 for all rows
r3_u_top30_count = 30 for all rows
top30_same_set = false for all rows
```

`rank_change_summary.csv`：

```text
ALL compared_rows = 250
ALL changed_rank_rows = 237
score_delta_min/median/max = -1.1848899690120602 / -0.03601045542602138 / 0.9886115799858244
rank_delta_min/median/max = -43 / 1.0 / 43
top30_membership_changed_rows = 70
top5_membership_changed_rows = 36
```

这些 diff artifacts 能解释 R3_U 相对 R3_R 的变化：freshness 明确从 stale formal price/TWII 提升到 R3_T isolated bridge，rerank score/rank/top30 集合均产生可量化变化。

## 5. Missing Evidence Or Open Questions

无阻塞缺失证据。

剩余低风险说明：

```text
本复审未重新运行 R3_U 脚本。
本复审未采集 OS 级网络审计日志。
```

该说明不影响闭环，因为脚本源码未出现网络库/API 调用，artifact/validator/forbidden audit 均声明并支持 no network，且执行产物已满足合同 gate。

## 6. Forbidden Actions Audit

`forbidden_scope_audit.csv`：

```text
network_access = PASS_NOT_PERFORMED
formal_latest_signal_pointer_write = PASS_NOT_PERFORMED
daily_ltr_rerank_latest_pointer_write = PASS_NOT_PERFORMED
latest_orthogonal_features_latest_pointer_write = PASS_NOT_PERFORMED
provider_publish = PASS_NOT_PERFORMED
provider_accepted_latest_switch = PASS_NOT_PERFORMED
qlib_accepted_latest_switch = PASS_NOT_PERFORMED
production_default_latest_frontend_agent_monitor_order_mutation = PASS_NOT_PERFORMED
order_target_quantity_broker_artifact = PASS_NOT_PRESENT
model_training_or_tuning = PASS_NOT_PERFORMED
fallback_or_fake_rerank_score = PASS_NOT_USED
forbidden_feature_columns = PASS_NOT_PRESENT
```

脚本静态复查：

```text
未发现 requests / urllib / httpx / aiohttp / curl / wget / Fetcher / yfinance / FinMind / akshare 等联网调用。
写入范围限于 R3_U 输出目录与 R3_U 执行报告。
未发现 provider/latest accepted switch/formal latest/order/target/broker 输出写入。
```

审查者本轮没有 revert 他人改动，没有修改执行脚本，没有重新运行执行脚本。

## 7. Next Work Document

本阶段结论为 `PASS`，可交 coordinator 做闭环。

建议 coordinator closure 记录：

1. `RCPT15_R3_U_RERUN_WITH_ISOLATED_PRICE_TWII_BRIDGE` 通过复审。
2. R3_U 已证明 stale formal price/TWII source 替换为 R3_T isolated fresh bridge 后，R3_R rerank 结果发生可审查变化。
3. 该结果仍为 readonly/research/diagnostic artifact，不得自动升级为 production/default/latest/order/target/broker。
4. 后续若要产品化，应另开 coordinator mainline，先定义 readonly bridge 纳入日更的 contract、acceptance gate 与 rollback policy。

## 8. Command For Executor Or Coordinator

建议 coordinator 执行闭环文档写作，不再派 R3_U repair executor：

```text
请根据 R3_U 执行报告与复审意见，写 RCPT15_R3_U coordinator closure，并决定下一阶段是否进入 readonly bridge 日更产品化合同。
```
