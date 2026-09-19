---
created_at: 2026-06-27
status: reviewed_rsr0_contract_and_data_readiness
phase: POLICY_RSR0_CONTRACT_AND_DATA_READINESS
reviewer: RSR0
verdict: PASS_WITH_CONDITIONS
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RSR0_CONTRACT_AND_DATA_READINESS_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RSR0_CONTRACT_AND_DATA_READINESS_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness
next_work_doc: docs/tw_portfolio_decision_model/POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_WORK_CN.md
production_allowed: false
readonly_only: true
---

# Review Opinion And Next Work Document

## 1. Verdict

`PASS_WITH_CONDITIONS`.

RSR0 交付物满足 contract/data readiness 阶段的核心通过条件：qlib-only signal、baseline/action ledger、price、TWII/market feature、portfolio state 来源均可追溯；score/rank/regime/holding-aware 诊断特征可构造；PIT/leakage audit 无 critical；forbidden action audit clean。

条件是：RSR1 开始前必须先物化 RSR1 专用诊断数据集边界，尤其是 `PortfolioState` 视图、diagnostic label 命名空间、feature/label/ledger 字段隔离和 consumer audit。该条件不构成 RSR0 阶段 fail，因为 RSR0 的目标是 readiness，不是生成 RSR1 数据集或正式 ReplayResultArtifact。

## 2. Findings

### Critical

无。

### High

无。

### Medium

1. `baseline_action_ledger_2023_2025` 是 `readonly_internal_replay_ledger_not_order_intent`，不是标准 `ReplayResultArtifact`。这不阻断 RSR1 诊断，因为 RSR0 work doc 接受 baseline/replay 或 action ledger 可追溯；但 RSR1 不得把该 internal ledger 伪装成 OrderIntent 或正式 replay 结果。若后续阶段要求标准 ReplayResultArtifact，只能只读包装现有 ledger，不得 rerun replay 或改结果。
2. `baseline_portfolio_state_2023_2025` 的源文件包含 `quantity`、`mark_price`、`market_value`、`unrealized_pnl`、`rank_change_3d`、`rank_change_5d`、`score_delta_5d` 等 accounting/diagnostic 字段。RSR1 必须物化专用 `PortfolioState` 视图，只保留允许的状态字段，并明确禁止 execution/accounting/PnL 字段进入 StrategyRule feature matrix。

### Low

1. `market_breadth` 仅标记为 optional constructible。RSR0 不要求 market breadth，因此不阻断；RSR1 若使用 market breadth，必须另做 PIT coverage audit。
2. `score_bucket` 需要在 RSR1 冻结 diagnostic-only bucket 定义。该冻结不得基于 replay PnL、future return 或收益搜索。

## 3. Mainline Compliance

- RSR0 范围合规：交付物只做 readiness inventory、feature availability、PIT/leakage 和 forbidden action audit；未实现策略规则、未生成 OrderIntent、未跑收益规则 replay、未训练、未调阈值。
- qlib-only 原则合规：输入 lineage 指向 `frozen_qlib_2018_2022` 标准信号、full qlib rank 和 qlib-only TEST fold；未使用 qlib+LTR adaptation 作为本阶段结论。
- 合同边界合规：审计明确 StrategyRule 输入不得包含 future return/label、realized PnL、execution price/date、next_open/next_close、broker/order 字段。
- 阶段输出合规：`manifest.json`、`input_lineage_inventory.csv`、`feature_readiness_audit.csv`、`pit_leakage_audit.csv`、`forbidden_action_audit.csv`、`rsr1_dataset_feasibility.md` 均存在并与执行报告一致。
- minor repair 分类合理：问题集中在 RSR1 数据集物化与合同包装，不是 RSR0 readiness 缺口，因此结论为 `PASS_WITH_CONDITIONS`，不是 `FAIL_NEEDS_REPAIR` 或 `STOP`。

## 4. Evidence Checked

已读取并核对：

- `docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR0_CONTRACT_AND_DATA_READINESS_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR0_CONTRACT_AND_DATA_READINESS_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/manifest.json`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/input_lineage_inventory.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/feature_readiness_audit.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/pit_leakage_audit.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/forbidden_action_audit.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/rsr1_dataset_feasibility.md`
- `scripts/audit_tw_policy_rsr0_contract_data_readiness.py`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`

关键证据：

- `manifest.json` 声明 `scope=contract_and_data_readiness_only`、`readonly_only=true`、`replay_rerun_performed=false`、`model_training_performed=false`、`threshold_tuning_performed=false`、`provider_publish_performed=false`、`accepted_latest_switch_performed=false`、`production_or_default_changed=false`、`order_or_target_or_quantity_output_generated=false`。
- `input_lineage_inventory.csv` 显示标准 qlib-only signal 119862 rows，窗口 `2023-01-03` 到 `2026-05-07`；TEST qlib-only input 89386 rows，窗口 `2023-01-03` 到 `2025-06-30`；baseline actions 1107 rows；position snapshots 5427 rows；TWII source 2771 rows。
- `feature_readiness_audit.csv` 标记 score bucket/percentile/gap、rank deltas、TWII MA/drawdown/volatility、holding state 均 ready 或 constructible。
- `pit_leakage_audit.csv` 无 critical/fail，forward return 被限制为 RSR1 diagnostic label，realized PnL 和 execution fields 被限制在 ledger/accounting 边界。
- `forbidden_action_audit.csv` 全部为 `PASS_NOT_PERFORMED`。

## 5. Missing Evidence Or Open Questions

1. RSR1 诊断数据集尚未物化，这是下一阶段工作，不属于 RSR0 缺失证据。
2. RSR1 专用 `PortfolioState` 视图尚未生成；必须在 RSR1 第一小步完成。
3. formal 2023-2025 `ReplayResultArtifact` 尚未为本路线生成；当前有 internal ledger 和标准 ReplayResultArtifact shape reference。仅当 RSR1 或 RSR2 gate 明确要求时，才做只读包装。
4. market breadth 可选，未纳入 RSR0 pass gate。若 RSR1 采用，需补 PIT coverage audit。

## 6. Forbidden Actions Audit

审查未发现以下行为：

- training / retraining；
- qlib refresh 或 LTR retrain；
- 收益规则 replay、PnL search、阈值调优；
- provider publish；
- accepted latest switch；
- production/default/frontend/daily update 修改；
- broker、quick-trade、真实订单；
- OrderIntentArtifact 生成；
- target_position、target_weight、quantity instruction 输出；
- external data pull。

`scripts/audit_tw_policy_rsr0_contract_data_readiness.py` 是本地只读 inventory 脚本，除写入 RSR0 readiness artifacts 和执行报告外，未调用 replay runner、training runner、publish/latest/default 相关路径。

## 7. Next Work Document

已写下一步工作文档：

```text
docs/tw_portfolio_decision_model/POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_WORK_CN.md
```

RSR1 必须按该工作文档执行：只做 score/rank/regime/holding-aware attribution diagnostic dataset 和诊断摘要，不训练、不 replay 收益规则、不调阈值、不产出 OrderIntent、不改 production/default/latest/publish。

RSR1 的入口条件：

1. 先物化 RSR1 专用 `PortfolioState` 视图。
2. feature matrix 不得包含 future return/label、execution fields、realized/unrealized PnL、cash/NAV、broker/order、target/weight/quantity instruction。
3. forward return 只能进入 diagnostic label namespace，并必须有 consumer audit。
4. score bucket 边界只能作为诊断分箱预声明，不得基于 replay PnL 或收益搜索选择。
5. rank delta 必须由 current signal date 与历史 signal dates 构造，不得跨未来。
6. market regime 必须只使用 signal date 当日或之前 TWII/price 数据。

## 8. Command For Executor Or Coordinator

```text
你是 RSR1 执行者。读取 docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md、docs/tw_portfolio_decision_model/POLICY_RSR0_CONTRACT_AND_DATA_READINESS_REVIEW_CN.md、docs/tw_portfolio_decision_model/POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_WORK_CN.md，以及 RSR0 artifact root 下所有 manifest/audit 文件。只执行 RSR1 attribution diagnostic：物化 PIT-safe 诊断数据集、PortfolioState 视图、feature/label/consumer audits 和诊断摘要。不要训练、不要跑收益规则 replay、不要调阈值、不要生成 OrderIntent、不要输出订单/仓位/权重/数量、不要 provider publish、不要 accepted latest switch、不要改 production/default/frontend/daily update。完成后写 POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_EXECUTION_REPORT_CN.md。
```
