# Phase 1B Prediction Repair 可行性报告

- 生成时间：`2026-06-11T05:16:36+00:00`
- 本步骤未联网、未使用 token、未重拉数据、未训练模型、未写 Qlib bin/provider、未 provider refresh/publish、未 accepted latest switching、未进入 Phase2。
- 结论：`prediction_repair_blocked_requires_reviewer_decision=true`
- 原因：本地 frozen model 可以在 `--research-only-skip-formal-validation` 下生成 2024 单日 smoke prediction；但不绕过 formal validation 时，2023 与 2024 单日 smoke 均因 `option_c_formal_source_missing_asof` 失败。工作文档要求如果现有预测脚本无法证明 point-in-time inference，应停止补预测，因此没有执行 2023-2024 全量 repair。

## 1. Inventory

| item | script | config | model/recorder | input data path | output path | needs_network | needs_training | writes_provider | notes |
|---|---|---|---|---|---|---|---|---|---|
| historical_backfill_script | scripts/backfill_tw_option_c_historical_signals.py | configs/tw_yahoo_primary_alpha158.yaml | mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a | qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin | qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill | False | False | False | Same local script family used by existing 2022/2025 historical backfills. |
| existing_2023_pred_fast_artifact | unknown/generated before this step | not recorded | not recorded | not recorded | qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill/option_c_historical_backfill_20230101_20231231_pred_fast | False | False | False | 239 prediction.csv files exist, but directory dates use `2023''MM''DD` and prediction columns are `asof,instrument,score,rank`, so Phase1B parser does not recognize them as standard qlib predictions. |
| 2024_full_artifact | not present |  |  |  | not found | False | False | False | No local 2024 prediction.csv artifact found before smoke checks. |

## 2. Feasibility Gate

| check | status | generated | failed | formal_validation_bypassed | notes |
|---|---|---:|---:|---|---|
| 2024 dry-run | pass | 0 | 0 | False | dry-run 仅列出 242 个本地交易日。 |
| 2024 research bypass smoke | accepted | 1 | 0 | True | 使用 frozen recorder/model 成功生成 `2024-01-02` 单日 prediction；metadata 显示无训练、无 refresh/publish/provider mutation。 |
| 2023 formal smoke | blocked_formal_validation_failed | 0 | 1 | False | `option_c_formal_source_missing_asof`。 |
| 2024 formal smoke | blocked_formal_validation_failed | 0 | 1 | False | `option_c_formal_source_missing_asof`。 |

判断：

- 可复用本地 frozen recorder/model 的证据存在：`2024-01-02` research-only bypass smoke 生成成功。
- 但 PIT/formal validation 无法在 2023/2024 历史 asof 上通过。
- 因此不能在本步骤直接全量生成 2023-2024 predictions，也不能把现有 2023 `pred_fast` artifact 直接标准化混入 Phase1B repaired baseline。

## 3. 已停止事项

未执行：

- 未全量生成 2023-2024 prediction。
- 未标准化 2023 `pred_fast` artifact。
- 未重跑 Phase1B Full。
- 未提出新的 Phase2 结论。

## 4. 后续需要审查者/用户决定

若审查者认为可接受 historical research-only bypass 作为 Phase1B repaired prediction 来源，则可授权下一步单独执行：

```bash
cd /home/chuliyang/taiwan-stock-quant-platform
python scripts/backfill_tw_option_c_historical_signals.py --start-date 2023-01-01 --end-date 2023-12-31 --batch-id option_c_historical_backfill_20230101_20231231_research_only --research-only-skip-formal-validation
python scripts/backfill_tw_option_c_historical_signals.py --start-date 2024-01-01 --end-date 2024-12-31 --batch-id option_c_historical_backfill_20240101_20241231_research_only --research-only-skip-formal-validation
```

这会是长任务；根据用户要求，执行前应再次确认或由用户本地运行。若审查者不接受 bypass，则应停止 repaired Phase1B，不进入 Phase2。

## 5. 产物

- Inventory：`data_tw/experiments/decision_orthogonal/phase1b_prediction_repair_inventory.csv`
- Smoke 结果：`data_tw/experiments/decision_orthogonal/phase1b_prediction_repair_feasibility_smoke.csv`
- Summary：`data_tw/experiments/decision_orthogonal/phase1b_prediction_repair_feasibility_summary.json`

