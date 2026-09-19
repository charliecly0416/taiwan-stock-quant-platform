---
created_at: 2026-06-24
status: coordinator_mainline
route: RCPT7_ADAPTIVE_SCORE_ALIGNED_RISK_CONTROL_REPAIR
parent_opinion: docs/tw_portfolio_decision_model/POLICY_RCPT6_ADAPTIVE_SCORE_COMPARISON_AND_NEXT_ROUTE_OPINION_CN.md
reference_baseline: rank_rotate_top50_adaptive_score
previous_candidate: RCPT1_RULE_05
production_allowed: false
order_or_target_output_allowed: false
model_training_authorized: false
---

# RCPT7 Adaptive-score-aligned Risk-control Repair 主线

## 1. 统筹结论

RCPT6 证明了：

```text
sell-side weak-rank-deterioration early sell 有风险控制价值。
```

但 RCPT6 也暴露了关键问题：

```text
RULE_05 收益捕获不足；
相对旧版 rank_rotate_top50_adaptive_score，不足以作为满意的风险控制策略。
```

因此 RCPT7 不再继续证明 RULE_05 本身，而是参考旧版 Top50 自适应 score，把路线调整为：

```text
adaptive-score-aligned risk-control repair
```

核心目标：

```text
保留大部分 baseline 收益，
同时在 2022 下跌年显著降低亏损和最大回撤。
```

## 2. 当前关键事实

旧版 `rank_rotate_top50_adaptive_score` 的 2022 结果：

```text
net_return_after_fee_tax = -0.124560
max_drawdown = -0.241499
```

RCPT6 `RULE_05` 的 2022 结果：

```text
net_return_after_fee_tax = -0.18603880
max_drawdown = -0.22907360
```

判断：

```text
RULE_05 回撤略好，但收益明显更差；
它不是满意的下跌年风险控制方案。
```

2023-2025 qlib-only strict OOS candidate 中：

```text
baseline net_return_after_fee_tax = 0.41214390
RULE_05 net_return_after_fee_tax = 0.31759959
return_capture = 77.1%
max_drawdown_delta = +0.20104594
```

判断：

```text
RULE_05 防守效果明确，但收益捕获率低于 production-grade 风控策略应有标准。
```

## 3. 旧版 Adaptive Score 机制

项目历史脚本中的 `adaptive_score_baseline` 公式：

```text
adaptive_score_baseline =
    0.70 * qlib_score_zscore_by_date
  + 0.15 * ret20
  - 0.10 * volatility20
  + 0.05 * TWII_ret20
```

产品解释：

```text
正常市况不干预 Top50 轮动；
谨慎/下跌市况使用 score 区间过滤补仓。
```

这说明旧版 adaptive score 同时解决：

```text
1. 横截面 qlib score；
2. 个股短期动量；
3. 高波动惩罚；
4. 大盘趋势；
5. risk-off 下补仓过滤。
```

RCPT7 必须参考这一机制，而不是只做 sell-side exit。

## 4. 目标

RCPT7 要回答：

```text
能否在旧版 adaptive score 的收益/回撤平衡基础上，
加入 RCPT 的 sell-side risk control，
得到更好的下跌年防守，同时保持较高收益捕获率？
```

最低目标：

```text
1. 2022 net loss 接近或优于 rank_rotate_top50_adaptive_score；
2. 2022 max_drawdown 接近或优于 rank_rotate_top50_adaptive_score；
3. 2023-2025 return_capture >= 0.85；
4. 理想目标 return_capture >= 0.90；
5. 不靠 all-cash/no-trade；
6. 不通过无界调参得到。
```

## 5. 非目标

本主线不授权：

```text
1. 训练 qlib/LTR/policy 模型；
2. 使用 LTR/orthogonal LTR/stacking score；
3. 无界 grid search；
4. 根据 2022 或 2023-2025 结果反复调阈值；
5. production/default/provider/frontend/Agent/monitor/order 链路改动；
6. OrderIntent、target_weight、target_position、quantity_instruction；
7. broker / quick-trade / real order；
8. 收益承诺、胜率承诺、上涨概率或买入概率。
```

本主线也不允许：

```text
把 RULE_05 的 qlib-only 研究通过，包装成 qlib+LTR 或生产策略通过。
```

## 6. 候选策略冻结范围

RCPT7 只允许以下预声明候选。

### Candidate A: RULE_05 + Adaptive Buy Filter

机制：

```text
正常市况沿用 qlib-only baseline/top50 轮动；
risk-off 中保留 RULE_05 early sell；
risk-off 中补仓必须按 adaptive_score_baseline 排序或通过 adaptive score 区间过滤。
```

目的：

```text
避免卖出弱持仓后又补入高风险、高波动、score 失真的标的。
```

### Candidate B: Top50 Adaptive Score + RULE_05 Sell Overlay

机制：

```text
以 rank_rotate_top50_adaptive_score 为主体；
仅叠加 RULE_05 weak-rank-deterioration early sell；
不改变 adaptive_score_baseline 公式。
```

目的：

```text
在旧版强基线基础上检查 sell overlay 是否能进一步降低 2022 风险。
```

### Candidate C: Adaptive Score Conservative Variant

机制：

```text
使用 adaptive_score_baseline；
risk-off 下提高补仓门槛或减少补仓数量；
候选阈值必须在 RCPT7A 合同阶段预冻结。
```

目的：

```text
接近旧版自适应 score，但进一步降低极端下跌市补仓风险。
```

## 7. 必须比较的 Baseline

RCPT7 不得再只比较弱 baseline。

必须比较：

```text
1. rank_rotate_top50_adaptive_score
2. rank_rotate_top50
3. RCPT1_RULE_05
4. qlib-only baseline used in RCPT5B
```

其中主 baseline 是：

```text
rank_rotate_top50_adaptive_score
```

## 8. 必须验证的窗口

### 8.1 2022 Downturn Diagnostic

语义：

```text
downturn diagnostic
not strict OOS
```

用途：

```text
检查是否接近/优于旧 Top50 adaptive score 的下跌年表现。
```

### 8.2 2021 Pre-2022 Sanity

语义：

```text
pre-2022 sanity diagnostic
not strict OOS
```

用途：

```text
检查候选是否提前暴露过度现金化、费用过高或收益崩坏。
```

### 8.3 2023-2025 Qlib-only Strict OOS Candidate

语义：

```text
qlib-only strict OOS candidate
```

用途：

```text
检查候选是否在独立 TEST fold 上保持收益捕获率和回撤改善。
```

## 9. 新 Gate

RCPT7 gate 必须比 RCPT6 更严格。

### 9.1 Return Capture

硬要求：

```text
return_capture_vs_rank_rotate_top50_adaptive_score >= 0.85
```

理想要求：

```text
return_capture_vs_rank_rotate_top50_adaptive_score >= 0.90
```

如果 baseline return 为负，则使用：

```text
loss_reduction_vs_rank_rotate_top50_adaptive_score >= 0
```

并要求：

```text
candidate loss 不得明显差于 adaptive baseline。
```

### 9.2 Downturn 2022 Gate

候选必须满足：

```text
2022 net_return_after_fee_tax >= rank_rotate_top50_adaptive_score - 0.03
2022 max_drawdown <= rank_rotate_top50_adaptive_score drawdown severity + 0.03
```

解释：

```text
允许最多 3pp 收益/回撤容忍带；
否则说明没有达到旧自适应 score 的实用水平。
```

### 9.3 Strict OOS 2023-2025 Gate

候选必须满足：

```text
return_capture >= 0.85
max_drawdown not worse than adaptive baseline by more than 3pp
primary_average_cash_rate <= 0.65
cash_gt_90pct_equity_day_share <= 0.25
fee/tax not worse without return compensation
top_month / top_symbol / top_trigger concentration PASS
```

### 9.4 行为 Gate

候选不得：

```text
1. all-cash/no-trade；
2. 长期空仓换低回撤；
3. 只靠少数月份/个股；
4. 费用或换手失控；
5. 使用 future return label；
6. replay 后调阈值再重跑。
```

## 10. 阶段计划

### RCPT7A: Adaptive Score Contract And Data Readiness

目标：

```text
合同化 adaptive_score_baseline、ret20、volatility20、TWII_ret20、qlib_score_zscore_by_date；
确认 2021/2022/2023-2025 是否都有可 PIT-safe 生成这些字段；
冻结 Candidate A/B/C；
冻结 gate。
```

输出：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT7A_ADAPTIVE_SCORE_CONTRACT_AND_DATA_READINESS_EXECUTION_REPORT_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt7a_adaptive_score_contract_and_data_readiness/
```

### RCPT7B: Predeclared Candidate Replay

前提：

```text
RCPT7A review PASS。
```

目标：

```text
只回放 RCPT7A 冻结的 Candidate A/B/C；
不得新增候选或调阈值。
```

输出：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT7B_ADAPTIVE_SCORE_ALIGNED_REPLAY_EXECUTION_REPORT_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt7b_adaptive_score_aligned_replay/
```

### RCPT7C: Closure

目标：

```text
判断是否存在候选达到“收益不过度牺牲 + 下跌年明显改善”的标准。
```

可能结论：

```text
PASS_AS_RESEARCH_CANDIDATE
PASS_READY_FOR_QLIB_LTR_ADAPTATION_DESIGN
FAIL_NO_CANDIDATE_BEATS_ADAPTIVE_BASELINE_TRADEOFF
STOP_SCOPE_OR_DATA_CONTRACT_VIOLATION
```

## 11. RCPT7A 工作文档

### 11.1 执行者任务

执行者必须：

```text
1. 读取本主线文档；
2. 读取 RCPT6 adaptive score comparison opinion；
3. 读取旧 adaptive_score_baseline 公式来源；
4. 盘点 2021/2022/2023-2025 需要的字段覆盖；
5. 判断 ret20、volatility20、TWII_ret20、qlib_score_zscore_by_date 是否可 PIT-safe 构造；
6. 冻结 Candidate A/B/C 的精确定义；
7. 冻结 gate；
8. 不执行 replay。
```

### 11.2 必须输出

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt7a_adaptive_score_contract_and_data_readiness/
```

必须生成：

```text
manifest.json
adaptive_score_formula_contract.md
adaptive_feature_coverage_audit.csv
pit_feature_derivation_contract.md
candidate_rule_contract.csv
baseline_comparison_contract.csv
gate_contract.md
forbidden_action_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT7A_ADAPTIVE_SCORE_CONTRACT_AND_DATA_READINESS_EXECUTION_REPORT_CN.md
```

### 11.3 审查者职责

审查者必须判断：

```text
1. adaptive_score_baseline 是否精确还原；
2. 所需字段是否 PIT-safe；
3. Candidate A/B/C 是否预声明且不可变；
4. gate 是否足够严格；
5. 是否没有 replay、训练、调参或生产越权。
```

审查结论只能是：

```text
PASS_READY_FOR_RCPT7B_PREDECLARED_REPLAY
FAIL_NEEDS_RCPT7A_REPAIR
STOP_ADAPTIVE_FEATURES_NOT_PIT_SAFE
STOP_SCOPE_OR_FORBIDDEN_ACTION_VIOLATION
```

## 12. 安全边界

RCPT7 全线禁止：

```text
production/default/provider change
frontend/Agent/monitor/order integration
broker / quick-trade / real order
OrderIntent
target_weight
target_position
quantity_instruction
model training
LTR score usage
unbounded threshold search
future return label as strategy input
```

内部 replay ledger 只能用于：

```text
readonly accounting and research attribution
```

不得用于真实交易建议。
