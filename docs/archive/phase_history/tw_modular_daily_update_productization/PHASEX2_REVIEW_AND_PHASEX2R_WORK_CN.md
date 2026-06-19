# Phase X2 审查与 Phase X2R Artifact Authority Repair 工作文档

生成日期：2026-06-18

## 1. X2 审查结论

X2 后端主骨架基本通过，但不建议直接进入 X3 前端。

已通过部分：

```text
新增 paper portfolio apply/reset API
apply/reset 均受 login_required 保护
写路径集中在 qd_tw_sim_* 模拟账户表
未触达 broker / quick-trade / real orders / provider publish / accepted latest / monitor / Agent / training
实现 paper_account_epoch
实现 apply/reset idempotency
实现 reset archive snapshot
实现 audit log
实现 unavailable / cash_insufficient / oversell 不成交
```

已复跑测试：

```text
python -m pytest backend/tests/test_build_tw_paper_portfolio_decision_artifact.py backend/tests/test_tw_stock_paper_portfolio_x2.py -q
12 passed
```

必须修复的问题：

```text
apply-decision 当前只验证请求 payload 内部字段一致
没有从服务端 artifact store 读取 X1/X1R 产物
没有服务端重算 canonical checksum
因此无法证明用户提交的 paper_order_intent 一定来自 X1/X1R 决策链路
```

X2R 目标是修复这个合同缺口。X2R 不扩大功能，不接前端，不做真实交易，不做 provider 更新。

## 2. X2R 目标

X2R 只做：

```text
为 POST /api/tw-stock/paper-portfolio/apply-decision 增加服务端 artifact 权威校验
补齐 HTTP/API 层测试
收紧 same-day apply 口径
产出 X2R 执行报告
```

X2R 完成后，才允许进入 X3 前端 UX 与 E2E。

## 3. 禁止边界

X2R 不允许新增或触达：

```text
真实 broker
/api/agent/v1/quick-trade/**
/api/quick-trade/**
real orders
provider publish
provider accepted latest / qlib accepted latest switch
monitor config / scan / alerts
Agent tool/action
training / tuning / model replacement
frontend UX
```

X2R 允许写：

```text
qd_tw_sim_accounts
qd_tw_sim_positions
qd_tw_sim_orders
qd_tw_sim_trades
qd_tw_sim_apply_runs
qd_tw_sim_reset_runs
qd_tw_sim_audit_log
```

X2R 允许读：

```text
data_tw/artifacts/paper_portfolio/**
```

X2R 不允许写 provider/latest/monitor/broker/Agent 相关表或 artifact。

## 4. Artifact Authority 合同

`POST /api/tw-stock/paper-portfolio/apply-decision` 必须支持服务端 artifact 权威路径。

推荐输入：

```text
paper_account_id
paper_account_epoch
decision_id
paper_order_intent_artifact_path 或 decision_artifact_id
input_checksum
idempotency_key
confirmed_by_user=true
confirm_text includes 模拟
```

允许保留 `paper_order_intent` payload 作为测试或兼容输入，但正式 apply 必须优先走服务端 artifact 读取。

最低要求：

```text
如果提供 artifact path/id，则服务端读取 artifact
artifact path 必须位于 data_tw/artifacts/paper_portfolio/**
禁止绝对路径逃逸和 ../ 路径逃逸
读取到的 artifact 必须是 PaperOrderIntentArtifact
服务端必须重算 canonical checksum
payload.input_checksum 必须等于服务端重算 checksum
payload.decision_id 必须等于 artifact.decision_id
payload.paper_account_id 必须等于 artifact.paper_account_id
payload.paper_account_epoch 必须等于 artifact.paper_account_epoch
artifact.paper_account_id 必须属于当前登录用户的模拟账户
```

如果只提交裸 `paper_order_intent` payload，必须至少满足以下之一：

```text
仅允许测试环境
或显式返回 invalid_artifact，要求客户端提交 artifact path/id
```

执行者可以选择更严格方案：生产路径完全禁止裸 payload apply。

## 5. Canonical Checksum 规则

X2R 必须冻结 checksum 规则，避免前后端或不同 Python 版本产生不一致。

建议规则：

```text
canonical_json = json.dumps(artifact, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
input_checksum = sha256(canonical_json.encode("utf-8")).hexdigest()
```

如果 X1/X1R 已有既定 checksum 生成函数，X2R 必须复用同一个函数，不得另起一套相似但不完全一致的算法。

若 artifact 内部已包含 `input_checksum` 字段，重算时必须明确是否排除该字段。推荐：

```text
用于校验 artifact 自身完整性的 checksum 不包含 input_checksum 字段
用于记录输入闭包的 checksum 必须在 X1/X1R 和 X2R 之间同源复用
```

执行报告必须说明最终采用哪一种，并给出测试证据。

## 6. Same-Day Apply 口径修复

当前 X2 只对 `status = applied` 的历史 apply 做 same-day 拒绝。X2R 应收紧为：

```text
同一 paper_account_id
同一 paper_account_epoch
同一 asof
只允许同一 decision_id / 同一 idempotency_key 幂等重放
不同 decision_id 必须拒绝
```

不应因为前一次 apply 只有 skipped/rejected/no_actions，就允许同一 asof 再应用另一个 decision。

拒绝状态继续使用：

```text
same_day_apply_rejected
```

## 7. HTTP/API 层测试

X2R 必须补 Flask route 或等价 HTTP 层测试，不能只测 service fake DB。

至少覆盖：

```text
GET /api/tw-stock/paper-portfolio/state 需要登录
GET /api/tw-stock/paper-portfolio/apply-runs 需要登录
POST /api/tw-stock/paper-portfolio/apply-decision 需要登录
POST /api/tw-stock/paper-portfolio/reset 需要登录

apply 成功返回 code=1 / data.simulation_only=true
invalid_artifact 返回 400
stale_epoch 返回 400
idempotency_conflict 返回 400
not_found 返回 404

user A 不能 apply user B 的 paper_account_id
artifact path 逃逸被拒绝
checksum mismatch 被拒绝
same-day different decision 被拒绝
```

如果现有 Flask app 测试环境搭建成本过高，允许先做 route handler 级别测试，但必须真实调用新增 route 函数和 `_sim_response`，不能只测 service。

## 8. Safety Boundary 测试

X2R 必须保留并增强 forbidden action audit。

测试或报告中必须证明未出现：

```text
quick-trade
quick_trade
broker
real_orders_enabled=true
connects_to_broker=true
provider publish
accepted latest switch
monitor scan
monitor alerts
Agent action
target_position / target_weight 写路径
```

注意：`paper_order`、`paper_trade`、`qd_tw_sim_orders` 是模拟账本允许词，不应误判为真实订单路径。

## 9. 不要求做的事

X2R 不要求：

```text
前端按钮
前端 reset UI
浏览器 E2E
真实 provider 拉取
每天自动脚本接入
模拟账户真实重置
真实券商接入
新模型或新策略
```

这些留给后续 X3 或更后面的阶段。

## 10. 验收标准

X2R 通过标准：

```text
apply-decision 默认使用服务端 artifact 权威读取
checksum 由服务端重算，不信任前端自报
path traversal 被拒绝
伪造但内部自洽的 paper_order_intent 不能绕过 artifact authority
same-day different decision 被拒绝，包括前一次 no_actions / skipped / rejected 的场景
HTTP/API 层测试覆盖新增 route
原 X2 service 测试继续通过
无 forbidden action 越界
```

建议执行命令：

```text
python -m py_compile backend/app/services/tw_stock_paper_portfolio.py backend/app/routes/tw_stock.py
python -m pytest backend/tests/test_build_tw_paper_portfolio_decision_artifact.py backend/tests/test_tw_stock_paper_portfolio_x2.py <新增 X2R 测试> -q
```

## 11. X2R 执行报告要求

执行者必须提交：

```text
docs/tw_modular_daily_update_productization/PHASEX2R_PAPER_APPLY_ARTIFACT_AUTHORITY_REPAIR_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
1. 修改文件清单
2. Artifact authority 最终方案
3. checksum 规则与 X1/X1R 是否同源
4. path safety / path traversal 防护说明
5. same-day apply 口径修复说明
6. HTTP/API 测试覆盖说明
7. forbidden action audit
8. 测试命令与结果
9. 是否建议进入 X3
```

## 12. 下一阶段判断

X2R 通过后，才进入 X3。

X3 才做：

```text
前端模拟策略应用按钮
前端 reset 模拟账户按钮
二次确认
已应用 / 已最新 / 不可应用原因展示
浏览器 E2E
network denylist
用户第一性原则验收
```

X2R 未通过前，不应让前端直接调用 apply/reset。
