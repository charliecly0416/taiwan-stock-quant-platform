# Phase3B Readonly Explanation Scope 工作文档

生成时间：2026-06-13

> 暂停状态：2026-06-13 用户要求先暂停本 Phase3B，只能在 Phase3A2 完整日频组合回放审查完成并重新获得用户确认后恢复。本文件不得作为当前执行入口。

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

用户决策依据：用户已选择 A，接受 Phase3A1 Route B tradeoff，允许进入 Phase3B，但限定：

```text
只做 readonly explanation
不进入主推荐
不声称收益更优
```

---

## 1. 本轮目标

本轮只做 Phase3B 的只读解释范围定义与最小产物准备。

目标是让系统能解释：

```text
为什么 turnover control 倾向于不替换 / 少替换
动作和换手为什么下降
当前结果为什么不能被解释成收益更优
```

本轮不是前端主推荐接入，不是策略通过宣告，也不是继续优化参数。

---

## 2. 本轮结论前提

Phase3A1 已修复 return accounting，并形成以下用户接受的 tradeoff：

```text
接受 independent_test 净收益低于 Phase1C simple baseline；
接受 validation / independent_test 回撤略差；
换取动作数与换手显著降低；
Phase3B 只做 readonly explanation，不包装成收益更优策略。
```

因此执行者必须把 Phase3B 语义限定为：

```text
降低换手
降低动作频率
解释为什么不替换
解释候选优势不足 / holding 约束 / action budget / turnover budget
```

禁止把它写成：

```text
收益更高
策略更优
胜率更高
上涨概率更高
买入 / 卖出 / 持有建议
仓位建议
```

---

## 3. 允许改动范围

本轮允许新增或修改只读研究产物生成脚本，例如：

```text
scripts/build_tw_ltr_phase3b_readonly_explanation_scope.py
```

允许新增输出目录：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3b_readonly_explanation_scope/
```

允许新增执行报告：

```text
docs/tw_ltr_rerank_regime_turnover/PHASE3B_READONLY_EXPLANATION_SCOPE_EXECUTION_REPORT_CN.md
```

本轮默认不允许改前端代码、不允许改 API。

如果执行者认为必须改前端或 API，必须停止并在执行报告中列出：

```text
需要改哪些字段
为什么现有产物无法支撑只读解释
改动是否会触及主推荐 / 交易 / provider / monitor 边界
```

等待审查者和用户确认后再做。

---

## 4. 固定输入

必须使用 Phase3A1 产物：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3a1_return_accounting_repair/phase3a1_window_replay_rows.csv
data_tw/experiments/ltr_rerank_regime_turnover/phase3a1_return_accounting_repair/phase3a1_independent_test_comparison.csv
data_tw/experiments/ltr_rerank_regime_turnover/phase3a1_return_accounting_repair/phase3a1_validation_selection.csv
data_tw/experiments/ltr_rerank_regime_turnover/phase3a1_return_accounting_repair/phase3a1_gate_summary.json
```

如需 row-level score，只能读取：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv
```

固定 score：

```text
score_head10_all_l31_alpha0.7_top50_only
```

禁止重建、改写或替换该 score。

---

## 5. 必须生成的只读解释产物

至少生成以下文件：

### 5.1 Explanation Scope JSON

路径建议：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3b_readonly_explanation_scope/phase3b_explanation_scope.json
```

必须包含：

```text
research_only = true
not_main_recommendation = true
not_return_superior_claim = true
accepted_tradeoff = true
source_gate = request_user_decision_route_b_tradeoff
user_selected_route = accept_turnover_tradeoff_readonly_explanation_only
```

必须列出允许解释项：

```text
baseline_rank_context
phase1c_rerank_context
turnover_control_reason
no_replacement_reason
action_budget_reason
turnover_budget_reason
min_holding_reason
regime_diagnostic_context_only
```

必须列出禁止解释项：

```text
buy_signal
sell_signal
hold_signal
target_position
target_weight
expected_return
win_rate
upside_probability
return_superior_claim
main_recommendation
```

### 5.2 Explanation Examples CSV

路径建议：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3b_readonly_explanation_scope/phase3b_explanation_examples.csv
```

每行必须是只读解释样例，字段建议：

```text
split
window_start_date
method
instrument_or_portfolio_scope
explanation_type
explanation_text_cn
allowed_surface
forbidden_surface
source_metric
source_value
```

样例必须覆盖：

- 候选优势不足所以不替换；
- 当日 / 当窗口 action budget 限制；
- turnover budget 限制；
- min holding 限制；
- regime diagnostic-only 的解释；
- Phase3A1 tradeoff 解释。

不得出现：

```text
建议买入
建议卖出
建议持有
目标仓位
预期收益
胜率
上涨概率
收益更优
主推荐
```

### 5.3 Frontend Copy Contract Markdown

路径建议：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3b_readonly_explanation_scope/phase3b_frontend_copy_contract_cn.md
```

必须写清楚：

- 页面可展示哪些文案；
- 页面禁止展示哪些文案；
- 如何说明 Phase3A1 tradeoff；
- 如何说明“降低动作/换手”；
- 如何说明“不代表收益更优”；
- 如何说明“不是交易建议”。

---

## 6. 必须遵守的语义边界

允许使用：

```text
研究排序
只读解释
历史回放
降低动作频率
降低换手
不替换原因
候选优势不足
换手预算限制
最小持有窗口限制
市场状态仅作诊断
不是交易建议
不代表收益更优
```

禁止使用：

```text
买入
卖出
持有
建仓
加仓
减仓
目标仓位
目标权重
预期收益
收益更优
胜率
上涨概率
主推荐
自动交易
下单
连接券商
```

注意：如果这些词只出现在“禁止事项”段落，可以接受；不得出现在面向用户的解释文案中。

---

## 7. 禁止事项

本轮禁止：

- 重新训练 LTR；
- 重建或改写 Phase1C score；
- 重新调 Phase3A1 参数；
- 用 independent_test 反选参数；
- 重新打开 regime gate；
- 使用 regime 控制组合；
- 新增数据源、联网、token；
- provider refresh / publish；
- accepted latest switching；
- 修改 frontend / API / monitor / database；
- 接入 broker / quick-trade / orders；
- 输出 target position / target weight；
- 输出买卖 / 持有 / 仓位建议；
- 输出收益承诺、胜率、上涨概率语义；
- 把 Phase3B 接入主推荐。

---

## 8. 必做验证

执行者必须至少运行：

```text
python -m py_compile scripts/build_tw_ltr_phase3b_readonly_explanation_scope.py
python scripts/build_tw_ltr_phase3b_readonly_explanation_scope.py
```

并做文本边界扫描，至少检查新增产物中是否含有禁用语义。若命中禁用词，必须区分：

```text
禁止事项段落中的命中：可接受
面向用户解释文案中的命中：不接受，必须修复
```

---

## 9. 必交付产物

执行报告：

```text
docs/tw_ltr_rerank_regime_turnover/PHASE3B_READONLY_EXPLANATION_SCOPE_EXECUTION_REPORT_CN.md
```

产物目录：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3b_readonly_explanation_scope/
```

至少包含：

```text
phase3b_explanation_scope.json
phase3b_explanation_examples.csv
phase3b_frontend_copy_contract_cn.md
```

---

## 10. 验收门槛

通过条件：

1. 只读解释范围清楚；
2. 明确写入用户选择 A 的 tradeoff；
3. 明确不进入主推荐；
4. 明确不声称收益更优；
5. 所有面向用户解释文本没有买入、卖出、持有、仓位、收益承诺、胜率、上涨概率语义；
6. 未改 frontend / API / provider / monitor / database；
7. 未新增模型、数据源或联网；
8. 能被下一轮审查者直接判断是否可进入“前端只读展示设计审查”。

失败收尾：

若无法在不触碰前端/API的情况下形成清晰解释契约，则停止在 Phase3B scope，不得自行实现 UI。

