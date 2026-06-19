# Phase S1B6R 审查意见与 Phase S2A Fresh Retrain Contract 工作文档

生成日期：2026-06-14

审查入口：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B6R_ACCOUNTING_REPAIR_EXECUTION_REPORT_CN.md
```

主线依据：

```text
docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B6_REVIEW_AND_PHASES1B6R_ACCOUNTING_REPAIR_WORK_CN.md
```

---

## 1. 审查结论

结论：`S1B6R accounting repair 通过，S1 结论为 split_aligned_ltr_method_supported，但只支持进入 S2 fresh retrain validation，不支持产品化或默认策略切换。`

理由：

- S1B6R 已修复 S1B6 的会计时点错误；
- 首日 NAV 已保持初始权益，首批交易从下一交易日才生效；
- accounting audit 满足上一轮要求；
- replay 只使用 `split == test` 的 `2023-01-03..2025-06-30`；
- 未发现训练、调参、改 feature/label/split/universe、联网、前端/API、provider、accepted latest、monitor 或交易链路越权；
- `split_aligned_ltr_turnover_controlled` 在 full test、12m rolling、regime 分段和动作数上显示足够继续验证的旧窗口增益。

但结论必须带 caveat：

- `split_aligned_ltr_simple` 单独不够强，full test 只小幅优于 Top50 adaptive，且 max drawdown 更差；
- `split_aligned_ltr_turnover_controlled` 在 `2025H1` 落后 Top50 adaptive，不能说稳定全面胜出；
- `rank_rotate_top50` 与 `rank_rotate_top30` 在当前 `position_count_target=10` 口径下退化为同一策略，不能当成两个独立 baseline 证据；
- S1 只是旧窗口公平验证通过，不能解释为当前可上线效果、未来收益更好、默认策略可切换。

允许进入：

```text
Phase S2A fresh retrain experiment contract freeze
```

不允许直接进入：

```text
产品化
前端/API 集成
provider refresh/publish
accepted latest switching
monitor
交易链路
默认策略切换
```

---

## 2. 关键证据

### 2.1 Accounting 修复证据

S1B6R accounting audit：

```text
signal_date_affects_same_day_nav = false
execution_date_before_or_equal_effective_nav_date = true
next_day_execution_not_counted_in_prior_day_nav = true
last_day_new_trade_without_next_price_count = 0
fee_tax_deducted_on_execution_date = true
accounting_mode = two_phase_pending_order_queue
```

首日 NAV：

```text
2023-01-03, equity=1000000.0, cash=1000000.0, holding_count=0
```

首批 action：

```text
signal_date=2023-01-03
execution_date=2023-01-04
effective_nav_date=2023-01-04
```

这说明上一轮发现的“下一交易日成交却计入 signal 当日 NAV”的问题已修复。

### 2.2 Full test 指标

| method | net_return | max_drawdown | actions | relative_return_vs_top50 | relative_drawdown_vs_top50 |
| --- | ---: | ---: | ---: | ---: | ---: |
| qlib_top50_adaptive_baseline | -0.112917 | -0.207861 | 1189 | 0.000000 | 0.000000 |
| confirmed_exit | -0.097833 | -0.184988 | 1189 | 0.015084 | 0.022873 |
| split_aligned_ltr_simple | -0.080041 | -0.276558 | 1185 | 0.032876 | -0.068697 |
| split_aligned_ltr_turnover_controlled | 0.130541 | -0.186466 | 180 | 0.243458 | 0.021395 |

解释：

- turnover-controlled LTR full test 明显优于 Top50 adaptive，且动作数显著更少；
- simple LTR 的收益略高，但回撤明显更差，不能单独作为强支持证据。

### 2.3 年度稳定性

`split_aligned_ltr_turnover_controlled`：

```text
2023: relative_return_vs_top50_adaptive = +0.186353
2024: relative_return_vs_top50_adaptive = +0.017311
2025H1: relative_return_vs_top50_adaptive = -0.040571
```

解释：

- 2023 和 2024 支持继续验证；
- 2025H1 不支持“全面稳定优于 baseline”的说法；
- 因此 S1 只能支持进入 S2 fresh retrain validation，不能支持产品默认化。

### 2.4 Rolling 稳定性

审查统计：

```text
6m rolling:
split_aligned_ltr_simple: 12/23 windows relative return > 0, mean +0.002123, median +0.014985
split_aligned_ltr_turnover_controlled: 14/23 windows relative return > 0, mean +0.024406, median +0.019087

12m rolling:
split_aligned_ltr_simple: 8/17 windows relative return > 0, mean +0.004587, median -0.005932
split_aligned_ltr_turnover_controlled: 14/17 windows relative return > 0, mean +0.106456, median +0.088271
```

解释：

- turnover-controlled 在 12m rolling 上较强；
- 6m rolling 只中等偏正；
- simple rolling 稳定性不足。

### 2.5 Regime 分段

`split_aligned_ltr_turnover_controlled` 相比 Top50 adaptive：

```text
caution: 0.088054 vs 0.044363
normal: 0.318305 vs 0.180720
risk_off: -0.211829 vs -0.280608
```

解释：

- regime 分段支持 turnover-controlled 继续验证；
- risk_off 仍为负收益，不能包装成防御性收益承诺。

---

## 3. Findings

### Medium 1：S1 支持的是“进入 S2 验证”，不是“LTR 已可上线”

S1B6R 的旧窗口公平验证显示 turnover-controlled LTR 有继续验证价值，但 2025H1 失败、6m rolling 不完全稳定，不能进入产品化或默认策略切换。

本结论只能写作：

```text
split_aligned_ltr_method_supported for S2 fresh retrain validation
```

不能写作：

```text
LTR 默认策略已成立
LTR 未来收益更好
LTR 当前上线效果更好
```

### Medium 2：simple LTR 不应单独作为强证据

`split_aligned_ltr_simple` full test 收益高于 Top50 adaptive，但 drawdown 更差；12m rolling 中位数为负。S2 必须继续同时评估 simple 与 turnover-controlled，不能只因为 full test 小幅收益更高就宣称 simple 有稳定增益。

### Low 1：rank_rotate_top50/top30 退化已解释

S1B6R 已说明：

```text
position_count_target=10 and both strategies sort by the same qlib score, so candidate pool top30/top50 degenerates to the same top10 holdings path
```

该解释可接受，但后续报告不得把二者当成两个独立 baseline 证据。

---

## 4. 安全边界审查

未发现以下越权：

- frontend/API 修改；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / quick-trade / orders；
- target position / target weight；
- 买卖建议、真实持有指令、收益承诺、胜率承诺、上涨概率承诺；
- 新数据源或联网。

只读安全边界通过。

---

## 5. S1 Gate

S1 结论：

```text
split_aligned_ltr_method_supported
```

解释：

该 gate 只表示旧窗口 split-aligned 公平验证中，LTR 方法，主要是冻结 turnover-controlled 使用层，有足够证据进入 S2 新鲜 qlib + LTR 重训验证。它不表示当前产品默认策略、上线效果或未来收益成立。

---

## 6. Phase S2A 工作文档：Fresh Retrain Experiment Contract Freeze

### 6.1 目标

Phase S2A 只冻结 S2 新鲜重训实验合同，不直接训练。

必须回答：

```text
S2 fresh qlib + fresh LTR 应使用什么 train / validation / test split、universe、feature/label、模型参数、资源策略、回放口径和验收 gate？
```

S2A 不训练 qlib，不训练 LTR，不跑回放，不输出收益结论。

### 6.2 S2 原则

S2 必须公平：

- qlib baseline 要按同样新鲜原则重训；
- LTR 要基于新鲜 qlib score/rank 或同一 fresh split 构建；
- 两者必须在同一个 untouched test 上比较；
- train 不得包含 test；
- validation 只能用于模型选择或已冻结规则确认；
- test 不得用于调参或阈值选择。

### 6.3 S2A 必须冻结 split 候选

执行者必须基于本地已有数据覆盖，提出一个明确 split，并说明为什么。

推荐候选：

```text
train: 2017-01-10..2024-12-31
validation: 2025-01-01..2025-06-30
test: 2025-07-01..latest available
```

如果 latest available 不足以形成可解释 test，执行者必须报告：

- latest available 的实际日期；
- test trading days；
- 可覆盖股票数；
- 是否需要调整为更保守 split；
- 调整会不会破坏 train/validation/test 纯度。

不得静默缩短或把 validation/test 混用。

### 6.4 S2A 必须冻结候选策略

S2 后续必须至少保留：

```text
fresh_qlib_top50_adaptive_baseline
fresh_rank_rotate_top50_or_equivalent_rank_baseline
fresh_confirmed_exit
fresh_ltr_simple
fresh_ltr_turnover_controlled
```

说明：

- 如果 `rank_rotate_top50` 与 `rank_rotate_top30` 在 `position_count_target=10` 下继续退化，S2A 可建议只保留一个 rank baseline，或保留两个但标注退化；不得把退化结果当成独立证据。
- `fresh_ltr_simple` 与 `fresh_ltr_turnover_controlled` 继续按同等级候选处理，不预设高低。

### 6.5 S2A 必须冻结模型与参数策略

必须冻结：

- qlib fresh retrain config 路径或待生成 config 路径；
- qlib train / validation / test split；
- qlib universe；
- qlib feature / label / handler；
- LTR sample build input；
- LTR feature list；
- LTR label policy；
- LTR model parameters；
- turnover-controlled usage-layer 是否沿用 S1 frozen config，或是否只允许 validation 内选择。

禁止：

- 在 S2A 里做参数搜索；
- 用 test 选择参数；
- 根据 S1B6R 的 2025H1 结果临时调规则；
- 引入新数据源或正交特征；
- 改 provider / accepted latest。

### 6.6 S2A 必须冻结资源策略

考虑此前本地 OOM，S2A 必须写清楚：

- 默认本地低线程训练策略；
- 本地线程数候选，例如 4 -> 2 -> 1；
- 何时允许迁移到远程服务器；
- 远程服务器只承担繁重训练，不改变数据口径和实验合同；
- 训练产物回传后必须先审查再进入下一步。

不得因为资源问题减少股票、改 universe 或改 split，除非先提交降级说明等待审查。

### 6.7 S2A 必须冻结指标和回放口径

S2 后续回放必须沿用 S1B6R 修复后的 accounting：

```text
signal_date/asof -> pending orders
execution_date -> next trading day close
effective_nav_date == execution_date
signal_date 不影响 same-day NAV
```

指标必须至少包含：

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

### 6.8 S2A 禁止事项

禁止：

- 训练 qlib；
- 训练 LTR；
- 跑组合回放；
- 输出收益结论；
- 调参；
- 改 feature / label / split / universe；
- 新增数据源；
- 联网；
- 改前端/API；
- provider refresh / publish；
- accepted latest switching；
- monitor / trading chain；
- broker / quick-trade / orders；
- 买卖、持有、仓位、收益承诺、胜率或上涨概率语义；
- 产品化或默认策略切换。

### 6.9 S2A 必须输出

执行报告：

```text
docs/tw_ltr_qlib_split_aligned_retrain/PHASES2A_FRESH_RETRAIN_CONTRACT_EXECUTION_REPORT_CN.md
```

建议产物：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2a_fresh_retrain_contract/phase_s2a_data_coverage_audit.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2a_fresh_retrain_contract/phase_s2a_split_contract.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2a_fresh_retrain_contract/phase_s2a_model_policy.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2a_fresh_retrain_contract/phase_s2a_strategy_policy.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2a_fresh_retrain_contract/phase_s2a_resource_policy.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2a_fresh_retrain_contract/phase_s2a_replay_accounting_policy.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2a_fresh_retrain_contract/phase_s2a_forbidden_action_audit.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2a_fresh_retrain_contract/phase_s2a_gate_summary.json
```

### 6.10 S2A Gate

允许 gate：

```text
s2a_fresh_retrain_contract_pass_request_s2b_fresh_qlib_training
s2a_blocked_by_data_coverage_gap
s2a_blocked_by_split_purity_risk
s2a_blocked_by_scope_violation
s2a_blocked_by_user_tradeoff_required
```

若 fresh test 区间太短、数据覆盖不足、或需要用户在“更长 train vs 更长 untouched test”之间做取舍，必须停止并回到用户确认。

---

## 7. 给执行者的一句话

请执行 Phase S2A：只冻结 fresh qlib + fresh LTR 重训验证的 split、universe、feature/label、模型参数、候选策略、资源策略和 S1B6R accounting 回放口径，不训练、不回放、不调参、不改前端/API、不触发 provider/accepted latest/monitor/交易链路；若 fresh test 覆盖不足或需要 split tradeoff，必须停止报告。
