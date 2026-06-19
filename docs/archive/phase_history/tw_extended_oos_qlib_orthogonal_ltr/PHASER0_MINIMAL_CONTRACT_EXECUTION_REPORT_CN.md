# Phase R0 最小合同冻结执行报告

生成日期：2026-06-16

## 1. 执行范围

本次仅执行 Phase R0：冻结研究/回放链路最小模块化 contract。

新增产物：

```text
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
```

本次未执行 R1/R2，未新增 adapter，未改 replay matrix。

## 2. 合同覆盖

| contract | required fields | forbidden fields/actions | candidate/buy/full rank 语义 | qlib/LTR 映射 | buggy_e8r 边界 |
| --- | --- | --- | --- | --- | --- |
| ModelSignalArtifact | 已定义 | 已定义 | 已定义 | 已定义 | 不作为 signal 策略证据入口 |
| StrategyRuleContract | 已定义 | 已定义 | 已定义 | 已定义 | diagnostic only |
| OrderIntentArtifact | 已定义 | 已定义 | 已引用 | 已通过标准字段约束 | diagnostic only，必须标记 |
| ReplayResultArtifact | 已定义，且必需输出已包含 coverage / position integrity / forbidden field audit | 已定义 | 已通过输入约束冻结 | 已禁止 legacy 私有列 | diagnostic only，summary 必须标记 |

## 3. 关键冻结语义

`candidate_rank`：

- 只决定 qlib top50 universe / exit boundary；
- `candidate_rank <= 50` 才进入策略候选池；
- LTR 不得静默替换该边界。

`buy_score`：

- 只决定 top50 内买入排序；
- qlib 可来自 qlib score 或受控 adaptive score；
- LTR 来自 LTR rerank score。

`full_qlib_rank`：

- 表示完整 qlib 截面排名；
- 用于持仓跌出 top50 后判断最差持仓；
- 不得由 LTR rank 替代。

## 4. qlib / LTR 统一信号

纯 qlib：

```text
candidate_rank <- qlib rank
buy_score <- qlib score 或 qlib-derived adaptive score
raw_score <- qlib 原始 score
full_qlib_rank <- 完整 qlib rank
```

LTR：

```text
candidate_rank <- 底座 qlib rank
buy_score <- LTR rerank score
raw_score <- LTR 原始 score
full_qlib_rank <- 底座完整 qlib rank
```

策略和回放只能读取标准字段，不得读取 legacy 私有列。

## 5. buggy_e8r 冻结结论

`one_sell_one_buy_buggy_e8r` 已在合同中固定为：

```text
diagnostic only
not_valid_strategy_evidence
```

它只能用于历史 bug 复现、异常归因和审计，不得用于：

- 默认策略；
- 策略收益证据；
- 收益筛选；
- 产品展示；
- 日更 publish。

## 6. 禁止事项执行记录

根据 R0 修复后的当前 diff，本次 R0 变更集仅包含合同文档和执行报告；审查中指出的前端与日更脚本改动已从 R0 变更集中移除。

本次 R0：

- 未训练模型；
- 未调参；
- 未重跑收益筛选；
- 未生成策略收益结论；
- 未修改前端；
- 未修改日更脚本；
- 未修改默认策略；
- 未触发 provider publish；
- 未切换 accepted latest；
- 未触发 monitor scan/config save；
- 未触发 broker、quick-trade 或 order。

## 7. R0 审查修复记录

已按 `PHASER0_REVIEW_AND_R1_WORK_CN.md` 完成以下修复：

- 移除 R0 变更集中的 `frontend/src/views/tw-stock-monitor/index.vue` 改动；
- 移除 R0 变更集中的 `scripts/run_daily_tw_stock_auto_update.py` 改动；
- `REPLAY_RESULT_CONTRACT_CN.md` 已将 `coverage_audit.csv`、`position_integrity_audit.csv`、`forbidden_field_audit.csv` 纳入必需输出；
- ReplayResult contract 已补齐 coverage / position integrity / forbidden field audit 的 required fields 和最小检查项；
- 禁止事项记录已更新为与当前 R0 diff 一致。

## 8. 后续入口

R0 审查通过后，下一步才可进入 R1：

```text
legacy replay-ready CSV
  -> legacy signal adapter
  -> standard ModelSignalArtifact
```

R1 必须证明 row count、duplicate key、candidate_rank、buy_score、full_qlib_rank、top50 coverage 与旧产物一致，且不改变任何 score 或排序。
