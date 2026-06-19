# Phase X 模拟账户策略与纸面应用支线工作文档

生成日期：2026-06-18

## 1. 目标

Phase X 的目标是把当前 readonly daily strategy 往 paper simulation 推进一步：

```text
读取当前模拟账户持仓
-> 基于默认模型 / 策略生成只读纸面决策
-> 用户手动确认后应用到模拟账户
-> 可独立重置模拟账户并从新 epoch 开始
```

Phase X 不做真实交易，不接真实 broker，不触发真实 quick-trade / orders，不切 provider accepted latest / qlib accepted latest，不写 monitor，不训练模型，不修改 Agent tool/action。

## 2. 背景判断

当前 U/V/W 主线已经证明：

```text
真实数据日更
DataReadinessGate
readonly daily latest
默认组合 e4_frozen_qlib_2023_2025_ltr + top50_exit_one_worst_sell
前端只读展示
```

但当前 daily order intent 仍使用：

```text
portfolio_state_source = u2_staging_empty_portfolio_state
```

这意味着它不是基于用户当前模拟账户持仓的再平衡决策。用户如果要从明天开始模拟买卖，必须先补 paper account 合同、持仓读取、纸面成交、幂等、reset 和前端确认链路。

## 3. 硬边界

允许：

```text
读取 paper account / paper positions / paper orders
生成 paper_order_intent
生成 paper_apply_preview
用户确认后写入 paper-only path
生成 paper_execution / paper_apply_result / paper_position_snapshot
显式 reset paper account
写 paper audit log
```

禁止：

```text
真实 broker connection
真实 quick-trade
真实 orders
真实账户 target_position / target_weight
provider publish
provider accepted latest / qlib accepted latest switch
monitor config / scan / alerts writes
training / tuning / model replacement
Agent tool/action expansion
daily auto update 自动应用到 paper account
```

特别要求：

```text
每日自动日更只能生成 readonly decision。
写入 paper account 必须由用户手动点击并二次确认。
```

## 4. 标准 Artifact

Phase X 必须冻结以下 artifact 名称和职责：

```text
PaperPortfolioStateArtifact
PaperOrderIntentArtifact
PaperApplyRequestArtifact
PaperApplyResultArtifact
PaperPositionSnapshotArtifact
PaperAuditLogArtifact
PaperAccountResetArtifact
```

命名必须包含 `paper`，避免和真实交易混淆。新增 API / artifact 不得使用容易误解的真实交易语义：

```text
order
target_position
target_weight
quick_trade
broker
```

如果历史表名里已经存在 `paper_orders`，可以继续读取，但新增接口和前端文案必须显式写明“模拟 / paper”。

## 5. 写入与幂等合同

Paper apply 是写操作，即使不是实盘，也必须幂等。

必须冻结：

```text
paper_account_id
user_id
paper_account_epoch
decision_id
apply_id
idempotency_key
input_checksum
already_applied
created_at
applied_at
```

规则：

```text
同一个 decision_id + paper_account_id + paper_account_epoch 只能应用一次。
重复点击必须返回已有 PaperApplyResultArtifact，不能重复成交。
不同 input_checksum 复用同一个 idempotency_key 必须拒绝。
```

## 6. 会计与成交规则

必须先冻结 deterministic paper accounting policy。最低口径：

```text
成交类型：paper close-price fill
成交价格：指定 asof / next execution date 的 close
交易单位：台股整股或明确零股规则
手续费：沿用当前 TW fee_rate
交易税：卖出时计入
滑点：默认 0 或显式配置
现金不足：拒绝或按规则缩量
卖出超过持仓：拒绝
持仓成本：按加权平均或 FIFO，必须固定
同一天多次 apply：默认拒绝，除非同一 decision_id 幂等返回
```

Apply 后必须能复现：

```text
cash
market_value
total_equity
position_cost
realized_paper_pnl
fee_and_tax
```

这些字段只能用于 paper simulation，不得用于真实交易或收益承诺。

## 7. 模块解耦

必须保持两层：

```text
StrategyDecisionEngine
  -> 只读生成 PaperOrderIntentArtifact / apply preview

PaperApplyEngine
  -> 写 paper account
  -> 生成 PaperApplyResultArtifact / PaperPositionSnapshotArtifact
```

X1 仍然只读；X2 才允许写 paper path。

## 8. Reset 合同

Reset 是高影响 paper 操作，必须独立于 apply。

必须满足：

```text
reset 前生成 archive snapshot
reset 需要二次确认
reset 不影响 readonly latest
reset 不影响真实账户
reset 后生成新的 paper_account_epoch
reset 写 PaperAuditLogArtifact
reset 后 cash / holdings / epoch 可复现
```

不得把 reset 做成 daily update 的自动步骤。

## 9. 阶段安排

### X0：Paper Account Contract and Safety Audit

目标：冻结模拟账户读写合同和安全边界。

必做：

```text
列出现有 paper account / positions / orders 表或 artifact
冻结 paper_account_id / user_id / paper_account_epoch 口径
列出允许写入的 paper-only 路径
列出禁止触达的 broker / quick-trade / real orders / monitor / provider latest 路径
冻结 accounting policy 草案
冻结 idempotency 规则
冻结 reset archive 规则
```

X0 不实现功能，不写账户。

### X1：Paper Decision and Accounting Engine

目标：让策略决策真正基于当前 paper holdings。

必做：

```text
读取 paper holdings
读取 model signal / strategy rule / price / fee policy
生成 PaperPortfolioStateArtifact
生成 PaperOrderIntentArtifact
生成 apply preview
解释 buy / sell / skip / unavailable 原因
```

X1 不写 paper positions，不写 paper executions。

### X2：Paper Apply / Reset API and Idempotency

目标：新增 paper-only 写接口并保证幂等。

允许新增：

```text
GET  /api/tw-stock/paper-portfolio/state
GET  /api/tw-stock/paper-portfolio/apply-runs
POST /api/tw-stock/paper-portfolio/apply-decision
POST /api/tw-stock/paper-portfolio/reset
```

必须验证：

```text
只写 paper path
重复 idempotency_key 不重复执行
apply 和 reset 均写 audit log
reset 前归档 snapshot
不接 broker / quick-trade / real orders
```

### X3：Frontend Paper Simulation UX and E2E Acceptance

目标：前端能清晰展示并安全触发 paper apply/reset。

必做：

```text
展示当前模拟持仓
展示策略建议和 apply preview
应用按钮二次确认
reset 按钮二次确认
展示 apply result / reset result / failure reason
已应用后按钮置灰或显示已应用
不可应用时显示短原因
E2E network audit 确认只调用 paper allowlist
```

## 10. 验收标准

Phase X 通过必须满足：

```text
strategy decision uses current paper holdings
paper apply writes only to paper account path
paper reset archives previous state before reset
apply/reset are idempotent or safely rejected on duplicate
frontend clearly distinguishes readonly decision vs paper execution
network audit has no broker / quick-trade / real orders / monitor / provider latest writes
no real trading semantics
```

## 11. 给执行者的总要求

不要直接实现完整 X。先执行 X0，输出：

```text
docs/tw_modular_daily_update_productization/PHASEX0_PAPER_ACCOUNT_CONTRACT_AUDIT_EXECUTION_REPORT_CN.md
```

审查者确认 X0 通过后，才能进入 X1。
