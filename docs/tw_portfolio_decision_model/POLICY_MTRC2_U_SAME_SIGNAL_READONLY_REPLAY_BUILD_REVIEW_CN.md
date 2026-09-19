---
created_at: 2026-06-28
status: review
phase: MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD
verdict: PASS_READY_FOR_MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC
readonly_only: true
simulation_only: true
diagnostic_only: true
research_only: true
production_allowed: false
---

# POLICY_MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD_REVIEW_CN

## 1. 审查范围

本审查只检查 MTRC2_U 是否按合同生成 readonly、simulation-only、diagnostic-only 的 ReplayResultArtifact。

本审查不授权：

```text
production readiness
provider/latest/default/frontend/API/Agent/daily 写入
broker / quick-trade / real order
target_weight / target_position
模型训练、inference、LTR 重算
解除 MTR5 concentration blocker
```

## 2. 读取材料

已读取：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
scripts/build_tw_policy_mtrc2_u_same_signal_readonly_replay.py
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_u_same_signal_readonly_replay_build/
```

使用技能边界：

```text
coordinator-executor-reviewer-workflow
tw-stock-new-strategy-onboarding
tw-stock-new-model-onboarding
```

其中 `tw-stock-new-model-onboarding` 只用于确认 ModelSignal 边界；本审查未授权、未执行训练或 inference。

## 3. Artifact 与合同检查

MTRC2_U 产物目录存在，且包含工作文档要求的 15 个文件：

```text
manifest.json
summary.csv
actions.csv
daily_nav.csv
position_snapshots.csv
coverage_audit.csv
position_integrity_audit.csv
forbidden_field_audit.csv
execution_audit.csv
forbidden_action_audit.json
skipped_actions.csv
daily_cash_audit.csv
input_manifest_links.json
validator_report.json
diagnostic_findings.md
```

字段检查结论：

```text
summary.csv required fields: pass
actions.csv required fields: pass
daily_nav.csv required fields: pass
position_snapshots.csv required fields: pass
coverage_audit.csv required fields: pass
position_integrity_audit.csv required fields: pass
forbidden_field_audit.csv required fields: pass
execution_audit.csv required fields: pass
```

`position_snapshots.csv` 额外包含 `mark_price_date`、`mark_price_policy`。这是 mark-to-market fallback 审计扩展，不违反 ReplayResult 合同。

## 4. 输入来源检查

`manifest.json` 与 `input_manifest_links.json` 显示 MTRC2_U 只消费以下输入：

```text
MTRC2_S OrderIntent manifest/order_intents
MTRC2_T_R price bridge manifest/prices/join audit
MTRC2_T gate rerun manifest/validator
MTRC1D signal manifest 作为 lineage link
```

未发现复用旧 MTR2_R/E3 replay 作为输入。`validator_report.json` 中：

```text
old_mtr2r_replay_not_reused = true
input_order_intent_artifact_equals_mtrc2_s = true
input_price_bridge_artifact_equals_mtrc2_t_r = true
mtrc2_t_gate_rerun_passed = true
signal_artifact_equals_mtrc1d = true
```

## 5. Replay 执行约束检查

执行报告与独立抽查结果一致：

```text
order_intent_count = 2378
active_action_count = 2332
buy_count = 1171
sell_count = 1161
skipped_action_count = 46
execution_date_not_after_signal_date = 0
active_action_quantity_bad = 0
max_holding_count = 10
duplicate_position_count = 0
negative_cash_count = 0
final_holdings_missing_mark = 0
blocking_reasons = []
```

独立抽查 `actions.csv`：

```text
execution_date <= signal_date rows = 0
quantity <= 0 or non-lot-size rows = 0
min action cash_after = 14876.006790
```

独立抽查 `daily_nav.csv`：

```text
daily_nav rows = 1194
min cash = 14876.006790
max holding_count = 10
equity != cash + market_value rows = 0
```

## 6. Skipped Actions 审查

`skipped_actions.csv` 共 46 行：

```text
insufficient_cash_for_budget_quantity = 23
sell_intent_without_current_holding = 23
```

这些 skipped actions 可追溯，且与 replay 语义一致：部分 buy 因 `equity / target_holdings` 预算对应的 lot-size 数量超出现金而跳过；之后对应 sell intent 因未实际持仓而跳过。

未发现：

```text
missing_or_non_positive_execution_price skip
missing_join_audit_row skip
静默成交
负现金成交
隐藏缺价成交
```

因此 46 条 skipped actions 是 replay warning，不构成合同失败。

## 7. Accounting Sanity Check

执行结果：

```text
initial_cash = 1000000.000000
final_equity = 2012130218.262249
total_return = 2011.1302182622
max_drawdown = -0.1990237415
```

这是一个非常大的 long-window replay return，不能被解释为生产可用收益结论。但从会计抽查来看，未发现直接导致该数值的明显记账 bug。

独立从 `actions.csv` 重放现金与持仓：

```text
reported final cash = 137648038.395306
independent action replay cash = 137648041.773454
cash difference = 3.378148
final positions count = 10
final positions exactly match position_snapshots = true
```

3.38 元差异来自 `actions.csv` 六位小数输出后的重算舍入，数量级可接受。

最终日 `2026-05-08`：

```text
reported market_value = 1874482179.866943
sum(final position_snapshots.market_value) = 1874482179.866944
reported cash = 137648038.395306
reported equity = 2012130218.262249
```

最终持仓 mark 情况：

```text
final holdings = 10
same-date close mark = 1
latest-prior-close audited fallback = 9
```

这说明最终 equity 可以由现金加持仓市值解释，不是由负现金、重复持仓、卖出 proceeds 重复入账、持仓数量重复或 NAV 公式错误直接造成。

需要保留的会计解释限制：

```text
missing_price_count = 10493
mark_to_market_close_coverage status = audit
```

大量 daily mark-to-market 使用 latest prior close fallback，尤其最后一天 10 个持仓中 9 个不是 same-day close。该行为符合 MTRC2_U 工作文档允许的 “latest available prior close with audit”，但会影响路径收益、日收益、回撤与最终估值的解释强度。MTRC3 必须把该问题纳入 concentration/window/mark-quality diagnostic，不能把当前 total_return 当成独立充分证据。

## 8. Forbidden Actions Audit

`forbidden_action_audit.json` status 为 `pass`。审查未发现以下行为：

```text
model_training
model_inference
model_signal_artifact_write
order_intent_artifact_write
ledger_build
formal_price_store_write
registry_or_config_write
provider_refresh_or_publish
accepted_latest_switch
frontend_api_agent_daily_production_write
broker_order_quick_trade_real_order
target_weight_or_target_position_instruction
production_readiness_claim
old_mtr2r_replay_reuse
```

`forbidden_field_audit.csv` 显示 forbidden broker/provider/latest/target/future label fields absent，且 replay result 字段未用于 ranking。

## 9. Findings

### Critical

无。

### High

无合同失败项。

但必须强调：`final_equity=2012130218.262249` 只能视为 research-only replay 数值，不得用于生产 readiness。原因是 replay window 长、复利效应强，且 mark-to-market fallback 很多，需要 MTRC3 做集中度、窗口、月份、风险区间与 mark-quality 诊断。

### Medium

`missing_price_count=10493`，最终日 9/10 持仓使用 latest-prior-close fallback。该问题已审计、未 silent fill，不阻断 MTRC2_U 合同通过；但会降低最终 equity、daily_return、max_drawdown 的解释强度。

### Low

46 条 skipped actions 可追溯，属于 warning，不构成失败。

## 10. Verdict

```text
PASS_READY_FOR_MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC
```

通过含义仅限：

```text
MTRC2_U 已合法生成 readonly/simulation-only/diagnostic-only ReplayResultArtifact。
```

不含义：

```text
不代表策略可生产化
不代表收益已被接受
不解除 MTR5 concentration blocker
不允许 provider/latest/default/frontend/API/Agent/daily/broker/order/target_weight/target_position
```

## 11. 下一步建议

只允许进入：

```text
MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC
```

MTRC3 必须至少检查：

```text
1. top1/top3 symbol share、top1 event share；
2. monthly return / negative month inventory；
3. rolling 20d/40d stability；
4. risk-off / drawdown window；
5. 2026-01 至 2026-05 与更长窗口拆分；
6. mark-to-market fallback 对 final_equity、max_drawdown、daily_return 的影响；
7. 是否收益由少数标的或少数交易事件驱动；
8. 仍保持 research-only，不得进入 production readiness。
```

建议给执行者的下一步命令：

```text
请执行 MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC。
只消费 MTRC2_U ReplayResultArtifact 与其输入 lineage，做集中度、窗口稳定性、月份、risk-off、drawdown、mark-quality 诊断。
不得调参、不得新增候选、不得训练/inference、不得写 production/latest/default/frontend/API/Agent/daily、不得 broker/order、不得 target_weight/target_position。
```
