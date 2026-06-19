# 台湾股票策略决策与回放解耦工作文档

生成日期：2026-06-16

## 1. 目标

本文件定义下一步必须完成的工程拆分：

```text
StrategyDecisionEngine
  -> OrderIntentArtifact
  -> ReplayExecutionEngine
  -> ReplayResultArtifact
```

目标不是新增一个更复杂的展示页，而是把“决定今天买什么/卖什么”和“计算回放收益”拆成两个独立模块。之后新增策略时，只需要补决策模块，不应再改回放引擎主体。

同时，本主线后续需要把两个标准产物接入只读 API / 前端：

```text
OrderIntentArtifact -> 前端展示当天具体策略意图
ReplayResultArtifact -> 前端展示受控窗口回放结果
```

前端只展示标准产物，不计算策略、不计算回放、不绕过 OOS 窗口限制。

## 2. 现状问题

当前系统已有：

- `ModelSignalArtifact`；
- `StrategyRuleContract`；
- `OrderIntentArtifact` 合同；
- `ReplayResultArtifact` 合同；
- 五种冻结规则；
- 现有回放脚本中的 `choose_sells()` / `replay_strategy()` 实现。

但当前实现仍把两件事混在同一个回放脚本里：

1. 根据信号和持仓决定卖什么、买什么；
2. 根据次日价格执行、记账并计算净值。

这会导致：

- 新增策略时要改回放脚本；
- 决策逻辑和回放记账耦合；
- replay 结果被误当成策略输入；
- 未来若支持多卖、多买、部分卖出、权重控制，需要改动大范围代码。

## 3. 分层定义

标准链路必须变成：

```text
ModelSignalArtifact
  -> StrategyDecisionEngine
  -> OrderIntentArtifact
  -> ReplayExecutionEngine
  -> ReplayResultArtifact
  -> Readonly API / Frontend Display
```

### 3.1 StrategyDecisionEngine

职责：

- 读取标准信号；
- 读取当前组合状态；
- 读取策略配置；
- 输出“今天的买卖意图”；
- 不计算成交、不算收益、不记账。

标准输入：

```text
ModelSignalArtifact
PortfolioState
StrategyRuleConfig
```

标准输出：

```text
OrderIntentArtifact
```

### 3.2 ReplayExecutionEngine

职责：

- 读取订单意图；
- 读取价格；
- 处理 next-day execution；
- 处理手续费、税费、现金、持仓；
- 计算 daily nav / return / drawdown / turnover。

标准输入：

```text
OrderIntentArtifact
PriceStore
ExecutionConfig
InitialPortfolioState
```

标准输出：

```text
ReplayResultArtifact
```

### 3.3 Readonly API / Frontend Display

职责：

- 读取 `OrderIntentArtifact` 展示当天具体策略意图；
- 读取 `ReplayResultArtifact` 展示回放收益、回撤、手续费、交易次数等；
- 提供策略下拉框和回放窗口选择；
- 不做策略计算；
- 不做回放计算；
- 不触发训练、调参、provider publish、accepted latest、monitor、broker、quick-trade、order。

前端必须符合用户第一性原则：

- 简单：默认展示主策略，复杂对照折叠；
- 准确：清楚标注模型、策略、日期、窗口、OOS 约束；
- 清晰：买卖意图、回放指标、费用风险分区展示；
- 实用：用户能直接看懂今天策略意图和指定窗口历史表现。

## 4. 第一批迁移对象

第一批只迁移当前五种冻结规则：

- `original`
- `top50_exit_all`
- `top50_exit_one_worst_sell`
- `one_sell_one_buy_correct`
- `one_sell_one_buy_buggy_e8r`

其中 `one_sell_one_buy_buggy_e8r` 只能作为 diagnostic 迁移对象，不得作为产品化策略证据。

## 5. 输入输出合同

### 5.1 决策模块输入

决策模块必须直接读取标准 `ModelSignalArtifact`，不能只依赖 readonly snapshot 的展示字段。

最低要求：

- `date`
- `instrument`
- `candidate_rank`
- `buy_score`
- `score_rank`
- `full_qlib_rank`
- `signal_asof`
- `available_at`

同时必须读取：

- `PortfolioState`
- `StrategyRuleConfig`

### 5.2 决策模块输出

输出必须是 `OrderIntentArtifact`，至少包含：

- `signal_date`
- `instrument`
- `intent_action`
- `intent_reason`
- `strategy_rule`
- `candidate_rank`
- `buy_rank`
- `full_qlib_rank`
- `max_buy_count`
- `max_sell_count`
- `model_name`
- `signal_artifact`

不得输出：

- 成交价；
- 成交日期；
- 手续费；
- 税费；
- 现金；
- 净值；
- broker 订单编号。

### 5.3 回放模块输入

回放模块只消费：

- `OrderIntentArtifact`
- `PriceStore`
- `ExecutionConfig`
- `InitialPortfolioState`

### 5.4 回放模块输出

回放模块只输出：

- `summary.csv`
- `actions.csv`
- `daily_nav.csv`
- `position_snapshots.csv`
- `coverage_audit.csv`
- `position_integrity_audit.csv`
- `forbidden_field_audit.csv`
- `execution_audit.csv`

### 5.5 前端决策展示输入

前端展示当天具体策略结果时，只能读取 `OrderIntentArtifact` 或其 API 包装，不得直接读取模型私有文件、回放中间状态或自行计算策略。

前端展示字段建议：

```text
signal_date
strategy_rule
model_name
intent_action
instrument
intent_reason
candidate_rank
buy_rank
full_qlib_rank
diagnostic_only
readonly_only
not_order
```

前端文案必须使用：

```text
候选买入
候选卖出
继续观察
跳过
只读策略意图
```

不得使用：

```text
下单
买入指令
卖出指令
目标仓位
自动交易
一键交易
保证收益
胜率承诺
```

### 5.6 前端回放展示输入

前端展示回放时，只能读取 `ReplayResultArtifact` 或其 API 包装，不得在浏览器端自行回放。

前端展示字段建议：

```text
strategy_rule
model_name
start_date
end_date
total_return
max_drawdown
action_count
buy_count
sell_count
commission
tax
fee_and_tax
turnover
skipped_action_count
coverage_status
position_integrity_status
diagnostic_only
```

回放窗口选择必须由后端 validator 校验，不得只靠前端控件限制。

## 6. 模块化目录建议

建议新增目录：

```text
data_tw/artifacts/order_intents/{strategy_rule}/{run_id}/
data_tw/artifacts/replays/{replay_name}/{run_id}/
```

### 6.1 OrderIntentArtifact

建议文件：

```text
manifest.json
order_intents.csv
schema.json
strategy_decision_audit.csv
forbidden_action_audit.json
```

### 6.2 ReplayResultArtifact

沿用既有合同目录与结构，不再从策略脚本内部读取决策细节。

## 7. 决策规则实现要求

五种规则必须先实现成独立决策函数，而不是写在回放记账循环里。

建议形态：

```text
decide_original(...)
decide_top50_exit_all(...)
decide_top50_exit_one_worst_sell(...)
decide_one_sell_one_buy_correct(...)
decide_one_sell_one_buy_buggy_e8r(...)
```

每个函数只做：

- 读取当天信号；
- 读取当前持仓；
- 返回当日意图列表。

不做：

- 价格执行；
- 现金记账；
- 收益计算；
- 净值计算。

## 8. 决策规则与回放的依赖关系

### 8.1 决策可以依赖的字段

决策模块可以依赖：

- `candidate_rank`
- `buy_score`
- `score_rank`
- `full_qlib_rank`
- `signal_asof`
- `available_at`
- `PortfolioState`

### 8.2 决策不得依赖的字段

决策模块不得依赖：

- `future_return_*`
- `label_*`
- `relevance_10d_top_heavy`
- `realized_pnl`
- `execution_price`
- `execution_date`
- `equity`
- `cash`
- `drawdown`
- `broker_order_id`

### 8.3 回放不得反向参与决策

回放模块不得：

- 因收益高低改写策略；
- 因净值变化改写意图；
- 因实际成交改写排序；
- 因某策略表现好自动成为默认。

### 8.4 OOS 回放窗口约束

任何前端可选回放窗口必须通过后端 `ReplayWindowPolicy` 校验。

最低要求：

- 不得允许回放窗口进入该模型或 LTR 的训练区间；
- 不得允许用户选择训练集收益作为策略优劣证据；
- 不得只用前端控件限制日期，必须由 API / validator 拒绝非法窗口；
- 每个模型必须登记 allowed replay windows。

示例：

```text
model_id: e4_frozen_qlib_2023_2025_ltr
qlib_train_window: 2018-01-01..2022-12-31
ltr_train_window: 2023-01-01..2025-12-31
allowed_replay_start_min: 2026-01-01
allowed_replay_end_max: latest_available_signal_date
```

如果未来新增模型，必须先登记训练窗口和允许回放窗口，再允许前端选择。

## 9. 迁移分阶段建议

### Phase D0：合同冻结与可行性审计

目标：

- 确认现有五种规则都能被 `OrderIntentArtifact` 表达；
- 确认 `ModelSignalArtifact` 已足够作为决策输入；
- 确认回放只需消费意图即可复现现有结果；
- 确认 readonly snapshot 只做展示，不作为 canonical 决策输入。

输出：

```text
docs/tw_modular_contracts/PHASED0_DECISION_REPLAY_DECOUPLING_WORK_CN.md
docs/tw_modular_contracts/PHASED0_DECISION_REPLAY_DECOUPLING_EXECUTION_REPORT_CN.md
```

### Phase D1：抽出 StrategyDecisionEngine

目标：

- 把 `choose_sells()` / `buy_order` 逻辑从 replay 脚本中移出；
- 生成独立 `OrderIntentArtifact`；
- 保持五种规则的意图语义不变。

输出：

```text
scripts/build_tw_modular_order_intent_artifact.py
scripts/validate_tw_modular_order_intent_artifact.py
```

### Phase D2：回放引擎只吃 OrderIntent

目标：

- 回放脚本不再直接知道五种规则的卖买细节；
- 只根据 `OrderIntentArtifact` 执行；
- 保持 next-day accounting、费用、税费、持仓、净值逻辑不变。

### Phase D3：五规则 parity

目标：

- 对五种规则做回放 parity；
- 与旧回放结果逐日对齐；
- 证明拆分后没有改变语义。

### Phase D4：只读决策 API / 前端展示

目标：

- 新增只读 API，读取 `OrderIntentArtifact`；
- 前端支持策略下拉选择；
- 选择策略后展示当天具体候选买入、候选卖出、继续观察、跳过；
- 前端不计算策略，只展示标准意图产物；
- 禁止交易、目标仓位、broker、quick-trade、order 语义。

必须支持：

```text
strategy_rule dropdown
signal_date / latest
model_name
candidate buy/sell/hold/skip table
diagnostic_only warning
source manifest link
validation status
```

### Phase D5：只读回放 API / 前端展示

目标：

- 新增只读 API，读取或触发受控 `ReplayResultArtifact` 查询；
- 前端支持策略与回放时间段选择；
- 后端强制校验 OOS allowed window；
- 展示收益、回撤、交易次数、手续费、税费、跳过交易、覆盖审计；
- 前端不执行回放，只显示后端标准产物。

必须支持：

```text
model dropdown
strategy_rule dropdown
date range picker
OOS window validation
return / drawdown / fee / tax / turnover summary
daily nav chart
actions table
coverage / integrity audit status
```

### Phase D6：新增策略扩展

目标：

- 新规则只需新增决策函数与 dependency；
- 回放引擎不再因策略扩展而频繁修改。

## 10. 兼容 readonly snapshot 的关系

当前 readonly snapshot 只负责展示：

- 当日排名；
- 当前回放状态；
- 调入候选；
- 调出观察；
- 审计状态。

它不是决策模块的唯一输入。

正确做法是：

```text
readonly snapshot = 展示层
ModelSignalArtifact + PortfolioState + StrategyRuleConfig = 决策层
OrderIntentArtifact = 决策层输出
ReplayResultArtifact = 回放层输出
```

如果未来需要让 snapshot 也能直接驱动决策，必须另开 `DecisionSnapshot` 合同，不得把展示字段硬改成订单字段。

## 11. 通过标准

当且仅当以下条件全部满足，才允许认为策略/回放已真正解耦：

- 五种规则都能通过独立决策模块输出 `OrderIntentArtifact`；
- 回放引擎只读取 `OrderIntentArtifact`；
- 新增策略不需要修改回放引擎主体；
- parity 与旧结果一致；
- 决策模块不读取未来收益、不读取回放结果；
- readonly snapshot 不承担决策职责；
- 前端决策展示只读取 `OrderIntentArtifact`；
- 前端回放展示只读取 `ReplayResultArtifact`；
- 回放窗口由后端强制 OOS 校验，不能进入训练窗口。

## 12. 执行者 Prompt

请按：

```text
docs/tw_modular_contracts/TW_MODULAR_DECISION_REPLAY_DECOUPLING_WORK_CN.md
```

执行决策与回放解耦重构。

目标是把当前五种规则从回放脚本中抽成独立 `StrategyDecisionEngine`，生成 `OrderIntentArtifact`，再让 `ReplayExecutionEngine` 只消费 `OrderIntentArtifact` 和价格/执行配置。不得改变训练、数据、模型、默认策略、前端、API、provider publish、accepted latest、monitor、broker、quick-trade、order。

必须先做 D0 合同冻结与可行性审计，再进入 D1-D3。D1-D3 通过后，才能进入 D4/D5 的 API 与前端只读展示。每一阶段都要单独输出执行报告，且 D3 必须有 parity 证据。

执行完成后提交：

```text
docs/tw_modular_contracts/PHASED0_DECISION_REPLAY_DECOUPLING_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/PHASED1_STRATEGY_DECISION_ENGINE_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/PHASED2_REPLAY_ENGINE_DECOUPLING_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/PHASED3_DECISION_REPLAY_PARITY_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/PHASED4_DECISION_READONLY_FRONTEND_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/PHASED5_REPLAY_READONLY_FRONTEND_EXECUTION_REPORT_CN.md
```

## 13. 审查者 Prompt

请按以下顺序审查：

```text
PHASED0_DECISION_REPLAY_DECOUPLING_EXECUTION_REPORT_CN.md
PHASED1_STRATEGY_DECISION_ENGINE_EXECUTION_REPORT_CN.md
PHASED2_REPLAY_ENGINE_DECOUPLING_EXECUTION_REPORT_CN.md
PHASED3_DECISION_REPLAY_PARITY_EXECUTION_REPORT_CN.md
PHASED4_DECISION_READONLY_FRONTEND_EXECUTION_REPORT_CN.md
PHASED5_REPLAY_READONLY_FRONTEND_EXECUTION_REPORT_CN.md
```

重点确认：

- 决策模块是否真的只消费 `ModelSignalArtifact` + `PortfolioState` + `StrategyRuleConfig`；
- 回放模块是否真的只消费 `OrderIntentArtifact` + `PriceStore` + `ExecutionConfig` + `InitialPortfolioState`；
- 五种规则是否都被正确迁移；
- `one_sell_one_buy_buggy_e8r` 是否仍然只限 diagnostic；
- 是否没有把回放结果反向用作策略输入；
- 是否没有训练、调参、provider publish、accepted latest、monitor、broker、quick-trade、order 越界；
- parity 是否与旧回放一致；
- D4 前端是否只展示 `OrderIntentArtifact`，没有自己计算策略；
- D5 前端是否只展示 `ReplayResultArtifact`，没有自己执行回放；
- 回放窗口是否由后端强制 OOS 校验，尤其 E4 只能选择 2026 及之后允许窗口；
- 前端文案是否简单、准确、清晰、实用，并且没有交易/目标仓位语义。

如果发现策略仍直接嵌在回放主循环里、决策仍依赖 replay result、或新增策略仍需改回放记账主体，必须停止并要求修复，不得放行进入下一阶段。

如果发现前端绕过标准 artifact 自己计算买卖或回放，或者只靠前端限制训练窗口，必须停止并要求修复。
