# Phase3A1 Return Accounting Repair 审查意见与用户决策文档

生成时间：2026-06-13

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

审查入口：`docs/tw_ltr_rerank_regime_turnover/PHASE3A1_RETURN_ACCOUNTING_REPAIR_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase3A1 的 return accounting 修复通过方法审查，但不能自动进入 Phase3B。

本轮已经修复上一轮 Phase3A 的关键错误：不再把重叠的 `future_return_10d` 当成逐交易日收益连续复利，而是采用非重叠 10 交易日窗口 replay。

但修复后结果形成真实 tradeoff：

```text
validation：turnover control 净收益更高、动作更少、换手更低，但回撤更差
independent_test：turnover control 动作更少、换手更低，但净收益低于 Phase1C simple baseline，回撤也略差
```

因此当前 gate：

```text
request_user_decision_route_b_tradeoff
```

审查接受为“必须回到用户确认”，不允许执行者自行推进 Phase3B。

---

## 2. 通过项

### 2.1 Return accounting 修复通过

执行者采用：

```text
return_accounting = non_overlapping_10d_windows
window_size_trading_days = 10
return_col = future_return_10d
```

每个 split 只取 `0, 10, 20, ...` 作为窗口起点，每个窗口只应用一次 10 日未来收益，换手、动作、成本和 holding 均按窗口频率计算。

这符合上一轮 Phase3A1 文档要求：

```text
若只能使用 future_return_10d，则必须改成非重叠 10 日窗口 replay
```

### 2.2 固定输入边界通过

执行者继续固定：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv
score_head10_all_l31_alpha0.7_top50_only
```

未重建、未改写、未替换 Phase1C score。

### 2.3 validation-only / independent_test 分离通过

validation 选择配置：

```text
k30_a3_gap0.0_buf0.0_holdw2_budget0.2
```

independent_test 只用 validation 选出的配置做终检，未发现 independent_test 反选。

### 2.4 安全与范围通过

本轮未发现：

- 重新训练 LTR；
- 重建 Phase1C score；
- 重新打开 Phase2 regime gate；
- 使用 regime gate 控制组合；
- 新增数据源、联网、token、provider refresh / publish；
- accepted latest switching；
- frontend / API / monitor / database 改动；
- broker / quick-trade / orders；
- target position / target weight；
- 买入、卖出、持有、仓位建议；
- 收益承诺、胜率、上涨概率承诺。

只读安全边界通过。

---

## 3. 关键结果

### 3.1 validation

Phase1C simple baseline：

```text
fee_tax_adjusted_net_return = 0.23498352942022582
max_drawdown = -0.21646929893177957
action_count = 814
turnover_proxy = 1.292063492063492
```

Phase1C turnover-controlled：

```text
fee_tax_adjusted_net_return = 0.36060129675125707
max_drawdown = -0.24929218130128938
action_count = 146
turnover_proxy = 0.2317460317460318
```

validation 结论：

```text
净收益改善：是
动作减少：是
换手降低：是
回撤不变差：否
```

### 3.2 independent_test

Phase1C simple baseline：

```text
fee_tax_adjusted_net_return = 2.4509187220889648
final_equity = 3.4509187220889648
max_drawdown = -0.051929830809715805
action_count = 750
turnover_proxy = 1.1904761904761902
```

Phase1C turnover-controlled：

```text
fee_tax_adjusted_net_return = 2.329407958934038
final_equity = 3.329407958934038
max_drawdown = -0.05747603476257801
action_count = 144
turnover_proxy = 0.2285714285714286
```

independent_test 结论：

```text
净收益未反转：否
动作减少：是
换手降低：是
回撤没有明显恶化：是
```

这说明 turnover control 的价值主要是降低动作与换手，不是提高 independent_test 净收益。

---

## 4. 不通过自动推进的原因

主文档要求：

```text
若出现需要用户做 tradeoff 判断，必须停下并回到用户确认。
```

当前结果不是单纯通过：

- validation 净收益更高，但回撤更差；
- independent_test 净收益低于 Phase1C simple baseline；
- baseline 覆盖仍不完整：`rank_rotate_top50_adaptive_score` 与 `confirmed_exit` 仍是 blocked；
- turnover control 的收益来自“动作/换手显著降低”，不是综合指标全面优于 baseline。

因此执行者不得自行把 Phase3A1 解释为 Phase3B 通过条件。

---

## 5. blocked baseline 审查

`rank_rotate_top50_adaptive_score` 与 `confirmed_exit` 因 Phase3A0 frozen artifact 缺少技术列继续 blocked。

审查意见：

```text
可接受为固定输入边界下的临时 blocked；
不可包装成完整 baseline 胜出；
不可因此直接推进前端主展示。
```

---

## 6. 已做验证

已执行：

```text
python -m py_compile scripts/evaluate_tw_ltr_phase3a1_return_accounting_repair.py
```

结果：通过。

普通沙箱执行：

```text
python scripts/evaluate_tw_ltr_phase3a1_return_accounting_repair.py
```

触发环境限制：

```text
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

按环境规则提升权限复跑同一只读脚本，结果通过：

```text
ok = true
gate = request_user_decision_route_b_tradeoff
```

---

## 7. 用户需要确认的 tradeoff

当前不能给执行者继续任务，必须先由用户确认路线。

### 选项 A：接受 Route B turnover tradeoff，进入 Phase3B

含义：

```text
接受 independent_test 净收益低于 Phase1C simple baseline；
接受 validation / independent_test 回撤略差；
换取动作数与换手显著降低；
Phase3B 只做 readonly frontend explanation scope，不包装成收益更优策略。
```

若用户选择 A，下一轮执行者只能做：

```text
Phase3B readonly explanation scope
```

且前端语义必须写成：

```text
降低换手 / 降低动作频率 / 解释为什么不替换
```

不得写成：

```text
收益更高
胜率更高
上涨概率更高
买入/卖出/持有建议
仓位建议
```

### 选项 B：不接受 tradeoff，停止 Stage 4 前端推进

含义：

```text
保留 Phase1C frozen rerank 作为有效研究成果；
保留 Phase3A1 turnover replay 作为“降低换手但净收益未占优”的研究证据；
不进入 Phase3B，不接前端主展示。
```

若用户选择 B，下一轮执行者只能做：

```text
Stage 4 closure / archive report
```

不得继续优化参数寻找更好结果，除非用户另开新主线。

---

## 8. 审查者建议

默认建议选择 B，或至少暂不进入前端主展示。

理由：

```text
主文档要求 turnover-controlled portfolio layer 能实质降低动作，并改善净收益 / 回撤 / 换手平衡。
当前只稳定证明了动作与换手改善，未证明 independent_test 净收益改善，回撤也没有改善。
```

如果用户产品上更重视“少动作、少换手、解释为什么不替换”，可以选择 A，但必须明确它是用户主动接受的取舍，而不是模型自动通过。

