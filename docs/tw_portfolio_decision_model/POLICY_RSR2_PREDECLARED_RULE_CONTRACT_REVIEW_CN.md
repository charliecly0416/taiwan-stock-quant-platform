---
created_at: 2026-06-27
status: reviewed_rsr2_predeclared_rule_contract
phase: POLICY_RSR2_PREDECLARED_RULE_CONTRACT
reviewer: RSR2
verdict: PASS_WITH_CONDITIONS
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RSR2_PREDECLARED_RULE_CONTRACT_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RSR2_PREDECLARED_RULE_CONTRACT_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr2_predeclared_rule_contract
next_work_doc: docs/tw_portfolio_decision_model/POLICY_RSR3_ORDER_INTENT_BUILDER_AND_PARITY_SMOKE_WORK_CN.md
production_allowed: false
readonly_only: true
diagnostic_only: true
---

# Review Opinion And Next Work Document

## 1. Verdict

`PASS_WITH_CONDITIONS`.

RSR2 交付物满足 `POLICY_RSR2_PREDECLARED_RULE_CONTRACT` 的核心要求：只做 predeclared rule contract design，冻结 5 个规则且 rule_family 全部来自允许集合，字段边界和 forbidden action audit 合规，YAML 只停留在 RSR2 artifact root，未进入正式 `configs/strategy_dependencies/`。

条件不是 RSR2 repair，而是 RSR3 进入条件：RSR3 必须重新声明并构造/适配 PIT-safe extensions，不能直接把 RSR1 diagnostic artifact 当作 StrategyRule runtime input；RSR3 只能生成 OrderIntentArtifact samples 与 baseline parity smoke，不得跑正式收益 replay，不得生成 ReplayResult 收益结论，不得 production/default/latest/publish/frontend/daily/external pull。

## 2. Findings

### Critical

无。

### High

无。

### Medium

无。

### Low

1. RSR1 `feature_schema.json` 将 score/rank/regime/holding diagnostic columns 标记为 `allowed_consumer=rsr1_diagnostic_summary_only`，并禁止 `StrategyRule/OrderIntent/ReplayExecution/ranking_threshold_selection` 直接消费。RSR2 已在 `required_fields_matrix.csv` 中把这些列声明为 `pit_safe_extension_draft`，这是可接受的合同表达；RSR3 必须重新通过 ModelSignalArtifact adapter 或独立 extension builder 生成 PIT-safe fields，不能直接读取 RSR1 diagnostic dataset。
2. `rsr2_market_regime_action_budget_v1` 冻结了 `max_buy_count=2`、`max_sell_count=2`，且 regime table 中 risk_on 为 `2/1`、risk_neutral 为 `1/1`、risk_off 为 `0/1`、crash 为 `0/2`。该表达未超出 RSR2 多买多卖 action budget 边界；RSR3 需要在 strategy decision audit 中逐日证明实际 buy/sell intent 数没有超过 regime-specific budget 和 YAML declared max。
3. RSR2 只生成 contract artifacts，没有运行 YAML schema validator。由于 RSR2 work doc 没要求正式注册 YAML，且 YAML 是 draft-only，未阻断 PASS；RSR3 若把草案转成正式 dependency input，必须补 YAML parse/contract validation。

## 3. Mainline Compliance

- 范围合规：`manifest.json`、执行报告和脚本均声明 `scope=predeclared_rule_contract_design_only`；未发现 StrategyRule implementation、OrderIntentArtifact generation、ReplayResult generation、replay rerun、threshold tuning、best rule/bucket selection。
- 规则数量合规：`predeclared_rule_contracts.csv` 共 5 条，未超过上限。
- rule_family 合规：5 条分别为 `score bucket gate`、`rank momentum buy gate`、`rank deterioration sell gate`、`market regime action budget`、`score/rank/regime interaction`，均来自 RSR2 work doc 允许集合。
- 每规则合同内容合规：每条规则均包含 required core fields、required extensions、forbidden fields、score bucket/percentile/gap definition、rank delta definition、market regime definition、holding state definition、max_buy_count、max_sell_count、sell_boundary、buy_ordering、tie_breaker、no_trade_zone、turnover/action budget、expected_tradeoff、later pass/fail gates、no replay/order-intent/threshold-tuning flags。
- 字段边界合规：required core fields 来自标准 ModelSignalArtifact / PortfolioState 边界；extensions 来自 RSR1 PIT-safe diagnostic mechanism 草案；forbidden fields 覆盖 `diagnostic_label_*`、future/forward return、label、realized/unrealized PnL、execution/next price、cash/NAV/equity/daily_return/replay_return、broker/order、target/weight/allocation/quantity instruction。
- 阈值来源合规：合同中的 score bins、percentile bands、rank deltas、TWII regime、material margin 和 participation/turnover gates 均声明来自 RSR1 固定诊断机制或 mainline 预设；未见 replay PnL/收益最大化搜索。
- YAML 位置合规：draft YAML 只存在于 `data_tw/experiments/.../rsr2_predeclared_rule_contract/rule_dependency_yaml_drafts/`；审查命令未发现 `configs/strategy_dependencies/rsr2*.yaml`。
- RSR2 pass/fail gates 合规：`pass_fail_gates.md` 预声明 PIT/available_at、forbidden field/action、coverage、active days、action change rate、no-trade/all-cash dependence、turnover/action budget、fee/tax net return、drawdown、regime sample gates，且明确 RSR2 不执行 replay。

## 4. Evidence Checked

已读取并核对：

- `docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR2_PREDECLARED_RULE_CONTRACT_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR2_PREDECLARED_RULE_CONTRACT_EXECUTION_REPORT_CN.md`
- `scripts/build_tw_policy_rsr2_predeclared_rule_contract.py`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr2_predeclared_rule_contract/manifest.json`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr2_predeclared_rule_contract/predeclared_rule_contracts.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr2_predeclared_rule_contract/predeclared_rule_contracts.md`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr2_predeclared_rule_contract/rule_dependency_yaml_drafts/README.md`
- all 5 YAML files under `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr2_predeclared_rule_contract/rule_dependency_yaml_drafts/`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr2_predeclared_rule_contract/required_fields_matrix.csv`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr2_predeclared_rule_contract/pass_fail_gates.md`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr2_predeclared_rule_contract/forbidden_action_audit.csv`
- RSR1 artifacts: `feature_schema.json`、`label_schema.json`、`consumer_forbidden_field_audit.csv`、`pit_leakage_audit.csv`、`diagnostic_summary.md`
- modular contracts: `STRATEGY_RULE_CONTRACT_CN.md`、`ORDER_INTENT_CONTRACT_CN.md`、`REPLAY_RESULT_CONTRACT_CN.md`、`TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`、`NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`

关键命令证据：

```text
python -m py_compile scripts/build_tw_policy_rsr2_predeclared_rule_contract.py
```

通过。

```text
rule_count 5
families_allowed True
readonly_all True
diagnostic_all True
no_replay_all True
no_order_intent_all True
no_threshold_tuning_all True
forbidden_audit_rows 13
forbidden_audit_clean True
manifest_flags all reviewed forbidden operation flags False
```

`find configs/strategy_dependencies -maxdepth 1 -type f -name 'rsr2*.yaml'` 无输出，确认 draft YAML 未注册到正式策略依赖目录。

## 5. Missing Evidence Or Open Questions

无阻断缺失证据。

开放问题/后续条件：

1. RSR2 没有也不应生成正式 StrategyDependency YAML；RSR3 若需要 runtime dependency input，必须从 RSR2 draft 转换为 smoke-only / sample-only dependency，并保留 `diagnostic_only=true`、`not_default_candidate=true`、`not_production_candidate=true`。
2. RSR3 需要明确 PIT-safe extension 生成路径：score bucket、score_percentile_band、score_gap_to_top、rank deltas/directions、market regime flags、holding support flags 必须来自标准 signal/PortfolioState 和 backward-asof market data，不得直接读取 RSR1 diagnostic dataset 或 `diagnostic_label_*`。
3. RSR3 baseline parity smoke 只能证明 OrderIntent builder 的 action boundary/parity，不得输出收益、NAV、PnL、ReplayResult 或正式 replay 结论。

## 6. Forbidden Actions Audit

审查未发现以下 forbidden actions：

- training / retraining；
- qlib refresh、LTR retrain 或 qlib+LTR adaptation；
- external data pull；
- StrategyRule production implementation；
- OrderIntentArtifact generation in RSR2；
- ReplayResult generation or replay rerun；
- replay PnL search、threshold tuning、best threshold/rule/bucket selection；
- provider publish、accepted latest switch；
- production/default/frontend/daily/latest 修改；
- broker、quick-trade、real order；
- target_position、target_weight、allocation_weight、quantity instruction 输出。

`forbidden_action_audit.csv` 共 13 行，全部为 `PASS_NOT_PERFORMED`。

## 7. Next Work Document

已写下一步工作文档：

```text
docs/tw_portfolio_decision_model/POLICY_RSR3_ORDER_INTENT_BUILDER_AND_PARITY_SMOKE_WORK_CN.md
```

RSR3 只允许根据 RSR2 合同实现/generate `OrderIntentArtifact` samples 与 parity smoke，并必须包含：

- forbidden field audit；
- strategy decision audit；
- OrderIntent contract validation；
- baseline parity smoke。

RSR3 仍不得跑正式收益 replay，不得生成 `ReplayResultArtifact` 收益结论，不得 provider/latest/default/production，不得真实订单/target position/weight/quantity。

## 8. Command For Executor Or Coordinator

```text
你是 RSR3 执行者。读取 POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md、POLICY_RSR2_PREDECLARED_RULE_CONTRACT_REVIEW_CN.md、POLICY_RSR3_ORDER_INTENT_BUILDER_AND_PARITY_SMOKE_WORK_CN.md、RSR2 artifact root 下 manifest/predeclared_rule_contracts/required_fields_matrix/pass_fail_gates/rule_dependency_yaml_drafts，以及 StrategyRule/OrderIntent/ReplayResult 合同。只做 OrderIntentArtifact samples 与 baseline parity smoke：根据 RSR2 合同生成 smoke-only、diagnostic-only 的 OrderIntent sample artifacts、strategy_decision_audit、forbidden_field_audit 和 OrderIntent contract validation output；做 baseline parity smoke 时只验证 action boundary/parity，不输出收益/NAV/PnL，不生成 ReplayResult 收益结论，不跑正式 replay，不 provider publish，不 accepted latest switch，不改 production/default/frontend/daily/latest，不外部拉取，不接 broker/quick-trade，不输出 target_position/target_weight/allocation_weight/quantity instruction。完成后写 POLICY_RSR3_ORDER_INTENT_BUILDER_AND_PARITY_SMOKE_EXECUTION_REPORT_CN.md。
```
