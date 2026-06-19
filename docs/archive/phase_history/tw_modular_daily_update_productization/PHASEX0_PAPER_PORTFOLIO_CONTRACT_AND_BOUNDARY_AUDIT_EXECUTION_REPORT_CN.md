# Phase X0 Paper Account 合同与安全边界审计执行文档

生成日期：2026-06-18

## 1. 本轮目标

X0 只做审计和合同冻结，不实现功能。

执行者必须回答：

```text
模拟账户从哪里读
纸面订单 / 纸面成交写到哪里
如何保证只写 paper path
如何保证 apply/reset 幂等
如何定义 paper accounting
如何 reset 并归档旧状态
```

本轮不得：

```text
重置账户
应用策略
写 paper orders
连接真实 broker
触发 quick-trade
创建真实 orders
改 daily auto update 主线
训练 / 调参 / 替换模型
```

## 2. 必须审计的代码与文档

执行者至少要读取：

```text
docs/tw_modular_daily_update_productization/PHASEX_REVIEW_AND_REVISION_SUGGESTION_CN.md
docs/tw_modular_daily_update_productization/PHASEX_PAPER_PORTFOLIO_STRATEGY_AND_SIMULATION_APP_WORK_CN.md
backend/app/routes/agent_v1/portfolio.py
backend/app/routes/agent_v1/quick_trade.py
backend/app/routes/agent_v1/admin.py
scripts/build_tw_daily_order_intent_artifact.py
scripts/run_tw_modular_daily_readonly_update.py
scripts/build_tw_modular_order_intent_artifact.py
configs/strategy_dependencies/top50_exit_one_worst_sell.yaml
```

如果发现实际路径不同，必须在报告里说明。

## 3. 必须冻结的合同

### 3.1 Paper account identity

必须明确：

```text
paper_account_id
user_id
tenant/session 口径
paper_account_epoch
initial_cash
base_currency
market_scope
```

如果当前系统没有 `paper_account_id` 或 `epoch`，必须提出新增字段或 artifact 的最小方案。

### 3.2 Paper portfolio state

必须定义 `PaperPortfolioStateArtifact`：

```text
artifact_type
schema_version
paper_account_id
user_id
paper_account_epoch
asof
cash
positions
source
created_at
checksum
```

positions 至少包含：

```text
instrument
quantity
avg_cost
last_price
market_value
unrealized_paper_pnl
source
```

### 3.3 Paper order intent

必须定义 `PaperOrderIntentArtifact`，由策略只读生成，不写账户。

至少包含：

```text
decision_id
model_id
strategy_rule
paper_account_id
paper_account_epoch
asof
actions
reason
input_checksum
readonly_decision_only
not_real_order
```

actions 必须使用 paper 命名：

```text
paper_buy_intent
paper_sell_intent
paper_skip
```

### 3.4 Paper apply request / result

必须定义：

```text
PaperApplyRequestArtifact
PaperApplyResultArtifact
PaperPositionSnapshotArtifact
PaperAuditLogArtifact
```

必须包含：

```text
decision_id
apply_id
idempotency_key
input_checksum
paper_account_id
paper_account_epoch
already_applied
paper_executions
cash_before / cash_after
positions_before / positions_after
fee_and_tax
created_at / applied_at
```

### 3.5 Reset contract

必须定义 `PaperAccountResetArtifact`：

```text
reset_id
paper_account_id
previous_epoch
new_epoch
archive_snapshot
initial_cash
idempotency_key
confirmed_by_user
created_at
```

Reset 前必须归档 snapshot，Reset 后必须进入新 epoch。

## 4. 幂等规则

执行者必须冻结以下规则：

```text
同一个 decision_id + paper_account_id + paper_account_epoch 只能 apply 一次
重复 idempotency_key + 相同 input_checksum 返回已有结果
重复 idempotency_key + 不同 input_checksum 必须拒绝
同一天多次 apply 默认拒绝，除非是同一 decision_id 幂等返回
reset 使用独立 reset_id / idempotency_key
reset 后旧 epoch 的 decision 不得再 apply
```

## 5. Paper accounting policy

必须冻结最低可复现口径：

```text
fill_policy = paper_close_price_fill
price_source = target_asof close 或 next_execution_date close
fee_rate
sell_tax_rate
slippage_rate
lot_size
cash_insufficient_policy
oversell_policy
cost_basis_policy
same_day_apply_policy
equity_calculation_policy
```

如果执行者认为当前系统已有会计口径，必须给出文件路径和字段映射。

## 6. 安全边界

报告必须列出 allowlist 和 denylist。

允许的 paper-only 写路径候选：

```text
POST /api/tw-stock/paper-portfolio/apply-decision
POST /api/tw-stock/paper-portfolio/reset
```

允许的 paper-only 读路径候选：

```text
GET /api/tw-stock/paper-portfolio/state
GET /api/tw-stock/paper-portfolio/apply-runs
```

禁止触达：

```text
broker
quick-trade
real orders
provider publish
provider accepted latest
qlib accepted latest
monitor config / scan / alerts
Agent tool/action
```

如果历史 `agent_v1/quick-trade/orders` 只能写 paper，也必须说明是否适合作为底层实现；新增前端文案不得叫 quick-trade。

## 7. 前端合同

X0 必须给出 X3 前端合同草案：

```text
当前模拟持仓
本次策略建议
应用后的模拟账户变化预览
二次确认弹窗
已应用状态
不可应用原因
reset 独立按钮
reset 前 archive 提示
仅模拟账户 / 非真实交易 文案
```

按钮文案必须包含：

```text
模拟
```

不得使用：

```text
真实交易
快速交易
下单
目标仓位
```

## 8. X0 输出

执行者必须输出：

```text
docs/tw_modular_daily_update_productization/PHASEX0_PAPER_ACCOUNT_CONTRACT_AUDIT_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
1. 现有 paper account / positions / orders 来源
2. 当前 daily strategy 是否读取模拟持仓
3. PaperPortfolioStateArtifact 合同草案
4. PaperOrderIntentArtifact 合同草案
5. PaperApplyRequest/Result/Snapshot/AuditLog 合同草案
6. Reset archive / epoch 合同草案
7. 幂等规则
8. accounting policy
9. API allowlist / denylist
10. 前端 apply/reset 文案合同
11. 是否可以进入 X1 的结论
```

## 9. 放行标准

只有同时满足以下条件，审查者才应允许进入 X1：

```text
paper account / positions / orders 读写路径清楚
paper_account_id / user_id / epoch 口径清楚
decision_id / apply_id / idempotency_key / input_checksum 冻结
accounting policy 可复现
reset 有 archive 与新 epoch
新增 API 不触达 broker / quick-trade / real orders
前端文案明确仅模拟账户
```

任一项不清楚，不得进入 X1。
