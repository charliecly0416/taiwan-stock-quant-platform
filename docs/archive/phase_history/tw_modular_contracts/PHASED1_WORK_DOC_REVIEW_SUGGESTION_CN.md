# Phase D1 工作文档审查完善建议

生成日期：2026-06-17

## 1. 目的

本文件给审查者使用，用于完善：

```text
docs/tw_modular_contracts/PHASED0_REVIEW_AND_PHASED1_WORK_CN.md
```

当前 D0 可以收口，D1 方向正确，但 D1 工作文档需要把两个关键点升级为硬 gate：

1. `buy_rank` 的来源映射；
2. `PortfolioState` 的来源与演化方式。

如果这两点不冻结，D1 可能生成表面合格的 `OrderIntentArtifact`，但 D2/D3 无法与旧 replay parity 接上。

## 2. 建议一：冻结 `buy_rank` 映射

D1 工作文档应明确：

```text
buy_rank = score_rank
```

或更完整地定义为：

```text
buy_rank 是策略买入排序 rank，由 ModelSignalArtifact 中 buy_score 按日降序、instrument 升序 tie-break 得到；当前五规则中直接映射自 score_rank。
```

必须禁止：

- 在 builder 中临时重新排序却不审计；
- 用 `candidate_rank` 代替 `buy_rank`；
- 用 LTR 私有列或 legacy score 列重新计算 rank；
- qlib 与 LTR 使用不同 tie-break。

Validator 必须检查：

```text
order_intents.buy_rank == source_signal.score_rank
```

或检查 D1 生成的 `buy_rank` 与按 `buy_score desc, instrument asc` 复算结果一致。

## 3. 建议二：冻结 `PortfolioState` 来源

D1 工作文档必须回答：

```text
StrategyDecisionEngine 在生成意图时，当前持仓从哪里来？
```

建议按 D1/D2 分层冻结：

### 3.1 D1 最小范围

D1 只允许生成两类产物：

1. 单日 latest / sample intent；
2. 基于 legacy replay snapshots 的样例 intent。

D1 不应尝试完整替代 replay loop，也不应自己演化现金、价格、成交和持仓。

如果 D1 生成全窗口样例 intent，`PortfolioState` 必须来自：

```text
legacy replay position snapshots
```

并在 manifest 中记录：

```text
portfolio_state_source: legacy_replay_snapshot_for_d1_sample_only
not_d2_replay_execution_source: true
```

### 3.2 D2/D3 正式方式

D2/D3 正式拆分时，`PortfolioState` 应由 `ReplayExecutionEngine` 在每日执行完 pending intents、更新持仓后传给 `StrategyDecisionEngine`。

标准流程应为：

```text
ReplayExecutionEngine maintains portfolio state
  -> calls StrategyDecisionEngine for signal_date
  -> receives OrderIntent rows
  -> schedules next-day execution
```

这样才能和旧 replay 的持仓、pending order、现金、next-day execution 语义保持一致。

D1 不得把 readonly snapshot 的 `hold_candidates` 当作 canonical portfolio state。

## 4. 建议三：D1 输出必须标注样例性质

如果 D1 生成 order intent artifact，但尚未由 D2 replay engine 消费，manifest 必须明确：

```text
artifact_stage: d1_decision_sample
not_used_for_replay_result: true
not_parity_evidence: true
```

D1 报告不得宣称：

- replay 已解耦；
- 收益已复现；
- parity 已完成；
- 可以替代旧 replay。

D1 只能宣称：

```text
StrategyDecisionEngine can emit contract-valid OrderIntentArtifact.
```

## 5. 建议四：D1 Validator 增补项

D1 validator 除现有检查外，建议增加：

- `buy_rank` 映射检查；
- `portfolio_state_source` 存在；
- 若 source 是 legacy snapshot，必须标记 sample-only；
- `OrderIntentArtifact` 不含 execution/accounting 字段；
- `diagnostic_only` 规则不能输出 valid strategy evidence；
- 每日 buy/sell intent count 不超过策略配置；
- `hold` / `skip` 是否按规则可解释。

## 6. 建议五：D1 审查硬 Gate

审查者应把以下设为 D1 放行条件：

```text
buy_rank_mapping_defined == true
buy_rank_mapping_validated == true
portfolio_state_source_defined == true
readonly_snapshot_not_portfolio_state == true
d1_artifact_marked_sample_if_not_replay_consumed == true
no_replay_execution_change == true
no_parity_claim_in_d1 == true
```

任一失败，不得进入 D2。

## 7. 给审查者的 Prompt

请审查并完善：

```text
docs/tw_modular_contracts/PHASED0_REVIEW_AND_PHASED1_WORK_CN.md
```

重点把以下两项加入 D1 硬 gate：

1. `buy_rank` 必须明确定义为 `score_rank` 或按 `buy_score desc, instrument asc` 复算，并由 validator 检查；
2. `PortfolioState` 必须明确来源。D1 样例可以来自 legacy replay snapshots，但必须标记 sample-only；D2/D3 正式拆分时，应由 ReplayExecutionEngine 维护并传入 StrategyDecisionEngine。不得把 readonly snapshot 的 `hold_candidates` 当作 canonical state。

同时要求 D1 artifact 若未被新 replay engine 消费，必须标记：

```text
not_used_for_replay_result: true
not_parity_evidence: true
```

D1 不得宣称 replay 解耦完成或 parity 完成。
