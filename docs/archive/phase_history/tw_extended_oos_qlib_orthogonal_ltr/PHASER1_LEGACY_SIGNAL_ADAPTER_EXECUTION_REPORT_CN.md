# Phase R1 Legacy Signal Adapter 执行报告

生成日期：2026-06-16

## 1. 执行范围

本次仅执行 R1：把 legacy replay-ready / score 产物转换为标准 `ModelSignalArtifact`。

未执行 R2；未修改 formal replay matrix；未训练、未调参、未重算模型分数、未产生策略收益结论。

## 2. Run

- run_id: `r1_legacy_signal_adapter_20260616`
- created_at: `2026-06-16T09:05:02+00:00`
- adapter: `scripts/build_tw_modular_legacy_signal_adapter.py`

## 3. 输出汇总

| model_name | family | rows | duplicate_key | quality | window | manifest |
| --- | --- | ---: | ---: | --- | --- | --- |
| fresh_qlib_adaptive | qlib | 30630 | 0 | pass | 2025-07-01..2026-05-07 | `data_tw/artifacts/signals/fresh_qlib_adaptive/r1_legacy_signal_adapter_20260616/manifest.json` |
| fresh_qlib_2025_ltr | ltr | 3950 | 0 | pass | 2026-01-02..2026-05-07 | `data_tw/artifacts/signals/fresh_qlib_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json` |
| frozen_qlib_2025_ltr | ltr | 3950 | 0 | pass | 2026-01-02..2026-05-07 | `data_tw/artifacts/signals/frozen_qlib_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json` |
| e4_frozen_qlib_2023_2025_ltr | ltr | 3950 | 0 | pass | 2026-01-02..2026-05-07 | `data_tw/artifacts/signals/e4_frozen_qlib_2023_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json` |
| frozen_qlib_2018_2022 | qlib | 119862 | 0 | pass | 2023-01-03..2026-05-07 | `data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json` |

## 4. 验收结果

- required fields：五个 `signals.csv` 均按 `MODEL_SIGNAL_CONTRACT_CN.md` 输出标准字段；
- duplicate key：五个 artifact 的 `date + instrument` duplicate key 均为 0；
- row count：五个 artifact 均与对应 legacy 输入或过滤后的 legacy 输入一致；
- score/rank：`candidate_rank`、`buy_score`、`raw_score` 按 legacy mapping 零改动搬运；
- full rank：`full_qlib_rank` 从声明的完整 qlib rank source join，非空覆盖通过；
- score_rank：由 `buy_score` 日内降序、`instrument` 升序稳定生成；
- LTR boundary：LTR 的 `candidate_rank` 仍来自底座 qlib rank；
- forbidden fields：标准 `signals.csv` 不包含 future label、future return、PnL、持仓、订单或成交字段；
- no strategy conclusion：本阶段不输出 replay summary、收益、回撤或默认策略结论。

## 5. 禁止事项记录

- 未训练 qlib 或 LTR；
- 未调参；
- 未重算模型分数；
- 未根据收益筛选模型；
- 未产生新的策略收益结论；
- 未改 replay rule；
- 未改 formal replay matrix；
- 未改默认策略；
- 未修改前端；
- 未修改日更脚本；
- 未触发 provider publish；
- 未切换 accepted latest；
- 未触发 monitor scan/config save；
- 未触发 broker、quick-trade 或 order。
