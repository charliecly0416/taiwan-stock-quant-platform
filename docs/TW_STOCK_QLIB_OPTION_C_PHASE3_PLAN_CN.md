---
created_at: 2026-06-02
status: phase_plan
scope: quantdinger_tw_stock_qlib_option_c_phase3_sustainable_daily_refresh
role_target: reviewer_and_executor
reviewer: codex_reviewer
backend_project: /path/to/taiwan-stock-quant-platform
frontend_project: /path/to/taiwan-stock-quant-platform-Vue
qlib_project: /home/chuliyang/qlib
---

# qlib Option C 台股研究信号 Phase 3 总体规划

Phase 3 的目标是把 qlib Option C 从“QuantDinger 只读消费已有 artifact”推进到“可持续的日更研究信号生产链路”。

用户期望：市场收盘后，如果有新的台股数据，系统可以像 QuantDinger 原有数据一样定期拉取新数据，并在数据更新后自动完成后续 qlib 研究分析，让 QuantDinger 展示新的研究排序。

Phase 3 不是交易自动化。它只允许自动化数据更新和研究信号生产，不允许自动下单、自动调仓、broker、quick-trade、paper/live order。

---

## 1. Phase 3 主线

Phase 3 主线：

```text
新市场数据可用
-> 受控拉取/更新台股数据
-> 受控刷新或重建 qlib provider
-> 运行 Option C daily signal dry-run
-> dry-run 通过后运行 normal signal
-> 产出 accepted / wait-state / blocked artifact
-> QuantDinger 继续只读展示 latest / history / health
```

核心原则：

- 自动化的是“研究数据生产链路”，不是交易链路。
- qlib score 仍然只是横截面研究排序，不是收益率、胜率、涨幅、买入概率或仓位。
- 自动流程必须可审计、可回放、可停止、可查看失败原因。
- 任何失败都只能进入 wait-state / blocked / stale 状态，不能绕过校验发布信号。

---

## 2. Phase 3 和 Phase 2 的边界变化

Phase 2 明确禁止：

```text
provider refresh
qlib signal generation
自动补数据
```

Phase 3 的边界调整为：

```text
允许在受控调度任务中执行数据更新、provider refresh/rebuild、daily signal generation。
```

但仍然禁止：

```text
自动交易
自动下单
broker 连接
quick-trade
paper/live order
生成 target position / target weight
模型重训
模型调参
切换 universe
切换模型 recorder
切换 FinMind fallback 或混合数据源
把 qlib score 合成为买入分
```

如需模型重训、universe 扩展、多数据源融合或交易接入，必须另开研究主线，不属于 Phase 3。

---

## 3. 建议阶段拆分

### Step 1：日更链路盘点和手动可复现验收

目标：

- 找出 qlib 侧真实可用的数据更新、provider 生成、daily signal 命令。
- 明确哪些命令会写数据，哪些命令只读。
- 用手动命令跑出完整链路证据。
- 建立自动化前的 allowlist、锁、日志、回滚和失败状态设计。

验收后才能进入 Step 2。

### Step 2：后端受控任务 runner

目标：

- QuantDinger 后端新增只允许固定命令的 qlib ops runner。
- 支持手动触发 preflight / dry-run / normal signal。
- 支持任务锁、超时、日志、状态查询。
- 默认关闭定时任务。

不得在 Step 2 直接启用无人值守自动刷新。

### Step 3：数据更新和 provider refresh 受控接入

目标：

- 在 runner 中接入已验收的数据更新/provider refresh 命令。
- 只允许 Yahoo-only、固定 universe、固定 provider path。
- refresh 后必须做数据覆盖、日期连续性、row count、symbol coverage、NaN/finite 检查。
- 失败时只写 ops 状态，不发布 accepted signal。

### Step 4：收盘后定时调度

目标：

- 增加可配置 schedule，例如台股收盘后延迟执行。
- 自动流程顺序必须固定：

```text
数据更新 -> provider validation -> signal dry-run -> normal signal -> artifact validation -> health refresh
```

- 支持环境变量关闭。
- 支持同一天幂等，不重复发布相同 asof。

### Step 5：前端运维状态页

目标：

- QuantDinger 前端展示 qlib ops job 状态。
- 展示最近任务、日志摘要、失败原因、latest accepted asof、wait-state。
- 提供手动触发按钮时必须有明确“研究数据更新，不是交易”提示。
- 不提供任何交易按钮。

### Step 6：Phase 3 完整仿真和收尾验收

目标：

- 覆盖新数据可用、新数据缺失、provider refresh 失败、dry-run 失败、normal signal accepted、blocked、重复 asof、任务锁冲突等场景。
- Playwright 验证前端状态。
- 后端验证任务状态、日志、幂等、安全边界。

---

## 4. Phase 3 成功标准

Phase 3 完成后，应达到：

- 每个交易日收盘后可以自动或手动受控更新 qlib 数据。
- 新数据通过校验后可以自动生成 Option C daily signal artifact。
- accepted artifact 自动成为 QuantDinger latest 展示对象。
- wait-state/blocked/missing/stale 都有清楚状态。
- 所有任务有日志、状态、耗时、命令、返回码、输出摘要。
- 任务失败不会发布错误信号。
- 任务重复运行不会破坏已有 accepted artifact。
- 全流程仍然没有交易能力。

---

## 5. Phase 3 第一审核断点

第一份执行文档：

```text
docs/TW_STOCK_QLIB_OPTION_C_PHASE3_STEP1_EXECUTION_CN.md
```

执行者完成后必须提交：

```text
docs/TW_STOCK_QLIB_OPTION_C_PHASE3_STEP1_REPORT_CN.md
```

审核者重点判断：

- 是否真的找到了 qlib 侧可复现日更命令。
- 是否明确区分了数据更新、provider refresh、daily signal generation。
- 是否有足够证据证明链路可持续。
- 是否存在越界：交易、重训、调参、切数据源、扩 universe。
- 是否可以进入 Step 2 的受控 runner 实现。

