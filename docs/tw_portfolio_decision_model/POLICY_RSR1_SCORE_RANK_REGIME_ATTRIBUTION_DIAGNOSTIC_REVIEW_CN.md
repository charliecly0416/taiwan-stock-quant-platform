---
created_at: 2026-06-27
status: reviewed_rsr1_score_rank_regime_attribution_diagnostic
phase: POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC
reviewer: RSR1
verdict: PASS
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic
next_work_doc: docs/tw_portfolio_decision_model/POLICY_RSR2_PREDECLARED_RULE_CONTRACT_WORK_CN.md
production_allowed: false
readonly_only: true
diagnostic_only: true
---

# Review Opinion And Next Work Document

## 1. Verdict

`PASS`.

RSR1 交付物满足主线和 RSR1 work doc 的 diagnostic-only 边界：已完成 RSR0 条件项 `portfolio_state_view.csv`，已物化 qlib-only PIT-safe attribution dataset、feature/label schema、lineage、consumer forbidden field audit、PIT/leakage audit、diagnostic summary 和 forbidden action audit。审查未发现训练、replay rerun、threshold tuning、OrderIntent/ReplayResult 生成、production/default/frontend/daily/latest/publish 修改或外部拉取。

本次 PASS 只允许进入 RSR2 `Predeclared Rule Contract` 设计阶段，不授权策略实现、OrderIntent、readonly replay、收益结论或 production 候选。

## 2. Findings

### Critical

无。

### High

无。

### Medium

无。

### Low

1. `baseline_action_context` 仍来自既有 `readonly_internal_replay_ledger_not_order_intent`，不是正式 `OrderIntentArtifact` 或 `ReplayResultArtifact`。RSR1 仅把它作为 attribution grouping context 使用，并在 lineage/audit 中声明边界，因此不阻断 PASS；RSR2 不得把该 internal ledger 当作 replay 收益证据或正式合同输入。
2. `consumer_forbidden_field_audit.csv` 对 `forward_return_*` 的通配检测不会匹配合法的 `diagnostic_label_forward_return_*` 列；但 `label_namespace_audit.csv` 和 `label_schema.json` 已单独覆盖这些列，且 `feature_schema.json` 未包含 label 列。该实现可接受，RSR2 仍必须显式禁止任何 StrategyRule/OrderIntent/ReplayExecution/ranking/threshold consumer 读取 `diagnostic_label_*`。

## 3. Mainline Compliance

- RSR1 范围合规：交付物只做 score/rank/regime/holding-aware attribution diagnostic dataset 与摘要；未产出策略规则、OrderIntent、ReplayResult、收益 replay 或阈值调优结论。
- RSR0 条件项合规：`portfolio_state_view.csv` 已物化，字段仅为 `asof_date`、`instrument`、`cost_basis`、`current_holding_flag`、`source_position_snapshot_path`、`source_snapshot_hash`。
- `portfolio_state_view.csv` 禁止字段合规：未出现 `quantity`、PnL、cash/NAV/equity、execution、broker/order、target position/weight、quantity instruction 字段。
- `rsr1_diagnostic_dataset.csv` namespace 合规：forward/excess returns 仅以 `diagnostic_label_forward_return_*` 和 `diagnostic_label_forward_excess_return_*` 存在；feature columns 未包含 future/label/realized_pnl/execution/next_open/next_close/cash/nav/replay_return/broker/order/target/weight/quantity instruction。
- PIT 语义覆盖合规：`feature_construction_audit.csv` 与 `pit_leakage_audit.csv` 覆盖 same-day score percentile/gap、history-only rank delta、TWII backward-asof regime、available_at 检查和 label-after-feature construction。
- 摘要边界合规：`diagnostic_summary.md` 明确 `diagnostic_only=true`、`not_strategy_evidence=true`，且说明未选择 best threshold/best rule/best bucket，未形成收益策略结论。
- qlib-only lineage 合规：manifest/input_lineage 指向 frozen qlib signal、qlib-only TEST manifest、full qlib rank、本地 baseline internal ledger、本地 price/TWII；未见 qlib+LTR adaptation 或外部新数据拉取。

## 4. Evidence Checked

已读取并核对：

- `docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR0_CONTRACT_AND_DATA_READINESS_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_EXECUTION_REPORT_CN.md`
- `scripts/build_tw_policy_rsr1_attribution_diagnostic.py`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/manifest.json`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/rsr1_diagnostic_dataset.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/portfolio_state_view.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/feature_schema.json`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/label_schema.json`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/input_lineage_links.json`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/feature_construction_audit.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/label_namespace_audit.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/consumer_forbidden_field_audit.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/pit_leakage_audit.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/diagnostic_summary.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/diagnostic_summary.md`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr1_score_rank_regime_attribution_diagnostic/forbidden_action_audit.csv`

关键抽查结果：

- `manifest.json` 声明 `readonly_only=true`、`diagnostic_only=true`、`not_strategy_evidence=true`、`replay_rerun_performed=false`、`model_training_performed=false`、`threshold_tuning_performed=false`、`order_intent_generated=false`、`provider_publish_performed=false`、`accepted_latest_switch_performed=false`、`production_or_default_changed=false`、`external_data_pull_performed=false`。
- `rsr1_diagnostic_dataset.csv` 为 89,112 rows、59 columns，窗口 `2023-01-03` 到 `2025-06-30`，150 instruments。
- `portfolio_state_view.csv` 为 5,427 rows、6 columns，未包含 quantity 或任何 execution/accounting/PnL/cash/NAV/target/weight/instruction 字段。
- `consumer_forbidden_field_audit.csv` 共 27 行，status 全为 `PASS`。
- `pit_leakage_audit.csv` 共 7 行，status 全为 `PASS`，available_at violation count 为 0。
- `label_namespace_audit.csv` 共 6 行，status 全为 `PASS`。
- `feature_construction_audit.csv` 共 7 行，status 全为 `PASS`。
- `forbidden_action_audit.csv` 共 9 行，status 全为 `PASS_NOT_PERFORMED`。
- `python -m py_compile scripts/build_tw_policy_rsr1_attribution_diagnostic.py` 通过。

## 5. Missing Evidence Or Open Questions

无阻断缺失证据。

保留开放边界：

1. RSR1 不产生正式 `StrategyRule`、`OrderIntentArtifact` 或 `ReplayResultArtifact`，因此不能作为收益策略结论或 production 候选证据。
2. RSR2 若引用 RSR1 机制，只能用于冻结不超过 5 个预声明规则合同；不得从 `diagnostic_summary.csv` 后验选择“最佳收益 bucket/threshold/rule”。
3. RSR2 若需要 `PortfolioState` 合同字段 `quantity`，只能在设计文档里声明为未来 OrderIntent/Replay 阶段的 standard state input，不得从 RSR1 diagnostic view 推导交易数量、目标仓位或权重。

## 6. Forbidden Actions Audit

审查未发现以下 forbidden actions：

- training / retraining；
- qlib refresh、LTR retrain 或 qlib+LTR adaptation；
- replay rerun、ReplayResult generation、PnL rule search；
- threshold tuning、best bucket/rule selection；
- StrategyRule implementation；
- OrderIntentArtifact generation；
- order、target_position、target_weight、quantity instruction 输出；
- broker、quick-trade、real order；
- provider publish、accepted latest switch；
- production/default/frontend/daily/latest 修改；
- external data pull。

脚本级抽查显示 `scripts/build_tw_policy_rsr1_attribution_diagnostic.py` 未调用训练、replay runner、provider publish、accepted latest、frontend/default/daily update 或 OrderIntent/ReplayResult 输出路径。

## 7. Next Work Document

已写下一步工作文档：

```text
docs/tw_portfolio_decision_model/POLICY_RSR2_PREDECLARED_RULE_CONTRACT_WORK_CN.md
```

RSR2 只允许做 predeclared rule contract design：冻结不超过 5 个规则，写明 required fields、score bucket/rank delta/market regime definitions、max_buy_count/max_sell_count、sell boundary、buy ordering、no-trade zone、diagnostic_only/readonly flags 和 pass/fail gates。

RSR2 不允许跑 replay、不允许生成 OrderIntent、不允许调参到收益、不允许改 production/default/latest/publish。

## 8. Command For Executor Or Coordinator

```text
你是 RSR2 执行者。读取 docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md、docs/tw_portfolio_decision_model/POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_REVIEW_CN.md、docs/tw_portfolio_decision_model/POLICY_RSR2_PREDECLARED_RULE_CONTRACT_WORK_CN.md、RSR1 artifact root 下 manifest/schema/audit/summary 文件，以及 StrategyRule/OrderIntent/ReplayResult 合同。只执行 predeclared rule contract design：冻结不超过 5 个规则合同或合同表，声明 required fields、score bucket/rank delta/market regime definitions、max_buy_count/max_sell_count、sell boundary、buy ordering、no-trade zone、readonly/diagnostic flags 和 pass/fail gates。不要实现策略代码，不要生成 OrderIntent，不要跑 replay，不要做收益阈值调参，不要 provider publish，不要 accepted latest switch，不要改 production/default/frontend/daily/latest。完成后写 POLICY_RSR2_PREDECLARED_RULE_CONTRACT_EXECUTION_REPORT_CN.md。
```
