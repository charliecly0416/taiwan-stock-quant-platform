---
created_at: 2026-06-28
status: work_doc
phase: MTRP7_R_CLEAN_DAILY_TIER_A_LINEAGE_REPAIR_AND_RERUN
parent_phase: MTRP7_ISOLATED_DAILY_SHADOW_DRY_RUN
strategy_candidate: top50_hold_rank_buffer_100
readonly_only: true
simulation_only: true
production_allowed: false
production_ready: false
default_switch_allowed: false
formal_phase_yz_write_allowed: false
latest_pointer_mutation_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
broker_authorized: false
---

# POLICY_MTRP7_R_CLEAN_DAILY_TIER_A_LINEAGE_REPAIR_AND_RERUN_WORK_CN

## 1. 目标

修复 MTRP7 的核心 blocker：

```text
tier_a_clean_daily_lineage_less_than_5_days
```

本阶段只允许在隔离路径中补齐 clean daily Tier A lineage，并用该 lineage 重跑 MTRP7。

目标输出：

```text
至少 5 个交易日的 isolated Tier A daily ModelSignalArtifact：
  model_a: qlib full-rank/top150 signal
  model_b: top50 LTR signal
  price: readonly next_open / mark source

然后重跑 isolated daily shadow dry-run，使 MTRP7 达到：
  PASS_READY_FOR_MTRP8_SHADOW_REVIEW
```

## 2. 非目标

本阶段不做：

```text
formal phase_yz 目录写入
production default switch
production registry selectable/default 修改
frontend/API/Agent 代码改动
daily auto 主链路/default path 改动
latest pointer 改动
provider refresh / publish
accepted latest switch
formal PriceStore write
broker / quick-trade / real order
target_weight / target_position / quantity instruction
模型训练 / 新模型 inference / LTR 重算
新收益筛选或调参
```

允许使用已有本地 artifact 做隔离 adapter：

```text
qlib_pipeline/data_tw/experiments/option_c_daily_signal/
data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank/
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/daily_e4_default_candidate/
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/strict_e4_daily_prework/
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/
data_tw/experiments/risk_control_policy_2022/.../stock_price_bridge/
```

但必须只读读取，不得触发 provider、模型训练、模型推理、日更主链路或 latest 切换。

## 3. 当前事实

MTRP7 审查结论：

```text
docs/tw_portfolio_decision_model/POLICY_MTRP7_ISOLATED_DAILY_SHADOW_DRY_RUN_REVIEW_CN.md
verdict = PASS_MECHANICS_READY_LINEAGE_BLOCKED
```

原因：

```text
input_tier = tier_b_repackaged_research_lineage_mechanics_only
tier_a_eligible_day_count = 1
production_lineage_blocker = true
```

正式 `data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/` 目前只有 2026-06-17 一天，不足 5 天。

## 4. Tier A 定义

一个交易日可计为 Tier A eligible，必须同时满足：

```text
model_a rows >= 100，目标 150
model_a 有 full_qlib_rank / candidate_rank / buy_score or raw_score / signal_asof / available_at
model_b rows = 50
model_b buy_score 来自既有 LTR rerank artifact 或已存在 top50 LTR daily artifact
model_b 不得通过本阶段重新训练或重新推理得到
price source 可提供 next_open 与 same-day mark 所需字段
available_at <= signal_asof
PIT audit pass
future label / future return absent
source lineage 与 checksum 可追踪
production_allowed = false
not_published_latest = true
```

注意：

```text
同一 signal_asof 必须同时具备 model_a、model_b、price。
不得用 2026-06-01 的 model_a 拼 2026-06-15 的 model_b。
不得用 replay return、未来收益、未来价格作为 signal/order 输入。
```

## 5. 执行者任务

新增 builder：

```text
scripts/build_tw_policy_mtrp7_r_clean_daily_tier_a_lineage_and_rerun.py
```

输出 root：

```text
data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp7_r_clean_daily_tier_a_lineage_repair_and_rerun/
```

必须输出：

```text
manifest.json
source_inventory.csv
tier_a_lineage_eligibility.csv
isolated_model_signal_register.csv
price_source_register.csv
rerun_mtrp7_summary.json
rerun_mtrp7_validator_report.json
lineage_checksum_audit.csv
pit_available_at_audit.csv
forbidden_field_audit.csv
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

如果能补齐至少 5 天，还应输出：

```text
isolated_phase_yz/yz1_strict_e4_model_signals/{signal_asof}/model_a/
isolated_phase_yz/yz1_strict_e4_model_signals/{signal_asof}/model_b_yz2/
isolated_phase_yz/yz2r_execution_price_readiness/{signal_asof}/
rerun_mtrp7/
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRP7_R_CLEAN_DAILY_TIER_A_LINEAGE_REPAIR_AND_RERUN_EXECUTION_REPORT_CN.md
```

## 6. Builder 要求

执行者必须先 inventory，再构建：

1. 扫描本地可用 source。
2. 按 signal_asof 聚合。
3. 只保留同日同时具备 model_a candidate、model_b LTR top50、price source 的日期。
4. 生成隔离 ModelSignalArtifact，不写 formal phase_yz。
5. 对每个隔离 artifact 生成 manifest/schema/signals/coverage/forbidden audit/source trace。
6. 修改或参数化 MTRP7 builder，使其可读取 isolated Tier A root；不得破坏原 MTRP7 Tier B fallback。
7. 用 isolated Tier A root 重跑 MTRP7。

## 7. Stop Conditions

必须 STOP 或 FAIL 的情况：

```text
同日 Tier A eligible days < 5
需要新训练或新 inference 才能补齐 model_b
需要网络/provider refresh 才能补齐数据
需要写 formal phase_yz / latest / accepted latest / provider
price source 缺 next_open 或 mark coverage
任何 signal/order artifact 含 future_return / label / replay_return / target / quantity / broker 字段
```

## 8. 允许 verdict

执行者 verdict：

```text
PASS_TIER_A_LINEAGE_REPAIRED_MTRP7_READY_FOR_MTRP8
FAIL_NEEDS_MTRP7_R_REPAIR
STOP_INSUFFICIENT_CLEAN_DAILY_TIER_A_INPUTS
STOP_COORDINATOR_DECISION_REQUIRED
```

审查者 verdict：

```text
PASS_TIER_A_LINEAGE_REPAIRED_MTRP7_READY_FOR_MTRP8
FAIL_NEEDS_MTRP7_R_REPAIR
STOP_INSUFFICIENT_CLEAN_DAILY_TIER_A_INPUTS
STOP_COORDINATOR_DECISION_REQUIRED
```

## 9. 审查重点

审查者必须确认：

```text
至少 5 个同日 Tier A clean lineage day
model_a/model_b/price 日期一致
model_b 来自既有 LTR daily artifact，不是本阶段新训练/新推理
隔离输出没有写 formal phase_yz
MTRP7 rerun 使用 Tier A，不再使用 Tier B
rerun verdict = PASS_READY_FOR_MTRP8_SHADOW_REVIEW
production/default/latest/provider/frontend/API/Agent/PriceStore/broker/order/target/quantity 均未触碰
```

## 10. 下一步

若通过：

```text
进入 MTRP8 shadow review / readonly exposure design review。
仍不授权 production default switch。
```

若 STOP：

```text
说明本地现有 artifact 不足以补齐 5 天 Tier A。
下一步应先修 daily auto clean ModelA/ModelB artifact accumulation，而不是继续用 Tier B 推生产。
```
