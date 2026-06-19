# Phase YZ4 后最终收口摘要（供统筹审查）

生成日期：2026-06-18

## 1. 结论

Phase YZ4 已补齐统筹指出的最终收口缺口。YZ 路线可以按“Strict E4 产品化链路已收口，当前成交价等待行情更新”的口径关闭。

本次收口不代表新增收益证明；它证明的是 clean E4 产品化链路、只读回放展示、模拟账户 apply 安全边界和前端用户态已经闭环。

## 2. YZ4 已修复的问题

1. Paper portfolio 后端不再硬编码旧模型 `e4_frozen_qlib_2023_2025_ltr`。
2. `apply_decision()` 在任何 schema / apply_runs / orders / trades 写入前检查 execution price gate。
3. 当前 `execution_price_unavailable` 时，后端直接拒绝 paper apply，不依赖前端按钮禁用。
4. `latest_decision()` 只接受 clean paper decision artifact，旧模型和非 clean artifact 会被过滤。
5. 已生成并登记两个 clean E4 readonly replay window artifact，D7 latest pointer 返回 2 个 clean windows。
6. 前端 E2E 只请求 clean E4 replay，不再默认请求旧模型。

## 3. Clean 生产集合

生产模型只保留：

```text
e4_frozen_qlib_2018_2022
e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
```

生产策略只保留：

```text
top50_exit_one_worst_sell
```

执行价模式：

```text
next_open
```

## 4. 验证结果

审查补跑结果：

```text
backend YZ pytest: 54 passed
paper/replay 局部 pytest: 29 passed
YZ4 artifact generator: ok, window_count=2
frontend static checks: passed
frontend build: passed
```

E2E 安全审计：

```text
forbidden_request_count = 0
paper_apply_write_count = 0
paper_reset_write_count = 0
provider publish/refresh/accepted latest write = 0
broker/quick-trade/order write = 0
console_errors = []
page_errors = []
```

## 5. 需要保持的收口口径

YZ4 replay artifact 当前是 pending execution price 状态下的 clean readonly 展示产物：

```text
action_count = 0
total_return = 0
note = clean_e4_readonly_replay_pending_execution_price_no_trades
```

因此最终总结里不能写成“YZ4 证明了 2026 收益表现”。正确表述是：

```text
clean E4 readonly replay window / index / frontend display 已闭环；
由于 2026-06-18 当天尚未形成可用 next_open execution price，paper apply 被后端阻断；
收益表现仍以此前正式 replay / matrix 结果为依据。
```

## 6. 最终判定

YZ 路线可以收口。

后续新模型、新策略、真实成交价形成后的有交易 replay、或模拟账户增强，应另开新路线，不再继续拖长 YZ 路线。
