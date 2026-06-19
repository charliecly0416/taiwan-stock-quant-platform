# Phase X 模拟账户接入策略路线审查意见与修订建议

生成日期：2026-06-18

## 1. 审查结论

`PHASEX_PAPER_PORTFOLIO_STRATEGY_AND_SIMULATION_APP_WORK_CN.md` 的方向是合理的，也符合当前项目从 readonly strategy 走向 paper simulation 的下一步需求。

但当前文档还不够完善，不建议直接进入实现。主要问题不是方向错，而是模拟账户写入、幂等、会计规则、前端确认和只读/纸面边界还没有冻结到足够细。

建议先修订 X 文档或补一份 X0 工作文档，再让执行者开工。

## 2. 当前 X 路线合理的部分

当前文档有几项关键方向是对的：

```text
不接真实 broker
不触发 quick-trade
不创建真实 orders
不切 provider accepted latest / qlib accepted latest
不写 monitor config / scan / alerts
不训练新模型
默认不自动应用到模拟账户
应用策略和重置账户拆开
```

这说明 X 路线的主边界是正确的：

```text
readonly strategy decision
-> paper portfolio apply
-> paper position snapshot
```

这个方向可以作为后续设计基础。

## 3. 必须补强的问题

### 3.1 Paper 账户写入合同不足

当前文档说“写入 paper positions / paper orders”，但没有冻结写入合同。

必须补清：

```text
paper_account_id / user_id / session_id 如何定义
当前模拟账户从哪里读
paper positions 写到哪里
paper orders / paper executions 写到哪里
哪些字段必须存在
哪些字段绝对不能出现真实账户语义
一次 apply 生成哪些 artifact
```

建议输出标准 artifact：

```text
PaperPortfolioStateArtifact
PaperOrderIntentArtifact
PaperApplyRequestArtifact
PaperApplyResultArtifact
PaperPositionSnapshotArtifact
PaperAuditLogArtifact
```

### 3.2 幂等与重复点击风险

“应用到模拟账户”是写操作，即使只是 paper，也必须幂等。

必须冻结：

```text
decision_id
apply_id
idempotency_key
input_checksum
already_applied=true/false
```

同一个 `decision_id + paper_account_id` 重复点击时，只能返回已有结果，不能重复买卖。

### 3.3 会计与成交规则不足

模拟账户不是简单把建议写进去。必须定义纸面成交规则，否则结果不可复现。

必须冻结：

```text
成交价格使用哪一天、哪个字段
手续费 / 交易税 / 滑点如何计算
现金不足怎么办
卖出数量超过持仓怎么办
整股 / 零股 / 最小交易单位如何处理
持仓成本如何更新
同一天是否允许多次 apply
apply 后的 cash / market_value / total_equity 如何计算
```

如果暂时不做复杂撮合，应明确是：

```text
paper close-price fill
single-day deterministic fill
research-only simulation
```

### 3.4 决策模块与应用模块必须解耦

X1 的策略决策仍然应该是只读的，不能直接写账户。

正确结构应是：

```text
StrategyDecisionEngine
  -> PaperOrderIntentArtifact
PaperApplyEngine
  -> PaperApplyResultArtifact
  -> PaperPositionSnapshotArtifact
```

策略模块只负责生成候选动作和解释；paper apply 模块才负责写模拟账户。

### 3.5 命名边界要更硬

为了避免和真实交易混淆，建议统一使用：

```text
paper_order_intent
paper_execution
paper_position_snapshot
paper_apply_result
paper_account_reset
```

避免在新增 API / artifact 里使用容易误解的名称：

```text
order
target_position
target_weight
quick_trade
broker
```

如果历史系统已有 `paper orders` 字段，可以继续读，但新增接口和前端文案必须明确 `paper`。

### 3.6 Reset 需要归档和确认

重置模拟账户是高影响 paper 操作，不能只是清空。

必须要求：

```text
reset 前生成 archive snapshot
reset 需要二次确认
reset 不得影响真实账户或 readonly latest
reset 后生成新的 paper account epoch
reset 操作写 audit log
```

### 3.7 前端用户第一性原则还要补细

前端应让用户明确看到三层：

```text
当前模拟持仓
本次策略建议
应用后的模拟账户变化预览
```

交互要求：

```text
默认只展示最重要的信息
应用前必须预览和二次确认
按钮文案必须包含“模拟”或“纸面”
已应用后按钮置灰或显示已应用
不可应用时显示短原因
reset 和 apply 必须分离
不要把 paper result 说成真实收益或真实交易
```

## 4. 建议修订后的 X 阶段

不建议切太细，可以保留 4 阶段：

```text
X0 Paper Account Contract and Safety Audit
X1 Paper Decision and Accounting Engine
X2 Paper Apply / Reset API and Idempotency
X3 Frontend Paper Simulation UX and E2E Acceptance
```

### X0：Paper Account Contract and Safety Audit

目标：冻结模拟账户读写合同和安全边界。

必做：

```text
列出现有 paper account / positions / orders 表或 artifact
冻结 paper_account_id / user_id / epoch 口径
列出允许写入的 paper-only 路径
列出禁止触达的 broker / quick-trade / real orders / monitor / provider latest 路径
冻结 accounting policy 草案
冻结 idempotency 规则
```

X0 不实现功能，只审计和冻结合同。

### X1：Paper Decision and Accounting Engine

目标：让策略决策真正基于当前 paper holdings。

必做：

```text
读取 paper holdings
读取 model signal / strategy rule / price / fee policy
生成 PaperOrderIntentArtifact
生成 apply preview
解释 buy / sell / skip / unavailable 原因
不写 paper positions
不写 paper executions
```

X1 仍然只读。

### X2：Paper Apply / Reset API and Idempotency

目标：新增 paper-only 写接口，并保证幂等。

允许新增：

```text
POST /api/tw-stock/paper-portfolio/apply-decision
POST /api/tw-stock/paper-portfolio/reset
GET  /api/tw-stock/paper-portfolio/state
GET  /api/tw-stock/paper-portfolio/apply-runs
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

目标：前端可清晰展示并安全触发 paper apply/reset。

必做：

```text
展示当前模拟持仓
展示策略建议和 apply preview
应用按钮二次确认
reset 按钮二次确认
展示 apply result / reset result / failure reason
E2E network audit 确认只调用 paper allowlist
```

## 5. 验收标准

X 路线通过必须满足：

```text
strategy decision uses current paper holdings
paper apply writes only to paper account path
paper reset archives previous state before reset
apply/reset are idempotent or safely rejected on duplicate
frontend clearly distinguishes readonly decision vs paper execution
network audit has no broker / quick-trade / real orders / monitor / provider latest writes
no real trading semantics
```

## 6. 必须禁止的事项

X 路线不得包含：

```text
真实 broker connection
quick-trade
real orders
target positions for real accounts
provider publish
provider accepted latest / qlib accepted latest switch
monitor config / scan / alerts writes
training / tuning / model replacement
Agent tool/action expansion
automatic paper apply during daily update
```

特别注意：

```text
每日自动日更只能生成 readonly decision。
用户必须手动点击并确认，才允许写入 paper account。
```

## 7. 给执行者的建议 Prompt

```text
请先不要直接实现 Phase X。请根据 docs/tw_modular_daily_update_productization/PHASEX_REVIEW_AND_REVISION_SUGGESTION_CN.md 先执行 X0 Paper Account Contract and Safety Audit。

X0 只做审计和合同冻结，不写功能。请列出现有 paper account / paper positions / paper orders 的来源、允许写入路径、禁止触达路径、paper_account_id/user_id/epoch 口径、idempotency 规则、accounting policy、reset archive 规则，以及前端 apply/reset 的安全文案合同。

禁止触发真实 broker、quick-trade、real orders、provider publish、accepted latest、monitor config/scan/alerts、Agent 扩权。X0 输出：docs/tw_modular_daily_update_productization/PHASEX0_PAPER_ACCOUNT_CONTRACT_AUDIT_EXECUTION_REPORT_CN.md
```

## 8. 给审查者的建议 Prompt

```text
请审查 docs/tw_modular_daily_update_productization/PHASEX0_PAPER_ACCOUNT_CONTRACT_AUDIT_EXECUTION_REPORT_CN.md，并对照 docs/tw_modular_daily_update_productization/PHASEX_REVIEW_AND_REVISION_SUGGESTION_CN.md 判断是否可以进入 X1。

重点审查：
1. paper account / positions / orders 的读写路径是否清楚；
2. 是否只允许写 paper path，不触达 broker / quick-trade / real orders；
3. idempotency、decision_id、apply_id、input_checksum 是否冻结；
4. accounting policy 是否足够复现；
5. reset 是否有 archive 与二次确认；
6. 前端文案是否明确“仅模拟账户”；
7. 是否没有训练、调参、provider latest、monitor、Agent 扩权。

如果任何一项不清楚，请不要放行 X1。
```

## 9. 最终建议

X 路线可以做，但必须先补合同。

建议结论：

```text
方向合理，可行；但原 X 文档还不够完善。
先做 X0 合同审计与修订，再进入功能实现。
```
