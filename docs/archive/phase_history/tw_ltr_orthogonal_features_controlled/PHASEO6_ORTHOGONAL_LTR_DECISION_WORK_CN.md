# Phase O6 工作文档：Orthogonal LTR Decision

生成日期：2026-06-15

依据：

```text
docs/tw_ltr_orthogonal_features_controlled/ORTHOGONAL_LTR_CONTROLLED_MAINLINE_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEO5_REVIEW_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEO5R_REVIEW_CN.md
```

## 1. O6 目标

O6 只做一件事：

```text
基于 O0-O5R 的冻结证据，判断正交数据是否给 Phase1C simple LTR 带来可用增益。
```

O6 是审查与决策记录，不是训练、回放、调参或产品化。

目标 gate：

```text
phase_o6_orthogonal_ltr_decision_recorded
```

## 2. 固定证据

O6 必须只使用既有冻结产物：

```text
O0 anchor/control contract
O1/O1R coverage and available_at contract
O2 PIT-safe feature builder outputs
O3 row-aligned treatment sample outputs
O4 controlled treatment LTR outputs
O5 controlled replay evaluation outputs
O5R common universe audit repair outputs
```

重点产物：

```text
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5r_full_universe_metrics.csv
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5r_common_universe_metrics.csv
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5_rank_metrics.csv
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5_monthly_performance.csv
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5_yearly_performance.csv
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5_pnl_concentration_summary.csv
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5_low_coverage_impact_audit.csv
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5_o4_feature_importance_top30.csv
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5r_nav_diff_summary.csv
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5r_action_diff_summary.csv
```

## 3. 必须回答的问题

O6 报告必须逐项回答：

```text
1. O4 orthogonal treatment 是否在 full universe 收益不低于 Phase1C control？
2. pairwise common universe 是否已审计闭环？
3. O4 treatment 的 max drawdown 是否明显恶化？
4. action_count / turnover 是否明显恶化？
5. 收益是否集中于单一月份、单一日期或单一股票？
6. 低覆盖股票是否贡献了不可接受的收益集中或风险？
7. rank/NDCG 改善是否与 replay PnL 方向一致？
8. O4 feature importance 是否显示正交特征确实被模型使用？
9. 是否存在 PIT / sample alignment / universe / next-day accounting 合同问题？
10. 是否足以进入“只读产品化设计”主线？
```

## 4. 决策标准

O6 可选择三种结论之一。

### 4.1 通过

只有同时满足以下条件，才允许通过：

```text
full universe return >= control；
pairwise common universe audit 已闭环；
max drawdown 没有不可接受恶化；
action_count / turnover 没有不可接受恶化；
收益不主要依赖单一月份、单一日期或单一股票；
低覆盖股票不是主要收益来源；
PIT、样本对齐、universe、next-day accounting 均无阻塞；
正交特征重要性具有可解释性。
```

通过后只允许进入：

```text
只读产品化设计主线
```

不得在 O6 直接改前端默认。

### 4.2 不通过

若出现以下任一情况，应不通过并收尾：

```text
收益改善不足以覆盖回撤恶化；
收益高度集中且不可解释；
低覆盖股票贡献过高；
正交特征重要性弱或噪音化；
common universe 虽闭环但不构成独立稳健证据；
用户第一性原则下不值得进入产品链路。
```

### 4.3 需要补充审计

若证据仍不足，应明确提出最小补审计项，不得直接继续实验扩张。

## 5. 禁止事项

O6 禁止：

```text
重新训练 qlib 或 LTR；
修改 Phase1C anchor；
修改 O4 treatment score；
修改窗口、label、feature、hyperparameter；
新增 filter、threshold、market gate、turnover control、stop loss、take profit；
新增 fresh qlib/fresh LTR 对照作为主结论；
改前端默认策略；
改 API/provider/accepted latest/monitor；
触发 broker/orders/quick-trade/target position/target weight；
把训练窗口或 validation ranking metric 当成策略优劣主证据。
```

## 6. 输出要求

执行者必须写：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEO6_ORTHOGONAL_LTR_DECISION_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
最终 decision；
decision gate；
支持证据；
反证或风险；
是否允许进入只读产品化设计主线；
明确禁止直接产品化或改默认；
下一步建议。
```

不得只给一句“通过/不通过”。
