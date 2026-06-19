# Phase Q0 执行报告：Control 与 Orthogonal Feature 合同冻结

生成时间：`2026-06-15T15:58:00+00:00`

## 1. 结论

- gate：`phase_q0_control_and_orthogonal_feature_contract_frozen`
- fresh qlib baseline 训练/回放合同已冻结。
- O2 PIT-safe 法人筹码与融资融券特征可作为唯一新增变量。
- 未训练、未调参、未改 split / label / universe / model。
- 未引入 LTR。
- 未触发前端 / API / provider / accepted latest / monitor / broker / orders / quick-trade / 交易链路。

## 2. 冻结的 control 合同

### 2.1 训练窗口

```text
train:      2017-01-10..2024-12-31
validation: 2025-01-01..2025-06-30
test:       2025-07-01..2026-05-07
```

### 2.2 handler / fit

```text
handler_start: 2015-05-04
handler_end:   2026-05-07
fit_start:     2015-05-04
fit_end:       2024-12-31
```

### 2.3 provider

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin
```

### 2.4 universe / post-score filter

```text
handler instruments = all
post-score filter = tw_liquid_dyn as-of active instrument range
same-day price
>=60 history
trailing 60-day value top150
```

### 2.5 模型家族

```text
qlib.contrib.model.gbdt.LGBModel
original S2B fresh qlib params
num_threads ladder: 4 -> 2 -> 1
```

### 2.6 replay 口径

```text
strategy: fresh_qlib_top50_adaptive_baseline
window: validation + untouched test
test focus: 2025-07-01..2026-05-07
execution: next-day execution
initial_equity: 1000000
fee_rate: 0.001425
tax_rate: 0.003
target_position_count: 10
candidate_k: 50
```

## 3. Control 证据

- S2B training manifest：`data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_training_manifest.json`
- S2B generated config：`data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_generated_qlib_config.yaml`
- S2B leakage audit：`data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_leakage_audit.json`
- S2D replay gate：`data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_gate_summary.json`

关键冻结字段已在上述产物中复核：

- train/validation/test 切分一致；
- provider URI 一致；
- handler `instruments = all`；
- `LGBModel` 与原 S2B fresh qlib 参数一致；
- replay 仍是 next-day execution；
- 未触发 provider refresh/publish、accepted latest、frontend/api、monitor、trading chain。

## 4. O2 正交特征白名单

允许作为唯一新增变量的特征家族：

- `institutional_flow`
- `margin_short`

允许输入来源：

- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/normalized_feature_daily.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/feature_dictionary.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/pit_leakage_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/pit_lineage_audit.csv`

白名单列按 O2 字典冻结为：

- `foreign_net_buy`
- `investment_trust_net_buy`
- `dealer_net_buy`
- `institutional_total_net_buy`
- `*_roll1/3/5/10`
- `institutional_total_net_buy_streak`
- `institutional_missing_flag`
- `institutional_delay_flag`
- `delay_days`
- `delay_reason`
- `margin_balance`
- `margin_balance_change`
- `short_balance`
- `short_balance_change`
- `*_roll1/3/5/10`
- `margin_direction_proxy`
- `short_direction_proxy`
- `margin_short_divergence_proxy`
- `margin_short_missing_flag`
- `margin_short_delay_flag`

## 5. PIT / 缺失合同

沿用已冻结合同：

```text
PIT-safe delayed availability
available_at >= next_trading_day(trade_date)
```

确认：

- 每行保留 `delay_days` / `delay_reason` / lineage；
- 缺失值 neutral fill；
- 不得人工提前 `available_at`；
- 不得因正交特征缺失删样本或删股票。

## 6. 禁止变化清单

- 不训练 LTR。
- 不改 split / label / universe / model。
- 不改 replay 规则。
- 不新增月营收 YoY、估值或其他 FinMind dataset。
- 不做 filter / market gate / turnover rule 变更。
- 不改默认前端策略。
- 不接 provider refresh / publish / accepted latest。
- 不接 monitor / broker / orders / quick-trade。

## 7. 允许进入下一阶段的条件

仅允许进入 Q1 的前提是：

- control 合同保持冻结；
- O2 正交特征仍是唯一新增变量；
- 不需要任何额外数据源或新特征族；
- 不改变 qlib 原有 Alpha158 特征、label、split、universe。

## 8. 输出报告

本报告对应：

- `phase_q0_control_and_orthogonal_feature_contract_frozen`

