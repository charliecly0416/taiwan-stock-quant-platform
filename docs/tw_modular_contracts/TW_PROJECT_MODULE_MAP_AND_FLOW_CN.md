# 台股量化平台模块地图与链路串联说明

生成日期：2026-06-18

## 1. 文档目的

本文档给后续开发者快速理解当前项目：有哪些模块、各模块输入输出是什么、前端/API/日更/回放/模拟账户如何串起来，以及哪些旧研究产物仍被保留为可追溯资料。

本项目当前产品主线是只读研究与模拟账户，不是实盘交易系统。任何新增能力都必须遵守只读、安全和模块合同边界。

## 2. 当前核心产品口径

当前产品口径只保留两个重要模型：

| 角色 | model_id | 说明 |
| --- | --- | --- |
| Base Qlib | `e4_frozen_qlib_2018_2022` | 2018-2022 训练的 frozen qlib 底座 |
| Orthogonal LTR | `e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025` | 在 Base Qlib top50 内用 2023-2025 正交 LTR 重排 |

当前默认策略规则：

```text
top50_exit_one_worst_sell
```

当前产品 artifact registry：

```text
configs/tw_product_artifact_registry.yaml
```

后续开发者不得在代码里新增另一套默认模型、默认策略或核心路径常量。需要改默认口径时，先改 registry，再跑测试，再审查。

## 3. 关键 Registry 分工

| Registry | 作用 | 是否产品入口 |
| --- | --- | --- |
| `configs/tw_product_artifact_registry.yaml` | 当前产品模型、策略、核心 artifact 路径、重建源路径 | 是 |
| `configs/tw_modular_registry.yaml` | 模块合同、生产可选模型/策略、research/deprecated 策略分类 | 是 |
| `configs/tw_replay_window_policy.yaml` | 只读回放允许窗口、模型/策略选择、默认回放配置 | 是 |
| `configs/strategy_dependencies/*.yaml` | 每个策略允许消费哪些字段和能力 | 是 |
| `configs/data_source_registry.yaml` 等 M 系列 registry | 模块化模板/扩展地基 | 开发参考 |

新增模型、策略、数据源时，至少要判断是否需要更新前三个 registry。

## 4. 当前模块地图

### 4.1 数据与价格

主要职责：保存价格、成交、日更原始数据或标准化价格。

当前相关位置：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt
backend/scripts/update_tw_stock_daily.py
scripts/run_daily_tw_stock_auto_update.py
```

边界：

- 数据模块不得输出策略结论。
- 数据模块不得切换 provider accepted latest，除非用户明确授权。
- 价格进入回放时必须经过可得性检查，尤其是 next_open / next_close。

### 4.2 特征

当前严格 E4/YZ 使用的正交特征来自：

```text
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/normalized_feature_daily.csv
```

对应配置在：

```text
configs/tw_product_artifact_registry.yaml -> rebuild_sources.o2_pit_feature_daily
```

边界：

- 特征必须满足 `available_at <= signal_asof`。
- 特征不得包含未来收益、label、真实成交、持仓收益等字段。
- 策略不得直接读取特征文件，只能读标准 ModelSignalArtifact 或显式 extension。

### 4.3 模型与信号

当前产品信号位置：

```text
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/{signal_asof}/model_a/manifest.json
data_tw/artifacts/phase_yz/yz1_strict_e4_model_signals/{signal_asof}/model_b_yz2/manifest.json
```

当前统一上下文服务：

```text
backend/app/services/tw_stock_current_strategy_context.py
GET /api/tw-stock/current-strategy-context
```

Model A 输出 qlib top150/top50；Model B 只在 Model A top50 内做 LTR 重排。

边界：

- 模型只输出分数和排名，不输出买卖动作。
- LTR 不改变 qlib top50 的卖出边界，只改变 top50 内买入排序。
- 任何新模型必须先转成 ModelSignalArtifact。

### 4.4 策略决策

策略只消费：

```text
ModelSignalArtifact
PortfolioState
StrategyRule / StrategyDependency
```

策略输出：

```text
OrderIntentArtifact
```

当前生产可选策略只有：

```text
top50_exit_one_worst_sell
```

边界：

- 策略不得读模型私有文件。
- 策略不得读 future return、label、回放收益。
- 策略不得输出真实订单，只能输出只读/模拟 order intent。

### 4.5 回放

回放消费：

```text
OrderIntentArtifact
PriceStore / price source
ExecutionConfig
InitialPortfolioState
```

回放输出：

```text
ReplayResultArtifact
ReadonlyReplayWindow
```

当前 API：

```text
GET /api/tw-stock/readonly-replay-window
GET /api/tw-stock/readonly-replay-window-index
```

边界：

- 回放不得反向修改策略动作。
- 回放不得根据收益改变模型分数或策略规则。
- 用户选择窗口时必须受 `configs/tw_replay_window_policy.yaml` 限制，不能回到训练集窗口做产品证据。

### 4.6 Readonly Snapshot

当前 snapshot latest：

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

当前 API：

```text
GET /api/tw-stock/readonly-strategy-snapshot
GET /api/tw-stock/readonly-strategy-snapshot/{asof}
```

边界：

- snapshot 是只读展示产物，不是 broker order，不是 target position。
- latest pointer 不是 provider accepted latest。
- 只有 validator 和 checksum 通过的 snapshot 才能作为当前展示。

### 4.7 Paper Portfolio / 模拟账户

当前模块：

```text
backend/app/services/tw_stock_paper_portfolio.py
scripts/build_tw_paper_portfolio_decision_artifact.py
```

模拟账户可以写入 simulation-only 表，但不得连接真实 broker。

边界：

- 只允许模拟账户 apply/reset。
- 不允许 real order、quick-trade、broker order。
- apply 前必须通过 registry/policy/model/strategy/epoch/checksum 校验。

### 4.8 前端

当前主页面：

```text
frontend/src/views/tw-stock-monitor/index.vue
```

前端应优先读取统一上下文：

```text
GET /api/tw-stock/current-strategy-context
```

然后按需要读取：

```text
readonly snapshot
readonly replay window
paper portfolio state / preview / apply
```

边界：

- 前端不得本地重算模型、策略、回放收益。
- 前端不得直接读实验 CSV。
- 前端不得暴露 deprecated/research-only 模型策略为普通用户选项。
- 页面展示要遵守用户第一性原则：简单、准确、清晰、实用。

### 4.9 日更与自动化

当前自动脚本：

```text
scripts/run_daily_tw_stock_auto_update.py
```

定位：调度、重试、状态记录、只读 snapshot publish gate。它不应该继续膨胀成抓取、特征、模型、策略、展示都写在一起的大脚本。

边界：

- 默认不触发 legacy provider publish / accepted latest。
- 只有数据、特征、模型、策略、snapshot validator 全通过，才允许更新只读 latest pointer。
- 失败必须保留 previous latest。

## 5. 功能如何串联模块

### 5.1 今日策略展示

```text
价格/特征 artifact
  -> frozen qlib score
  -> LTR rerank top50
  -> ModelSignalArtifact model_a/model_b
  -> current-strategy-context API
  -> frontend 策略上下文 / Top10 / Top50 展示
```

### 5.2 今日模拟决策

```text
current ModelSignalArtifact
  -> StrategyRule top50_exit_one_worst_sell
  -> OrderIntentArtifact
  -> PaperPortfolio preview
  -> 用户确认模拟 apply
  -> simulation-only tables
```

### 5.3 历史回放

```text
ModelSignalArtifact + StrategyRule + PriceStore + ExecutionConfig
  -> OrderIntent per day
  -> ReplayExecution
  -> ReplayResultArtifact
  -> ReadonlyReplayWindow API
  -> frontend 回放结果展示
```

### 5.4 每日自动更新

```text
两小时调度
  -> 数据可得性检查
  -> 数据更新/标准化
  -> 特征更新
  -> 模型信号生成
  -> 策略快照/只读 snapshot
  -> validators
  -> latest pointer update or keep previous latest
  -> frontend 读取最新只读上下文
```

## 6. 历史研究与归档规则

历史脚本归档位置：

```text
scripts/archive/historical_research/
```

历史实验数据归档位置：

```text
data_tw/experiments/archive/historical_research/
```

归档规则：

- 归档不代表删除研究证据。
- 归档脚本不得作为当前产品入口。
- 如果要恢复归档脚本，必须重新审查它是否符合当前 registry、合同和只读边界。

## 7. 当前开发者最低验证命令

```bash
python -m py_compile   backend/app/services/tw_stock_artifact_registry.py   backend/app/services/tw_stock_current_strategy_context.py   backend/app/services/phase_yz3_productization_status.py   backend/app/services/tw_stock_paper_portfolio.py   scripts/build_phase_yz2_orthogonal_package.py   scripts/build_tw_paper_portfolio_decision_artifact.py

PYTHONPATH=backend python -m pytest   backend/tests/test_phase_yz0_clean_registry.py   backend/tests/test_phase_yz1_strict_e4_model_adapters.py   backend/tests/test_phase_yz2_orthogonal_package.py   backend/tests/test_phase_yz3_productization_status.py   backend/tests/test_build_tw_paper_portfolio_decision_artifact.py   backend/tests/test_tw_stock_paper_portfolio_x2.py   backend/tests/test_tw_stock_paper_portfolio_x2r_api.py   backend/tests/test_tw_stock_readonly_replay_window_api.py   backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py -q

cd frontend && corepack pnpm build
```

## 8. 仍可优化的模块

当前项目已比之前清晰，但仍有后续优化空间：

1. 将 `frontend/src/views/tw-stock-monitor/index.vue` 拆成更小组件。
2. 将仍被当前重建链路引用的历史实验数据提升为正式 product artifact。
3. 将日更脚本进一步拆成 orchestrator + module steps。
4. 为新增模型、新增策略提供一键模板生成器。
5. 为 readonly snapshot 设计更稳定的 checksum 范围，避免旧快照因脚本归档而失效。
