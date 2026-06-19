# Phase S1B0 工作文档：Qlib Score/Rank 生成政策与 Universe 口径冻结

生成日期：2026-06-14

## 1. 背景与入口

依据用户确认，本轮进入 S1B0，但不是直接训练或回放。

输入文档：

- `docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md`
- `docs/tw_ltr_qlib_split_aligned_retrain/PHASES1A_SCORE_RANK_COVERAGE_REPORT_CN.md`
- `docs/tw_ltr_qlib_split_aligned_retrain/PHASES1A_REVIEW_STOP_AND_USER_DECISION_CN.md`

S1A 已确认：

- frozen qlib `pred.pkl` 只覆盖 `2023-01-03..2025-06-30`；
- S1 train `2015-05-04..2020-12-31` 与 validation `2021-01-01..2022-12-31` 没有 frozen qlib score/rank；
- 当前 LTR rerank 方法依赖 `qlib_score_raw` / `qlib_rank`；
- 不能直接进入 S1B 样本构建与 LTR 训练。

用户已选择默认路线：

```text
cross-fit / walk-forward qlib scores + 优先 PIT/as-of active universe
```

## 2. S1B0 目标

S1B0 只回答：

```text
是否能以可审查、PIT-safe、无 test 反馈的方式，为 S1 split 生成 qlib score/rank，并冻结 universe 口径、fold/window/参数和可行性检查？
```

S1B0 不回答：

- LTR 方法是否有效；
- LTR 是否比 qlib / Top50 baseline 更好；
- 是否进入 S2 新鲜重训；
- 是否改变前端默认策略。

## 3. S1B0 严格禁止事项

本轮禁止：

- 不训练 LTR；
- 不训练 qlib 模型；
- 不实际生成 qlib score/rank；
- 不构建 S1 LTR 训练样本；
- 不跑组合回放；
- 不调参；
- 不改前端/API；
- 不联网；
- 不触发 provider refresh / publish；
- 不切换 accepted latest；
- 不触发 monitor config save / scan / alerts write；
- 不连接 broker、orders、quick-trade；
- 不输出买卖、持有、仓位、target position、target weight、收益承诺、胜率或上涨概率。

S1B0 只能读取本地已有文件，输出设计与可行性审计文档/表格。

## 4. 固定 S1 Split

S1 split 仍固定为：

| split | 日期区间 | 说明 |
| --- | --- | --- |
| train | `2015-05-04..2020-12-31` | LTR split-aligned 训练期，但 qlib score 必须避免 in-sample 语义污染 |
| validation | `2021-01-01..2022-12-31` | LTR 参数选择/模型选择期 |
| test | `2023-01-01..2025-06-30` | 最终评估期，不得用于训练、调参、fold 设计修改 |

## 5. 默认 Qlib Score/Rank 生成政策

### 5.1 默认路线：walk-forward qlib scores

默认采用 walk-forward qlib score/rank，而不是 frozen qlib 模型对 train 期回打 in-sample score。

原则：

- 每个被打分日期的 qlib 模型只能使用该日期之前的数据训练；
- 不使用 S1 test 结果决定 fold/window/参数；
- qlib 参数沿用 frozen Option C 配置，不做搜索；
- 生成的 score/rank 只作为 LTR input feature，不得解释为交易信号；
- 后续实际训练/打分必须另行授权，S1B0 只冻结计划。

### 5.2 预冻结 qlib 参数

执行者必须从以下配置读取并固化，不得修改：

- config：`qlib_pipeline/configs/tw_yahoo_primary_alpha158.yaml`
- model：`qlib.contrib.model.gbdt.LGBModel`
- handler：`qlib.contrib.data.handler.Alpha158`
- dataset：`qlib.data.dataset.DatasetH`
- feature：Alpha158 标准特征
- provider：本地 qlib 数据，不触发 provider refresh/publish

参数以 frozen config 为准，包括但不限于：

- `loss: mse`
- `learning_rate: 0.05`
- `colsample_bytree: 0.8879`
- `subsample: 0.8789`
- `lambda_l1: 205.6999`
- `lambda_l2: 580.9768`
- `max_depth: 8`
- `num_leaves: 210`
- `num_threads: 8`

如执行者发现实际 recorder artifact 与 config 不一致，必须报告并停止，不得自行选择。

### 5.3 预冻结 walk-forward window 草案

S1B0 需要验证以下草案是否可行，不实际训练：

| score target | qlib train window | qlib validation window | score window | 用途 |
| --- | --- | --- | --- | --- |
| WF-2017 | `2015-05-04..2016-12-31` | none or internal last 3 months | `2017-01-01..2017-12-31` | LTR train score |
| WF-2018 | `2015-05-04..2017-12-31` | none or internal last 3 months | `2018-01-01..2018-12-31` | LTR train score |
| WF-2019 | `2015-05-04..2018-12-31` | none or internal last 3 months | `2019-01-01..2019-12-31` | LTR train score |
| WF-2020 | `2015-05-04..2019-12-31` | none or internal last 3 months | `2020-01-01..2020-12-31` | LTR train score |
| WF-VAL | `2015-05-04..2020-12-31` | frozen qlib validation `2021-01-01..2022-12-31` only for qlib training protocol if required | `2021-01-01..2022-12-31` | LTR validation score |
| TEST | frozen recorder `950741cfd5f14ee5a05464fec3e12e0a` | fixed | `2023-01-01..2025-06-30` | LTR test score / baseline comparison |

重要说明：

- `2015-05-04..2016-12-31` 无法在严格 walk-forward 下被打分，因为没有足够更早训练数据。S1B0 必须报告这段是否从 LTR train 中排除，或是否需要用户接受 blocked cross-fit 降级方案。
- 默认不采用 blocked K-fold cross-fit，因为它会让某些 train 日期的 qlib score 使用 train 内未来日期训练，不符合严格 PIT/as-of 优先原则。
- 若执行者认为 walk-forward 样本不足，必须报告样本规模与影响，不得自动改成 in-sample 或 blocked cross-fit。

### 5.4 允许的降级 score 方案

若 walk-forward qlib scores 因训练窗口太短、数据缺口或 qlib 执行成本不可行，S1B0 可提出降级方案，但不能执行。

可讨论降级：

1. `blocked_cross_fit_within_train_only`
   - 只在 S1 train 内做 blocked cross-fit；
   - 不碰 validation/test；
   - 结论降级为 train-internal cross-fit rerank validation，不称严格 PIT walk-forward。

2. `static_in_sample_frozen_train_scores`
   - 用 `2015-05-04..2020-12-31` 训练后的 qlib 模型回打 train；
   - 仅可作为最低优先级方案；
   - 结论必须大幅降级，不能声称严格样本外方法验证。

执行者不得选择降级方案，只能列出可行性、风险和所需用户确认。

## 6. Universe 口径冻结

### 6.1 默认优先：PIT/as-of active dynamic universe

S1B0 必须优先验证 dynamic universe 是否可行。

定义：对每个 asof 日期，候选股票必须同时满足：

- 在 qlib `tw_liquid_dyn` instrument range 中当日有效；
- 本地 normalized price 当日存在；
- 计算 Alpha158 / LTR 技术特征所需历史窗口足够；
- 没有使用 future accepted list、future top list 或全窗口 active days 排序；
- 若需要限制为 Top150，必须用 as-of 可得的 trailing liquidity 排序，例如截至当日的过去 20/60 日成交金额，不能用未来数据。

S1B0 必须先检查本地是否有足够字段支持 trailing liquidity Top150：

- close / vwap；
- volume；
- factor / adjusted price；
- calendar；
- instrument start/end range。

若 daily dynamic Top150 可行，应冻结为 S1 默认 universe。

### 6.2 dynamic universe 可行性表

执行者必须输出按 split / year 的 universe feasibility：

- active symbol count；
- top150 selected count；
- missing price count；
- insufficient history count；
- excluded by instrument range count；
- selected universe min / median / max count；
- 是否存在日期 selected count < 50 或其他不可训练风险。

### 6.3 static accepted 150 降级方案

若 dynamic universe 不可行，允许设计 static accepted 150 降级方案，但必须满足：

- 明确 static list 来源；
- 明确是否包含未来才入池股票；
- 明确这是 static research universe，不是严格 PIT/as-of active universe；
- 后续 S1 结论必须降级为 `static_accepted_150_research_replay`；
- 不得宣称严格全市场 PIT 公平验证。

执行者不得在 S1B0 直接采用 static accepted 150，只能报告 dynamic 不可行原因并提出降级方案等待审查。

## 7. S1B0 必须产出

建议输出目录：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b0_policy_freeze/
```

必须产物：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b0_policy_freeze/phase_s1b0_qlib_score_generation_policy.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b0_policy_freeze/phase_s1b0_walk_forward_fold_plan.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b0_policy_freeze/phase_s1b0_qlib_config_freeze.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b0_policy_freeze/phase_s1b0_dynamic_universe_feasibility.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b0_policy_freeze/phase_s1b0_static_universe_degrade_plan.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b0_policy_freeze/phase_s1b0_gate_summary.json
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B0_POLICY_FREEZE_EXECUTION_REPORT_CN.md
```

## 8. S1B0 报告必须回答

1. walk-forward qlib score 生成计划是否覆盖足够的 LTR train / validation / test？
2. 2015-2016 无法严格 walk-forward 打分时，建议如何处理？排除、降级，还是停止？
3. qlib 参数是否完全沿用 frozen config？是否发现 config / recorder 不一致？
4. dynamic PIT/as-of active universe 是否可行？
5. 如果 dynamic universe 不可行，static accepted 150 降级方案是什么，结论如何降级？
6. 是否需要执行者下一轮实际训练 qlib folds / 生成 score/rank？
7. 是否存在任何 provider、accepted latest、monitor、前端/API、交易链路越权？

## 9. S1B0 Gate

S1B0 只能给以下 gate 之一：

```text
s1b0_policy_freeze_pass_request_s1b1_qlib_score_generation
s1b0_dynamic_universe_infeasible_static_degrade_requires_user_confirmation
s1b0_walk_forward_score_generation_infeasible
s1b0_blocked_by_leakage_or_scope_violation
```

解释：

- `s1b0_policy_freeze_pass_request_s1b1_qlib_score_generation`：walk-forward qlib score 计划和 dynamic universe 都可行，可申请下一轮实际生成 qlib score/rank。
- `s1b0_dynamic_universe_infeasible_static_degrade_requires_user_confirmation`：dynamic universe 不可行，只能走 static accepted 150 降级，必须由用户确认。
- `s1b0_walk_forward_score_generation_infeasible`：walk-forward qlib score/rank 计划不可行，S1 不能继续。
- `s1b0_blocked_by_leakage_or_scope_violation`：发现 future leakage、provider/accepted latest/monitor/交易链路越权或其他主线外扩。

## 10. 下一轮不得做的事

即使 S1B0 输出设计可行，执行者也不得在同一轮继续实际训练或生成 qlib score/rank。必须等待审查者审查 S1B0 报告后，再由审查者撰写 S1B1 工作文档。

## 11. 给执行者的一句话

请执行 Phase S1B0：只读冻结 cross-fit / walk-forward qlib score/rank 生成政策、fold/window/参数、PIT/as-of dynamic universe 可行性与 static accepted 150 降级方案；不得训练 qlib/LTR、不得生成 score、不得构建 LTR 样本、不得回放、不得调参、不得改前端/API、不得 provider/accepted latest/monitor/交易链路；完成后提交 `docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B0_POLICY_FREEZE_EXECUTION_REPORT_CN.md` 等待审查。
