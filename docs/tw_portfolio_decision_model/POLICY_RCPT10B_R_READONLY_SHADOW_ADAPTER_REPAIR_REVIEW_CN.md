---
created_at: 2026-06-25
status: independent_repair_review
role: RCPT10B_R_independent_reviewer
phase: RCPT10B_READONLY_SHADOW_ADAPTER_REPAIR_REVIEW
production_allowed: false
order_or_target_output_allowed: false
verdict: PASS_WITH_CONDITIONS_FOR_RCPT10C
---

# RCPT10B Repair 独立复审

## 1. 复审结论

本次 RCPT10B repair 复审结论为：

```text
PASS_WITH_CONDITIONS_FOR_RCPT10C
```

判断依据：

1. 上一轮指出的核心 readonly/shadow 语义越界问题已经被修复；
2. 业务 shadow artifacts 已移除 `action_type`、`execution_date`、`buy_signal_count`、`sell_signal_count`、`buy_block_count`、`sell_overlay_trigger_count`；
3. `candidate_decision_trace.csv` 与 `candidate_daily_summary.csv` 已去重到合理水平；
4. validator 已扩展到显式禁字段、隐性动作语义字段、以及 CSV 中孤立 `buy` / `sell` 值扫描；
5. M1-only、M2/M3 forbidden、以及不触碰 replay/training/threshold tuning/production/default/provider/latest/frontend/Agent/monitor/order 的边界仍然保持。

但当前仍有一个需要在进入 RCPT10C 执行前完成的条件：

```text
data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/diagnostic_findings.md
仍保留旧的 FAIL 文案，与当前 validator_report.json / manifest.json 的 PASS 结论不一致。
```

这不是生产边界越权问题，但它会破坏 shadow evidence 的内部一致性，因此本轮给出 `PASS_WITH_CONDITIONS_FOR_RCPT10C`，而不是无条件 PASS。

## 2. 本次已读输入

- [POLICY_RCPT10_M1_PRODUCTION_READINESS_SAFETY_INTEGRATION_MAINLINE_CN.md](/home/chuliyang/taiwan-stock-quant-platform/docs/tw_portfolio_decision_model/POLICY_RCPT10_M1_PRODUCTION_READINESS_SAFETY_INTEGRATION_MAINLINE_CN.md)
- [POLICY_RCPT10B_READONLY_SHADOW_ADAPTER_WORK_CN.md](/home/chuliyang/taiwan-stock-quant-platform/docs/tw_portfolio_decision_model/POLICY_RCPT10B_READONLY_SHADOW_ADAPTER_WORK_CN.md)
- [POLICY_RCPT10B_READONLY_SHADOW_ADAPTER_REVIEW_CN.md](/home/chuliyang/taiwan-stock-quant-platform/docs/tw_portfolio_decision_model/POLICY_RCPT10B_READONLY_SHADOW_ADAPTER_REVIEW_CN.md)
- [POLICY_RCPT10B_R_READONLY_SHADOW_ADAPTER_REPAIR_EXECUTION_REPORT_CN.md](/home/chuliyang/taiwan-stock-quant-platform/docs/tw_portfolio_decision_model/POLICY_RCPT10B_R_READONLY_SHADOW_ADAPTER_REPAIR_EXECUTION_REPORT_CN.md)
- [POLICY_RCPT10B_READONLY_SHADOW_ADAPTER_EXECUTION_REPORT_CN.md](/home/chuliyang/taiwan-stock-quant-platform/docs/tw_portfolio_decision_model/POLICY_RCPT10B_READONLY_SHADOW_ADAPTER_EXECUTION_REPORT_CN.md)
- [build_tw_policy_rcpt10b_readonly_shadow_adapter.py](/home/chuliyang/taiwan-stock-quant-platform/scripts/build_tw_policy_rcpt10b_readonly_shadow_adapter.py)
- `data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/`

## 3. 逐项复审

### 3.1 业务 shadow artifacts 是否已移除指定字段

结论：`PASS`

证据：

- 脚本把隐性动作语义字段列入禁扫名单：[build_tw_policy_rcpt10b_readonly_shadow_adapter.py](/home/chuliyang/taiwan-stock-quant-platform/scripts/build_tw_policy_rcpt10b_readonly_shadow_adapter.py:27)
- `candidate_signal_snapshot.json` 未再出现 `action_type` / `execution_date` / `buy_signal_count` / `sell_signal_count` / `buy_block_count` / `sell_overlay_trigger_count`：[candidate_signal_snapshot.json](/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/candidate_signal_snapshot.json:1)
- `candidate_decision_trace.csv` 列头已不再包含这些字段：[candidate_decision_trace.csv](/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/candidate_decision_trace.csv:1)
- `candidate_daily_summary.csv` 列头已不再包含这些字段：[candidate_daily_summary.csv](/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/candidate_daily_summary.csv:1)
- `validator_report.json` 对上述字段均返回 `present=false`：[validator_report.json](/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/validator_report.json:32)

### 3.2 是否不再出现孤立 buy/sell 业务值

结论：`PASS`

证据：

- validator 新增 `forbidden_business_value_scan`，专门扫描业务 CSV 中孤立 `buy` / `sell` 值：[build_tw_policy_rcpt10b_readonly_shadow_adapter.py](/home/chuliyang/taiwan-stock-quant-platform/scripts/build_tw_policy_rcpt10b_readonly_shadow_adapter.py:347)
- 当前 `validator_report.json` 返回 `ALL_CSV ... PASS`：[validator_report.json](/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/validator_report.json:92)

说明：

`candidate_signal_snapshot.json` 与 `candidate_decision_trace.csv` 中仍可见 `blocked_sell_count` 这样的市场状态/特征字段，但未出现孤立业务值 `buy` / `sell`。本轮复审按 repair 目标判定该项通过。

### 3.3 产物是否去重合理

结论：`PASS`

证据：

- `candidate_decision_trace.csv` 已按 `date + symbol` 唯一，280 行无重复键；
- `candidate_daily_summary.csv` 已按 `date` 唯一，205 行无重复键；
- 脚本显式使用 `seen` 集合按 key 去重：[build_tw_policy_rcpt10b_readonly_shadow_adapter.py](/home/chuliyang/taiwan-stock-quant-platform/scripts/build_tw_policy_rcpt10b_readonly_shadow_adapter.py:267)

独立判断：

`candidate_signal_snapshot.json` 当前只有两条 top symbol snapshot，也未见明显重复；`candidate_decision_trace.csv` / `candidate_daily_summary.csv` 已不再存在上一轮那种显著重复。

### 3.4 validator 是否扩展到隐性交易语义扫描，且扫描范围合理

结论：`PASS_WITH_CONDITIONS`

证据：

- `FORBIDDEN_BUSINESS_TERMS` 已纳入：
  - `action_type`
  - `execution_date`
  - `buy_signal_count`
  - `sell_signal_count`
  - `buy_block_count`
  - `sell_overlay_trigger_count`
  见 [build_tw_policy_rcpt10b_readonly_shadow_adapter.py](/home/chuliyang/taiwan-stock-quant-platform/scripts/build_tw_policy_rcpt10b_readonly_shadow_adapter.py:35)
- `scan_forbidden_fields()` 已将这些字段限制在业务 artifacts 范围内扫描：[build_tw_policy_rcpt10b_readonly_shadow_adapter.py](/home/chuliyang/taiwan-stock-quant-platform/scripts/build_tw_policy_rcpt10b_readonly_shadow_adapter.py:337)
- `scan_forbidden_business_values()` 已新增孤立 `buy` / `sell` 值扫描：[build_tw_policy_rcpt10b_readonly_shadow_adapter.py](/home/chuliyang/taiwan-stock-quant-platform/scripts/build_tw_policy_rcpt10b_readonly_shadow_adapter.py:347)

条件：

当前 `diagnostic_findings.md` 是在草稿 validator 阶段生成，仍写着：

- `required_files_status = FAIL`
- `FAIL_NEEDS_RCPT10B_REPAIR`

见 [diagnostic_findings.md](/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/diagnostic_findings.md:1)

而最终 `validator_report.json` / `manifest.json` 已是 PASS：

- [validator_report.json](/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/validator_report.json:1)
- [manifest.json](/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/manifest.json:1)

因此扫描能力本身已扩展，但最终证据链尚未完全自洽。RCPT10C 启动前应先把 `diagnostic_findings.md` 重生成为最终 PASS 版本。

### 3.5 是否仍保持 M1-only、M2/M3 forbidden

结论：`PASS`

证据：

- `manifest.json` 只声明 `candidate_id = M1_QLIB_SCORE_COMPONENT_PRIMARY`：[manifest.json](/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/manifest.json:1)
- 脚本显式保留 `FORBIDDEN_MAPPINGS`，并在 validator 中扫描非 M1 mapping：[build_tw_policy_rcpt10b_readonly_shadow_adapter.py](/home/chuliyang/taiwan-stock-quant-platform/scripts/build_tw_policy_rcpt10b_readonly_shadow_adapter.py:48)
- `validator_report.json` 的 `m1_only_status = PASS`：[validator_report.json](/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/validator_report.json:1)

### 3.6 是否仍无 replay/training/threshold tuning/production/default/provider/latest/frontend/Agent/monitor/order 越权

结论：`PASS`

证据：

- 脚本输出范围仍限定在 `data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/` 与 execution report：[build_tw_policy_rcpt10b_readonly_shadow_adapter.py](/home/chuliyang/taiwan-stock-quant-platform/scripts/build_tw_policy_rcpt10b_readonly_shadow_adapter.py:12)
- `validator_report.json` 明确：
  - `replay_performed = false`
  - `model_training_performed = false`
  - `threshold_tuning_performed = false`
  - `production_chain_modified = false`
  见 [validator_report.json](/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/validator_report.json:1)
- `forbidden_scope_audit.csv` 仍保持 `no_production_chain_write`、`no_replay_execution`、`no_training`、`no_threshold_tuning` 全 PASS：[forbidden_scope_audit.csv](/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/forbidden_scope_audit.csv:1)

## 4. 额外发现

### 4.1 文档一致性问题

严重度：`Medium`

`diagnostic_findings.md` 是草稿阶段写入，未在最终 validator/manifest 落盘后重写，因此和最终 PASS 证据冲突。

根因见脚本写入顺序：

- 先生成 `draft_validator`
- 再用 `draft_validator` 写 `diagnostic_findings.md`
- 最后才生成正式 `validator_report.json`

见 [build_tw_policy_rcpt10b_readonly_shadow_adapter.py](/home/chuliyang/taiwan-stock-quant-platform/scripts/build_tw_policy_rcpt10b_readonly_shadow_adapter.py:439)

这会导致 shadow artifact 内部证据不一致。RCPT10C 启动前应先修正。

### 4.2 decision trace 存在少量空指标行

严重度：`Low`

`candidate_decision_trace.csv` 至少有 2 行出现 `score/rank/score_component/qlib_score_raw/ltr_score` 为空的情况，例如：

- `2025-07-14,TW6919`

见 [candidate_decision_trace.csv](/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/candidate_decision_trace.csv:13)

这不构成 RCPT10B repair 失败，但 RCPT10C 做 shadow replay diagnostic 时应把它作为 completeness 监控项，而不是继续默默放过。

## 5. 是否可以进入 RCPT10C

结论：`YES, WITH CONDITIONS`

允许进入 RCPT10C 的前提条件：

1. 重新生成 `diagnostic_findings.md`，使其与最终 `validator_report.json` / `manifest.json` 的 PASS 结论一致；
2. RCPT10C 执行时把 decision trace 的空指标行计入 completeness diagnostic，不得把该类缺口误写为 full PASS evidence。

## 6. 最终 verdict

```text
PASS_WITH_CONDITIONS_FOR_RCPT10C
```
