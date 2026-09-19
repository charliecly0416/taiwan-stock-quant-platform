---
created_at: 2026-06-27
status: reviewed_rsr4_predeclared_readonly_replay
phase: POLICY_RSR4_PREDECLARED_READONLY_REPLAY
reviewer: RSR4
verdict: PASS_WITH_CONDITIONS
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RSR4_PREDECLARED_READONLY_REPLAY_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RSR4_PREDECLARED_READONLY_REPLAY_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr4_predeclared_readonly_replay
next_work_doc: docs/tw_portfolio_decision_model/POLICY_RSR5_ROBUSTNESS_AND_ABLATION_WORK_CN.md
production_allowed: false
readonly_only: true
historical_readonly_research_artifact: true
---

# Review Opinion And Next Work Document

## 1. Verdict

`PASS_WITH_CONDITIONS`.

RSR4 执行者交付物满足 historical readonly replay 的核心合同：5 条 RSR2 冻结规则均有 historical `OrderIntentArtifact` 和 `ReplayResultArtifact`，replay result 文件齐全，根级和规则级 fee/tax/turnover、cash/no-trade、coverage、missing price、PIT/leakage、forbidden field/action、baseline clone、regime budget 审计齐全，且独立结构校验未发现 fail。

放行条件：RSR5 只能带入唯一通过 RSR4 gate 的候选 `rsr2_rank_deterioration_sell_gate_v1`。其余 4 条规则必须视为 RSR4 rejected rules，不能进入 RSR5 robustness/ablation，除非 coordinator 另开 repair route；本 RSR5 work doc 不授权 repair 或重放调参。

## 2. Findings

### Critical

无。

### High

无。

### Medium

无。

### Low

1. RSR4 builder 是 route-local self-contained builder，而不是复用一个项目级 replay engine API。审查未发现它在 `execute_replay()` 中重新选股或绕过 `OrderIntentArtifact`，但 RSR5 应继续保留 `decision_source=OrderIntentArtifact`、`no_inline_strategy_logic_in_replay=true`、`execution_audit.csv` 证据。
2. `rsr2_score_bucket_regime_gate_v1`、`rsr2_rank_momentum_buy_gate_v1`、`rsr2_market_regime_action_budget_v1`、`rsr2_score_rank_regime_interaction_v1` 均被 preliminary rejected，主要因为 `cash_gt_90pct_day_share > 5%` / all-cash-no-trade gate 触发 review/rejection；它们不是 artifact failure，但也不是 RSR5 候选。
3. `rsr2_rank_deterioration_sell_gate_v1` 的 turnover proxy 为 `225.55655867`，高于 baseline `106.03114336` 的 2 倍，但 net after fee/tax 仍显著通过 Type A material margin，且 `high_turnover_gross_only_rejection=false`。RSR5 必须继续做 transaction cost sensitivity 和 action-level attribution，确认不是单窗口高换手偶然。

## 3. Mainline Compliance

- 冻结规则边界合规：RSR4 仅包含 RSR2 冻结的 5 条规则，`manifest.json` 的 `rule_names` 与 RSR2 contracts 一致；未发现新增/删除/改名规则。
- 阈值边界合规：脚本中的 score bucket、rank delta、TWII regime 和 action budget 与 RSR2 contracts 对齐；未发现基于 replay PnL 的阈值搜索、best bucket 或 best rule selection。
- 标准链路合规：每条规则先生成 historical `OrderIntentArtifact`，再由 `execute_replay()` 读取 `order_intents.csv` 产生 `ReplayResultArtifact`；`execution_audit.csv` 声明 decision source 为 OrderIntentArtifact，replay 不修改 OrderIntent/ranking/threshold。
- ReplayResult 合同合规：每条规则均包含 `manifest.json`、`summary.csv`、`actions.csv`、`daily_nav.csv`、`position_snapshots.csv`、`coverage_audit.csv`、`position_integrity_audit.csv`、`forbidden_field_audit.csv`、`execution_audit.csv`、`forbidden_action_audit.json`。
- OrderIntent 禁止字段合规：独立校验未发现 `execution_price`、`cash`、`nav`、`pnl`、`broker/order`、`target_position/target_weight/allocation_weight/quantity/shares/lots` 等字段出现在 RSR4 `order_intents.csv`。
- Replay 输出语义合规：`quantity`、execution、cash、NAV/PnL 只出现在 replay output 文件中，作为 `ReplayExecution` 结果，不作为 OrderIntent 指令。
- Risk neutral 条件已补齐：`rsr2_market_regime_action_budget_v1` 在 `risk_neutral` 有 `active_days=35`、`buy_intents=35`、`sell_intents=19`、`budget_violation_count=0`、`risk_neutral_conclusion_allowed=True`。
- Preliminary classification 合规：唯一 Type A 是 `rsr2_rank_deterioration_sell_gate_v1`，其 net return `1.98685891` 高于 baseline `0.4121439` 超过 2 percentage points，max drawdown `-0.37160781` 相比 baseline `-0.5590545` 没有恶化，baseline clone audit pass，cash/no-trade audit pass，fee/tax 后仍通过。
- Rejected rule disposition 合规：4 条 rejected rules 有完整 artifacts，但 RSR4 gates 不通过；本 review 将其分类为 gate rejection，不允许进入 RSR5。

## 4. Evidence Checked

已读取并核对：

- `docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR4_PREDECLARED_READONLY_REPLAY_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR2_PREDECLARED_RULE_CONTRACT_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR3_ORDER_INTENT_BUILDER_AND_PARITY_SMOKE_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RSR4_PREDECLARED_READONLY_REPLAY_EXECUTION_REPORT_CN.md`
- `scripts/build_tw_policy_rsr4_predeclared_readonly_replay.py`
- RSR4 root artifacts: `manifest.json`、`replay_result_index.csv`、`input_manifest_links.json`、`baseline_clone_audit.csv`、`fee_tax_turnover_audit.csv`、`regime_budget_audit.csv`、`missing_price_audit.csv`、`pit_leakage_audit.csv`、`cash_no_trade_audit.csv`、`forbidden_field_audit.csv`、`forbidden_action_audit.csv`
- all 5 historical `OrderIntentArtifact` directories under `rsr4_predeclared_readonly_replay/order_intents/`
- all 5 `ReplayResultArtifact` directories under `rsr4_predeclared_readonly_replay/replay_results/`
- RSR2 `predeclared_rule_contracts.csv`、`pass_fail_gates.md`、draft YAMLs as needed
- RSR3 contract validation, smoke samples, strategy decision and forbidden audits as needed
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`

独立校验结果：

```text
python -m py_compile scripts/build_tw_policy_rsr4_predeclared_readonly_replay.py
pass
```

```text
RSR4 artifact structure validation:
problem_count=0
5/5 OrderIntentArtifact directories present
5/5 ReplayResultArtifact directories present
no required replay audit file missing
no OrderIntent forbidden sizing/execution/cash/NAV/broker/target fields detected
no coverage/position_integrity/forbidden_field/execution audit fail rows detected
```

关键 RSR4 summary：

| strategy_rule | classification | net_return | max_drawdown | action_count | disposition |
| --- | --- | ---: | ---: | ---: | --- |
| `rsr2_score_bucket_regime_gate_v1` | `REJECTED_PRELIMINARY` | 0.54919662 | -0.18462362 | 676 | gate rejection; do not enter RSR5 |
| `rsr2_rank_momentum_buy_gate_v1` | `REJECTED_PRELIMINARY` | -0.06796673 | -0.2400165 | 696 | gate rejection; do not enter RSR5 |
| `rsr2_rank_deterioration_sell_gate_v1` | `TYPE_A_PRELIMINARY_HISTORICAL_READONLY` | 1.98685891 | -0.37160781 | 1053 | allowed into RSR5 only |
| `rsr2_market_regime_action_budget_v1` | `REJECTED_PRELIMINARY` | 0.89624386 | -0.14047453 | 811 | gate rejection; do not enter RSR5 |
| `rsr2_score_rank_regime_interaction_v1` | `REJECTED_PRELIMINARY` | 0.48104163 | -0.20151035 | 674 | gate rejection; do not enter RSR5 |

## 5. Missing Evidence Or Open Questions

无阻断缺失证据。

RSR5 仍需验证的开放风险：

1. `rsr2_rank_deterioration_sell_gate_v1` 目前只是 2023-2025 qlib-only single-window historical readonly evidence，尚未证明 2021 sanity、2022 downturn diagnostic、parameter neighborhood stability、market regime ablation 和 transaction cost sensitivity。
2. Type A 候选 turnover 明显高于 baseline，虽非 gross-only rejection，但必须在 RSR5 中做成本敏感性和 action-level attribution。
3. RSR5 不得把 RSR4 preliminary Type A 包装为 production/default/latest/published candidate；它仍只是 historical readonly research candidate。

## 6. Forbidden Actions Audit

未发现以下 forbidden actions：

- training / retraining；
- qlib refresh；
- LTR retrain 或 qlib+LTR adaptation；
- external data pull；
- 修改 RSR2 冻结规则或阈值；
- threshold tuning to replay returns；
- best threshold / best rule / best bucket selection；
- provider publish；
- accepted latest switch；
- production/default/frontend/daily/latest 修改；
- broker、quick-trade、real order；
- target_position、target_weight、allocation_weight、quantity instruction；
- replay result 包装成 production candidate、默认策略或投资建议。

证据：RSR4 root `forbidden_action_audit.csv` 全部为 `PASS_NOT_PERFORMED`；RSR4 root manifest 对上述行为均声明 false；git status 显示工作树已有大量并行改动，本 review 未回滚或修改执行产物。

## 7. Next Work Document

已写下一步工作文档：

```text
docs/tw_portfolio_decision_model/POLICY_RSR5_ROBUSTNESS_AND_ABLATION_WORK_CN.md
```

RSR5 只允许对 `rsr2_rank_deterioration_sell_gate_v1` 做 robustness/ablation。Rejected rules 不得进入 RSR5；不得借 RSR5 repair、调参或重新选择规则。

## 8. Command For Executor Or Coordinator

```text
你是 RSR5 执行者。读取 POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md、POLICY_RSR4_PREDECLARED_READONLY_REPLAY_REVIEW_CN.md、POLICY_RSR5_ROBUSTNESS_AND_ABLATION_WORK_CN.md、RSR2/RSR3/RSR4 合同与 artifacts。只允许对 RSR4 reviewer 放行的唯一候选 rsr2_rank_deterioration_sell_gate_v1 做 robustness/ablation：2021 sanity、2022 downturn diagnostic、2023-2025 qlib-only strict candidate re-check、parameter neighborhood stability、action-level attribution、market regime ablation、transaction cost sensitivity、cash/no-trade and baseline clone re-check。不得让 rejected rules 进入 RSR5，不得训练、不得改阈值调参、不得 qlib refresh/LTR adaptation、不得 provider/latest/default/production/frontend/daily/publish、不得 broker/quick-trade/real order、不得 target/weight/allocation/quantity instruction。完成后写 POLICY_RSR5_ROBUSTNESS_AND_ABLATION_EXECUTION_REPORT_CN.md。
```
