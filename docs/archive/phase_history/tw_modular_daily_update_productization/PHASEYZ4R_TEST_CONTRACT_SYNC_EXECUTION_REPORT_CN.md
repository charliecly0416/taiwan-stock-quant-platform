# Phase YZ4R 测试合同同步与最终验收执行报告

生成日期：2026-06-18

## 1. 执行结论

Phase YZ4R 已完成。

本轮只修复 YZ4 收口审查指出的测试合同缺口和一个轻量 HTTP 状态映射问题：

```text
pending next_open / execution_price_unavailable 时，paper apply 后端必须拒绝；
ready mock 状态下，clean strict E4 paper intent 仍能进入原有模拟 apply 成功路径；
旧 paper API route 测试不再假设 pending 状态可以成功 apply；
POST /paper-portfolio/apply-decision 对 execution_price_unavailable 返回 HTTP 400。
```

未执行：

```text
模型训练 / 调参
provider refresh / publish
accepted latest switch
monitor config / scan / alerts 写入
broker / order / quick-trade
生产模型或生产策略变更
```

## 2. 修改范围

### 2.1 Route-level paper API 测试合同同步

修改文件：

```text
backend/tests/test_tw_stock_paper_portfolio_x2r_api.py
```

修改内容：

```text
_RouteHarness 默认注入 price_ready_status，使既有 route success / stale / same-day 测试验证 ready 状态下的原有 apply 路径；
新增 test_paper_portfolio_apply_route_pending_execution_price_rejected_before_writes；
该新增测试注入 price_pending_status，确认 execution_price_unavailable 时后端拒绝，且 apply_runs/orders/trades/audit/schema 写入均未发生。
```

### 2.2 HTTP 状态映射修复

修改文件：

```text
backend/app/routes/tw_stock.py
```

修改内容：

```text
_sim_response() 将 execution_price_unavailable 纳入 400 错误状态集合。
```

原因：

```text
POST /paper-portfolio/apply-decision 在 pending next_open 时是后端拒绝，不应以 HTTP 200 表达为成功请求。
```

## 3. 验证结果

### 3.1 paper/replay 局部测试

命令：

```text
python -m pytest backend/tests/test_tw_stock_paper_portfolio_x2.py backend/tests/test_tw_stock_paper_portfolio_x2r_api.py backend/tests/test_build_tw_paper_portfolio_decision_artifact.py backend/tests/test_tw_stock_readonly_replay_window_api.py -q
```

结果：

```text
42 passed in 2.18s
```

### 3.2 YZ + paper/replay 全套相关测试

命令：

```text
python -m pytest backend/tests/test_phase_yz0_clean_registry.py backend/tests/test_phase_yz1_strict_e4_model_adapters.py backend/tests/test_phase_yz2_orthogonal_package.py backend/tests/test_phase_yz2r_execution_price_readiness.py backend/tests/test_phase_yz3_productization_status.py backend/tests/test_tw_stock_paper_portfolio_x2.py backend/tests/test_tw_stock_paper_portfolio_x2r_api.py backend/tests/test_build_tw_paper_portfolio_decision_artifact.py backend/tests/test_tw_stock_readonly_replay_window_api.py -q
```

结果：

```text
67 passed in 2.98s
```

## 4. 当前收口判断

YZ4R 后，前一轮阻塞项已解除：

```text
paper API 既有失败测试已同步新合同；
pending execution_price_unavailable 后端拒绝已被 route-level 测试覆盖；
ready mock 状态下原有 clean paper apply 路径仍被测试覆盖；
Model B readonly replay API smoke 已存在并通过；
YZ + paper/replay 相关 pytest 全绿。
```

因此，按当前范围可以判定：

```text
YZ 路线可收口。
```

## 5. 保留口径

YZ/YZ4/YZ4R 的收口只证明：

```text
strict E4 产品化链路、clean registry、readonly replay display、paper apply gate、pending 用户态和安全边界已闭环。
```

不证明：

```text
新的收益表现；
真实交易可用；
next_open 已有成交价；
paper apply 当前可以执行。
```

当前 pending 状态仍应按以下口径解释：

```text
当前 signal 的 next_open 成交价尚不可用；
paper apply 被后端和前端共同阻断；
readonly replay 中的 0 return / 0 action 是 pending 展示产物，不是策略收益证据。
```
