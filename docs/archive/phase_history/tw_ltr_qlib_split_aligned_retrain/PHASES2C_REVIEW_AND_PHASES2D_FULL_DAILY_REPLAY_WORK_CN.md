# Phase S2C 审查意见与 Phase S2D Full Daily Replay 工作文档

生成日期：2026-06-14

审查入口：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES2C_FRESH_LTR_SAMPLE_TRAINING_EXECUTION_REPORT_CN.md
```

主线依据：

```text
docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md
docs/tw_ltr_qlib_split_aligned_retrain/PHASES2B_REVIEW_AND_PHASES2C_FRESH_LTR_SAMPLE_TRAINING_WORK_CN.md
```

---

## 1. 审查结论

结论：`S2C 通过，允许进入 Phase S2D full daily replay。`

通过理由：

- S2C 使用了 S2B post-filter qlib score/rank；
- 使用的是 post-filter 后的 `qlib_rank`，不是 raw `qlib_rank_raw_by_split`；
- feature 合同仍为 S1B3 冻结的 34 个输入列；
- label 合同仍为 `ltr_relevance_label / topk_forward_bucket / 10 trading days / fixed percentile thresholds`；
- 实际训练脚本使用 `training_row_eligible == true` 作为训练输入；
- `training_row_eligible` 已验证等于 `sample_complete & split_purity_keep` 的子集，没有 eligible 但不 complete 或不 purity keep 的行；
- fresh LTR 模型已训练，LTR score/rank 已物化；
- test LTR score 覆盖 `2025-07-01..2026-05-07` 共 205 个交易日；
- turnover-controlled usage config 仅复用冻结配置，未重选；
- 未跑 replay、未比较收益、未调参、未改前端/API、未触发 provider refresh/publish、未切换 accepted latest、未触发 monitor 或交易链路。

允许进入：

```text
Phase S2D full daily replay
```

不允许跳到：

```text
default strategy decision
frontend/API integration
provider refresh/publish
accepted latest switching
monitor
trading chain
```

---

## 2. 关键证据

### 2.1 Label horizon / split purity

S2C 样本审查核查：

| split | rows | sample_complete | split_purity_keep | training_row_eligible |
| --- | ---: | ---: | ---: | ---: |
| train | 136685 | 132875 | 135845 | 132035 |
| validation | 10068 | 9958 | 9228 | 9118 |
| test | 22613 | 22474 | 21215 | 21080 |

只读核查：

```text
eligible_not_sample_complete = 0
eligible_not_purity_keep = 0
```

解释：

- train / validation / test 末尾 label horizon 溢出的 sample_complete rows 已从 `training_row_eligible` 中剔除；
- train 模型拟合不使用越过 train end 的 label；
- validation 评估不使用越过 validation end 的 label；
- test 没有用于训练或调参。

### 2.2 实际训练脚本使用 eligible rows

`scripts/train_tw_ltr_s2c_fresh_model.py` 中实际逻辑：

```text
train_sample = sample[sample["training_row_eligible"] == True]
train = train_sample[train_sample["split"] == "train"]
valid = train_sample[train_sample["split"] == "validation"]
```

因此虽然报告/manifest 有命名不清，实际训练输入已按 purge 后 eligibility 执行。

### 2.3 LTR score 覆盖

S2C LTR score coverage：

| split | date_start | date_end | date_count | row_count | selected_min | selected_median | selected_max |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| train | 2017-01-17 | 2024-12-31 | 1934 | 132875 | 12 | 68.0 | 89 |
| validation | 2025-01-02 | 2025-06-30 | 116 | 9958 | 82 | 86.0 | 89 |
| test | 2025-07-01 | 2026-05-07 | 205 | 22474 | 87 | 109.0 | 149 |

LTR score：

```text
ltr_score_missing = 0
ltr_rank_missing = 0
duplicate_date_instrument = 0
```

解释：

- test 日期完整覆盖；
- LTR score 行数略少于 S2B qlib post-filter，是 feature completeness 过滤导致；
- S2D 必须如实记录各策略 score universe 覆盖差异，不得静默补齐 LTR 缺失行。

---

## 3. Findings

### Low 1：S2C 报告中的 `training_row_eligible` 表格列名有误

S2C 报告的 Label Horizon 表格中 `training_row_eligible` 列实际写入的是 `split_purity_keep_row_count`：

```text
train: report training_row_eligible = 135845
actual training_row_eligible = 132035
```

该问题不影响训练结果，因为脚本实际使用 `training_row_eligible == true`，但 S2D 报告中不得沿用这组错误列名。

### Low 2：training manifest 的 split_rows 是 scoring rows，不是 training rows

`phase_s2c_training_manifest.json` 的 `split_rows` 来自 scored rows：

```text
train = 132875
validation = 9958
test = 22474
```

这些等于 `sample_complete` / feature-complete scoring rows，不是实际训练 eligible rows。S2D 引用时必须写作 `scored_rows`，不要写成 `training_rows`。

### Low 3：安全边界通过

未发现以下越权：

- frontend/API 修改；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 真实买卖建议、收益承诺、胜率承诺或上涨概率承诺；
- 新数据源或联网。

---

## 4. Gate

S2C gate 接受：

```text
s2c_fresh_ltr_training_pass_request_s2d_full_daily_replay
```

下一轮执行：

```text
Phase S2D full daily replay
```

---

## 5. Phase S2D 工作目标

S2D 只回答一个问题：

```text
在同一个 S2 fresh validation/test 和同一个 S1B6R accounting 口径下，fresh qlib baseline 与 fresh LTR 候选策略的历史模拟表现如何？
```

S2D 可以做历史组合回放和指标比较，但不能决定产品默认策略，也不能进入前端/API。

---

## 6. Phase S2D 固定输入

### 6.1 qlib baseline score

必须使用：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv
```

用于：

```text
fresh_qlib_top50_adaptive_baseline
fresh_rank_rotate_top50
fresh_confirmed_exit
```

### 6.2 LTR score

必须使用：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_score_rank.csv
```

用于：

```text
fresh_ltr_simple
fresh_ltr_turnover_controlled
```

### 6.3 split

必须分开输出：

```text
validation = 2025-01-01..2025-06-30
test = 2025-07-01..2026-05-07
```

validation 可作为诊断，不得用于重选参数或重选 usage config。

test 是 S2 fresh holdout，不得反向调参。

---

## 7. Phase S2D 回放口径

必须沿用 S1B6R accounting：

```text
signal_date/asof -> pending orders
execution_date -> next trading day close
effective_nav_date == execution_date
signal_date 不影响 same-day NAV
```

必须保留：

```text
initial_equity
fee / tax
next-day close execution
last signal without next trading price 不得生成新成交
```

不得回到旧的 same-day NAV 口径。

---

## 8. Phase S2D 候选策略

至少比较：

```text
fresh_qlib_top50_adaptive_baseline
fresh_rank_rotate_top50
fresh_confirmed_exit
fresh_ltr_simple
fresh_ltr_turnover_controlled
```

说明：

- `fresh_ltr_simple` 与 `fresh_ltr_turnover_controlled` 仍保持同级候选，不得提前分高低；
- turnover-controlled 只能复用冻结 config `k30_a3_gap0.0_buf0.0_holdw2_budget0.2`；
- 不得在 validation/test 上重选 turnover 参数；
- 如果 qlib baseline 和 LTR score universe 行数不同，必须如实报告 coverage 差异，不得填补或删除对手策略的有效分数以制造一致。

---

## 9. Phase S2D 指标

必须输出：

```text
fee_tax_adjusted_net_return
max_drawdown
action_count
buy_count
sell_count
fee_and_tax
turnover_proxy_by_notional_over_avg_equity
relative_return_vs_fresh_top50_adaptive
relative_drawdown_vs_fresh_top50_adaptive
relative_actions_vs_fresh_top50_adaptive
```

必须分段：

```text
validation full
test full
2025H2 test
2026YTD_to_2026-05-07 test
rolling 6m within test only
```

如 test 长度不足以形成某个 rolling 窗口，必须写明，不得越界。

---

## 10. Phase S2D 必须审计

执行者必须输出：

1. score coverage audit：
   - 每个策略每日可用 score 数；
   - missing score / duplicate key；
   - LTR 与 qlib baseline 的 universe 差异。

2. accounting audit：
   - 首日 NAV 是否等于 initial equity；
   - 首批 action 是否从下一交易日生效；
   - signal date 是否影响 same-day NAV；
   - 最后一天是否错误生成无法成交订单；
   - fee/tax 是否只在 execution date 扣除。

3. split / tuning audit：
   - validation 是否只用于诊断；
   - test 是否未用于调参；
   - turnover usage config 是否未重选；
   - 是否未新增策略变体。

4. safety audit：
   - no frontend/API；
   - no provider refresh/publish；
   - no accepted latest switching；
   - no monitor/trading chain；
   - no broker / quick-trade / orders；
   - no target position / target weight；
   - no future return / win-rate / probability promise。

---

## 11. Phase S2D 禁止事项

本轮禁止：

- 训练 qlib；
- 训练 LTR；
- 调参或参数搜索；
- 重选 turnover-controlled config；
- 新增策略变体；
- 改 split；
- 改 feature / label；
- 新增数据源；
- 联网；
- provider refresh / publish；
- accepted latest switching；
- 改前端/API；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 买卖建议、收益承诺、胜率承诺、上涨概率承诺；
- 决定产品默认策略。

---

## 12. Phase S2D 交付物

建议输出目录：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/
```

必须产物：

```text
phase_s2d_strategy_input_coverage_audit.json
phase_s2d_replay_metrics_by_strategy.csv
phase_s2d_replay_metrics_by_segment.csv
phase_s2d_rolling_6m_metrics.csv
phase_s2d_action_summary_by_strategy.csv
phase_s2d_accounting_audit.json
phase_s2d_split_tuning_audit.json
phase_s2d_forbidden_action_audit.json
phase_s2d_gate_summary.json
```

执行报告：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES2D_FULL_DAILY_REPLAY_EXECUTION_REPORT_CN.md
```

---

## 13. Phase S2D 通过条件

只有全部满足时，才允许下一轮进入 S2E fresh retrain conclusion / default candidate review：

```text
full_daily_replay_completed = true
s1b6r_accounting_preserved = true
validation_and_test_reported_separately = true
test_not_used_for_tuning = true
turnover_config_reused_without_reselection = true
all_required_candidates_reported = true
all_required_metrics_reported = true
score_coverage_differences_disclosed = true
no_training_in_s2d = true
no_parameter_search = true
no_new_strategy_variant = true
no_default_strategy_decision = true
no_provider_refresh_publish = true
no_accepted_latest_switching = true
no_frontend_or_api = true
no_monitor_or_trading_chain = true
```

通过 gate：

```text
s2d_full_daily_replay_pass_request_s2e_fresh_retrain_conclusion_review
```

失败 gate：

```text
s2d_blocked_by_accounting_regression
s2d_blocked_by_missing_candidate
s2d_blocked_by_metric_gap
s2d_blocked_by_test_tuning_or_config_reselection
s2d_blocked_by_scope_violation
```

---

## 14. 给执行者的一句话

请执行 Phase S2D：只用 S2B qlib score 和 S2C LTR score，在 S1B6R next-day accounting 下对 fresh qlib/top50/confirmed_exit/LTR simple/turnover-controlled 做 validation 与 untouched test 的完整日频历史回放，输出收益、回撤、动作、费用、换手、rolling 6m、coverage/accounting/tuning/safety 审计；不得训练、调参、重选 turnover config、改 feature/label/split、决定默认策略或触发 provider/accepted latest/前端/API/monitor/交易链路。
