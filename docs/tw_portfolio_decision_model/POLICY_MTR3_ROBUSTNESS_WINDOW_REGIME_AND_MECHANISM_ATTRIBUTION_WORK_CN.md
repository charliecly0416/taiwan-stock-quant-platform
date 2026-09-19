# POLICY_MTR3_ROBUSTNESS_WINDOW_REGIME_AND_MECHANISM_ATTRIBUTION_WORK_CN

生成日期：2026-06-28

## 1. 任务定位

本阶段是：

```text
POLICY_MTR_MECHANISM_TRANSFER_TO_BASELINE / MTR3
```

MTR3 不是新策略搜索，也不是生产化。MTR3 只做：

```text
robustness / window / regime / action-level mechanism attribution
```

MTR2_R 已通过：

```text
PASS_MTR2_R_WITH_BROAD_FULL_RANK_TRANSFER_CANDIDATE
```

通过候选固定为：

```text
M2_hold_rank_buffer_100
```

MTR3 目标是判断 MTR2_R 的强正结果是否可信、是否集中在少数日期/标的、是否只是减少交易带来的偶然收益、是否在不同 market regime 下仍合理。

## 2. 必读文档

执行者和审查者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_MTR_MECHANISM_TRANSFER_TO_BASELINE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR2_R_BROAD_FULL_RANK_VISIBILITY_REPAIR_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR2_R_BROAD_FULL_RANK_VISIBILITY_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR2_R_BROAD_FULL_RANK_VISIBILITY_REPAIR_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
```

可参考脚本：

```text
scripts/run_tw_policy_mtr2_r_broad_full_rank_visibility_repair.py
```

但 MTR3 不得修改 MTR2_R 结果或重新调参。

## 3. 固定输入

MTR3 必须消费 MTR2_R 已落地 artifacts：

```text
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025_broad_full_rank_mtr2_r/r1_broad_full_rank_visibility_repair_20260628/manifest.json
```

主要 replay：

```text
baseline_top50_exit_one_worst_sell
M2_hold_rank_buffer_100
```

允许对照：

```text
M0_baseline_parity
M2_hold_rank_buffer_75
```

禁止新增候选、禁止调参、禁止把 M2_75 反向提为主候选。

## 4. 输出路径

MTR3 输出目录：

```text
data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTR3_ROBUSTNESS_WINDOW_REGIME_AND_MECHANISM_ATTRIBUTION_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTR3_ROBUSTNESS_WINDOW_REGIME_AND_MECHANISM_ATTRIBUTION_REVIEW_CN.md
```

## 5. 必须产出

MTR3 至少输出以下文件：

```text
manifest.json
input_artifact_lineage_audit.csv
window_robustness_summary.csv
monthly_return_comparison.csv
regime_attribution_summary.csv
drawdown_segment_attribution.csv
action_level_pnl_attribution.csv
hold_buffer_trigger_pnl_attribution.csv
missed_replacement_opportunity_audit.csv
symbol_concentration_audit.csv
event_concentration_audit.csv
turnover_fee_tax_decomposition.csv
position_overlap_timeseries.csv
coverage_and_validator_audit.csv
forbidden_field_audit.csv
forbidden_action_audit.csv
```

如果某项无法生成，必须在 `manifest.json` 与执行报告中说明原因，不得静默跳过。

## 6. 分析要求

### 6.1 Window robustness

必须至少做以下窗口切片：

```text
full_window = 2026-01-02..2026-05-07
first_half = full window 前半段交易日
second_half = full window 后半段交易日
monthly windows = 按 YYYY-MM 聚合
rolling_20d_windows = 20 个交易日滚动或不重叠切片，若样本不足则说明
```

指标：

```text
net_total_return_after_fee_tax
gross_total_return
max_drawdown
average_turnover
total_fee_plus_tax
buy_count
sell_count
hold_buffer_trigger_count
non_top50_buy_intent_count
```

通过倾向：

```text
M2_100 full window positive；
至少多数子窗口不显著劣于 baseline；
成本/换手下降不是只发生在单一窗口；
非 top50 buy 始终为 0。
```

### 6.2 Regime attribution

不得引入未来标签定义 regime。

允许使用：

```text
baseline daily_nav daily_return
M2 daily_nav daily_return
TWII 历史价格/回报，如果已有可用 PIT 文件
```

若无法取得 TWII PIT 数据，使用 replay day 的 baseline daily_return 做 diagnostic regime：

```text
risk_on: baseline daily_return > +0.5%
neutral: -0.5% <= baseline daily_return <= +0.5%
risk_off: baseline daily_return < -0.5%
```

这只能作为归因诊断，不得作为策略输入。

必须输出：

```text
regime
day_count
baseline_return
m2_return
delta
baseline_drawdown_contribution
m2_drawdown_contribution
hold_buffer_trigger_count
turnover_delta
fee_tax_delta
```

### 6.3 Action-level PnL attribution

必须用 replay 输出侧的 `actions.csv`、`daily_nav.csv`、`position_snapshots.csv` 做归因。

目标：

```text
解释 M2_100 的净收益提升来自哪些 skipped baseline sell、延后换仓、费用节省或持仓保留。
```

必须输出：

```text
date
instrument
baseline_action
m2_action
reason
baseline_next_position
m2_next_position
approx_pnl_delta
fee_tax_delta
holding_days_delta
```

注意：

```text
MTR3 可以在分析中使用 realized replay PnL 做 attribution；
但不得把 realized PnL 反馈给策略决策，也不得改策略规则。
```

### 6.4 Missed replacement audit

必须回答：

```text
M2_100 少交易是否错过了 baseline 中高收益替换？
```

输出：

```text
baseline_buy_instrument
m2_skipped_or_delayed
subsequent_window_return_approx
missed_gain_or_avoided_loss
classification
```

classification 建议：

```text
avoided_bad_replacement
missed_good_replacement
neutral_or_unclear
fee_saving_only
```

该归因可使用 replay 后验，但只能作为 analysis artifact。

### 6.5 Concentration audit

必须检查：

```text
收益提升是否集中在少数标的；
收益提升是否集中在少数日期；
hold buffer 触发是否集中在少数标的；
最大单标的贡献占总 delta 的比例；
最大单日贡献占总 delta 的比例。
```

建议阈值：

```text
top1_symbol_delta_share > 40% -> concentration_warning
top3_symbol_delta_share > 70% -> concentration_warning
top1_event_delta_share > 30% -> event_concentration_warning
```

warning 不一定失败，但必须审查。

## 7. 通过 / 风险 / 失败判定

MTR3 可给出：

```text
PASS_MTR3_ROBUSTNESS_SUPPORTS_MTR4_READINESS_DESIGN
PASS_MTR3_WITH_CONCENTRATION_OR_WINDOW_RISK
FAIL_NEEDS_REPAIR_OR_MORE_DATA
STOP_ARTIFACT_INCOMPLETE
STOP_SCOPE_VIOLATION
```

PASS 倾向要求：

```text
M2_100 full-window net delta positive；
turnover and fee/tax reduction remain material；
hold_buffer_trigger_count > 0；
non_top50_buy_intent_count = 0；
baseline parity and artifact lineage intact；
没有单一事件完全解释收益；
至少没有明显 regime 单点崩坏。
```

若收益提升高度集中，最多给：

```text
PASS_MTR3_WITH_CONCENTRATION_OR_WINDOW_RISK
```

若 M2 只在一个月或一个标的有效，且其他窗口明显差，不能进入 MTR4 readiness。

## 8. Forbidden actions

全阶段禁止：

```text
训练模型
调参
后验扩候选
改 M2 hold_rank_buffer 参数
让非 top50 broad rows 参与买入候选
修改 MTR2_R replay result 后重写更好结果
修改 production/default/frontend/API/Agent/daily/provider/latest
provider publish
accepted latest switch
monitor scan/config save/alerts write
broker / quick-trade / real order
target_weight / target_position / quantity instruction
把 realized PnL / replay return 反馈为策略输入
```

允许：

```text
读取 replay output 做 attribution；
读取 OrderIntent / ReplayResult / broad signal manifest 做验证；
新增只读 analysis artifact；
新增 MTR3 分析脚本。
```

## 9. Stop conditions

必须停止：

```text
MTR2_R artifacts 缺失；
MTR2_R broad signal validator 或 replay validator 有 fail；
baseline parity 证据缺失；
无法证明 M2_100 是固定候选；
需要重新生成不同策略结果才能做归因；
需要 production/default/frontend/API/Agent/daily/provider/latest 改动；
发现非 top50 buy intent > 0；
发现 target_weight/target_position 或 broker/order 字段进入 OrderIntent。
```

## 10. 执行报告结构

执行报告必须包含：

```text
1. Verdict
2. Scope
3. Documents / Contracts Read
4. Input Artifact Lineage
5. Window Robustness
6. Regime Attribution
7. Action-level PnL Attribution
8. Concentration Audit
9. Turnover / Fee / Tax Decomposition
10. Forbidden Actions Audit
11. Files Changed
12. Recommendation
```

## 11. 审查重点

审查者必须确认：

```text
1. MTR3 没有改策略、调参或新增候选；
2. 分析只消费 MTR2_R artifacts；
3. full-window 强结果是否被多窗口/归因支持；
4. 是否存在严重窗口、标的、事件集中；
5. realized PnL 只用于 attribution，没有反馈进策略；
6. non-top50 buy intent 仍为 0；
7. forbidden actions clean；
8. 是否可以进入 MTR4 readiness design，或需要更多数据/修复。
```

## 12. 下一步

若 MTR3 通过：

```text
进入 MTR4 Adapter / Production Readiness Design，仍不得直接切生产。
```

若 MTR3 风险通过：

```text
先做更长窗口或 concentration repair，不进入生产 readiness。
```

若 MTR3 失败：

```text
关闭 qlib+LTR M2 transfer，保留 research-only 记录。
```
