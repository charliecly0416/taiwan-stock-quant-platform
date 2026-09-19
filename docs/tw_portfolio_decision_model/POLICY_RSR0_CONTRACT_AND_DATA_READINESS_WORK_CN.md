# POLICY_RSR0_CONTRACT_AND_DATA_READINESS_WORK_CN

## 1. Phase Goal

执行 `POLICY_RSR0_CONTRACT_AND_DATA_READINESS`。

本阶段只做规则研究主线的合同和数据可行性检查，不跑收益 replay，不生成策略候选，不调阈值。

## 2. Required Documents

执行者必须读取：

- `docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MODEL_RESEARCH_ROUTE_CLOSURE_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FINAL_CLOSURE_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT6_RESEARCH_CLOSURE_PACKAGE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT7C_ADAPTIVE_SCORE_ALIGNED_CLOSURE_REVIEW_CN.md`

## 3. Required Checks

### 3.1 Signal Readiness

确认是否存在可追溯 qlib-only signal / ranking 输入，至少能构造：

- `signal_date`
- `instrument`
- `candidate_rank`
- `buy_score` 或可映射 score
- `raw_score` 若可用
- `score_rank`
- `full_qlib_rank`
- `signal_asof`
- `available_at`
- source artifact / manifest

不得读取模型私有训练文件作为策略输入。

### 3.2 Baseline / Replay Readiness

确认是否可追溯 baseline policy replay 或 baseline action ledger：

- baseline strategy name；
- baseline action dates；
- baseline holdings；
- baseline buy/sell actions；
- fee/tax assumptions；
- cash / NAV / drawdown metrics；
- price source；
- replay result artifact。

RSR0 不重跑 replay。

### 3.3 Market Feature Readiness

确认是否可 PIT-safe 构造：

- TWII close；
- TWII MA5 / MA10 / MA20；
- TWII drawdown；
- TWII volatility；
- market breadth 如可用；
- trading calendar。

若 market breadth 不可用，不得阻塞 RSR0；可标记 optional。

### 3.4 Score / Rank Feature Readiness

确认是否可构造：

- score buckets；
- score percentile；
- score gap / top score dispersion；
- rank_1d_delta；
- rank_3d_delta；
- rank_5d_delta；
- rank improvement / deterioration flags；
- holding-aware state。

### 3.5 PIT / Leakage Readiness

必须确认：

- forward return 只作为 RSR1 diagnostic label；
- 策略输入不包含 future return / label / realized pnl；
- execution price / next_open / next_close 不进入 StrategyRule；
- market regime 使用 signal date 可得数据；
- rank delta 不跨越未来日期。

## 4. Required Artifacts

建议输出目录：

```text
data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr0_contract_and_data_readiness/
```

必须产出：

- `manifest.json`
- `input_lineage_inventory.csv`
- `feature_readiness_audit.csv`
- `pit_leakage_audit.csv`
- `forbidden_action_audit.csv`
- `rsr1_dataset_feasibility.md`

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RSR0_CONTRACT_AND_DATA_READINESS_EXECUTION_REPORT_CN.md
```

## 5. Pass Criteria

RSR0 通过条件：

- qlib-only signal 可追溯；
- baseline/replay 或 action ledger 可追溯；
- market regime 至少可用 TWII MA / drawdown / volatility 中两类；
- score bucket 和 rank delta 可构造；
- holding state 可追溯或有明确 repair 方案；
- PIT/leakage audit 无 critical；
- forbidden action audit clean。

## 6. Stop / Repair Conditions

必须 STOP 或 repair：

- 找不到 qlib-only signal；
- 找不到 baseline/action ledger；
- 无法构造任何 market regime；
- rank delta 只能通过未来数据计算；
- 需要读取 future return 才能决策；
- 发现 provider publish / accepted latest switch / production write；
- 执行者开始调阈值或跑收益 replay。

## 7. Forbidden Actions

本阶段禁止：

- training；
- replay PnL rule search；
- qlib refresh；
- LTR retrain；
- provider publish；
- accepted latest switch；
- frontend/default strategy change；
- broker/order/target_position/target_weight/quantity；
- real data pull。

## 8. Reviewer Brief

审查者重点判断：

- RSR0 是否只是 readiness；
- 输入 lineage 是否可追溯；
- 是否足以进入 RSR1 attribution diagnostic；
- 若不足，repair 是否具体；
- 是否有任何 forbidden action。

若通过，审查者应写：

```text
POLICY_RSR1_SCORE_RANK_REGIME_ATTRIBUTION_DIAGNOSTIC_WORK_CN.md
```
