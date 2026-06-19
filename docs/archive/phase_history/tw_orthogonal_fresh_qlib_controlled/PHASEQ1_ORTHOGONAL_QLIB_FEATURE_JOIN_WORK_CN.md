# Phase Q1 工作文档：Orthogonal Qlib Feature Join 与样本对齐

生成日期：2026-06-15

## 1. 本阶段目标

本阶段只做一件事：

```text
在不改变原 fresh qlib baseline 的 Alpha158、label、split、universe、模型参数和回放合同的前提下，
把 Q0 已冻结的 O2 PIT-safe 正交特征按 instrument + datetime 拼接成 qlib 可训练样本，
并输出 schema、行对齐、缺失、PIT 安全审计。
```

本阶段不训练模型、不回放、不比较收益。

## 2. 上游合同

必须严格沿用：

- 主线文档：`docs/tw_orthogonal_fresh_qlib_controlled/ORTHOGONAL_FRESH_QLIB_CONTROLLED_MAINLINE_CN.md`
- Q0 执行报告：`docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ0_CONTROL_AND_FEATURE_CONTRACT_EXECUTION_REPORT_CN.md`

Q0 gate 必须保持为：

```text
phase_q0_control_and_orthogonal_feature_contract_frozen
```

## 3. Control 冻结项

Q1 不得改变以下 fresh qlib control 合同：

```text
train:      2017-01-10..2024-12-31
validation: 2025-01-01..2025-06-30
test:       2025-07-01..2026-05-07

handler_start: 2015-05-04
handler_end:   2026-05-07
fit_start:     2015-05-04
fit_end:       2024-12-31

provider: qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin
handler instruments: all
post-score filter: tw_liquid_dyn as-of active instrument range / same-day price / >=60 history / trailing 60-day value top150
model family: qlib.contrib.model.gbdt.LGBModel
replay: next-day execution, target_position_count=10, candidate_k=50
```

Q1 只能验证 treatment 样本是否能在上述合同下安全拼接。

## 4. 唯一允许新增变量

唯一允许新增：

```text
Q0 已批准的 O2 PIT-safe 法人筹码与融资融券正交特征，以及对应 missing / delay / lineage 字段。
```

允许输入目录：

```text
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/
```

必须读取并复核：

```text
normalized_feature_daily.csv
feature_dictionary.csv
pit_leakage_audit.csv
pit_lineage_audit.csv
```

允许数据族：

```text
TaiwanStockInstitutionalInvestorsBuySell
TaiwanStockMarginPurchaseShortSale
```

禁止新增：

- 月营收 YoY；
- 估值数据；
- 其他 FinMind dataset；
- 新技术指标；
- 新市场状态指标；
- LTR score / LTR rank / LTR label；
- 任何新 filter / market gate / turnover rule。

## 5. Q1 执行范围

执行者应完成：

1. 读取原 fresh qlib baseline 的可训练样本定义、日期切分和 label 定义。
2. 设计 qlib handler / dataset 对外部正交特征的接入方式。
3. 保留原 Alpha158 特征，不得重命名、删除或改写原特征。
4. 按 `instrument + datetime` 对齐正交特征。
5. Treatment 必须按真实 `available_at` 做 as-of join。
6. 缺失值只能 neutral fill，并保留每个正交特征族的 missing flag。
7. 保留 `delay_days` / `delay_reason` / lineage。
8. 输出 control vs treatment 的 schema diff。
9. 输出 row alignment audit。
10. 输出 missing report。
11. 输出 PIT leakage audit。
12. 输出 forbidden action audit。

## 6. PIT 与 available_at 合同

必须沿用：

```text
PIT-safe delayed availability
available_at >= next_trading_day(trade_date)
```

硬约束：

- 必须按真实 `available_at <= signal_asof` 取数；
- 不得人工提前 `available_at`；
- 不得把 delayed rows 当作 exact T+1；
- 不得用 test 后数据修正 test 内特征；
- 不得用未来日期的正交数据填补过去样本；
- 不得因为正交特征缺失删除原 fresh qlib 样本或股票。

如果发现某些正交数据无法在 next-day / delayed availability 合同下使用，只能记录为 missing 或 delay，不得调整样本窗口或提前可用时间。

## 7. 必须满足的等式

Q1 报告必须明确证明：

```text
control_label == treatment_label
control_split == treatment_split
control_universe_policy == treatment_universe_policy
only_added_columns == approved_orthogonal_features_and_missing_flags
```

并给出证据路径。

## 8. 输出产物要求

执行者应输出到独立 Q1 实验目录，例如：

```text
data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q1_orthogonal_qlib_feature_join/
```

至少包含：

```text
feature_join_manifest.json
schema_diff.csv
row_alignment_audit.csv
missing_report.csv
pit_leakage_audit.csv
available_at_join_audit.csv
forbidden_action_audit.json
```

如生成 qlib handler / dataset config 草案，必须放在 Q1 目录下，并标明：

```text
draft only, no training executed
```

## 9. 执行报告要求

必须输出：

```text
docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ1_ORTHOGONAL_QLIB_FEATURE_JOIN_EXECUTION_REPORT_CN.md
```

报告必须包含：

- 做了什么；
- 使用的 artifact；
- 输入/输出路径；
- row count；
- 日期范围；
- symbol 覆盖；
- control/treatment schema diff；
- control/treatment row alignment；
- missing ratio by feature family；
- available_at / signal_asof join 口径；
- PIT leakage audit 结果；
- 是否改变 label / split / universe / Alpha158；
- 是否引入 LTR；
- 是否新增 filter / market gate / turnover rule；
- 是否触发 frontend / API / provider / accepted latest / monitor / broker / orders / quick-trade；
- 是否触发停止条件；
- 是否建议进入 Q2。

## 10. 停止条件

遇到以下任一情况必须停止并报告，不得自行绕过：

- qlib handler 无法安全接入外部正交特征；
- 必须改变 label 或 split；
- 必须改变 universe 或 post-score filter；
- 必须删行、删股票或缩小样本才能对齐；
- 原 Alpha158 特征被改动；
- 正交特征 join 出现未来函数风险；
- `available_at` 需要从 delayed availability 改成更激进口径；
- 需要新增 O2 之外的数据源或特征族；
- 需要训练模型才能判断 Q1 是否通过。

如果合同需要改变，必须停下来让用户确认。

## 11. 禁止事项

Q1 禁止：

- 训练 Orthogonal Fresh Qlib；
- 训练或调用 LTR；
- 调参；
- 改 label；
- 改 split；
- 改 universe；
- 改 post-score filter；
- 改 replay 规则；
- 用收益率证明策略优劣；
- 改默认前端策略；
- 接 provider refresh / publish / accepted latest；
- 接 monitor / broker / orders / quick-trade；
- 发出任何真实交易建议、目标仓位、目标权重、收益承诺、胜率或上涨概率。

## 12. Gate

Q1 通过 gate：

```text
phase_q1_orthogonal_qlib_feature_join_passed
```

只有在以下条件全部满足时，审查者才可允许进入 Q2：

- control 合同未变；
- 原 Alpha158、label、split、universe 未变；
- 只新增 Q0 白名单正交特征与 missing/delay/lineage 字段；
- row alignment 没有删样本或删股票；
- PIT / available_at 审计无未来函数；
- 没有引入 LTR 或任何额外规则；
- 没有触发前端、provider、accepted latest、monitor 或交易链路。

## 13. 给执行者的一句话

```text
请按 docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ1_ORTHOGONAL_QLIB_FEATURE_JOIN_WORK_CN.md 执行 Phase Q1：在不改原 fresh qlib Alpha158、label、split、universe、模型参数和回放合同的前提下，只把 Q0 批准的 O2 PIT-safe 法人筹码与融资融券正交特征按 instrument + datetime 和真实 available_at 做 as-of join，输出 schema diff、row alignment、missing、PIT/available_at 和 forbidden action 审计；不得训练模型、不得引入 LTR、不得新增规则或触发前端/provider/accepted latest/monitor/交易链路。
```

## 14. 给审查者的一句话

```text
请按 docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ1_ORTHOGONAL_QLIB_FEATURE_JOIN_WORK_CN.md 审查执行者 Q1 报告，重点确认 control_label/split/universe 与 treatment 完全一致、only_added_columns 只包含 Q0 白名单正交特征和 missing/delay/lineage 字段、available_at join 无未来函数、没有删样本或删股票、没有训练模型或引入 LTR/额外规则，并判断是否允许进入 Q2。
```
