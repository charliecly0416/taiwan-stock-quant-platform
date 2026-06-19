# Phase 3A Route B：基于 Phase1C 的 Turnover / Portfolio Replay 工作文档

生成时间：2026-06-13

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

路线依据：`docs/tw_ltr_rerank_regime_turnover/LTR_MAINLINE_NEXT_ROUTE_AFTER_PHASE2B_CN.md`

用户确认：

```text
不浪费 Phase1C 成果；
允许走路线 B；
明确接受 Phase2 / Phase2B / Phase2C 没有证明 regime-aware gating；
允许绕过未验证 regime gate，以 Phase1C qlib-preserving LTR rerank 为输入进入 turnover / portfolio replay。
```

---

## 1. 本轮定位

本轮是 Phase3A，但不是因为 Stage 3 regime gating 已通过。

本轮正确定位是：

```text
qlib baseline
-> Phase1C qlib-preserving LTR rerank
-> turnover / portfolio replay
```

其中：

```text
regime-aware gating = 未通过，只能作为只读分组诊断字段
```

执行者不得声称：

```text
Phase2 / Phase2B / Phase2C 已验证 regime gate 成立
```

---

## 2. 本轮目标

验证 Phase1C 排序增强在组合回放层是否有实际价值。

重点不是再优化 rank / NDCG，而是回答：

```text
在固定 Phase1C rerank score 的前提下，
加入 turnover control 后，
是否能相对现有 baseline rule 改善净值、回撤、动作次数、换手和成本后的表现？
```

---

## 3. 固定输入

必须固定使用 Phase1C score：

```text
score_head10_all_l31_alpha0.7_top50_only
```

语义必须保持：

```text
qlib-preserving LTR rerank
```

它不是：

- 全市场自由重排；
- 替代 qlib 的新主模型；
- 收益率预测；
- 上涨概率；
- 买入概率；
- 仓位权重。

---

## 4. Regime 使用规则

本轮允许读取 regime 字段，但只能用于：

- 分组统计；
- 解释诊断；
- 失败原因分析；
- “不同市场状态下 replay 表现如何”的只读切片。

本轮禁止：

- 用 regime gate 控制进出；
- 把 regime 作为已验证过滤器；
- 声称 risk_off gate 已成立；
- 用 Phase2B selected gate 作为正式 gating；
- 用 `caution_only_c40_r50` 作为交易/组合前提。

报告中必须明确写出：

```text
Regime-aware gating was not validated.
Regime is diagnostic-only in Phase3A.
```

---

## 5. 允许实现范围

允许新增一个只读离线 replay 脚本。

建议脚本：

```text
scripts/evaluate_tw_ltr_phase3a_route_b_turnover_replay.py
```

建议输出目录：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase3a_route_b_turnover_replay/
```

允许实现的机制限定在主文档 Stage 4 第一版要求内：

- `no_trade_buffer`
- `confidence_gap`
- `partial_rebalance`
- `max_actions_per_day`
- `min_holding_days`（若样本与现有规则兼容）
- `score_or_confidence_clipping`
- `turnover_budget`

本轮可以做小规模参数网格，但必须：

- validation 选择参数；
- independent_test 只做最终检验；
- 不用 independent_test 反选；
- 不扩展成复杂优化器；
- 不做真实交易系统。

---

## 6. 必须对照的 baseline

至少对照：

- `rank_rotate_top30`
- `rank_rotate_top50`
- `rank_rotate_top50_adaptive_score`
- `confirmed_exit`
- Phase1C 无 turnover control 的简单 TopK replay（如果可构造）

如果某个 baseline 因现有产物不可用无法复现，必须在报告中说明原因，不能静默省略。

---

## 7. 必须报告指标

组合层回放必须至少报告：

- gross return；
- fee/tax-adjusted net return；
- final equity；
- max drawdown；
- action count；
- turnover proxy；
- average holding days；
- cost drag；
- yearly result；
- validation / independent_test 分开结果；
- regime diagnostic-only 分组结果。

不得只报告毛收益。

不得把任何指标写成：

- 收益承诺；
- 胜率承诺；
- 上涨概率；
- 买入概率；
- 仓位建议。

---

## 8. 禁止事项

执行者不得：

- 重新训练 LTR；
- 调整 Phase1C score；
- 重新打开 Phase2 regime gate 搜索；
- 把 regime gate 作为已验证控制层；
- 新增数据源；
- 联网；
- provider refresh / publish；
- accepted latest switching；
- 改 frontend；
- 改 API；
- 改 monitor；
- 改 database；
- 接 broker；
- quick-trade；
- orders；
- target position；
- target weight；
- 输出买入、卖出、持有、仓位建议；
- 输出收益承诺、胜率、上涨概率；
- 做真实交易动作。

---

## 9. 必须输出产物

必须输出：

- `phase3a_validation_selection.csv`
- `phase3a_independent_test_comparison.csv`
- `phase3a_yearly_metrics.csv`
- `phase3a_regime_diagnostic_metrics.csv`
- `phase3a_turnover_action_summary.csv`
- `phase3a_gate_summary.json`
- `docs/tw_ltr_rerank_regime_turnover/PHASE3A_ROUTE_B_TURNOVER_REPLAY_EXECUTION_REPORT_CN.md`

---

## 10. Gate 结论

`phase3a_gate_summary.json` 必须给出以下之一：

### 10.1 `request_phase3b_replay_repair`

仅当：

- Phase1C + turnover 在 validation 上有明确净值/回撤/换手/成本改善方向；
- independent_test 没有出现明显反转；
- action count 和 turnover proxy 有实质改善；
- 没有牺牲过大 final equity 或 max drawdown；
- 没有 safety / scope 问题。

此结论只允许进入下一轮 replay 修复或稳健性检查，不允许直接进入前端。

### 10.2 `request_user_decision_route_b_tradeoff`

当出现必须由用户决定的 tradeoff，例如：

- 净收益改善但回撤变差；
- 换手下降但 final equity 明显下降；
- independent_test 与 validation 方向冲突；
- 成本假设对结论高度敏感。

### 10.3 `stop_phase3a_turnover_not_supported`

当：

- Phase1C + turnover 无法优于 baseline；
- 改善只出现在单一窗口；
- 成本后优势消失；
- 动作减少但组合表现显著恶化；
- 或发现任何越界。

---

## 11. 验证要求

执行者必须运行：

```text
python -m py_compile scripts/evaluate_tw_ltr_phase3a_route_b_turnover_replay.py
python scripts/evaluate_tw_ltr_phase3a_route_b_turnover_replay.py
```

如普通沙箱因环境限制失败，报告中必须写明失败原因与复跑方式。

---

## 12. 执行报告必须包含

1. 本轮目标；
2. Route B tradeoff 确认；
3. 实际完成内容；
4. 改动文件清单；
5. 新增产物清单；
6. 固定 Phase1C score 的说明；
7. regime diagnostic-only 的说明；
8. validation 参数选择；
9. independent_test 最终结果；
10. baseline 对照；
11. 年度结果；
12. turnover / action / cost 结果；
13. 验证命令与结果；
14. 是否达到 gate；
15. 禁止事项遵守情况；
16. 需要审查者重点检查的点。

---

## 13. 审查重点

审查者下一轮重点检查：

- 是否真实固定 Phase1C；
- 是否没有重新包装 Phase2/Phase2B/Phase2C；
- 是否没有使用 regime gate 做控制；
- 是否 validation-only 选参；
- independent_test 是否只是最终检验；
- 是否报告成本后净结果；
- 是否与 baseline 全面对照；
- 是否存在交易语义或系统越权；
- 若结果不成立，是否停止而不是强推前端。

