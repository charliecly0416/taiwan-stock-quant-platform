# Phase O6 审查结论：Orthogonal LTR Decision

生成日期：2026-06-15

审查对象：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEO6_ORTHOGONAL_LTR_DECISION_WORK_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEO6_ORTHOGONAL_LTR_DECISION_EXECUTION_REPORT_CN.md
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/
```

## 1. 结论

O6 通过。

执行报告没有偏离 O6 工作文档：它只做决策记录，没有重训、没有重放新规则、没有修改 Phase1C anchor 或 O4 treatment score，也没有触发前端/API/provider/accepted latest/monitor/交易链路。

允许进入下一步：

```text
只读产品化设计主线
```

但路线必须严格表述为：

```text
O4 orthogonal LTR 可以替代原 Phase1C simple LTR，作为 LTR 研究展示/对照候选；
当前产品默认策略仍保持 fresh qlib / rank_rotate_top50_adaptive_score；
不得在本阶段直接改默认。
```

## 2. 证据核对

同窗口 final test：

```text
2025-07-01..2026-05-07
```

Full universe：

```text
Phase1C simple LTR return = 0.721631
O4 orthogonal LTR return = 0.800329
absolute improvement = +0.078698

Phase1C max_drawdown = -0.050830
O4 max_drawdown = -0.074962
drawdown change = -0.024132

Phase1C action_count = 405
O4 action_count = 403

Phase1C turnover_proxy = 40.328422
O4 turnover_proxy = 39.761877
```

判断：

```text
收益提升明确；
动作数与 turnover 未恶化；
最大回撤明显更深，必须作为产品化风险标注。
```

## 3. O5R Common Universe 状态

O5R 已证明：

```text
full/common action diff = 0
full/common NAV diff = 0
next-day accounting pass = yes
```

因此 O5/O5R 的 common universe 疑点已闭环。

但 common universe 主要是审计闭环，不是独立稳健性证明。产品化文案不得写成：

```text
common universe 独立证明 orthogonal LTR 稳健胜出
```

只能写成：

```text
pairwise common universe 没有改变本轮实际 replay 路径，full/common 指标相同可复现。
```

## 4. 产品化路线判断

用户给出的路线：

```text
可以代替原本的 simple LTR，但是默认还是先保持 fresh qlib
```

审查判断：可行。

理由：

- O4 orthogonal LTR 在同窗口收益高于 Phase1C simple LTR；
- O4 action_count 与 turnover 不高于 Phase1C；
- PnL 未集中于单一股票或单一日期；
- 低覆盖股票不是主要收益来源；
- Rank IC / NDCG 方向与 replay 收益方向基本一致；
- feature importance 显示正交特征确实被模型使用；
- PIT / row alignment / next-day accounting 未发现阻断问题。

边界：

- O4 最大回撤更深，不适合作为默认策略直接替换 fresh qlib；
- O4 仍是离线历史回放结果，不代表实时收益、胜率或交易优势；
- 当前只能进入只读展示和解释设计，不得接入自动刷新、监控写入或交易链路。

## 5. 审查 Gate

推荐 gate：

```text
phase_o6_orthogonal_ltr_decision_accepted_for_readonly_product_design
```

下一步应启动只读产品化设计工作文档。

只读产品化设计的核心合同：

```text
default_strategy = fresh qlib / rank_rotate_top50_adaptive_score
ltr_research_candidate = O4 orthogonal LTR
legacy_simple_ltr = replaced in LTR comparison slot, retained as audit baseline
```

## 6. 禁止事项

下一阶段仍禁止：

```text
改前端默认策略；
把 O4 orthogonal LTR 设为默认；
触发 provider refresh/publish；
切换 accepted latest；
触发 monitor scan/config/alerts；
触发 broker/orders/quick-trade/target position/target weight；
输出买入/卖出/持仓建议；
承诺收益、胜率或上涨概率。
```
