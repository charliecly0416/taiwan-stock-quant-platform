# 面试展示交接归档

这份文档是给负责面试 PPT、讲稿和现场演示的智能体使用的单一入口。它描述当前应该展示什么、按什么顺序展示、每一步证明什么，以及哪些内容不能夸大。

## 一句话定位

这是一个面向台股研究者的只读量化研究工作台：它把有日期的数据、Model A 基线、Model A+B 研究候选、策略、历史回放、模拟账户和研究解释串成一个可追溯流程。它不是实盘交易系统，也不连接券商。

## 面试目标

面试官应该在 5 到 8 分钟内看懂三件事：

1. 用户能看见“这份结果是哪一天、来自什么模型和策略”。
2. Model A 与 Model A+B 可以在同一窗口比较，但研究候选不会绕过准入门槛替换 baseline。
3. 从数据到排名、策略意图、历史回放和展示都有清晰的合同和只读边界。

不要把重点放在算法名词堆叠上。重点是产品闭环、可追溯性、失败隔离和可扩展的模型轨道。

## 推荐现场顺序

### 1. 首屏：今日研究上下文

打开：`http://127.0.0.1:8000/#/tw-stock-monitor`

先指出四个信息：

- 模型日期和行情日期；
- 当前榜单和榜首标的；
- 数据链路状态；
- 页面顶部的只读研究声明。

讲稿可以说：

> 用户先看到日期和数据状态，再看排名。页面不会把旧数据伪装成今天的数据，也不会把研究排名直接变成交易指令。

对应代码：

- 页面：`frontend/src/views/tw-stock-monitor/index.vue`
- 当前上下文 API：`frontend/src/api/tw-stock-readonly.js`
- baseline 配置：`configs/active_baseline_descriptor.yaml`

### 2. 候选名单：Model A 的可解释输出

滚动到“候选名单”，展示候选调入、调出复核、信号日期和技术详情折叠区。

要强调：

- 这是 ModelSignal/Readonly Strategy Snapshot 的展示；
- 候选有来源日期和校验状态；
- Agent 不是排名计算器，只解释已经验证的 artifact。

对应组件：

`frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue`

### 3. 模型比较：Model A 与 Model A+B

在“模型与策略对比”中切换模型下拉框，展示 Model A 和 Model A+B 的同窗比较。

现场要展示：

- 净收益；
- 最大回撤；
- 费用/换手；
- 收益集中度；
- 弱市表现；
- Bootstrap 稳定性下界；
- A+B Top5 收益集中度。

讲稿要说清楚：

> Model A 是当前 active baseline。Model A+B 是冻结的研究 challenger。它可以在同一窗口展示比较结果，但本页的下拉选择只改变展示，不修改 baseline、latest 或模拟账户。

如果展示当前 B19R2R 结果，应直接说：

> A+B 在这段窗口的单项收益可能更高，但联合稳定性、弱市表现或集中度门槛没有通过，所以继续作为研究候选，不替换 Model A。

对应代码和配置：

- 组件：`frontend/src/views/tw-stock-monitor/components/ReadonlyModelStrategyComparisonPanel.vue`
- API：`/api/tw-stock/readonly/model-strategy-comparison`
- 模型轨道：`configs/readonly_model_tracks.yaml`
- 资格边界：`configs/tw_modular_registry.yaml`

### 4. 动态历史回放：真正串起统一任务入口

在“自定义历史回放”中展示模型、策略、开始日期、结束日期和“运行动态回放”。面试演示可以使用已验证窗口：

```text
模型：model_a_only
策略：top50_exit_one_worst_sell
请求区间：2026-01-01 至 2026-05-07
```

这一步证明回放不是固定写死的一张表，而是把用户选择传给统一的 `readonly_backtest` 任务，再轮询任务状态和读取 ReplayResult。

最近一次真实前端验收结果：

```text
状态：SUCCEEDED
实际窗口：2026-01-02 至 2026-05-07
净收益率：1.01%
最大回撤：-16.11%
期末资产：2,010,924.71
手续费/税费：48,531.66
交易动作：121（买 65 / 卖 56）
交易日：79
缺失价格：0
artifact：CANDIDATE_HOLD
```

必须说明：`CANDIDATE_HOLD` 是独立历史回放结果，不代表模型已经进入生产准入或模拟账户允许列表。

对应代码：

- 前端组件：`frontend/src/views/tw-stock-monitor/components/DynamicReadonlyReplayPanel.vue`
- 提交 API：`frontend/src/api/tw-stock-action.js`
- 选项/状态 API：`frontend/src/api/tw-stock-readonly.js`
- 后端路由：`backend/app/routes/tw_stock_dynamic_replay.py`
- 后端服务：`backend/app/services/tw_stock_dynamic_replay.py`
- 统一调度器：`tw_stock_workflow/task_dispatcher.py`

最近一次真实证据：

`tmp/dynamic_replay_acceptance/acceptance_fixed.json`

这份证据不应在 fresh checkout 中被承诺为一定存在，因为 `tmp/` 和市场数据是本机运行产物。PPT 可以使用上面的结果作为封存演示数据，并标注日期和只读性质。

### 5. 模拟账户：展示边界，不做交易

最后展示“模拟账户状态”面板，只说明：

- 它是 simulation-only；
- 应用/重置是独立确认流程；
- 当前面试演示不点击应用、重置、下单或券商相关入口；
- 没有模拟账户时，页面会显示空状态，不会把 404 当成前端崩溃。

对应组件：

`frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue`

### 6. Agent：解释研究结果

可以点击已有的“解释原因”或展示 Agent 区域，但讲稿要明确：

- Agent 消费验证后的 DailyAgentPromptArtifact 和研究上下文；
- 前端不直连 OpenAI；
- Agent 不能生成订单、目标仓位或券商动作；
- 解释失败不能清空已经加载的研究结果。

不要把 Agent 说成预测模型或自动交易员。

## 现场截图与验收证据

当前可用的截图和 JSON 证据位于本机 `tmp/`，适合面试前封存或导出：

- 正常 fixture：`tmp/product_fixture_acceptance/healthy_final/`
- 故障隔离 fixture：`tmp/product_fixture_acceptance/fault_final/`
- 真实本地前端三尺寸：`tmp/live_frontend_acceptance/`
- 动态回放真实点击：`tmp/dynamic_replay_acceptance/acceptance_fixed.json`

最近一次真实本地三尺寸验收结果：

```text
1440×980：核心面板存在，无横向溢出，无失败响应，无 console/page error
1024×768：核心面板存在，无横向溢出，无失败响应，无 console/page error
390×900：核心面板存在，无横向溢出，无失败响应，无 console/page error
```

fixture 验收还覆盖正常依赖和主动注入依赖失败两种状态。故障场景中的 503 是测试注入，不要说成线上故障。

## 产品架构讲法

用下面这条链解释代码和数据：

```text
数据来源
  -> PIT 特征/数据快照
  -> ModelTrack（Model A 或 Model A+B）
  -> ModelSignalArtifact
  -> StrategyRule
  -> OrderIntentArtifact
  -> ReplayResult
  -> Readonly API
  -> 前端工作台 / Agent 解释
```

Model A 和 Model A+B 在产品框架中都是 ModelTrack；差异由各自 adapter 和治理配置决定。A+B 内部如何使用 A 候选和 B 重排，封装在自己的 adapter 中，不要求前端重新组合模块。

## 必须诚实说明的限制

- 当前 active baseline 只有 Model A：`e4_frozen_qlib_2018_2022`。
- B19R2R 仍是 `production_allowed=false` 的研究 challenger。
- 产品是只读研究工作台和模拟账户，不是实盘交易系统。
- fixture 截图是封存演示数据，不证明实时行情新鲜度。
- 冻结模型和部分市场数据不在 git 中；fresh checkout 需要额外供应本机资产才能复现真实结果。
- 后端仍有渐进迁移中的大入口和 legacy route 委托，应该说“合同边界清晰、持续解耦中”，不要说“所有代码已经完全解耦”。
- 目前没有证明多机器高可用、自动收益结算闭环或长期无人值守生产稳定性。

## 不要展示或不要触发

- provider refresh/publish；
- accepted latest 或 controlled latest 切换；
- 真实数据抓取和模型训练；
- monitor 保存配置或手动 scan；
- 模拟账户 apply/reset；
- broker、quick-trade、order 相关入口；
- 在浏览器端直接调用 OpenAI。

## 给讲稿智能体的输出要求

生成 PPT 或讲稿时，请按“用户问题 -> 页面证据 -> 后端合同 -> 工程取舍”的顺序写。每个页面最多讲一个核心观点，数字必须带日期、窗口和只读/封存说明。不要只写“用了 LightGBM、Qlib、Agent”，要说明它们在数据流中的位置和为什么不会绕过治理门槛。

推荐 PPT 页序：

1. 产品问题和用户工作流；
2. 首屏日期、数据状态和候选；
3. Model A / Model A+B 同窗比较；
4. 动态历史回放和指标；
5. 模块合同与统一任务入口；
6. 只读边界、失败隔离和可维护性；
7. 当前限制与后续工作。

更详细的产品说明见 `docs/INTERVIEW_DEMO_CN.md`；架构和数据流见 `docs/tw_modular_contracts/TW_PROJECT_MODULE_MAP_AND_FLOW_CN.md` 与 `docs/tw_modular_contracts/TW_BACKEND_CODE_FRAMEWORK_CN.md`。
