# Phase X1R Paper Decision Preview Repair 执行报告

生成日期：2026-06-18

## 1. 修复范围

本轮按 `docs/tw_modular_daily_update_productization/PHASEX1_REVIEW_AND_PHASEX1R_WORK_CN.md` 执行 X1R。

X1R 仍然是 readonly repair。本轮未执行：

```text
写 qd_tw_sim_accounts
写 qd_tw_sim_positions
写 qd_tw_sim_orders
写 qd_tw_sim_trades
新增 apply-decision 写接口
新增 reset 写接口
重置模拟账户
应用策略到模拟账户
调用 /api/agent/v1/quick-trade/**
连接 broker
创建真实 orders
provider publish
provider accepted latest / qlib accepted latest switch
monitor config / scan / alerts writes
训练 / 调参 / 替换模型
Agent tool/action expansion
```

## 2. 修复点说明

修复文件：

```text
scripts/build_tw_paper_portfolio_decision_artifact.py
backend/tests/test_build_tw_paper_portfolio_decision_artifact.py
```

核心修复：

```text
修复前：先用 sells 释放仓位槽位，再计算 buy slot。
修复后：先生成 sell preview 并判断 applicability，只有 applicable sell 才加入 applicable_sells。
       remaining = held_set - applicable_sells。
       open_slots 基于真实 remaining holdings 计算。
```

修复后规则：

```text
unavailable sell 不释放仓位槽位
unavailable sell 不增加 cash preview
unavailable sell 不触发由该 sell 释放出来的 buy
applicable sell 仍释放槽位，并允许后续 buy preview
```

## 3. 修复前问题复现说明

X1 原逻辑：

```text
sells = outside[:max_sell]
remaining = held_set - set(sells)
open_slots = target_holding_count - len(remaining)
```

问题场景：

```text
当前模拟账户只持有 1 个标的 TW9999
target_holding_count = 1
TW9999 不在 top50 candidate_set
TW9999 缺少 reference price，paper_sell_intent applicability=unavailable
```

修复前会把 TW9999 从 remaining 移除，错误得到：

```text
remaining = empty
open_slots = 1
可能继续生成 paper_buy_intent
```

这等价于假设不可应用卖出已经执行，违反 X1 preview 语义。

## 4. 修复后 artifact 示例

修复后示例产物：

```text
data_tw/artifacts/paper_portfolio/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/x1r_readonly_fixture_repaired_20260618/manifest.json
```

命令：

```text
python scripts/build_tw_paper_portfolio_decision_artifact.py \
  --paper-account-json tests/fixtures/tw_paper_portfolio_x1_account.json \
  --model-signal data_tw/artifacts/daily_model_signals/e4_frozen_qlib_2023_2025_ltr/u3_readonly_daily_demo_success_signal/manifest.json \
  --signal-asof 2026-03-27 \
  --run-id x1r_readonly_fixture_repaired_20260618 \
  --json
```

结果：

```text
decision_id = paper_decision_7f354aff9e76b7c9
paper_sell_intent = 1
paper_buy_intent = 1
paper_skip = 0
readonly_only = true
not_applied = true
no_broker_order = true
no_quick_trade = true
```

该示例中：

```text
paper_sell_intent TW9999 applicability=applicable
paper_buy_intent  TW6683 applicability=unavailable reason=missing_reference_price
cash_after_preview 只包含 applicable sell 的现金变化
```

这证明 applicable sell 仍正常释放槽位，missing buy price 只输出 unavailable buy preview，不写账户。

## 5. unavailable sell 不释放 slot 的测试证据

新增测试：

```text
test_unavailable_sell_does_not_release_slot_or_trigger_buy
```

测试输入：

```text
target_holding_count = 1
当前持仓 = TW9999
TW9999 不在 candidate_set
TW9999 缺 reference price
buy candidate TW1111 有 reference price
```

修复后断言：

```text
paper_sell_intent = 1
paper_sell_intent.applicability = unavailable
paper_buy_intent = 0
cash_after_preview = cash_before
forbidden actions 全 false
```

这覆盖了：

```text
unavailable sell 不释放 slot
missing sell price 时不产生由该 sell 释放出来的 buy
unavailable sell 不增加 cash preview
```

## 6. 其他测试覆盖

新增 / 扩展测试：

```text
test_missing_buy_price_outputs_unavailable_buy_preview
test_empty_signal_rows_keep_sell_only_semantics
test_db_loader_and_price_fill_execute_select_only
```

覆盖：

```text
missing buy price 只输出 unavailable buy preview，不写账户
empty signal rows 的 sell-only 语义稳定
mock DB connection / cursor 断言 DB 模式只执行 SELECT
forbidden_action_audit 所有写动作仍为 false
```

## 7. DB readonly / no-write 证据

新增 mock DB 测试：

```text
test_db_loader_and_price_fill_execute_select_only
```

测试方式：

```text
monkeypatch app.utils.db.get_db_connection
FakeCursor.execute 记录 SQL 首 token
若 SQL 首 token 不是 SELECT，测试立即失败
覆盖 load_account_state_from_db
覆盖 fill_missing_prices_from_db
```

断言：

```text
set(executed_verbs) == {"SELECT"}
```

该测试证明 X1 builder 的 DB 读取路径不执行：

```text
INSERT
UPDATE
DELETE
CREATE
ALTER
DROP
TRUNCATE
```

## 8. forbidden_action_audit 结果

修复后示例产物：

```text
data_tw/artifacts/paper_portfolio/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/x1r_readonly_fixture_repaired_20260618/forbidden_action_audit.json
```

结果：

```text
status = pass
sim_account_write = false
paper_order_write = false
paper_execution_write = false
reset = false
broker_order = false
quick_trade = false
real_order = false
provider_publish = false
provider_accepted_latest_switch = false
qlib_accepted_latest_switch = false
monitor_write = false
monitor_scan = false
agent_tool_action_expansion = false
training = false
tuning = false
```

## 9. 必跑验证

已执行：

```text
python -m py_compile scripts/build_tw_paper_portfolio_decision_artifact.py
python -m pytest backend/tests/test_build_tw_paper_portfolio_decision_artifact.py -q
```

结果：

```text
6 passed
```

说明：本轮 `apply_patch` 在当前 sandbox 下多次失败，报错为：

```text
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

因此源码和测试修复使用 escalated 本地文件编辑命令完成。该操作仅修改工作区内 X1R 允许文件，不访问网络，不触发账户写入。

## 10. 是否可以进入 X2

X1R 修复项已完成，可以进入 X2 的设计/实现审查准备，但不能跳过 X2 独立合同。

进入 X2 前仍必须单独冻结并实现：

```text
paper_account_epoch
apply_runs 幂等存储
reset_runs 与 archive snapshot
PaperAuditLogArtifact
same-day apply guard
realized_paper_pnl
lot_size 最终口径
X2 API network denylist
```

X1R 不包含任何 apply/reset 写账户实现。
