# POLICY_MTR4_READINESS_DESIGN_AND_EXTENDED_EVIDENCE_CONTRACT_REVIEW_CN

生成日期：2026-06-28

## 1. Verdict

```text
PASS_READY_FOR_MTR5_EXTENDED_EVIDENCE
```

MTR4 执行结果通过审查。该结论只表示可以进入 `MTR5_EXTENDED_OOS_SHADOW_AND_PRODUCTION_READINESS_DIAGNOSTIC`，不表示 production ready，不允许切默认、不允许 provider publish、不允许 accepted latest switch、不允许 frontend/API/Agent/daily/production 改动。

## 2. 审查范围

已读取并核对：

- `docs/tw_portfolio_decision_model/POLICY_MTR4_READINESS_DESIGN_AND_EXTENDED_EVIDENCE_CONTRACT_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTR4_READINESS_DESIGN_AND_EXTENDED_EVIDENCE_CONTRACT_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTR_MECHANISM_TRANSFER_TO_BASELINE_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTR3_ROBUSTNESS_WINDOW_REGIME_AND_MECHANISM_ATTRIBUTION_REVIEW_CN.md`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr4_readiness_design_and_extended_evidence_contract/manifest.json`
- MTR4 输出目录下全部 contract CSV、`validator_report.json`、`diagnostic_findings.md`、`mtr5_work_recommendation.md`
- 模块化合同：`TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`、`STRATEGY_RULE_CONTRACT_CN.md`、`ORDER_INTENT_CONTRACT_CN.md`、`REPLAY_RESULT_CONTRACT_CN.md`、`NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`

## 3. Artifact 完整性与 Machine-readable

MTR4 输出目录包含工作文档要求的全部 12 个文件：

- `manifest.json`
- `readiness_gate_contract.csv`
- `extended_evidence_contract.csv`
- `broad_full_rank_visibility_contract.csv`
- `non_top50_buy_validator_contract.csv`
- `window_regime_gate_contract.csv`
- `concentration_risk_contract.csv`
- `production_boundary_contract.csv`
- `mtr5_work_recommendation.md`
- `forbidden_scope_audit.csv`
- `validator_report.json`
- `diagnostic_findings.md`

独立解析结果：

| artifact | rows / status |
| --- | ---: |
| `readiness_gate_contract.csv` | 10 rows |
| `extended_evidence_contract.csv` | 10 rows |
| `broad_full_rank_visibility_contract.csv` | 4 rows |
| `non_top50_buy_validator_contract.csv` | 4 rows |
| `window_regime_gate_contract.csv` | 8 rows |
| `concentration_risk_contract.csv` | 3 rows |
| `production_boundary_contract.csv` | 9 rows |
| `forbidden_scope_audit.csv` | 20 rows |
| `manifest.json` | verdict parse ok |
| `validator_report.json` | `ok=true` |

结论：artifact 完整，CSV/JSON 可机器解析，manifest 声明 `artifact_type=policy_mtr4_readiness_design_and_extended_evidence_contract`、`readonly_only=true`、`simulation_only=true`、`production_allowed=false`、`replay_performed=false`。

## 4. MTR3 风险到 Gate 的映射

结论：完整映射。

MTR3 月度/rolling 风险已进入 `window_regime_gate_contract.csv`：

- `monthly_positive_delta_ratio >= 0.60`，MTR3 值 `0.6`，gate effect 为 `warn_if_only_barely_passes`。
- `rolling_window_positive_delta_ratio >= 0.60`，MTR3 值 `0.75`，gate effect 为 `requires_daily_rolling_recheck`。
- `extended_evidence_contract.csv` 明确 MTR5 必须补每日 rolling 20d，并优先补 40d；负月 `2026-02`、`2026-05` 必须做 inventory。

MTR3 risk_off/drawdown 风险已进入 `window_regime_gate_contract.csv` 和 `extended_evidence_contract.csv`：

- `risk_off_net_delta >= 0`，MTR3 值 `0.01063245`，标记为 `small_positive_is_not_enough_for_production`。
- `drawdown_segment_delta >= 0`，MTR3 值约 `0.03056198`，并要求 MTR5 做 drawdown segment inventory。
- 合同明确 full-window 正收益不能覆盖 risk_off 或 drawdown segment 恶化。

MTR3 symbol/event concentration 风险已进入 `concentration_risk_contract.csv`：

- `top1_symbol_delta_share=0.631760` -> `warn_requires_disclosure_and_more_evidence`。
- `top3_symbol_delta_share=0.972756` -> `fail_or_research_only_pending_extended_evidence`。
- `top1_event_delta_share=0.300709` -> `warn_requires_event_disclosure`。

上述分类与 MTR3 审查结论 `PASS_MTR3_WITH_CONCENTRATION_OR_WINDOW_RISK` 一致，且足以阻断直接生产化。

## 5. Broad Full-rank 与 Non-top50 Buy Gate

结论：足够硬，可以进入 MTR5。

`broad_full_rank_visibility_contract.csv` 明确：

- `candidate_rank / full_qlib_rank` 是 qlib base rank。
- `buy_score` 只是在 qlib top50 内的 LTR rerank score。
- non-top50 broad rows 只能用于已有持仓 hold/sell visibility。
- MTR2_R broad artifact 仍是 research-only / diagnostic-only，不能静默替代 accepted latest 或 product default。

`non_top50_buy_validator_contract.csv` 明确 4 条 hard fail：

- buy intent 的 `candidate_rank` 缺失即 fail。
- buy intent 的 `candidate_rank` 非数值即 fail。
- buy intent 的 `candidate_rank > 50` 即 fail。
- strategy trace/reason 与 `order_intents.csv` 不一致、或 non-top50 行进入 buy trace/reason 即 fail。

这覆盖了 OrderIntent 合同和 StrategyRule 字段语义要求，满足 MTR5 与未来 production-readiness 前置 hard gate。

## 6. Production Boundary

结论：production no-go 明确，未发现 MTR4 授权范围内的生产边界越界。

MTR4 manifest 与合同均声明：

- `production_allowed=false`
- `production_ready=false`
- `provider_publish_allowed=false`
- `accepted_latest_switch_allowed=false`
- `frontend_default_switch_allowed=false`
- `model_training_performed=false`
- `strategy_tuning_performed=false`
- `replay_performed=false`

`production_boundary_contract.csv` 对以下项目全部标记 `blocked`：production/default/frontend/API/Agent/daily/provider/latest change、provider publish、accepted latest switch、broker/quick-trade/real order、target_weight/target_position/quantity instruction、model training/retraining、strategy tuning、posthoc candidate expansion、realized pnl / replay return as StrategyRule input。

`forbidden_scope_audit.csv` 显示 MTR4 未跑新收益 replay、未改 StrategyRule/strategy dependency、未训练/调参、未改 production/default/latest/provider/frontend/API/Agent/daily。MTR3 source forbidden audit 也均为 `performed=False`、`status=pass`。

审查时发现工作树存在大量既有未提交改动，但 MTR4 builder 写入点限定在 MTR4 输出目录和 MTR4 执行报告；本次审查未将无关 dirty files 归因给 MTR4。

## 7. 禁止事项复核

未发现 MTR4 执行阶段存在以下行为：

- 新收益 replay
- 模型训练或重训
- 策略调参
- 新增候选
- 修改 M2 参数
- 重写 MTR2_R 或 MTR3 产物
- 修改 production/default/latest/provider/frontend/API/Agent/daily
- provider publish 或 accepted latest switch
- broker / quick-trade / real order
- target_weight / target_position / quantity instruction

MTR4 使用 MTR3 后验归因结果定义 gate，但没有把 replay return / realized pnl 反馈给 StrategyRule。

## 8. 下一步工作文档

# MTR5_EXTENDED_OOS_SHADOW_AND_PRODUCTION_READINESS_DIAGNOSTIC

## 8.1 目标

MTR5 仍为 readonly / simulation-only 阶段，不得生产化。目标是按 MTR4 合同收集 extended evidence，判断 `M2_hold_rank_buffer_100` 是否可进入 MTR6 production readiness proposal，或必须保持 research-only。

## 8.2 必读输入

- MTR4 审查报告：`docs/tw_portfolio_decision_model/POLICY_MTR4_READINESS_DESIGN_AND_EXTENDED_EVIDENCE_CONTRACT_REVIEW_CN.md`
- MTR4 manifest：`data_tw/experiments/policy_mtr_mechanism_transfer/mtr4_readiness_design_and_extended_evidence_contract/manifest.json`
- MTR4 全部 contract CSV
- MTR3 manifest、window/regime/drawdown/concentration/validator/forbidden audit artifacts
- `STRATEGY_RULE_CONTRACT_CN.md`
- `ORDER_INTENT_CONTRACT_CN.md`
- `REPLAY_RESULT_CONTRACT_CN.md`

## 8.3 必做范围

1. 复核 MTR3 同窗口 `2026-01-02` 至 `2026-05-07`，不得修改 M2 参数。
2. 补每日 rolling 20d，并优先补 rolling 40d。
3. 复核 monthly attribution，列出所有 negative month inventory。
4. 复核 risk_on / neutral / risk_off attribution，risk_off delta 不得恶化。
5. 复核 drawdown segment attribution，full-window 正收益不能覆盖 drawdown 恶化。
6. 分解 turnover / fee / tax，确认低换手机制不是 accounting artifact。
7. 应用 symbol/event concentration gate。
8. 执行 permanent non-top50 buy validator，任何 buy intent 的 `candidate_rank` 缺失、非数值或 > 50 都 hard fail。
9. 若存在更长 strict OOS 或 readonly shadow signal lineage，必须纳入；若不存在，必须写 data lineage blocker，不得虚构窗口。

## 8.4 建议输出

- `manifest.json`
- `same_window_replay_confirmation.csv`
- `daily_rolling_window_attribution.csv`
- `monthly_negative_inventory.csv`
- `regime_attribution_summary.csv`
- `drawdown_segment_attribution.csv`
- `turnover_fee_tax_decomposition.csv`
- `symbol_concentration_gate.csv`
- `event_concentration_gate.csv`
- `non_top50_buy_validator_report.json`
- `data_lineage_blocker.md`，如适用
- MTR5 执行报告
- MTR5 审查报告

## 8.5 MTR5 允许 Verdict

```text
GO_TO_MTR6_PRODUCTION_READINESS_PROPOSAL
KEEP_RESEARCH_ONLY
STOP_LINEAGE_OR_VALIDATOR_BLOCKER
```

任何 MTR5 verdict 都不得直接切 production/default/latest/provider/frontend/API/Agent/daily。

## 9. Final Gate

```text
artifact_complete = true
all_required_contracts_present = true
mtr3_risks_mapped_to_gates = true
non_top50_buy_hard_fail_defined = true
production_no_go_explicit = true
forbidden_scope_clean = true
mtr5_next_step_defined = true
```

最终结论：

```text
PASS_READY_FOR_MTR5_EXTENDED_EVIDENCE
```
