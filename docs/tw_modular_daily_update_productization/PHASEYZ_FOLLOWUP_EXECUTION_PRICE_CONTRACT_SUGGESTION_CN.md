# Phase YZ 后续补充意见：成交价口径、开盘执行对照与 Replay 合同

生成日期：2026-06-18

## 1. 背景

YZ0 已完成 clean registry 收口，YZ1 当前工作重点是 Strict E4 daily model adapters。YZ1 文档本身主要冻结模型身份、daily signal artifact、validator 和 blocked manifest，不适合在这一轮混入策略回放或前端改造。

但在 YZ0/YZ1 之间，审查者补做了一个只读对照实验：同一 E4 模型、同一 2026-01-01..2026-05-07 窗口、同一手续费/税费/lot/持仓规则，只把成交价从“下一交易日收盘价”改成“下一交易日开盘价”。结果显示，成交价口径会明显影响部分组合，尤其是 qlib-only。

因此后续 YZ2/YZ3 必须补充“成交价口径合同”，避免产品化后把研究回测收益、前端展示、paper portfolio 和真实可执行含义混在一起。

## 2. 已完成的只读对照实验

实验产物目录：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/addon_e4_open_vs_close_execution_2026/
```

主要产物：

```text
e4_2026_open_vs_close_summary.csv
e4_2026_open_vs_close_delta.csv
e4_2026_open_vs_close_daily_nav.csv
e4_2026_open_vs_close_actions.csv
manifest.json
```

核心结果：

```text
E4 LTR + one_sell_one_buy_correct:
  next-day close execution: 90.93%
  next-day open execution : 90.72%
  open - close            : -0.21 pct

E4 LTR + top50_exit_one_worst_sell:
  next-day close execution: 91.24%
  next-day open execution : 90.87%
  open - close            : -0.37 pct

E4 qlib-only + one_sell_one_buy_correct:
  next-day close execution: 64.67%
  next-day open execution : 58.19%
  open - close            : -6.48 pct

E4 qlib-only + top50_exit_one_worst_sell:
  next-day close execution: 129.19%
  next-day open execution : 101.55%
  open - close            : -27.64 pct
```

初步判断：

- E4 LTR 在该窗口对 open/close 成交价假设不敏感。
- E4 qlib-only 对成交价假设更敏感，尤其 `top50_exit_one_worst_sell`。
- 该实验是只读附加实验，不应直接替代正式 replay benchmark；但足以说明 YZ3 必须显式固化成交价口径。

## 3. 建议加入后续工作的原则

### 3.1 不改 YZ1 主任务

YZ1 仍应只做：

```text
Strict E4 ModelSignalArtifact
Model A / Model B adapter
validator registry-driven
blocked manifest
source artifact trace
```

YZ1 不应新增：

```text
replay benchmark
paper portfolio accounting
frontend execution-price selector
策略收益优劣判断
```

原因：YZ1 是模型 artifact 接口层，提前混入回放会再次造成模型、策略、执行价格、前端展示互相污染。

### 3.2 YZ2 可补充数据字段检查，但不做策略收益判断

YZ2 如果涉及正交数据 package 和 model signal artifact，应确保后续 replay 可以拿到执行价格所需的市场价格字段。YZ2 只需检查数据可用性，不做收益评判。

建议 YZ2 增补检查项：

```text
对于每个 signal_asof 和 instrument，后续 replay 至少能定位：
  next_trading_day
  next_trading_day_open
  next_trading_day_close
  close_on_or_before_signal_asof

若 open 缺失，必须显式 blocked 或标注 execution_price_unavailable；
不得悄悄 fallback 到 close。
```

### 3.3 YZ3 必须正式固化 replay execution price contract

YZ3 应新增 replay/paper/frontend 合同：

```text
signal_asof = T
decision generated after T close
default executable replay price = next trading day open
research comparison price = next trading day close
mark-to-market price = close
```

也就是说：

- 默认产品化、paper portfolio、用户前端看到的“可执行回放”应优先采用 next-day open。
- next-day close 可以保留为 research-only sensitivity，不应作为默认收益证据。
- 任意 API payload、manifest、前端指标都必须带上 `execution_price_mode`，不能只写 return。

建议支持的枚举：

```text
execution_price_mode:
  next_open
  next_close_research_only
```

不建议在本轮加入复杂成交价：

```text
VWAP
成交量冲击模型
滑点模型
盘中触发价
```

这些可以留到后续真实交易模拟增强，不应阻塞 YZ 收口。

## 4. 建议追加到 YZ3 的执行要求

执行者在 YZ3 需要补充：

1. replay window API/policy 增加 `execution_price_mode`。
2. 默认值必须是 `next_open`。
3. `next_close_research_only` 必须明确 research-only，不得作为默认策略收益证据。
4. replay manifest 必须记录：

```text
model_id
strategy_rule
window_start
window_end
signal_asof_range
execution_price_mode
order_timing_contract
fee_rate
sell_tax_rate
lot_size
max_holdings
initial_cash
```

5. order/action 明细必须记录：

```text
signal_asof
execution_date
execution_price_mode
execution_price
side
instrument
quantity
cash_before
cash_after
position_before
position_after
```

6. 若某个交易日缺少 next open 价格，必须：

```text
blocked_reason: next_open_price_missing
affected_dates: [...]
affected_symbols: [...]
no_fallback: true
```

不得自动改用 next close。

## 5. 建议追加到前端的展示要求

前端用户第一性原则：

- 默认只展示可执行口径，即 `next_open`。
- 如果展示 research-only close 对照，必须清楚标记为“研究对照”，不能和默认收益混排。
- 用户选择模型/策略/回放窗口时，返回结果必须显示成交价口径。
- 不能让用户误以为“前一日收盘后生成的决策，可以用下一日收盘价成交”是现实可执行操作。

建议前端文案语义：

```text
成交口径：次一交易日开盘
研究对照：次一交易日收盘，不作为默认执行口径
```

不建议使用：

```text
真实收益
保证可成交
实盘收益
```

## 6. 给执行者的补充 prompt

请在 YZ1 完成并通过审查后，将以下要求并入 YZ2/YZ3，不能提前混入 YZ1：

```text
根据 `docs/tw_modular_daily_update_productization/PHASEYZ_FOLLOWUP_EXECUTION_PRICE_CONTRACT_SUGGESTION_CN.md`，在 YZ2/YZ3 补充 replay execution price contract。

YZ2 只检查 next trading day open/close 所需价格字段可用性，不做收益判断。

YZ3 必须让 replay window、paper portfolio、frontend/API payload 显式携带 execution_price_mode。默认可执行口径为 next_open；next_close 只能作为 research-only sensitivity。不得在 next_open 缺失时 fallback 到 next_close。不得改模型、不得重训、不得 provider publish/accepted latest/monitor/broker/order/quick-trade。
```

## 7. 给审查者的补充 prompt

审查 YZ2/YZ3 时，请额外检查：

```text
1. YZ1 是否仍只做模型 adapter，没有混入 replay 收益判断。
2. YZ2 是否证明 next open / next close 价格字段可用，且没有用 close 填 open。
3. YZ3 replay API、manifest、前端展示是否显式包含 execution_price_mode。
4. 默认 execution_price_mode 是否为 next_open。
5. next_close 是否明确 research-only，不作为默认策略收益证据。
6. 是否存在 next_open 缺失时悄悄 fallback 到 next_close。
7. paper portfolio 的模拟成交口径是否和 replay 默认口径一致。
8. 前端是否避免把 close-execution research return 展示成可执行收益。
9. 是否仍保持 readonly/paper-only 安全边界，没有 provider/accepted latest/monitor/broker/order/quick-trade 写入。
```

如果以上任一项不满足，应停止，不允许 YZ 收口。

## 8. 当前建议结论

不需要退回 YZ0，也不需要改 YZ1 当前主目标。

建议：

```text
YZ1 继续按现文档执行；
YZ2 增加 execution price 所需价格字段可用性检查；
YZ3 正式固化 next_open 默认执行口径，并把 next_close 降级为 research-only sensitivity。
```

这样既不会打乱当前 Strict E4 产品化收口节奏，也能把“收盘成交回测可能不够现实”的问题纳入正式合同。
