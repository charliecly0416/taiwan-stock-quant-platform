# Phase X1 审查与 X1R 修复工作文档

生成日期：2026-06-18

## 1. 审查结论

X1 已完成只读 paper decision builder 的主体能力：

```text
读取模拟持仓
读取 readonly model signal
读取 top50_exit_one_worst_sell 策略配置
生成 PaperPortfolioStateArtifact
生成 PaperOrderIntentArtifact
生成 PaperApplyPreviewArtifact
生成 forbidden_action_audit
```

X1 没有证据显示写入 `qd_tw_sim_*`、调用 quick-trade、连接 broker、触发真实订单、provider latest、monitor 或 Agent 扩权。

但 X1 不能直接进入 X2。进入 X2 前必须先做 X1R 小修复。

## 2. 必须修复的问题

### 2.1 不可应用卖出不得释放仓位槽位

当前 `scripts/build_tw_paper_portfolio_decision_artifact.py` 在计算买入空间时，先把待卖标的从 `remaining` 移除：

```text
sells = outside[:max_sell]
remaining = held_set - set(sells)
open_slots = target_holding_count - len(remaining)
```

问题是：如果某个 sell 因价格缺失、数量异常等原因被标记为：

```text
applicability = unavailable
```

preview 不应假设它已经卖出，也不应因此释放仓位槽位或触发后续 buy slot。

X1R 必须改成：

```text
只有 applicable 的 paper_sell_intent 才释放仓位槽位。
unavailable sell 不改变 remaining holdings。
unavailable sell 不增加 open_slots。
unavailable sell 不增加 cash preview。
```

### 2.2 补正式测试覆盖

必须新增或扩展测试覆盖：

```text
sell unavailable 不释放 slot
missing sell price 时不产生由该 sell 释放出来的 buy
missing buy price 只输出 unavailable buy preview，不写账户
empty signal rows 的 sell-only 语义稳定
forbidden_action_audit 所有写动作仍为 false
```

### 2.3 补 DB readonly / no-write 证据

X1 报告称 DB 模式只执行 `SELECT`，不调用 `ensure_schema()`，但测试主要覆盖 fixture。

X1R 至少要补一种 no-write 证据：

```text
mock connection / cursor 断言没有 INSERT / UPDATE / DELETE / CREATE / ALTER
或新增审计脚本扫描 builder DB SQL，只允许 SELECT
或 DB readonly smoke，配合 forbidden_action_audit 证明没有写 qd_tw_sim_* 表
```

优先建议用 mock cursor 单测，避免真实 DB 依赖。

## 3. X1R 执行范围

允许修改：

```text
scripts/build_tw_paper_portfolio_decision_artifact.py
backend/tests/test_build_tw_paper_portfolio_decision_artifact.py
docs/tw_modular_daily_update_productization/PHASEX1R_PAPER_DECISION_PREVIEW_REPAIR_EXECUTION_REPORT_CN.md
```

如需新增只读 validator / audit 脚本，也可以新增：

```text
scripts/validate_tw_paper_portfolio_decision_artifact.py
```

但 X1R 不要求实现 X2 API。

## 4. 禁止事项

X1R 仍然是 readonly repair，不得：

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

## 5. 修复后验收标准

X1R 通过必须满足：

```text
unavailable sell 不释放仓位槽位
unavailable sell 不触发额外 buy slot
applicable sell 仍正常释放槽位并允许 buy preview
missing buy price 正确标记 unavailable
PaperPortfolioStateArtifact / PaperOrderIntentArtifact / PaperApplyPreviewArtifact schema 不倒退
forbidden_action_audit.status = pass
所有 forbidden actions = false
单元测试通过
py_compile 通过
```

## 6. 必跑验证

执行者必须运行：

```text
python -m py_compile scripts/build_tw_paper_portfolio_decision_artifact.py
python -m pytest backend/tests/test_build_tw_paper_portfolio_decision_artifact.py -q
```

如果新增 validator，则还必须运行 validator 的 golden / fixture 测试。

## 7. 交付物

X1R 完成后必须提交：

```text
docs/tw_modular_daily_update_productization/PHASEX1R_PAPER_DECISION_PREVIEW_REPAIR_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
1. 修复点说明
2. 修复前问题复现说明
3. 修复后 artifact 示例
4. unavailable sell 不释放 slot 的测试证据
5. DB readonly / no-write 证据
6. forbidden_action_audit 结果
7. 是否可以进入 X2 的判断
```

## 8. 是否进入 X2

X1R 通过后，才可以考虑进入 X2。

即使 X1R 通过，X2 仍必须单独冻结并实现：

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

不得把 X1R 修复扩大成 X2 写账户实现。
