# POLICY_JMD2_SUPERVISED_JOINT_UTILITY_BASELINE_EXECUTION_REPORT_CN

## 1. 范围

本次执行 JMD2 lightweight supervised joint utility baseline。产物仅为 readonly research artifact；未接入 production/default/frontend/API/Agent/daily/provider/latest，未生成 OrderIntent，未输出交易、目标仓位或券商指令。

## 2. 数据覆盖 Gate

- verdict: `PASS_JMD2_INFRA_ONLY_NO_GO_TO_TRAINING_EXPANSION`
- coverage_status: `pass`
- reason: 2015-2021 price/TWII coverage sufficient for JMD2 top150 diagnostic universe
- TWII: 2015-01-05..2021-12-30, rows=1712, valid_rows=1712
- stock_files=1986, stocks_with_window_rows=1797, fullish_stock_count=1537
- daily coverage: 2015-01-02..2021-12-30, days_ge150=1707/1773, median_count=1678

## 3. Validation Accounting

2021 validation 使用同 lineage raw price/TWII 特征；收益口径为 diagnostic close-to-next-close label accounting，扣除 fee/tax，非产品收益承诺。

| policy_name | net_total_return_after_fee_tax | gross_total_return | max_drawdown | average_turnover | cash_no_selection_day_count |
| --- | --- | --- | --- | --- | --- |
| baseline_all_cash_diagnostic | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 242 |
| baseline_equal_weight_liquidity_top10 | 0.418059 | 0.481223 | -0.309439 | 0.063636 | 0 |
| baseline_momentum_top10_ret20 | 0.559470 | 1.076559 | -0.473929 | 0.407438 | 0 |
| jmd2_supervised_utility_ridge_seed11 | -0.349629 | 0.588862 | -0.505849 | 1.265702 | 0 |

## 4. 输出

- artifact_root: `data_tw/experiments/policy_jmd_joint_model_decision_research/jmd2_supervised_joint_utility_baseline`
- `manifest.json` / `dataset_manifest.json` / audits / metrics / validator_report.json
- `joint_policy_artifact/manifest.json` / `model_card.md` / `training_config.json`
- `joint_decision_diagnostic_artifact.csv`

## 5. 边界声明

- 未读取 2023-2025 LTR/private artifacts。
- 未使用 standard qlib/LTR score 作为 JMD2 主输入。
- supervised label 只用于训练/validation accounting，未进入 feature/state。
- 未修改 registry、production default、frontend、API、Agent、daily update、provider/latest。

## 6. Verdict / Recommendation

- verdict: `PASS_JMD2_INFRA_ONLY_NO_GO_TO_TRAINING_EXPANSION`
- recommendation: `DO_NOT_EXPAND_TRAINING_UNTIL_FEATURE_MECHANISM_OR_COST_EDGE_IS_REPAIRED`
