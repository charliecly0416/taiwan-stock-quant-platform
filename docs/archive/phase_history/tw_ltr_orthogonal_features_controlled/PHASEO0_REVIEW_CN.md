# Phase O0 审查结论：Anchor 与 Control 合同冻结

生成日期：2026-06-15

审查对象：

```text
docs/tw_ltr_orthogonal_features_controlled/ORTHOGONAL_LTR_CONTROLLED_MAINLINE_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEO0_ANCHOR_AND_CONTROL_CONTRACT_EXECUTION_REPORT_CN.md
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o0_contract_freeze/
```

## 1. 审查结论

结论：

```text
通过
```

推荐 gate：

```text
phase_o0_anchor_and_control_contract_frozen
```

执行者本轮没有偏离新主线。O0 停留在 anchor/control 合同冻结，没有进入 O1，没有拉取 FinMind 数据，没有训练 qlib/LTR，没有回放新策略，也没有触发 frontend/API/provider/accepted latest/monitor/交易链路。

## 2. 通过项

### 2.1 Control identity 对齐主线

O0 报告与 Phase1C anchor card 对齐：

```text
candidate_id: head10_all_l31_alpha0.7_top50_only
model_id: head10_all_l31
score_column: score_head10_all_l31_alpha0.7_top50_only
blend_alpha: 0.7
preserve_scope: top50_only
label_col: relevance_10d_top_heavy
num_leaves: 31
learning_rate: 0.03
n_estimators: 120
random_state: 42
```

未发现替换 control、换 score column、换 label、换模型或换超参数。

### 2.2 Anchor replay 指标对齐

冻结窗口：

```text
2025-07-01..2026-05-07
```

Full universe：

```text
fee_tax_adjusted_net_return: 0.721631
max_drawdown: -0.050830
action_count: 405
```

Common universe：

```text
common universe key count: 22474
fee_tax_adjusted_net_return: 0.641235
max_drawdown: -0.076739
action_count: 405
```

这些数值与 Phase A2 anchor card 一致。

### 2.3 Control sample 合同已记录

O0 已记录 control 样本规模与 split：

```text
sample_raw_rows: 159993
sample_complete_rows: 152249
date_min: 2022-01-03
date_max: 2026-06-12
instrument_count: 150
train_rows: 92717
validation_rows: 31296
independent_test_rows: 31350
out_of_split_or_incomplete_rows: 4630
```

这满足 O0 “先冻结合同”的要求。后续 O3 必须继续证明 treatment 与 control 行级对齐，不能因为正交数据缺失而删行。

### 2.4 禁止变化清单符合主线

O0 输出的 forbidden checklist 覆盖了主线关键禁令：

```text
不重训 qlib
不训练 LTR
不进入 O1
不拉 FinMind
不改 control sample rows
不改 label / original features / model / hyperparameters
不新增 filter / threshold / market gate / turnover rule
不因正交特征缺失删行
不改 frontend/API/provider/accepted latest/monitor/trading
不使用收益率选择 O0 合同
```

未发现用户未授权的新规则。

## 3. 需要保留的风险提示

O0 的 score reproduction 使用的是既有 reproduction metrics 摘要：

```text
metric_rows: 24
max_abs_diff: 4.440892098500626e-16
tolerance: 0.0007
pass: yes
```

这对 O0 合同冻结可以接受，因为 Phase A1/A2 已经完成 anchor 复刻。但后续不能只靠这个摘要继续推进。

从 O3 开始必须把以下内容作为硬门槛：

```text
control_rows == treatment_rows
control_label_hash == treatment_label_hash
control_original_feature_hash == treatment_original_feature_hash
新增列只来自 O2 审查通过的正交特征族
缺失值只做 neutral fill + missing flag，不删行
```

## 4. 是否允许进入 O1

允许进入 O1，但 O1 只能做：

```text
正交数据可得性与 PIT 审计
```

O1 允许：

```text
小范围 FinMind 可得性测试
统计 API 成功率、字段稳定性、日期覆盖、缺失分布
验证 available_at = next_trading_day(trade_date)
输出 raw archive 设计与 PIT 审计报告
```

O1 禁止：

```text
训练 qlib 或 LTR
拼接 treatment 训练样本
改变 control 样本行
改变 label / 原有特征 / 训练窗口 / 回放窗口
引入月营收 YoY
引入新数据源或新账号权限后静默继续
新增过滤器、阈值、market gate、turnover rule
改前端/API/provider/accepted latest/monitor/交易链路
```

如 O1 发现 402/403/429、字段不稳定、历史覆盖不足、无法构造 `available_at`，或必须引入新数据源，应停止并提交用户确认。

## 5. 最终判断

Phase O0 可以通过并收尾。

下一步建议进入 Phase O1，但严格限定为 FinMind 法人筹码与融资融券的 PIT 可得性审计；不得提前训练、不得提前样本拼接、不得以收益率或策略效果作为 O1 的判断依据。
