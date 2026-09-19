# 台股量化平台后续开发宪法

生成日期：2026-06-19

本文是台股量化平台后续开发、审查和统筹的最高层规则。它不替代具体合同、runbook、字段字典或阶段总结；当需求、实现、实验报告、前端展示或日更脚本之间发生冲突时，本文用于判断什么可以继续、什么必须停止。

## 1. 项目身份

当前台股主线是：

```text
只读研究 + 产品化候选展示 + 模拟账户
```

它不是：

```text
实盘交易系统
自动下单系统
收益承诺系统
一个实验一个脚本的研究仓库
```

所有开发必须服务于一个目标：让数据、模型、策略、回放、API、前端和模拟账户以可审查、可复现、可回滚的方式协同工作。

## 2. 当前产品主线

当前 active baseline：

```text
e4_frozen_qlib_2018_2022
```

当前研究 challenger 是 `modelb_b19r2r_lambdarank_exact50_78f_v2`。它只在 Model A 同日 Top50 内重排，保持 `production_allowed=false`，只能进入只读比较、prospective shadow 和审查报告。旧 `e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025` 是 legacy research artifact，不是当前 challenger 或默认模型。

当前默认策略规则：

```text
top50_exit_one_worst_sell
```

产品默认模型、默认策略、核心 artifact 路径和安全配置必须来自：

```text
configs/active_baseline_descriptor.yaml
configs/tw_product_artifact_registry.yaml
configs/tw_modular_registry.yaml
configs/tw_replay_window_policy.yaml
```

baseline/default 身份以 `active_baseline_descriptor.yaml` 为准；模块准入和 consumer 边界以 `tw_modular_registry.yaml` 为准；live 是否可用以 `/api/ready` 和只读运维 API 为准。旧阶段文档与兼容路径不得覆盖这些事实。

不得在前端、API、脚本或测试中重新硬编码另一套产品默认口径。确实需要改变默认模型、默认策略或核心路径时，必须先改 registry，再补 validator/test，再审查放行。

## 3. 不可破坏的模块边界

标准链路是：

```text
DataSource / PriceStore / FeatureArtifact
  -> Model / ModelAdapter
  -> ModelSignalArtifact
  -> StrategyRule
  -> OrderIntentArtifact
  -> ReplayExecution
  -> ReplayResultArtifact
  -> Readonly Artifact / API / Frontend / PaperPortfolio
```

各模块只能消费上游标准产物，不得跨层读取私有文件。

| 模块 | 只能做什么 | 不得做什么 |
| --- | --- | --- |
| 数据源/日更 | 产生标准化数据、readiness、manifest | 输出策略结论、切 accepted latest、连接 broker |
| 特征 | 产生 PIT-safe FeatureArtifact | 包含未来收益、label、真实成交、持仓收益 |
| 模型 | 读取标准输入并输出 raw score 或模型产物 | 直接输出买卖动作 |
| ModelAdapter | 输出 ModelSignalArtifact | 训练、调参、按收益筛选 |
| 策略 | 读取 ModelSignalArtifact 和 PortfolioState，输出 OrderIntentArtifact | 读取模型私有 CSV、未来价格、回放收益、broker 状态 |
| 回放 | 读取 OrderIntent/PriceStore/ExecutionConfig，输出 ReplayResultArtifact | 反向修改信号、策略或模型 |
| Readonly API/前端 | 展示标准 artifact 和上下文 | 直读实验 CSV、本地重算策略、承诺收益 |
| PaperPortfolio | 写 simulation-only 账户状态 | 连接真实 broker、提交真实订单、触发 quick-trade |

如果一个需求无法落入这些模块之一，必须先新增合同和 validator，而不是先写实现。

## 4. 开发顺序

后续任何新增数据源、特征、模型、策略、回放、前端展示、日更能力或模拟账户行为，都必须按以下顺序推进：

```text
定义模块归属
  -> 定义输入/输出合同
  -> 更新 registry/dependency/policy
  -> 生成标准 artifact
  -> 运行 validator/golden sample/test
  -> 编写审查报告或执行说明
  -> 只读 API/前端接入
  -> 必要时进入模拟账户
```

禁止反向流程：

```text
先写脚本跑结果
  -> 按收益挑一个结果
  -> 改前端默认展示
  -> 最后补文档
```

实验可以存在，但实验结果不能绕过合同、registry、validator 和审查进入产品主线。

## 5. 只读与交易安全红线

除非用户在独立任务中明确要求并经过专项设计，台股主线默认禁止：

```text
provider publish
provider accepted latest switch
qlib accepted latest switch
monitor scan / config save / alerts write
broker connection
quick-trade
real order
target position instruction
自动实盘执行
```

允许的写入范围仅限：

```text
simulation-only paper account
readonly artifact
job artifact
validator/audit/report artifact
```

任何 API、前端按钮、Agent 输出、日更脚本或测试夹具，只要可能被理解为真实买卖指令、目标仓位、券商订单或收益承诺，都必须重写或阻断。

## 6. PIT 与时间边界

所有数据、特征、模型和回放必须显式说明：

```text
asof
signal_asof
available_at
训练窗口
验证窗口
回放窗口
执行价口径
```

硬性规则：

- `available_at` 不得晚于可用决策时间。
- 特征不得包含 future return、forward return、label、realized pnl、未来成交或未来持仓。
- 训练窗口、LTR 训练窗口、回放窗口不得混用。
- 不得在训练集窗口上证明产品策略有效。
- execution price 缺失时不得 fallback 到 next_close、signal close、0、空值、上一日价格或手写价格。
- 当前产品执行价口径为 `next_open`，缺失时必须进入 pending/block 状态。

## 7. ModelSignal 是策略唯一入口

策略不得直接读取模型私有产物。任何模型进入策略前，必须转成 `ModelSignalArtifact`。

核心字段语义不得被改写：

```text
candidate_rank
buy_score
raw_score
score_rank
full_qlib_rank
signal_asof
available_at
source_artifact
source_model_artifact
source_feature_artifact
```

当前 LTR 语义：

```text
Qlib top50 定义候选与卖出边界
LTR 只在 Qlib top50 内重排买入顺序
LTR 不改变 Qlib top50 的退出边界
```

如果新模型希望改变 universe、sell boundary、多 horizon 决策或风险口径，必须新增合同版本并单独审查，不能复用当前字段语义偷渡。

## 8. 策略必须先有 dependency

新增策略前，必须先写：

```text
configs/strategy_dependencies/{strategy_rule}.yaml
```

dependency 至少声明：

```text
required_core_fields
required_capabilities
required_extensions
ranking_usage
max_buy_count
max_sell_count
forbidden_fields
forbidden_actions
diagnostic_only / research_only / production_default
```

策略输出只能是：

```text
OrderIntentArtifact
```

不得输出真实订单、目标仓位、broker id、真实成交价或未来价格。

## 9. API 与前端原则

前端优先读取统一上下文：

```text
GET /api/tw-stock/current-strategy-context
```

然后按需要读取：

```text
GET /api/tw-stock/readonly-strategy-snapshot
GET /api/tw-stock/readonly-replay-window
GET /api/tw-stock/readonly-replay-window-index
GET /api/tw-stock/paper-portfolio/latest-decision
GET /api/tw-stock/paper-portfolio/state
```

前端不得：

- 直接读取实验 CSV 或本地 artifact 文件。
- 本地重算模型、策略或回放收益。
- 把 research-only/deprecated 模型策略暴露为普通默认选项。
- 把 top10/top50 展示文案写成买入建议。
- 在行情 pending 时展示 realized return 或允许 paper apply。

前端必须：

- 明确 readonly、not order、not target position、not investment advice。
- 展示 pending/block 原因。
- 使用 API 返回的模型、策略、asof、execution_price_mode、checksum 和 validation 状态。
- 对模拟账户 apply/reset 使用二次确认和服务端 artifact authority。

## 10. 日更编排原则

日更脚本是 orchestrator，不是业务逻辑容器。

推荐链路：

```text
DataSource refresh
  -> DataReadinessGate
  -> FeatureArtifact refresh
  -> Model A Qlib signal
  -> Model B LTR rerank signal
  -> StrategyRule
  -> OrderIntentArtifact
  -> ReadonlyStrategySnapshot
  -> CurrentStrategyContext API
  -> Frontend / PaperPortfolio
```

日更默认不得：

- 训练模型或调参。
- 自动切换默认模型或默认策略。
- 自动切换 accepted latest。
- 自动发布 legacy provider。
- 静默吞掉数据缺失并继续生成可交易结果。

失败时必须保留 previous latest，记录 pending asof、失败原因、job artifact 和 validator 状态。

## 11. 审查放行规则

执行报告或 PR 只有同时满足以下条件，才可以进入下一步：

- 模块归属清楚。
- 输入/输出 artifact 合同清楚。
- registry/dependency/policy 已同步。
- PIT/available_at/训练窗口/回放窗口通过检查。
- validator/golden sample/test 通过或明确解释跳过原因。
- 不触发安全红线。
- 前端/API 不暴露旧默认、research-only 或 deprecated 路径。
- 对用户展示不构成收益承诺、买卖建议或真实订单。

以下情况必须停止并沟通：

- 默认模型或默认策略被代码私自切换。
- 策略读取模型私有文件或回放收益。
- 训练/验证/回放窗口混用。
- future return、label、realized pnl 进入特征或策略。
- next_open 缺失时使用 fallback 成交价。
- 日更脚本触发 accepted latest、provider publish、monitor 写入或 broker/order。
- 前端请求旧模型 detail 或展示 deprecated/research-only 选项为默认路径。
- paper apply 接受裸 payload 而不校验服务端 artifact/checksum/epoch。

## 12. 文档优先级

日常开发和审查按以下优先级阅读：

1. 本文档：`TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
2. 项目入口与归档政策：`TW_CURRENT_PROJECT_DOC_ENTRY_AND_ARCHIVE_POLICY_CN.md`
3. 模块地图：`TW_PROJECT_MODULE_MAP_AND_FLOW_CN.md`
4. 未来开发规范：`TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md`
5. 开发测试手册：`TW_DEVELOPER_TEST_AND_EXPERIMENT_PLAYBOOK_CN.md`
6. 当前策略上下文字段字典：`TW_CURRENT_STRATEGY_CONTEXT_API_FIELD_DICTIONARY_CN.md`
7. 日更 runbook：`TW_DAILY_AUTO_UPDATE_RUNBOOK_CN.md`
8. 当前路线最终总结与 checklist
9. 归档历史文档，仅用于追溯历史争议

如果本文与具体合同冲突：

- 安全边界、模块边界、开发顺序以本文为准。
- 字段级 schema、validator 参数和 API 细节以具体合同为准。
- 若冲突影响产品默认口径或安全边界，必须先修正文档，再继续开发。

## 13. 最小只读验证基线

进入新开发前，建议先确认当前基线可用：

```bash
python -m pytest backend/tests/test_phase_yz0_clean_registry.py backend/tests/test_phase_yz1_strict_e4_model_adapters.py backend/tests/test_phase_yz2_orthogonal_package.py backend/tests/test_phase_yz3_productization_status.py backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py backend/tests/test_tw_stock_readonly_replay_window_api.py backend/tests/test_tw_ltr_readonly_explanation_api.py -q

cd frontend
corepack pnpm build
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
node tests/unit/tw-stock-readonly-replay-window-check.mjs
```

完整页面 E2E 可以作为补充，但必须确认它不产生写入、不下单、不切 accepted latest。

## 14. 统筹者最终判断

后续统筹者不应只问“这个功能能不能跑”，而应先问：

```text
它属于哪个模块？
它消费了哪个标准 artifact？
它输出了哪个标准 artifact？
它是否改变默认产品口径？
它是否破坏只读/模拟边界？
它是否能被 validator 和审查复现？
```

如果这些问题没有清楚答案，开发不应继续进入产品链路。
