# Phase 2C Risk-off-only 最终诊断工作文档

生成时间：2026-06-13

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

前置结论：

- Phase1C `qlib-preserving LTR rerank` 已作为当前最稳 rerank 成果保留；
- Phase2 / Phase2B 未证明可放行 Stage 3；
- 用户确认允许再做一次非常窄的 `risk_off-only` 最终诊断；
- 本轮不是 Phase3，不得进入 turnover-controlled portfolio layer。

---

## 1. 本轮目标

只回答一个问题：

```text
为什么 Phase2B selected gate 在 risk_off 下没有形成有效保守过滤？
```

本轮目标不是继续寻找更高指标，也不是重新训练模型，而是给出最终诊断：

- 是 `risk_off` 样本太少；
- 是 `risk_off` 定义导致信号不可分；
- 是 `risk_off` 中 Phase1C 本身已经足够保守；
- 是进一步收缩 scope 会破坏 TopK；
- 还是现有数据无法支持 risk_off gating。

---

## 2. 固定输入

必须固定使用 Phase1C score：

```text
score_head10_all_l31_alpha0.7_top50_only
```

语义必须保持：

```text
qlib-preserving LTR rerank
```

不得重新训练 LTR；
不得新增 LTR 特征；
不得把 Phase1C 解释成替代 qlib 的全市场模型。

---

## 3. 允许范围

只允许做只读诊断：

1. 复用 Phase2B 产物与样本；
2. 对 Phase2B 已有 regime definitions 的 `risk_off` 子样本做分解；
3. 对 Phase2B 已有 gating rules 的 `risk_off` 效果做表格化诊断；
4. 允许补充非常小的 sensitivity check，但仅限：
   - `risk_scope` 在已有 Top50 内收缩；
   - 不新增 regime feature；
   - 不使用 independent_test 反选最终参数；
   - 只用于解释为什么 risk_off 不成立；
5. 明确比较：
   - Phase1C risk_off；
   - Phase2B selected gate risk_off；
   - 更严格 risk_scope 的诊断性结果。

---

## 4. 禁止事项

执行者不得：

- 进入 Phase3；
- 做 turnover portfolio layer；
- 做组合净值、动作次数、换手、成本回放；
- 新增数据源；
- 联网；
- provider refresh / publish；
- accepted latest switching；
- 改 frontend / API / monitor / database；
- 重新训练 LTR；
- 引入 `trend_score`；
- 引入 forbidden features；
- 新增白名单外 regime 特征；
- 使用 `institutional_net_buy`、`margin_balance`、`short_balance`、`monthly_revenue_yoy_mom`、`valuation_PER_PBR`；
- 输出买入、卖出、持有、仓位、target position / target weight；
- 输出收益承诺、胜率、上涨概率；
- 把 risk_off gate 包装成交易信号。

---

## 5. 建议实现

建议新增脚本：

```text
scripts/diagnose_tw_ltr_phase2c_risk_off_only.py
```

建议输出目录：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase2c_risk_off_diagnosis/
```

脚本应尽量复用 Phase2B 的样本、score 与 regime definition，不要复制出一条新模型主线。

---

## 6. 必须输出产物

必须输出：

- `phase2c_risk_off_distribution.csv`
- `phase2c_risk_off_scope_sensitivity.csv`
- `phase2c_risk_off_by_year.csv`
- `phase2c_risk_off_gate_diagnosis.json`
- `docs/tw_ltr_rerank_regime_turnover/PHASE2C_RISK_OFF_ONLY_DIAGNOSIS_REPORT_CN.md`

---

## 7. 必须诊断的问题

报告必须逐项回答：

1. 每个 regime definition 的 `risk_off` 在 train / validation / independent_test 的 date_count 与 row_count；
2. Phase2B selected definition 下，`risk_off` 是否样本不足；
3. `risk_off` 中 Phase1C 的 Top10 / Top30 / Top50 指标是否已经优于 qlib；
4. `risk_scope=50/45/40/35/30/20` 对 Top30 future excess rank、NDCG@30、median qlib rank、changed ratio 的影响；
5. 是否存在某个更严格 `risk_scope` 在 validation 与 independent_test 同时不伤害 Phase1C；
6. 如果不存在，明确说明是：
   - 样本不足；
   - 指标冲突；
   - risk_off 内排序不可分；
   - 或进一步过滤会牺牲 TopK；
7. 给出最终 gate：
   - `risk_off_gating_not_supported_final`
   - 或 `risk_off_diagnosis_needs_user_tradeoff`

不得给出 `request_phase3_turnover_layer_work`。

---

## 8. 验收门槛

本轮只有诊断验收，不存在 Phase3 放行验收。

通过条件：

- 产物齐全；
- 只使用主文档允许的 risk/regime 字段；
- 没有新模型、新数据源、新接口、新前端；
- 诊断能解释 Phase2B risk_off 为什么没有生效；
- 明确给出失败收尾或用户 tradeoff；
- 没有交易语义或安全边界问题。

失败条件：

- 又变成大范围参数搜索；
- 用 independent_test 反选参数；
- 把 risk_off 诊断包装成可用 gate；
- 进入 Phase3；
- 新增数据源或越权系统改动；
- 输出买卖、仓位、收益、概率语义。

---

## 9. 交付报告格式

执行报告必须包含：

1. 本轮目标；
2. 实际完成内容；
3. 改动文件清单；
4. 新增产物清单；
5. risk_off 样本分布；
6. risk_scope sensitivity；
7. validation vs independent_test 是否一致；
8. 最终诊断结论；
9. 验证命令与结果；
10. 禁止事项遵守情况；
11. 需要审查者重点检查的点。

---

## 10. 本轮结束后的状态

无论 Phase2C 诊断结果如何，本轮结束后都必须停止，由审查者判断。

若结论是：

```text
risk_off_gating_not_supported_final
```

则 Stage 3 应正式收尾为证据不足。

若结论是：

```text
risk_off_diagnosis_needs_user_tradeoff
```

则必须回到用户确认，不能由执行者自行进入 Phase3。

