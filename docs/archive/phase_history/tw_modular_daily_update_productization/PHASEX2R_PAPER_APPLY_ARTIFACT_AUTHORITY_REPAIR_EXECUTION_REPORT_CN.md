# Phase X2R Paper Apply Artifact Authority Repair 执行报告

生成日期：2026-06-18

## 1. 修改文件清单

本轮修改：

```text
backend/app/services/tw_stock_paper_portfolio.py
backend/tests/test_tw_stock_paper_portfolio_x2.py
```

本轮新增：

```text
backend/tests/test_tw_stock_paper_portfolio_x2r_api.py
docs/tw_modular_daily_update_productization/PHASEX2R_PAPER_APPLY_ARTIFACT_AUTHORITY_REPAIR_EXECUTION_REPORT_CN.md
```

本轮未修改前端，未接浏览器 E2E，未触达 provider / monitor / broker / Agent / training。

## 2. Artifact Authority 最终方案

`POST /api/tw-stock/paper-portfolio/apply-decision` 默认要求服务端 artifact authority：

```text
paper_order_intent_artifact_path
或 decision_artifact_id
```

服务端行为：

```text
读取 data_tw/artifacts/paper_portfolio/** 下的 paper_order_intent.json
读取同目录 paper_portfolio_state.json
验证 artifact_type = PaperOrderIntentArtifact
服务端重算 input_checksum
验证 payload.input_checksum == 服务端重算 checksum
验证 artifact.input_checksum == 服务端重算 checksum
验证 payload.decision_id == artifact.decision_id
验证 payload.paper_account_id == artifact.paper_account_id
验证 payload.paper_account_epoch == artifact.paper_account_epoch
再用当前 login user_id 查询 qd_tw_sim_accounts，确认账户属于当前用户
```

裸 `paper_order_intent` payload 默认拒绝：

```text
status = invalid_artifact
message = paper_order_intent_artifact_path or decision_artifact_id is required
```

仅 service 测试可通过 `allow_inline_intent=True` 保留旧 X2 行为覆盖；生产 route 使用默认 `False`。

## 3. Checksum 规则与 X1/X1R 同源说明

X1/X1R 既有函数为 `scripts/build_tw_paper_portfolio_decision_artifact.py::sha_payload`：

```text
json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
"sha256:" + sha256(data).hexdigest()
```

X2R 在 `backend/app/services/tw_stock_paper_portfolio.py::_canonical_checksum` 复用同一规则，没有改用另一套 separators。

X1/X1R 的 `input_checksum` 不是整个 intent 文件 checksum，而是输入闭包 checksum：

```text
portfolio_state_checksum
source_model_signal_artifact
strategy_rule
asof
actions
```

因此 X2R 从 intent 同目录读取 `paper_portfolio_state.json`，取其 `checksum`，按同源 payload 重算 `input_checksum`。若 artifact 内部 `input_checksum` 与服务端重算值不一致，返回 `invalid_artifact`。

## 4. Path Safety / Traversal 防护

实现位置：

```text
TWStockPaperPortfolioService._resolve_artifact_path
TWStockPaperPortfolioService._recompute_intent_input_checksum
```

防护规则：

```text
拒绝绝对路径
拒绝 .. 路径片段
resolved path 必须位于 artifact_root 下
artifact 文件名必须是 paper_order_intent.json
decision_artifact_id 不允许 /、\ 或 ..
source_portfolio_state_artifact 必须与 paper_order_intent.json 同目录
```

测试覆盖：

```text
test_authoritative_artifact_path_traversal_rejected
test_paper_portfolio_apply_route_rejects_invalid_stale_not_found_and_artifact_abuse
```

## 5. Same-Day Apply 口径修复

X2R 将 `_find_same_day_apply` 从只查：

```text
status = 'applied'
```

收紧为查询同账户同 epoch 的全部历史 apply run：

```text
paper_account_id
paper_account_epoch
asof
```

结果：

```text
同一 decision_id / idempotency_key 仍走幂等重放
不同 decision_id 的同 asof apply 返回 same_day_apply_rejected
前一次即使是 no_actions / skipped / rejected，也会阻止同 asof 不同 decision
```

测试覆盖：

```text
test_same_day_rejects_after_previous_no_actions_run
test_paper_portfolio_apply_route_rejects_same_day_different_decision
```

## 6. HTTP/API 测试覆盖说明

新增 `backend/tests/test_tw_stock_paper_portfolio_x2r_api.py`，使用 Flask test client 注册 `tw_stock_bp`，真实走：

```text
login_required wrapper
/api/tw-stock/paper-portfolio/* route function
_sim_response status mapping
TWStockPaperPortfolioService
fake qd_tw_sim_* DB
临时 artifact_root
```

覆盖：

```text
GET /paper-portfolio/state 需要登录
GET /paper-portfolio/apply-runs 需要登录
POST /paper-portfolio/apply-decision 需要登录
POST /paper-portfolio/reset 需要登录
apply 成功返回 code=1 / data.simulation_only=true
trading.real_orders_enabled=false
trading.connects_to_broker=false
invalid_artifact 返回 400
stale_epoch 返回 400
idempotency_conflict 返回 400
not_found 返回 404
user A 不能 apply user B 的 paper_account_id
artifact path 逃逸被拒绝
checksum mismatch 被拒绝
same-day different decision 被拒绝
```

## 7. Forbidden Action Audit

本轮未新增或触达：

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

静态审计命令：

```text
rg -n "quick-trade|quick_trade|broker|real_orders_enabled.*true|connects_to_broker.*true|provider publish|accepted latest switch|monitor scan|monitor alerts|Agent action|target_position|target_weight" backend/app/services/tw_stock_paper_portfolio.py backend/tests/test_tw_stock_paper_portfolio_x2.py backend/tests/test_tw_stock_paper_portfolio_x2r_api.py
```

结果只命中：

```text
服务文件顶部禁止边界说明
not_real_order / not_target_position artifact validation
测试中对 connects_to_broker is False 的断言
测试中的 forbidden denylist 字符串
```

未发现真实 quick-trade / broker / provider / monitor / Agent / target_position 写路径。

## 8. 测试命令与结果

已执行：

```text
python -m py_compile backend/app/services/tw_stock_paper_portfolio.py backend/app/routes/tw_stock.py scripts/build_tw_paper_portfolio_decision_artifact.py backend/tests/test_tw_stock_paper_portfolio_x2.py backend/tests/test_tw_stock_paper_portfolio_x2r_api.py
python -m pytest backend/tests/test_build_tw_paper_portfolio_decision_artifact.py backend/tests/test_tw_stock_paper_portfolio_x2.py backend/tests/test_tw_stock_paper_portfolio_x2r_api.py -q
```

结果：

```text
22 passed in 1.20s
```

## 9. 是否建议进入 X3

建议进入 X3。

X2R 已补齐 apply-decision artifact authority、服务端 checksum 重算、path traversal 防护、same-day no_actions/skipped/rejected 后的不同 decision 拒绝，以及 HTTP/API 层测试。

X3 仍必须单独完成：

```text
前端模拟策略应用按钮
前端 reset 模拟账户按钮
二次确认
已应用 / 已最新 / 不可应用原因展示
浏览器 E2E
network denylist，只允许 paper-portfolio apply/reset POST
禁止 quick-trade / broker / orders / monitor / provider ops 请求
```
