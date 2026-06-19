# Phase R0 返工修复审查说明

生成日期：2026-06-16

## 1. 本次修复目标

根据 `PHASER0_REVIEW_AND_R1_WORK_CN.md` 的审查意见，仅修复 R0，不进入 R1。

修复目标：

- 从 R0 变更集中移除前端改动；
- 从 R0 变更集中移除日更脚本改动；
- 补齐 `ReplayResultArtifact` 必需审计产物；
- 更新 R0 执行报告，使其与当前 diff 一致。

## 2. 修改文件

本次 R0 返工后，供审查的文件为：

```text
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER0_MINIMAL_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER0_REPAIR_REVIEW_HANDOFF_CN.md
```

R0 原始四份合同仍为：

```text
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
```

## 3. 已移除的越界改动

审查意见指出以下文件不应出现在 R0 变更集中：

```text
frontend/src/views/tw-stock-monitor/index.vue
scripts/run_daily_tw_stock_auto_update.py
```

本次已将这两个文件恢复到 HEAD 状态。R0 当前不包含前端、日更、provider、accepted latest、monitor、broker 或 order 相关代码改动。

审查者可用以下命令复核：

```bash
git status --short frontend/src/views/tw-stock-monitor/index.vue scripts/run_daily_tw_stock_auto_update.py
git diff -- frontend/src/views/tw-stock-monitor/index.vue scripts/run_daily_tw_stock_auto_update.py
```

预期结果：

- `git status --short` 不显示上述两个文件；
- `git diff` 为空。

## 4. ReplayResult 合同修复

已在 `REPLAY_RESULT_CONTRACT_CN.md` 中将以下文件纳入必需输出：

```text
coverage_audit.csv
position_integrity_audit.csv
forbidden_field_audit.csv
```

同时保留：

```text
execution_audit.csv
forbidden_action_audit.json
```

新增/明确的审计内容：

- `coverage_audit.csv` required fields；
- `position_integrity_audit.csv` required fields；
- `forbidden_field_audit.csv` required fields；
- actual window 不得越过 requested window；
- active action quantity > 0；
- `execution_date > signal_date`；
- `max_holding_count <= target_holding_count`；
- duplicate position 为 0；
- future label / return 不得进入 ranking；
- final holdings 必须 mark-to-market；
- `one_sell_one_buy_buggy_e8r` 只能作为 diagnostic result。

审查者可用以下命令复核：

```bash
rg -n "coverage_audit.csv|position_integrity_audit.csv|forbidden_field_audit.csv|actual_start_date|final holdings|diagnostic result" docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
```

## 5. 执行报告修复

已更新 `PHASER0_MINIMAL_CONTRACT_EXECUTION_REPORT_CN.md`：

- 明确当前 R0 变更集仅包含合同文档和执行报告；
- 记录前端与日更脚本改动已从 R0 变更集中移除；
- 记录 ReplayResult contract 已补齐三类必需 audit；
- 保持禁止事项声明：未训练、未调参、未重跑收益筛选、未修改默认策略、未触发 provider / accepted latest / monitor / broker / order。

审查者可用以下命令复核：

```bash
rg -n "R0 审查修复记录|前端与日更脚本改动已从 R0|coverage_audit.csv|position_integrity_audit.csv|forbidden_field_audit.csv" docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER0_MINIMAL_CONTRACT_EXECUTION_REPORT_CN.md
```

## 6. 未执行事项

本次未执行：

- R1 legacy signal adapter；
- R2 config-driven replay matrix；
- 模型训练；
- 模型调参；
- 分数重算；
- 收益筛选；
- 前端展示接入；
- 日更 orchestrator 接入；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker、quick-trade 或 order。

## 7. 建议审查结论口径

若审查者确认：

- 四份 R0 contract 仍存在；
- ReplayResult 必需输出已包含三类 audit；
- 前端和日更脚本不再有 diff；
- 执行报告与当前 diff 一致；
- `buggy_e8r` 仍为 diagnostic only；

则 R0 可进入复审通过状态，并由审查者单独决定是否放行 R1。
