# Phase R2 审查与返工建议

生成日期：2026-06-16

## 1. 审查结论

R2 暂不放行。

说明：用户提到“R3”，但本次 handoff 文件为：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_REVIEW_HANDOFF_CN.md
```

其内容是 Phase R2 config-driven replay matrix，不是 R3。

本次 R2 已完成 config-driven replay matrix 的初步实现，summary 与 daily_nav parity 显示为 pass；但 actions parity 没有按 R2 工作要求完成。当前脚本对 `actions` 直接标记 pass，并说明 baseline actions 没有 `window` column，因此用 summary counts 和 daily_nav 代替。这不满足 R2 放行条件中“active action key 完全一致”的要求。

因此，R2 必须返工，补齐可审计的 action-level parity。

## 2. 审查对象

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

Baseline：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix/
```

## 3. 已通过项

### 3.1 R2 范围基本正确

新增/修改范围集中在：

```text
configs/tw_modular_replay_matrix.yaml
scripts/run_tw_modular_config_replay_matrix.py
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_REVIEW_HANDOFF_CN.md
```

未发现前端、日更脚本、旧 formal replay matrix 的 tracked diff。

### 3.2 Config 已读取标准 signal manifest

`configs/tw_modular_replay_matrix.yaml` 指向 R1 产出的标准 `ModelSignalArtifact manifest`：

- `fresh_qlib_adaptive`
- `fresh_qlib_2025_ltr`
- `frozen_qlib_2025_ltr`
- `e4_frozen_qlib_2023_2025_ltr`
- `frozen_qlib_2018_2022`

R2 runner 读取 `candidate_rank`、`buy_score`、`full_qlib_rank` 等标准字段，未直接读取 legacy 私有 score 字段作为策略输入。

### 3.3 Summary / daily_nav parity 当前为 pass

当前 `r2_parity_audit.csv`：

```text
summary, baseline_rows=25, modular_rows=25, status=pass
daily_nav, baseline_rows=1975, modular_rows=1975, status=pass
```

执行报告中 summary rows、daily_nav rows 与 baseline `2026_ytd` 对齐。

### 3.4 基础审计文件存在

R2 输出包含：

```text
formal_replay_summary.csv
formal_replay_daily_nav.csv
formal_replay_actions.csv
formal_replay_position_snapshots.csv
formal_replay_coverage_audit.csv
formal_replay_position_integrity_audit.csv
formal_replay_forbidden_field_audit.csv
formal_replay_rule_contract.csv
formal_replay_manifest.json
r2_parity_audit.csv
```

`formal_replay_forbidden_field_audit.csv` 显示策略输入字段为标准字段：

```text
candidate_rank
buy_score
full_qlib_rank
```

## 4. 阻塞问题

### 4.1 actions parity 被跳过但标记为 pass

问题级别：高。

`scripts/run_tw_modular_config_replay_matrix.py` 的 `compare_with_baseline()` 对 actions 的逻辑是：

```text
Baseline actions lacks a window column and includes long-window frozen qlib rows.
R2 validates actions through summary active counts plus daily_nav parity; row-level action diff is advisory only.
```

然后直接将 actions check 记为 pass。

当前 `r2_parity_audit.csv`：

```text
actions, baseline_rows=23571, modular_rows=3651, status=pass,
baseline actions has no window column; action parity covered by summary counts and daily_nav
```

这不满足 R2 审查要求。R2 放行条件明确要求与旧 formal replay 在 `2026_ytd` 的 active action key 完全一致。summary counts 和 daily_nav 不能替代逐笔 action key 证明。

### 4.2 独立检查显示 baseline actions 可部分过滤，但 key 未完全对齐

我做了只读独立检查：

```text
baseline total actions rows: 23571
baseline signal_date in 2026-01-01..2026-05-07 rows: 7352
modular actions rows: 3651
```

进一步按 action key 去重比较：

```text
keys = method, rule, signal_date, execution_date, symbol, action, quantity, price, reason

baseline filtered unique keys: 5131
modular unique keys: 3651
baseline_not_modular: 1480
modular_not_baseline: 0
```

这说明 modular action keys 是当前过滤方式下 baseline 的子集，但 baseline 还有 1480 个唯一 action key 未被解释。它们可能来自 baseline actions 缺少 window column 造成的混窗，也可能是真实 action parity 缺口。无论是哪种，都不能直接标 pass，必须产出明确、可复核的过滤口径和 diff 解释。

示例缺失 key：

```text
fresh_qlib_adaptive, original, 2026-01-02, 2026-01-05, TW4971, historical_risk_reduce, 460, 305.0000, original_sell
fresh_qlib_adaptive, original, 2026-01-02, 2026-01-05, TW3260, historical_add, 500, 280.6095, original_buy
fresh_qlib_adaptive, original, 2026-01-05, 2026-01-06, TW3105, historical_risk_reduce, 760, 184.0000, original_sell
fresh_qlib_adaptive, original, 2026-01-05, 2026-01-06, TW4991, historical_add, 650, 217.5000, original_buy
fresh_qlib_adaptive, original, 2026-01-06, 2026-01-07, TW4991, historical_risk_reduce, 650, 212.5000, original_sell
```

### 4.3 Report 的 parity_status 过早标为 pass

`formal_replay_manifest.json` 当前为：

```text
parity_status: pass
gate: r2_config_driven_replay_matrix_completed
```

但 actions row-level parity 未完成。这会误导后续阶段以为 R2 已达到“完全复现旧 formal replay”的门槛。

修复前应改为：

```text
parity_status: fail
gate: r2_config_driven_replay_matrix_action_parity_incomplete
```

或等补齐 action parity 后再标 pass。

## 5. 返工要求

### 5.1 补齐 action-level parity

R2 必须新增可审计的 actions parity 文件，例如：

```text
r2_action_key_parity_audit.csv
r2_action_key_diff_sample.csv
```

至少包含：

```text
filter_policy
baseline_total_rows
baseline_filtered_rows
baseline_unique_action_keys
modular_action_rows
modular_unique_action_keys
baseline_not_modular_count
modular_not_baseline_count
duplicate_baseline_action_key_count
duplicate_modular_action_key_count
status
details
```

action key 至少包含：

```text
method
rule
signal_date
execution_date
symbol
action
quantity
price
reason
```

如 fee/tax 也需要一致，应单独加入 value parity：

```text
fee_and_tax
effective_nav_date
```

### 5.2 明确 baseline actions 的 2026_ytd 过滤口径

baseline actions 缺少 `window` column 不是跳过 parity 的理由。执行者必须选定并证明过滤口径，例如：

- 通过 baseline summary 中的 25 个 `method/rule/window=2026_ytd` 组合过滤；
- 通过 `signal_date` 与 `execution_date` 的 requested/actual window 过滤；
- 通过与 baseline daily_nav 日期集合和 method/rule 组合交叉过滤；
- 如 baseline actions 真的无法唯一归属窗口，必须输出 `baseline_action_window_ambiguity_audit.csv`，列明哪些 action 无法归属，以及为什么不会影响 replay parity 结论。

不能只写“baseline actions has no window column”并标 pass。

### 5.3 修正 parity 判定逻辑

`compare_with_baseline()` 必须：

- 对 summary 做内容比对；
- 对 daily_nav 做内容比对；
- 对 actions 做 active action key 比对；
- actions 不一致时将 `r2_parity_audit.csv` 的 actions status 标为 `fail`；
- 任一 check fail 时 manifest `parity_status` 必须为 `fail`；
- 生成 diff sample 并停止，不得写 `r2_config_driven_replay_matrix_completed` gate。

### 5.4 更新执行报告和 handoff

执行报告必须明确写出：

- baseline actions 缺少 window column 的处理方式；
- action-level parity 的行数、唯一 key 数和 diff 数；
- 若存在无法归属窗口的 baseline actions，必须作为 residual risk，而不是 pass；
- R1 `full_qlib_rank` fallback 是否影响 actions parity。

## 6. 复审清单

返工后审查者至少复核：

- `r2_parity_audit.csv` 中 summary/actions/daily_nav 均为 pass；
- `r2_action_key_parity_audit.csv` 中 `baseline_not_modular_count = 0`；
- `r2_action_key_parity_audit.csv` 中 `modular_not_baseline_count = 0`；
- 若 baseline 有重复 action key，重复原因被解释；
- `formal_replay_manifest.json.parity_status = pass` 仅在所有 parity check 通过后出现；
- 前端、日更、旧 formal replay matrix 仍无 diff；
- 不训练、不调参、不重算模型分数；
- 不触发 provider / accepted latest / monitor / broker / order。

## 7. 给执行者的返工指令

请返工 R2，不要进入 R3：

1. 修复 `scripts/run_tw_modular_config_replay_matrix.py` 的 `compare_with_baseline()`，不得跳过 actions parity。
2. 明确 baseline actions 的 `2026_ytd` 过滤口径。
3. 新增 `r2_action_key_parity_audit.csv` 和必要的 diff sample。
4. 若 action key 无法完全对齐，将 `parity_status` 标为 fail 并停止。
5. 只有 summary、actions、daily_nav 三类关键结果都可审计地完全一致，才允许写 `r2_config_driven_replay_matrix_completed`。

返工完成后，重新提交：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_REVIEW_HANDOFF_CN.md
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/r2_parity_audit.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/r2_action_key_parity_audit.csv
```
