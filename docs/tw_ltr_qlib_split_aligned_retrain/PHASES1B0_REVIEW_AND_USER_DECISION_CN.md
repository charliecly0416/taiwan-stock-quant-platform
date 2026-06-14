# Phase S1B0 审查意见与用户决策点

生成日期：2026-06-14

## 1. 审查范围

主线依据：`docs/TW_STOCK_LTR_QLIB_SPLIT_ALIGNED_AND_FRESH_RETRAIN_MAINLINE_CN.md`

工作文档：`docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B0_QILB_SCORE_POLICY_AND_UNIVERSE_WORK_CN.md`

审查入口：`docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B0_POLICY_FREEZE_EXECUTION_REPORT_CN.md`

## 2. 审查结论

结论：`S1B0 政策冻结基本合格，但不放行 S1B1 实际 qlib fold 训练 / score 生成。必须先处理 dynamic universe 可行性问题，或由用户确认降级路线。`

当前 gate：

```text
s1b0_dynamic_universe_infeasible_requires_calendar_or_universe_decision
```

不使用执行者建议的 `s1b0_dynamic_universe_infeasible_static_degrade_requires_user_confirmation` 直接转 static，因为低覆盖日期可能包含 calendar/price trading-day 口径问题，未必证明 dynamic universe 本身不可行。

## 3. 通过项

### 3.1 范围合规

执行者本轮只做政策冻结与只读可行性检查，未训练 qlib/LTR、未生成 score/rank、未构建 LTR 样本、未跑回放、未调参、未改前端/API、未联网、未触发 provider refresh/publish、未切换 accepted latest、未触发 monitor/broker/orders/quick-trade。

### 3.2 qlib 参数冻结合格

`phase_s1b0_qlib_config_freeze.json` 显示：

- frozen config：`qlib_pipeline/configs/tw_yahoo_primary_alpha158.yaml`
- recorder：`950741cfd5f14ee5a05464fec3e12e0a`
- model：`LGBModel`
- handler：`Alpha158`
- train：`2015-05-04..2020-12-31`
- valid：`2021-01-01..2022-12-31`
- test：`2023-01-01..2025-06-30`
- `config_recorder_consistency_ok = true`

未发现参数搜索或 test feedback。

### 3.3 walk-forward score 政策方向合格

冻结计划为：

- WF-2017：训练 `2015-05-04..2016-12-31`，打分 `2017`
- WF-2018：训练至 `2017-12-31`，打分 `2018`
- WF-2019：训练至 `2018-12-31`，打分 `2019`
- WF-2020：训练至 `2019-12-31`，打分 `2020`
- WF-VAL：训练至 `2020-12-31`，打分 `2021..2022`
- TEST：使用 frozen recorder pred，覆盖 `2023..2025H1`

该设计避免用 qlib train 全期模型回打 train 的 in-sample score。`2015-2016` 无法严格 walk-forward 打分，执行者建议排除，方向合理，但仍需在后续样本合同中显式冻结。

## 4. 阻断问题

### High：dynamic universe 不可直接判死，需先做 calendar / trading-day 修复诊断

执行者报告 dynamic universe 在早期年份不可行：

- dates selected < 50 total：`63`
- dates selected < 150 total：`686`
- min selected count：`0`

抽查 daily 明细发现，部分低覆盖日期像是交易日历/价格日历口径问题，而不一定是 universe 本身不可行。例如：

- `2016-02-08..2016-02-12`
- `2017-01-25..2017-02-01`
- `2016-09-15..2016-09-16`

这些日期在台湾市场可能包含春节/假期或非正常交易日。若 qlib calendar 把非交易日纳入，而 normalized price 没有对应价格，selected count 会异常偏低。

因此不能直接进入 static accepted 150 降级。正确下一步应先做很窄的 `S1B0R calendar/price trading-day repair diagnosis`：

1. 对 selected count < 50 的 63 个日期逐日列出：是否在 qlib calendar、是否在 normalized price calendar、是否台湾市场真实交易日、是否只有少数股票有价格。
2. 判断是否应从 S1 scoring/replay calendar 中排除非交易日或 price-unavailable 日期。
3. 重新计算 dynamic universe feasibility after calendar repair。
4. 不得训练、不得生成 score、不得构建 LTR 样本、不得回放。

### Medium：早期 train 排除会改变 S1 train 窗口

严格 walk-forward 下，`2015-05-04..2016-12-31` 无法被打分。若排除，S1 LTR train 实际变成 `2017-01-01..2020-12-31`，不再完全等同 qlib train `2015-05-04..2020-12-31`。

这不是阻断，但后续必须降级表述：

```text
qlib-old-window-aligned test with walk-forward LTR train scores from 2017 onward
```

不能称为完整 `2015..2020` LTR train 对齐。

## 5. 台股只读安全边界审查

### Findings

未发现真实 broker、quick-trade、orders、target-position、target-weight、monitor write、provider publish/refresh、accepted latest switching。

### Network Audit

S1B0 为本地只读诊断，未涉及前端/API/E2E，未要求 network audit。

### Text / Agent Semantics

报告中的“训练、score、买卖、仓位、收益”等词均为研究设计、禁止事项或历史回放语境，不构成交易建议、收益承诺、胜率或上涨概率承诺。

### Verdict

只读安全边界通过。

## 6. 用户决策点

我建议先选 A。

### A：先做 S1B0R calendar/price trading-day 修复诊断，推荐

不急着降级 static universe。先确认低覆盖日期是否由 calendar/price 日期错配造成；如果修复后 dynamic universe 可行，再继续 S1B1。

### B：接受 dynamic universe 早期日期排除

直接允许后续以 `2017-01-01..2020-12-31` 作为 LTR train scored rows，并排除 selected count < 50 的异常日期。结论需注明日期排除，不是完整原始 qlib train 窗口。

### C：降级为 static accepted 150 research replay

可以更快推进，但结论必须降级为 `static_accepted_150_research_replay`，不能声称严格 PIT/as-of active universe，也不能证明全市场公平验证。

### D：停止 S1

判定 split-aligned data insufficient，不继续旧窗口公平验证。

## 7. 给执行者的暂停指令

执行者不得进入 S1B1 qlib fold 训练 / score 生成。若用户选择 A，下一步只做 S1B0R：calendar/price trading-day 修复诊断与 dynamic universe feasibility 重算。
