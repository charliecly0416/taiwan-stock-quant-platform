# Phase3A Route B Turnover Replay 审查意见与 Phase3A1 Return 口径修复工作文档

生成时间：2026-06-13

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

审查入口：`docs/tw_ltr_rerank_regime_turnover/PHASE3A_ROUTE_B_TURNOVER_REPLAY_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase3A 本轮不通过，不能进入 Phase3B，也不能把当前结果作为用户 tradeoff 决策依据。

本轮没有发现主线外新增模型、数据源、联网、provider、前端、API、真实交易或买卖语义越权；Route B、frozen Phase1C score、regime diagnostic-only、validation-only 选参方向基本符合边界。

但当前 replay 把 `future_return_10d` 当作逐交易日组合收益连续复利，导致 `fee_tax_adjusted_net_return`、`final_equity`、`max_drawdown` 的金融含义不成立。当前 gate：

```text
request_user_decision_route_b_tradeoff
```

必须撤回为：

```text
stop_phase3a_return_accounting_invalid
```

下一轮只允许做很窄的 Phase3A1：修复 replay return 对齐口径后重跑。

---

## 2. 主要问题

### High：10 日未来收益被按逐日收益复利，当前净值与回撤无效

脚本中：

```text
RETURN_COL = future_return_10d
period_return = selected_df[RETURN_COL].mean()
equity_net *= 1.0 + net_return
```

审查确认 `validation` 与 `independent_test` 各有 209 个交易日，日期基本为逐交易日频率；而 `future_return_10d` 是 10 日未来收益标签。当前实现等价于每天把重叠的 10 日未来收益作为当天组合收益复利。

因此当前报告中的超大 `final_equity` 和 `fee_tax_adjusted_net_return` 不能解释为真实或近似现实的组合回放结果，`max_drawdown` 也随之失真。

受影响产物包括：

- `phase3a_validation_selection.csv`
- `phase3a_independent_test_comparison.csv`
- `phase3a_yearly_metrics.csv`
- `phase3a_regime_diagnostic_metrics.csv`
- `phase3a_gate_summary.json`
- `PHASE3A_ROUTE_B_TURNOVER_REPLAY_EXECUTION_REPORT_CN.md`

这些产物可保留为失败证据，但不得作为通过证据。

### Medium：当前 gate 基于无效收益指标生成

报告给出：

```text
request_user_decision_route_b_tradeoff
```

但该 gate 依赖 `fee_tax_adjusted_net_return`、`final_equity` 与 `max_drawdown`。在 return accounting 修复前，不能把“净收益改善但回撤略差”提交给用户做取舍。

### Low：blocked baseline 暂可接受

`rank_rotate_top50_adaptive_score` 与 `confirmed_exit` 因 Phase3A0 frozen artifact 缺少技术列而 blocked。考虑上一轮要求固定 frozen score artifact，且当前首要问题是 replay return accounting，这一点暂不构成叫停原因。

Phase3A1 仍可保留 blocked 行，但必须清楚说明：主文档要求这些 baseline，当前只是固定输入边界下的临时 blocked，不得把 baseline 覆盖不足包装成完整对照。

---

## 3. 安全与范围审查

本轮未发现：

- 重新训练 LTR；
- 重建或替换 Phase1C score；
- 重新打开 Phase2 regime gate；
- 用 regime 控制组合进出或参数选择；
- 新增数据源、联网、token、provider refresh / publish；
- accepted latest switching；
- frontend / API / monitor / database 改动；
- broker / quick-trade / orders；
- target position / target weight；
- 买入、卖出、持有、仓位建议；
- 收益承诺、胜率、上涨概率承诺。

只读安全边界通过；失败原因是回放方法学，不是安全越权。

---

## 4. 已做审查验证

已验证：

```text
python -m py_compile scripts/evaluate_tw_ltr_phase3a_route_b_turnover_replay.py
```

结果：通过。

已只读检查 frozen artifact 日期与标签：

```text
validation date_count = 209
independent_test date_count = 209
date diff 主要为 1 / 3 / 4 个自然日
return column = future_return_10d
```

结论：样本是逐交易日频率，不能直接把重叠 10 日未来收益按每日收益连续复利。

---

## 5. 下一步给执行者：Phase3A1 Replay Return Accounting Repair

## 5.1 本轮目标

只回答一个问题：

```text
在固定 Phase1C row-level score 的前提下，
用不重叠或明确对齐的 return accounting 重新评估 turnover control，
其净收益 / 回撤 / 动作次数 / 换手 / 成本对照是否成立？
```

本轮不是重新寻找更高收益，也不是重新打开模型或 regime。

## 5.2 允许改动范围

允许修改：

```text
scripts/evaluate_tw_ltr_phase3a_route_b_turnover_replay.py
```

建议也可以另建窄脚本，若更清晰：

```text
scripts/evaluate_tw_ltr_phase3a1_return_accounting_repair.py
```

允许输出新目录：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3a1_return_accounting_repair/
```

允许新增执行报告：

```text
docs/tw_ltr_rerank_regime_turnover/PHASE3A1_RETURN_ACCOUNTING_REPAIR_EXECUTION_REPORT_CN.md
```

## 5.3 固定输入

必须继续使用：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv
```

固定 score：

```text
score_head10_all_l31_alpha0.7_top50_only
```

禁止重建、改写或替换该 score。

## 5.4 必须修复的 return 口径

执行者必须选择并实现一种清晰口径，优先顺序如下：

1. 若 frozen artifact 或同一已冻结本地输入中存在可用的逐日收益列，则用逐日收益进行每日组合回放。
2. 若只能使用 `future_return_10d`，则必须改成非重叠 10 日窗口 replay，例如每 10 个交易日结算一次，且换手 / 成本 / holding 口径同步按窗口计算。
3. 若只能做标签代理回放，必须把指标命名为 `label_proxy_*`，不得继续命名为现实含义的 `final_equity` / `fee_tax_adjusted_net_return`，也不得生成进入 Phase3B 的 gate。

禁止继续：

```text
逐交易日遍历 + future_return_10d 每日复利
```

## 5.5 必须保留的 Phase3A 边界

必须保留：

- Route B；
- frozen Phase1C score；
- validation-only 参数选择；
- independent_test 只做终检；
- regime diagnostic-only；
- Stage 4 turnover 机制范围。

禁止：

- 重新训练 LTR；
- 重新选择 Phase1C candidate；
- 使用 independent_test 反选参数；
- 重新打开 Phase2 / Phase2B / Phase2C regime gate；
- 引入新模型主线；
- 新增数据源或联网；
- 改前端、API、monitor、database；
- provider refresh / publish；
- accepted latest switching；
- broker / quick-trade / orders / target position / target weight；
- 买入、卖出、持有、仓位建议；
- 收益承诺、胜率、上涨概率语义。

## 5.6 必须输出指标

若实现现实对齐 replay，必须报告：

- gross return；
- fee/tax-adjusted net return；
- final equity；
- max drawdown；
- action count；
- turnover proxy；
- average holding days；
- cost drag；
- validation / independent_test 分开结果；
- yearly result；
- regime diagnostic-only 分组结果；
- 与 baseline 的差异。

若只能实现 label proxy replay，必须报告：

- `label_proxy_mean_return`；
- `label_proxy_cost_adjusted_score`；
- action count；
- turnover proxy；
- cost drag；
- validation / independent_test 分开结果；
- 明确声明不能进入 Phase3B。

## 5.7 Baseline 要求

至少保留对照：

- `rank_rotate_top30`
- `rank_rotate_top50`
- `phase1c_simple_topk_no_turnover`
- `phase1c_turnover_controlled`

`rank_rotate_top50_adaptive_score` 与 `confirmed_exit` 若仍因 fixed frozen artifact 无法复现，可继续保留 blocked 行，但报告必须说明这意味着 baseline 覆盖不完整，不能包装成完整 baseline 胜出。

## 5.8 Gate 规则

Phase3A1 只能输出以下 gate 之一：

```text
request_user_decision_route_b_tradeoff
request_phase3b_frontend_explanation_scope
stop_phase3a_turnover_not_supported
stop_phase3a_realistic_replay_not_available
```

只有在现实对齐 replay 通过后，才允许输出前两个 gate。

如果仍然只能做 label proxy replay，必须输出：

```text
stop_phase3a_realistic_replay_not_available
```

## 5.9 验收门槛

通过条件：

1. 不再把重叠 `future_return_10d` 当作逐日收益复利；
2. return / equity / drawdown 命名与计算口径一致；
3. validation-only 选参和 independent_test 终检严格分离；
4. turnover/action/cost 与新 return 时间粒度一致；
5. regime 仅 diagnostic-only；
6. 无安全边界越权；
7. 报告明确说明 Phase3A 当前旧结果已废弃或仅作失败证据。

失败收尾：

若无法构造现实对齐 replay，则停止 Stage 4 推进，不进入 Phase3B；保留 Phase1C frozen rerank 成果，只把 turnover replay 结论标记为证据不足。

