# Phase R2 返工复审与 R3 工作建议

生成日期：2026-06-16

## 1. 复审结论

R2 返工复审通过，允许进入 R3。

本次确认：

- R2 config-driven replay matrix 可复跑；
- summary parity 通过；
- daily_nav parity 通过；
- action-level key/value parity 已补齐并通过；
- `formal_replay_manifest.json.parity_status = pass`；
- 未发现前端、日更脚本、旧 formal replay matrix 的 tracked diff；
- R2 仍未触发训练、调参、provider publish、accepted latest、monitor、broker 或 order。

R2 已完成最小闭环：

```text
legacy replay-ready / score
  -> R1 ModelSignalArtifact
  -> R2 YAML config
  -> config-driven replay matrix
  -> 与旧 formal replay matrix 的 2026_ytd 关键结果完全一致
```

## 2. 复审对象

R2 handoff：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_REVIEW_HANDOFF_CN.md
```

R2 执行报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_EXECUTION_REPORT_CN.md
```

R2 config：

```text
configs/tw_modular_replay_matrix.yaml
```

R2 runner：

```text
scripts/run_tw_modular_config_replay_matrix.py
```

R2 输出：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/
```

## 3. 复核结果

### 3.1 R2 可复跑

复核命令：

```bash
python scripts/run_tw_modular_config_replay_matrix.py --config configs/tw_modular_replay_matrix.yaml
```

复核结果：

```text
ok: true
parity_status: pass
summary: pass
daily_nav: pass
actions: pass
```

### 3.2 Summary / Daily NAV / Actions 全部对齐

当前 `r2_parity_audit.csv`：

```text
summary, baseline_rows=25, modular_rows=25, status=pass
daily_nav, baseline_rows=1975, modular_rows=1975, status=pass
actions, baseline_rows=3651, modular_rows=3651, status=pass
```

独立复核结果：

```text
summary equal: True
nav equal: True
```

### 3.3 Action-level parity 已补齐

当前 `r2_action_key_parity_audit.csv`：

```text
filter_policy: baseline_actions_prefix_by_2026_ytd_summary_action_plus_skipped_count
baseline_total_rows: 23571
baseline_filtered_rows: 3651
baseline_unique_action_keys: 3651
modular_action_rows: 3651
modular_unique_action_keys: 3651
baseline_not_modular_count: 0
modular_not_baseline_count: 0
duplicate_baseline_action_key_count: 0
duplicate_modular_action_key_count: 0
value_mismatch_count: 0
status: pass
```

独立复核结果：

```text
N: 3651
baseline prefix rows: 3651
modular rows: 3651
key duplicate baseline/modular: 0 / 0
key set baseline/modular: 3651 / 3651
both: 3651
left_only: 0
right_only: 0
fee mismatch: 0
effective_nav_date mismatch: 0
```

### 3.4 Baseline action 过滤口径有代码依据

旧 formal replay runner 默认 window 顺序为：

```text
2026_ytd,2023,2024,2025,2023_2026_ytd
```

旧 runner 按 window 外层循环写出 `formal_replay_actions.csv`，因此 baseline actions 前 N 行可作为 `2026_ytd` action universe。N 由 baseline summary 中 `window=2026_ytd` 的：

```text
sum(action_count + skipped_trade_count)
```

计算得到。

本次 N 为 3651，与 modular actions 行数一致，并且 key/value 完全一致。

### 3.5 禁止事项复核

未发现以下文件有 tracked diff：

```text
frontend/src/views/tw-stock-monitor/index.vue
scripts/run_daily_tw_stock_auto_update.py
scripts/run_extended_oos_formal_replay_matrix.py
```

说明：

- `scripts/run_extended_oos_formal_replay_matrix.py` 在当前工作区仍显示为既有未跟踪文件；
- 本次 R2 复审以 `git diff` 为空确认没有对旧 formal replay matrix 做 tracked 修改。

`formal_replay_forbidden_field_audit.csv` 显示 R2 使用：

```text
candidate_rank
buy_score
full_qlib_rank
```

未发现 forbidden columns 被用于 ranking。

## 4. 残余风险

### 4.1 baseline actions prefix 口径依赖旧 runner 顺序

本次已经确认旧 runner 默认 window 顺序和写出顺序支持 prefix 口径。但该口径仍依赖旧 runner 的生成顺序约定，而不是 baseline actions 自带 `window` column。

建议后续保留：

```text
r2_action_key_parity_audit.csv
```

并在 R3/R4 中考虑给 replay actions 增加 `window` 字段，避免后续再依赖 prefix 推断。

### 4.2 R1 full_rank fallback 仍是已知风险

R1 中：

- `fresh_qlib_adaptive` 有 8017 行 `full_qlib_rank` fallback；
- `fresh_qlib_2025_ltr` 有 675 行 `full_qlib_rank` fallback。

R2 结果与旧 formal replay 完全一致，因此该 fallback 未破坏旧结果复现。但后续若新增策略强依赖完整 qlib rank，应优先补齐 full-rank primary source，而不是扩大 fallback 使用。

## 5. R3 建议方向

R0-R2 已完成最小复现闭环。R3 不应继续扩大旧脚本堆叠，而应进入可扩展 contract 机制设计。

建议 R3 主题：

```text
Extensible Contract / Capability / Plugin Registry Design
```

目标：

- 不破坏 R0-R2 已复现的旧结果；
- 支持未来更多模型、策略、信号字段和 replay 输出；
- 保持 strict core contract，同时允许受控 extension；
- 所有 extension 必须通过 manifest capability 和 schema 声明；
- 策略必须声明自身依赖，validator 检查 signal artifact 是否满足依赖。

## 6. R3 工作范围

R3 只做设计文档和最小 validator skeleton，不接入生产链路。

建议产出：

```text
docs/tw_modular_contracts/EXTENSIBLE_CONTRACT_CAPABILITY_DESIGN_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/STRATEGY_DEPENDENCY_CONTRACT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER3_EXTENSIBLE_CONTRACT_DESIGN_EXECUTION_REPORT_CN.md
```

如需要新增代码，只允许新增只读 validator skeleton，例如：

```text
scripts/validate_tw_modular_artifact_contract.py
```

不得改 R2 replay 结果，不得改旧 formal replay matrix。

## 7. R3 必须设计的问题

R3 至少回答：

1. 哪些字段是 immutable core fields？
2. 哪些字段可以作为 optional extension fields？
3. extension fields 如何在 manifest 中声明 schema？
4. model artifact 如何声明 capabilities？
5. strategy rule 如何声明 required / optional signal dependencies？
6. validator 如何判断某个 strategy 是否可以消费某个 signal artifact？
7. forbidden fields/actions 如何继续全局强制？
8. 如何避免策略直接读取 legacy 私有列？
9. 如何处理不同 horizon、risk score、sector exposure、ensemble score 等扩展输入？
10. ReplayResult 是否需要 action/window/schema version 等更强审计字段？

## 8. R3 禁止事项

R3 禁止：

- 训练 qlib 或 LTR；
- 调参；
- 重算模型分数；
- 根据收益筛选模型；
- 修改 R2 replay 输出；
- 修改旧 formal replay matrix；
- 修改默认策略；
- 修改前端；
- 修改日更脚本；
- provider publish；
- accepted latest 切换；
- monitor scan/config save；
- broker、quick-trade 或 order 行为。

## 9. 给执行者的 R3 指令

请在 R2 审查通过后执行 R3：设计可扩展 contract / capability / strategy dependency 机制。

只做文档和可选只读 validator skeleton，不改 replay 结果、不改前端、不改日更、不接入生产链路。

必须保持 R0-R2 旧结果复现闭环不变，并解释未来新增模型/策略如何通过：

```text
core fields
extension schema
capabilities
strategy dependencies
validator
```

受控接入。
