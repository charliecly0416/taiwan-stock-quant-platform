# Phase O5 执行报告：Controlled Replay Evaluation

生成时间：2026-06-15T11:52:01+00:00

## 1. Gate

推荐 gate：`phase_o5_controlled_replay_evaluation_completed`。

## 2. 固定合同

- 窗口：`2025-07-01..2026-05-07`。
- 回放：next-day execution、fee_rate `0.001425`、tax_rate `0.003`、target positions `10`。
- Control：`score_head10_all_l31_alpha0.7_top50_only`，原 Phase1C anchor score column 未改。
- Treatment：`phaseo4_treatment_ltr_score`，回放候选按 `qlib_rank <= 50` 落实 `preserve_scope=top50_only`。
- 本轮未训练 qlib/LTR，未修改 score artifact、窗口、label、特征、API、provider、accepted latest、monitor 或交易链路。

## 3. Full Universe

- Phase1C anchor：return `0.721631`，max DD `-0.05083`，actions `405`。
- O4 treatment：return `0.800329`，max DD `-0.074962`，actions `403`，relative return `0.078698`。

## 4. O5 Pairwise Common Universe

- key count：`10110`。
- Phase1C anchor：return `0.721631`，max DD `-0.05083`，actions `405`。
- O4 treatment：return `0.800329`，max DD `-0.074962`，actions `403`，relative return `0.078698`。

说明：O0/A1 冻结的 S2F common key count 为 `22474`，其 Phase1C common return 为 `0.641235`；O5 同时输出该来源说明，但主 common comparison 使用 Phase1C anchor 与 O4 treatment 的 pairwise replay key。

## 5. Accounting

- next-day accounting pass：`True`。
- full active actions：control `405`，treatment `403`。

## 6. Ranking 与 PnL 审计

- treatment rank IC：`0.068649444085`。
- treatment NDCG@10/30/50：`0.450302908476 / 0.590148409191 / 0.760603038855`。
- treatment top symbol abs share：`0.102661`。
- treatment top day abs share：`0.069842`。

## 7. Low Coverage

- low coverage audit rows：`11`。
- 低覆盖股票持仓/交易/PnL 与 missing/delay flag 暴露已写入 `phaseo5_low_coverage_impact_audit.csv`。

## 8. 输出产物

- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5_replay_manifest.json`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5_full_universe_metrics.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5_common_universe_metrics.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5_rank_metrics.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5_action_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5_next_day_accounting_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5_daily_nav.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5_monthly_performance.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5_yearly_performance.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5_pnl_contribution_by_symbol.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5_pnl_contribution_by_day.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5_pnl_concentration_summary.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5_low_coverage_impact_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5_common_universe_key_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5_o4_feature_importance_top30.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o5_controlled_replay_evaluation/phaseo5_summary.json`
- `docs/tw_ltr_orthogonal_features_controlled/PHASEO5_CONTROLLED_REPLAY_EVALUATION_EXECUTION_REPORT_CN.md`
