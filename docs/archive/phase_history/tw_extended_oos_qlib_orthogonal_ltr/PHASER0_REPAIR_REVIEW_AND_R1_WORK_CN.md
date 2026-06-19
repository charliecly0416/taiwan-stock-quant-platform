# Phase R0 返工复审与 R1 工作建议

生成日期：2026-06-16

## 1. 复审结论

R0 返工复审通过，允许进入 R1。

本次复审确认：

- 前端改动已从 R0 变更集中移除；
- 日更脚本改动已从 R0 变更集中移除；
- 四份 R0 contract 仍存在；
- `REPLAY_RESULT_CONTRACT_CN.md` 已补齐 `coverage_audit.csv`、`position_integrity_audit.csv`、`forbidden_field_audit.csv` 三类必需审计产物；
- R0 执行报告已更新为与当前 diff 一致；
- `one_sell_one_buy_buggy_e8r` 仍被限定为 diagnostic only。

因此，R0 可视为完成。下一步可以进入 R1 legacy signal adapter，但 R1 仍必须严格限制在只读研究/回放链路，不得提前接入前端、日更或生产链路。

## 2. 复审对象

返工 handoff：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER0_REPAIR_REVIEW_HANDOFF_CN.md
```

R0 执行报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER0_MINIMAL_CONTRACT_EXECUTION_REPORT_CN.md
```

R0 contract：

```text
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
```

越界改动复核对象：

```text
frontend/src/views/tw-stock-monitor/index.vue
scripts/run_daily_tw_stock_auto_update.py
```

## 3. 复审确认

### 3.1 前端与日更改动已移除

复核命令：

```bash
git status --short frontend/src/views/tw-stock-monitor/index.vue scripts/run_daily_tw_stock_auto_update.py
git diff -- frontend/src/views/tw-stock-monitor/index.vue scripts/run_daily_tw_stock_auto_update.py
```

复核结果：

- `git status --short` 未显示上述两个文件；
- `git diff` 为空。

结论：R0 当前不再包含前端或日更脚本改动。

### 3.2 ReplayResult contract 已补齐必需审计产物

`docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md` 的必需文件已包含：

```text
manifest.json
summary.csv
actions.csv
daily_nav.csv
position_snapshots.csv
coverage_audit.csv
position_integrity_audit.csv
forbidden_field_audit.csv
execution_audit.csv
forbidden_action_audit.json
```

其中 `coverage_audit.csv` 已定义：

- required fields；
- `actual_start_date >= requested_start_date`；
- `actual_end_date <= requested_end_date`；
- 回放窗口不得越过请求窗口；
- signal / price 覆盖可追溯；
- 缺失 signal / price 必须有 skip 或 audit。

`position_integrity_audit.csv` 已定义：

- required fields；
- active action quantity > 0；
- `execution_date > signal_date`；
- `max_holding_count <= target_holding_count`；
- duplicate position day/instrument 为 0；
- final holdings mark-to-market。

`forbidden_field_audit.csv` 已定义：

- required fields；
- future label / future return 字段不存在；
- forbidden model/private 字段未被 ReplayExecution 读取；
- realized PnL、成交结果、持仓字段未参与策略 ranking；
- `one_sell_one_buy_buggy_e8r` 只能标记为 diagnostic result。

结论：ReplayResult contract 已与 R0-R2 工作文档的必需审计闭环对齐。

### 3.3 执行报告已与当前 diff 对齐

`PHASER0_MINIMAL_CONTRACT_EXECUTION_REPORT_CN.md` 已补充 R0 审查修复记录：

- 前端与日更脚本改动已从 R0 变更集中移除；
- ReplayResult contract 已补齐三类必需 audit；
- 当前 R0 变更集仅包含合同文档和执行报告；
- 禁止事项记录仍声明未训练、未调参、未重跑收益筛选、未改默认策略、未触发 provider / accepted latest / monitor / broker / order。

结论：执行报告与本次复审观察一致。

## 4. 残余风险

当前工作区仍存在大量未跟踪历史文档和脚本，但本次 R0 复审只针对 R0 contract、R0 执行报告和明确的越界改动修复。

R1 执行者不得把这些历史未跟踪文件混入 R1 结论。R1 报告必须明确列出 R1 新增/修改的文件和 artifact，并与 R0 产物区分。

## 5. R1 工作范围

R1 目标：

```text
legacy replay-ready CSV / score artifact
  -> legacy signal adapter
  -> standard ModelSignalArtifact
```

R1 至少支持以下模型信号：

- `fresh_qlib_adaptive`
- `fresh_qlib_2025_ltr`
- `frozen_qlib_2025_ltr`
- `e4_frozen_qlib_2023_2025_ltr`
- `frozen_qlib_2018_2022`

R1 输出目录：

```text
data_tw/artifacts/signals/{model_name}/{run_id}/
```

每个模型必须输出：

```text
manifest.json
signals.csv
schema.json
coverage_audit.csv
forbidden_field_audit.csv
legacy_mapping_audit.csv
```

R1 执行报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER1_LEGACY_SIGNAL_ADAPTER_EXECUTION_REPORT_CN.md
```

## 6. R1 必须证明

每个 `ModelSignalArtifact` 必须证明：

- required fields 全部存在；
- `date + instrument` duplicate key 为 0；
- row count 与旧产物对齐；
- `candidate_rank` 与旧 qlib candidate rank 对齐；
- `buy_score` 与旧指定 score 对齐；
- `full_qlib_rank` 与旧完整 qlib rank 对齐；
- `score_rank` 由 `buy_score` 日内降序稳定生成；
- LTR 的 `candidate_rank` 仍来自底座 qlib，而不是 LTR rank；
- forbidden fields 不进入 `signals.csv`；
- adapter 不改变 score；
- adapter 不改变排序；
- adapter 不改变 universe；
- adapter 不训练、不调参、不重算模型分数。

## 7. R1 禁止事项

R1 禁止：

- 训练 qlib 或 LTR；
- 调参；
- 重算模型分数；
- 根据收益筛选模型；
- 产生新的策略收益结论；
- 改 replay rule；
- 改 formal replay matrix；
- 改默认策略；
- 修改前端；
- 修改日更脚本；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker、quick-trade 或 order 行为。

## 8. 给执行者的 R1 指令

请在 R0 复审通过的基础上执行 Phase R1：新增 legacy signal adapter，把现有 fresh qlib、fresh+2025 LTR、frozen+2025 LTR、E4 LTR、frozen qlib 2018-2022 的旧 replay-ready/score 产物转换为标准 `ModelSignalArtifact`。

输出到：

```text
data_tw/artifacts/signals/{model_name}/{run_id}/
```

每个模型必须有：

```text
manifest.json
signals.csv
schema.json
coverage_audit.csv
forbidden_field_audit.csv
legacy_mapping_audit.csv
```

必须证明 row count、date/instrument key、candidate_rank、buy_score、full_qlib_rank 与旧产物对齐，且不改变 score、不改变排序、不训练、不重算、不产生策略收益结论。

执行报告写到：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER1_LEGACY_SIGNAL_ADAPTER_EXECUTION_REPORT_CN.md
```
